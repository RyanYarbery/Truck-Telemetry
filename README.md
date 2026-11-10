# Truck Telemetry

A gauge dashboard for a 2001 Ford F-350 with the 7.3L Power Stroke diesel. A Raspberry Pi Zero 2 W
reads engine data from the truck's OBD-II port through a Vgate vLinker FS Bluetooth adapter and
draws it on a 1024x600 screen in the cab: RPM, speed, injection control pressure, oil and fuel
temperatures, boost, battery voltage, fuel flow and trip MPG. This repository holds a
copy of the Pi's software, the circuit that lets the Pi shut down when the key is turned off, and
the notes from building it.

There are no photos in the repository. The circuit diagrams are text drawings in
`REVISED-CIRCUIT.md`.

## Hardware

- 2001 Ford F-350, 7.3L Power Stroke (OBD-II over SAE J1850 PWM, not CAN)
- Raspberry Pi Zero 2 W running Raspberry Pi OS
- Vgate vLinker FS OBD adapter, paired with the Pi over Bluetooth
- Waveshare 7" HDMI display, 1024x600
- 12 V to 5 V converter on constant battery power
- Ignition-sense board on GPIO17 (one RFP30N06LE MOSFET, a 1N5408 diode, a 1.5KE18A TVS diode and
  resistors), fed from passenger-compartment fuse 27 through an add-a-circuit fuse tap

## How it works

Four services run on the Pi:

| Service | What it does |
|---------|--------------|
| `vlinker-rfcomm` | Connects the vLinker as `/dev/rfcomm0` |
| `truck-telemetry` | Polls the PCM through the vLinker, writes live values to `/run/truck-telemetry/live.json` and saves trip totals to `/var/lib/truck-telemetry/trip.json` |
| `truck-dashboard` | Draws the gauges full screen with pygame (SDL on KMS/DRM, no desktop) |
| `truck-ignition` | Powers the Pi off after 45 s of key OFF; turning the key back on cancels it |

`pi/captures/` has two sample readings (key on engine off, and idling) that show every value
`telemetry.py` reports.

## Install

On a Raspberry Pi OS image with Python 3:

```bash
sudo apt install python3-serial python3-pygame bluez
sudo mkdir -p /opt/truck-telemetry /opt/truck-dashboard /opt/truck-ignition
sudo cp pi/opt/truck-telemetry/telemetry.py     /opt/truck-telemetry/
sudo cp pi/opt/truck-dashboard/dashboard.py     /opt/truck-dashboard/
sudo cp pi/opt/truck-ignition/ignition_watch.py /opt/truck-ignition/
sudo cp pi/systemd/*.service /etc/systemd/system/
sudo cp pi/systemd/vlinker-rfcomm.env.example /etc/default/vlinker-rfcomm   # then set VLINKER_MAC
sudo systemctl daemon-reload
sudo systemctl enable --now vlinker-rfcomm truck-telemetry truck-dashboard truck-ignition
```

Pair the vLinker first (`bluetoothctl`, then `pair` and `trust` its address).

Useful commands on the Pi:

```bash
python3 /opt/truck-telemetry/telemetry.py --show-trip           # saved trip totals
python3 /opt/truck-telemetry/telemetry.py --reset-trip
python3 /opt/truck-telemetry/telemetry.py --set-calibration 1.05 # fuel calibration factor
sudo systemctl stop truck-ignition                              # keep the Pi up with the key off
```

## Configuration

- **Bluetooth address:** `VLINKER_MAC` in `/etc/default/vlinker-rfcomm` (template:
  `pi/systemd/vlinker-rfcomm.env.example`).
- **User account:** `truck-telemetry.service` and `truck-dashboard.service` run as the user `ryan`.
  Change `User=` and `Group=` to your own account.
- **Display:** the 1024x600 HDMI mode is set in `pi/boot/config.txt` (`hdmi_cvt=1024 600 60 6 0 0 0`).
- **Shutdown delay:** `OFF_DELAY_S` in `ignition_watch.py` (45 s).
- **Serial port and paths:** constants at the top of `telemetry.py` and `dashboard.py`.

