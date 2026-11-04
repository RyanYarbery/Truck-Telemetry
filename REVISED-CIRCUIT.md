# Revised ignition and power circuit — complete build sheet

Written 2026-11-02. Supersedes the circuit section of NOTES.md and folds in SHUTDOWN-PROBLEM.md.
Confirmed symptom: after key OFF the dashboard stays drawn and the Pi keeps running. That means
two faults, not one. The sense path (or its software) never triggers a shutdown, and even when it
does, nothing removes power. This sheet fixes both. Everything uses parts already on hand:
RFP30N06LE, 1N5408, 1.5KE18A, 10 kΩ and 100 kΩ ¼ W resistors.

## Three parts, in the order to do them

| # | What | Fixes | Needs |
|---|------|-------|-------|
| 1 | Verify the sense board actually switches, and stiffen its gate drive | key-OFF never detected | meter, 20 min |
| 2 | Make the software shut down on key OFF | Pi keeps running | Pi reachable over Wi-Fi |
| 3 | Add the Q1/Q2 power-cut stage + `gpio-poweroff` overlay | screen and Pi stay powered, Pi can't come back | 2 MOSFETs, 1 diode, 4 resistors |

Part 3 is useless until parts 1 and 2 pass. Do not build it first.

## Full schematic

```
                          ┌──────────────────────── SENSE STAGE (existing board, one change) ─────────────────────────┐
FUSE 27 (ign RUN 12 V) ──┤ 1N5408 ├──●── node A ───┬───────── R1 ───────●─────────────── Q0 GATE  ┐
  via add-a-circuit tap    A     K   │              │   (was 3×100k ‖ = 33k;             │        │  RFP30N06LE Q0
                                     │   1.5KE18A   │    now 2×10k in series = 20k)   R2 10k      │  DRAIN ── Pi pin 11 (GPIO17) ──┬── R3 10k ── Pi pin 1 (3.3 V)
                                     │   K (stripe) │                                    │        │  SOURCE ── GND                  │
                                     │   up to A    │                                   GND       │                      key ON  → GPIO17 LOW  (≈0 V)
                                     │   A to GND   │                                             │                      key OFF → GPIO17 HIGH (3.3 V)
                                     │              │                                             ┘
                                    GND             │
                                                    │
                          ┌─── POWER-CUT STAGE (new) ──┴────────────────────────────────────────────────────────────────┐
                          │   node A ──── R4 100k ────●──────────────────────────────── Q1 GATE                          │
                          │                           │                                   │                               │
                          │   Pi 5 V ── R5 10k ──●── 1N5408 ──┘                        R6 100k     RFP30N06LE Q1            │
                          │   (pin 2 or 4)        │   A      K                            │        DRAIN  ── converter 12 V IN (−)
                          │                       │                                      GND       SOURCE ── TRUCK GND       │
                          │                    Q2 DRAIN                                                                     │
                          │                 RFP30N06LE Q2                                                                   │
                          │                    Q2 SOURCE ── GND                                                             │
                          │                    Q2 GATE ──●── R7 10k ── Pi pin 13 (GPIO27)                                  │
                          │                              │                                                                  │
                          │                            R8 100k                                                              │
                          │                              │                                                                  │
                          │                             GND                                                                 │
                          └─────────────────────────────────────────────────────────────────────────────────────────────────┘

BATTERY +12 V (constant) ──────────────────────────────────────────────── converter 12 V IN (+)
converter 5 V OUT (+) ── Pi 5 V and display micro-USB        converter OUT (−) ── Pi GND (this is also Q1's drain side)
```

MOSFET pinout, flat face toward you, legs down: GATE – DRAIN – SOURCE, metal tab = drain.
All three MOSFETs are the same RFP30N06LE. Diode stripe = cathode (K).

### Resistor list

| Ref | Value | Role |
|-----|-------|------|
| R1 | 20 kΩ (2 × 10 kΩ in series) | sense divider top. Replaces the 3 × 100 kΩ parallel group. |
| R2 | 10 kΩ | Q0 gate pull-down (unchanged) |
| R3 | 10 kΩ | GPIO17 pull-up to 3.3 V (unchanged) |
| R4 | 100 kΩ | ignition → Q1 gate |
| R5 | 10 kΩ | keep-alive from Pi 5 V |
| R6 | 100 kΩ | Q1 gate pull-down |
| R7 | 10 kΩ | GPIO27 → Q2 gate |
| R8 | 100 kΩ | Q2 gate pull-down (keeps Q2 off during boot before the kernel owns the pin) |

If a 5.1 kΩ exists, R1 = 10 kΩ with R2 = 5.1 kΩ is equivalent. Do not use a 10 kΩ for R6: the
keep-alive could then only reach ≈2.2 V at Q1's gate, inside the threshold spread.

### Voltages to expect

