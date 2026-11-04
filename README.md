# Truck Telemetry

OBD telemetry dashboard for a 2001 Ford F-350 7.3L Power Stroke, running on a Raspberry Pi Zero 2 W
(`truckpi.local`) with a Vgate vLinker FS over Bluetooth and a 1024x600 display.

## Layout

| Path | What |
|------|------|
| `pi/opt/` | The code from the Pi's `/opt`, including the dated `*-before-*` copies made along the way |
| `pi/systemd/` | `truck-dashboard`, `truck-telemetry` and `vlinker-rfcomm` units |
| `pi/state/` | Saved state from `/var/lib` on the Pi |
| `pi/captures/` | Captures from `~/truck-project-captures` |
| `pi/boot/` | `config.txt` and `cmdline.txt` |
| `tools/` | `truckpi-restore-wifi.sh`, which rebuilds the Wi-Fi profile on the card from a laptop |
| `REVISED-CIRCUIT.md` | Authoritative circuit build sheet and three-part plan |
| `NOTES.md`, `SHUTDOWN-PROBLEM.md` | Earlier analysis; the circuit sections are superseded |
| `chatgpt-transcripts/` | The original design chats |

`pi/` is a snapshot of the SD card taken 2026-11-04. The card's `network-config` and `user-data` are left
out on purpose, because they hold the Wi-Fi key and the login password hash.

## Status (2026-11-04)

The Pi never shuts down on key OFF, and it had dropped off the network. Reading the SD card explained both.

**No software reads the ignition.** There is no GPIO code in the dashboard or telemetry, no ignition or
shutdown service, and no overlay in `config.txt`. Part 2 of `REVISED-CIRCUIT.md` therefore means writing
that service, not repairing it. The sense board may be fine, but it still needs its meter check (part 1).
The root crontab has not been reviewed.

**The Wi-Fi profile had been wiped.** `/etc/netplan/90-NM-*.yaml` was 0 bytes and `system-connections` was
empty, both stamped 2026-10-17 05:22. A hard power cut during a write is the likely cause, but this is not
proven: the Pi has no RTC and keeps no persistent journal. Until the shutdown and power-cut work is done,
it can happen again.

`tools/truckpi-restore-wifi.sh` has been run on the card, which now has a `THE WIFI` profile. Whether the
Pi rejoins the network has not been tested yet.

## Next

1. Boot the Pi in range of `THE WIFI` and confirm `ssh truckpi.local`.
2. Meter-check the sense board (part 1).
3. Write the ignition shutdown service (part 2).
4. Resolve the ground question below, then build the power cut (part 3).

## Open question: ground reference in part 3

Q1 switches the converter's negative input, and the schematic puts the Pi's ground on Q1's drain side,
while the sense stage and Q2 sit on truck ground. The build notes say everything shares one ground point,
so the sheet contradicts itself. With Q1 off, the Pi's ground could float toward 12 V through the converter
while pins 11 and 13 still connect to parts on truck ground. Settle this before building part 3.