## Repository layout

| Path | What |
|------|------|
| `pi/opt/` | The code from the Pi's `/opt`, including the dated `*-before-*` copies made along the way |
| `pi/systemd/` | `truck-dashboard`, `truck-telemetry`, `truck-ignition` and `vlinker-rfcomm` units |
| `pi/state/` | Saved state from `/var/lib` on the Pi |
| `pi/captures/` | Sample readings captured on the Pi |
| `pi/boot/` | `config.txt` and `cmdline.txt` |
| `tools/` | `truckpi-restore-wifi.sh`, which rebuilds the Pi's Wi-Fi profile on its SD card from a laptop |
| `REVISED-CIRCUIT.md` | Current circuit build sheet and the three-part plan |
| `NOTES.md`, `SHUTDOWN-PROBLEM.md` | Earlier analysis; their circuit sections are superseded |
| `chatgpt-transcripts/` | The original design chats |

`pi/` is a snapshot of the SD card taken 2026-11-04. The card's `network-config` and `user-data` are
left out on purpose, because they hold the Wi-Fi key and the login password hash. For publishing, the
Bluetooth addresses, the partition ID and the Wi-Fi network name were replaced with placeholders, and
the vLinker's address moved from the unit file to `/etc/default/vlinker-rfcomm`.

## Status (2026-11-04)

The dashboard and telemetry work. The open problem is power: the Pi never shut down on key OFF.

**No software read the ignition.** There was no GPIO code in the dashboard or telemetry, no ignition or
shutdown service, no overlay in `config.txt`, and no root or user crontab. Part 2 of `REVISED-CIRCUIT.md`
therefore meant writing that service, not repairing it. The sense board may be fine, but it still needs its
meter check (part 1).

**`truck-ignition` now exists and is enabled on the Pi** (`pi/opt/truck-ignition/`, `pi/systemd/`). It powers
off after 45 s of key OFF. Tested in the truck with the real key and sense board on 2026-11-04: a 14 s key OFF
cancelled, and a full key OFF powered down 46 s later. The Pi still can't restart itself on key ON, and the
5 V stays on after shutdown, until part 3 is built.

GPIO17 goes HIGH for about 1 s while cranking, which the service rides through. `REVISED-CIRCUIT.md` assumed
fuse 27 stays live in START, so check node A with a meter in START and allow for it in part 3.

One drop on the bench is unexplained: after the first replug, the Pi left the network about a minute after
coming back. The likely cause is the test's pull-up surviving a quick replug, but this is not confirmed. After
a replug with 30 s unpowered, GPIO17 read LOW and it stayed up.

The phone can hold the vLinker's Bluetooth connection and lock the Pi out. It reconnects by itself once the
phone lets go.

**The Wi-Fi profile had been wiped.** `/etc/netplan/90-NM-*.yaml` was 0 bytes and `system-connections` was
empty, both stamped 2026-10-17 05:22. A hard power cut during a write is the likely cause, but this is not
proven: the Pi has no RTC and keeps no persistent journal. Until the shutdown and power-cut work is done,
it can happen again. `tools/truckpi-restore-wifi.sh` was run on the card, and the Pi rejoined the network
on its next boot.

### Next

1. Meter-check node A in START, and make the R1 change (part 1).
2. Build and bench-test the power cut (part 3), using the relay revision below.

### Ground reference in part 3

The first part 3 design had Q1 switch the converter's negative input, which put the Pi's ground on Q1's
drain side while the sense stage and Q2 sat on truck ground. With Q1 off, the Pi's ground could float toward
12 V through the converter while pins 11 and 13 still connected to parts on truck ground. The 2026-11-04
revision in `REVISED-CIRCUIT.md` changes Q1 to drive a relay coil instead, so the converter, Pi and sense
stage all stay on truck ground. It has not been built yet.

## About this project

This is a personal project for one truck, shared as-is in case it helps someone with a similar
7.3L or a Pi in a vehicle. It is not a product and comes with no support. Check any wiring against
your own truck's fuse chart and a meter before connecting it.