| Point | Key OFF | Key ON, 12 V | Key ON, 14.4 V charging |
|-------|---------|--------------|-------------------------|
| node A | 0 V | ≈11.3 V | ≈13.7 V |
| Q0 gate (old 33k/10k) | 0 V | ≈2.6 V | ≈3.2 V |
| Q0 gate (new 20k/10k) | 0 V | ≈3.8 V | ≈4.6 V |
| Pi pin 11 / GPIO17 | ≈3.3 V | ≈0 V | ≈0 V |
| Q1 gate, Pi running | ≈3.9 V (keep-alive) | ≈5.7 V | ≈6.9 V |
| Q1 gate, Pi halted | 0 V | ≈5.7 V | ≈6.9 V |

Gate absolute maximum is ±10 V. A TVS clamp event (≈25 V at node A) reaches ≈8.3 V at Q0's gate
through 20k/10k and ≈12 V at Q1's gate through 100k/100k. If a spare 1.5KE18A exists, add one from
Q1 gate to ground (stripe toward the gate). It never conducts in normal operation.

## Part 1: prove the sense stage switches

Meter black lead on truck ground. Pi may stay connected.

1. Node A: ≈0 V key OFF, ≈11–14 V key RUN, still ≈11 V in START. (Also confirms fuse 27 is the right fuse.)
2. Q0 gate to ground: ≈0 V OFF, ≥2.5 V ON. Below 2.5 V ON means the divider is wrong or a 100 kΩ is open.
3. Pi pin 11 to ground: ≈3.3 V OFF, <0.3 V ON.

If step 3 swings, the board works and the fault is software (part 2). If it does not swing while
step 2 does, Q0 is dead or wired GATE/DRAIN/SOURCE out of order. Replace R1 with 2 × 10 kΩ in series
while the board is on the bench either way; it costs two resistors and removes the margin question.

## Part 2: software (do when the Pi is on Wi-Fi)

Run on the Pi:

```bash
systemctl list-units --type=service | grep -iE 'ign|shutdown|truck|dash'
systemctl status <the ignition service>
journalctl -u <the ignition service> -b --no-pager | tail -40
pinctrl get 17        # or: raspi-gpio get 17   → level=0 key ON, level=1 key OFF
```

Then read the service's script and check these four things:

1. It uses **BCM 17** (pin 11). `GPIO.setmode(GPIO.BOARD)` with 17 reads the 3.3 V pin and never changes.
2. It treats **LOW as key ON** and HIGH as key OFF. If reversed it either shuts down right after boot or never.
3. The key-OFF debounce/delay timer actually fires (30–60 s) and ends in `systemctl poweroff` or `shutdown -h now`, run as root.
4. The unit is enabled and active, and not crashing on a missing library (`gpiozero`, `RPi.GPIO`, `lgpio`).

Fix whatever fails, then test: key OFF, wait 90 s, the Pi should halt (activity LED stops, dashboard freezes,
`ssh truckpi.local` stops answering). The screen will still be lit at this point. That is expected until part 3.

## Part 3: power-cut stage

### Pi config

Add to `/boot/firmware/config.txt` (older images: `/boot/config.txt`; DietPi: `/boot/dietpiEnv.txt` overlays line):

```
dtoverlay=gpio-poweroff,gpiopin=27
```

GPIO27 defaults to pull-down at power-on, so Q2 stays off and the keep-alive is asserted from the first
instant the 5 V rail comes up, before the kernel runs. Do not use GPIO0–8 (default pull-up, would release
the keep-alive during boot).

### Build

Build Q1, Q2, R4–R8 and the diode on the existing carrier or a scrap of perfboard. Q1 carries up to ≈0.8 A
on the 12 V side; no heatsink needed (≈30 mW at Rds(on)). Converter IN(−) goes to Q1 drain, Q1 source to the
single project ground point. Everything else that said "GND" stays on that same ground point.

### Bench test with the converter on a bench supply, before the truck

1. No Pi connected. Apply 12 V to node A (simulated key ON): converter output rises to 5 V. Remove it: output drops.
2. Connect the Pi (overlay installed) and display. Apply ignition, let it boot, remove ignition: 5 V must stay up.
3. `sudo poweroff`: the 5 V rail must collapse within about a second of the activity LED stopping, and the display must go dark.
4. Re-apply ignition: the Pi must cold-boot.
5. Key-cycle test: ignition off, back on within 20 s: the dashboard must keep running (software cancels the shutdown).

### Behaviour once installed

- Key ON: Q1 on through R4, converter runs, Pi boots, display lights.
- Pi up: keep-alive holds Q1 through R5 and the diode. Power now stays on with or without ignition.
- Key OFF: software waits 30–60 s, re-checks GPIO17, runs `poweroff`.
- At poweroff: kernel drives GPIO27 high, Q2 shorts the keep-alive, R6 pulls Q1's gate to 0 V, converter, Pi and display go dark.
- Key ON again: cold boot through R4.
- `sudo poweroff` with the key still ON: Pi halts but stays powered until the key is cycled. Acceptable.

## Still open

- Fuse 27 meter check in OFF / RUN / START (part 1, step 1).
- The ignition service name and its code (part 2).
- Whether the 7" display is powered from the converter's 5 V or from a Pi USB port. Either way it is downstream of Q1.
