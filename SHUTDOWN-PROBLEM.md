# Why the monitor stays on after key OFF, and how to fix it

Written 2026-10-24. Symptom reported by Ryan: the display does not shut down when the key is turned off.

## Root cause

The design in the ChatGPT thread never removes power from anything. The 12 V → 5 V converter is on constant battery power, and it feeds both the Pi and the Waveshare 7" HDMI display (the display is powered over its micro-USB port, not by the HDMI signal). The ignition-sense board only tells Linux "the key is off". ChatGPT acknowledged this gap three separate times and deferred it ("we'll handle that after"). So even if the software works perfectly:

1. The Pi halts, but stays powered. The Waveshare panel keeps its backlight on with no signal, so the screen stays lit.
2. The Pi cannot come back on the next time the key is turned on. The ignition line is on GPIO17, and the only pin that can wake a halted Pi is GPIO3, so nothing restarts it until the converter's power is physically cycled.

There is a second possibility stacked on top: the Pi may not be shutting down at all (software never installed, wrong GPIO numbering, polarity backwards, timer never fires). The two cases look different on the screen.

## Five-minute test to tell the two cases apart

Turn the key on, let the dashboard boot fully, then turn the key off and wait two full minutes.

| What you see after 2 minutes | Meaning |
|---|---|
| Dashboard still drawn and values still updating (or clock advancing) | Pi never shut down. Software problem on top of the power problem. |
| Screen went black / "No signal" but backlight still lit | Pi halted correctly. Only the power-cut problem remains. |

Extra checks if the Pi is reachable: `ssh truckpi.local` after key OFF (reachable = still running). On the Pi, `pinctrl get 17` (or `raspi-gpio get 17`) should read `level=0` with the key ON and `level=1` with it OFF. `journalctl -b -1 | tail` after a power cycle shows whether the last boot ended with a clean shutdown.

## The fix: let the Pi cut its own power (parts already on hand)

Add a second RFP30N06LE as a low-side power switch (Q1) in the converter's 12 V negative lead. Its gate is held up by either the ignition line or a "keep-alive" from the Pi. When both go away, the converter, the Pi, and the display all lose power. Key ON brings everything back from a cold boot, so no GPIO3 wake is needed.

```
BATTERY +12 V (constant) ───────────────────────────► converter 12 V IN (+)
                                                       converter 12 V IN (−) ──┐
                                                                               │ Q1 DRAIN
                                                                           RFP30N06LE (Q1)
                                                                               │ Q1 SOURCE
TRUCK GND ─────────────────────────────────────────────────────────────────────┴──── GND

Q1 GATE node ("hold power on"):
   ignition path:   protected ignition node* ──100 kΩ──┐
   keep-alive path: Pi 5 V rail ──10 kΩ──┬── 1N5408 ─►┤── Q1 GATE
                                         │             │
                                      Q2 DRAIN      100 kΩ
                                  RFP30N06LE (Q2)      │
                                      Q2 SOURCE ─────── GND
   Q2 GATE ◄──10 kΩ── Pi GPIO27 (pin 13), with 100 kΩ from Q2 gate to GND

* the node after the existing 1N5408 + 1.5KE18A on the ignition-sense board
```

How it behaves:

- **Key ON:** ignition path puts ≈6.9 V on Q1's gate (≈5.7 V at 12 V). Q1 turns on, converter runs, Pi boots, display lights.
- **Pi running:** GPIO27 is low, Q2 is off, so the 5 V rail feeds Q1's gate through the 10 kΩ and diode (≈4.0 V after the divider with the 100 kΩ). Power now stays on with or without ignition.
- **Key OFF:** ignition path drops. Keep-alive holds Q1 on. The existing software waits its 30 to 60 s, re-checks GPIO17, then runs `poweroff`.
- **At poweroff:** the kernel's `gpio-poweroff` overlay drives GPIO27 high. Q2 turns on and shorts the keep-alive to ground. With ignition gone, Q1's gate is pulled to 0 V by its 100 kΩ. Q1 opens and the converter, Pi, and display all go dark within milliseconds.
- **Key ON again:** ignition path turns Q1 on, cold boot. Key cycled during the 30 to 60 s delay: software cancels, nothing is lost.
- **Manual `sudo poweroff` while the key is ON:** Pi halts but stays powered until the key is cycled. Acceptable.

Pi config (in `/boot/firmware/config.txt`):

```
dtoverlay=gpio-poweroff,gpiopin=27
```

GPIO27 is chosen because GPIOs 9 to 27 default to pull-down at boot, so Q2 stays off (keep-alive asserted) before the kernel claims the pin. The 100 kΩ on Q2's gate guarantees that. Do not use GPIO0 to 8 (default pull-up, would release keep-alive at boot).

### Numbers

- Q1 load: Pi Zero 2 W plus 7" display is roughly 1 to 1.5 A at 5 V, which is about 0.5 to 0.8 A on the 12 V side. RFP30N06LE is rated 30 A, 0.047 Ω at Vgs 5 V, with threshold 1 to 2 V. The datasheet's saturation curves go down to Vgs 3 V, so 4 V of keep-alive drive and 5.7 to 6.9 V of ignition drive are comfortably in its logic-level range.
- Gate limit is +10 V. The ignition path tops out at 6.9 V during charging. A transient clamped by the 1.5KE18A (worst case ≈25 V at full rated pulse) reaches ≈12 V at the gate through the 100 kΩ / 100 kΩ divider, so if a spare 1.5KE18A exists, put one from Q1 gate to ground as well. It will never conduct in normal operation.
- 100 kΩ is used as Q1's gate pull-down specifically so the keep-alive path can be driven from 5 V through a 10 kΩ. With a 10 kΩ pull-down the keep-alive would only reach ≈2.2 V, which is too close to the threshold.
- If 100 kΩ and 10 kΩ are the only values on hand, every resistor above is one of those two.

### Why not simpler alternatives

- **Switch the display only:** leaves the Pi halted and un-wakeable until power is cycled. Fixes the symptom, not the problem.
- **Keep-alive from a GPIO straight into Q1's gate through a diode:** only ≈2.6 to 2.8 V at the gate, inside the 1 to 2 V threshold spread. Too marginal to sink a boot-time surge. That is why Q2 and the 5 V rail are used instead.
- **gpio-shutdown on GPIO3 to wake:** would need rewiring ignition sense to GPIO3, and the display and converter would still stay on all night.
- **Delay-off relay module:** cleanest commercially, but violates the no-new-parts constraint.

## Software side (verify when the Pi is reachable)

1. Find the ignition service: `systemctl list-units | grep -i -E 'ign|shutdown|truck'` and read its script.
2. Confirm it reads **GPIO17 (BCM) / pin 11 (BOARD)** and treats **LOW as key ON**. If it uses `GPIO.setmode(GPIO.BOARD)` with 17, it is reading the wrong pin (board pin 17 is 3.3 V).
3. Confirm it is enabled and running: `systemctl status <name>`.
4. On a non-Pi-OS image (DietPi etc.), the overlay line may belong in `/boot/dietpiEnv.txt` or `/boot/config.txt` instead.
5. After installing the overlay and wiring Q1/Q2, bench test with the converter on a bench supply before putting it back in the truck: key-on simulation should power up, `sudo poweroff` should drop the 5 V rail within a second once ignition is removed.

## Bench-test sequence

1. Build Q1/Q2 stage on the carrier or a scrap of perfboard. Converter output unloaded.
2. Apply 12 V to the "ignition" input: converter output should come up to 5 V. Remove it: output should drop (no keep-alive yet).
3. Connect the Pi. Apply ignition, let it boot, remove ignition: 5 V must stay up.
4. `sudo poweroff`: 5 V must collapse within about a second of the activity LED stopping.
5. Re-apply ignition: Pi must boot from cold.
6. Only then install the fuse tap in fuse 27 (meter-verified: ≈0 V OFF, ≈12 V RUN, still ≈12 V in START).

## Sources

- Raspberry Pi overlays README, `gpio-poweroff` and `gpio-shutdown` entries: https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README
- RFP30N06LE datasheet (Fairchild, Rev. B1): https://electrokit.com/upload/product/41004/41004353/RFP30N06LE.pdf
- Waveshare 7inch HDMI LCD (C) wiki, power and backlight notes: https://www.waveshare.com/wiki/7inch_HDMI_LCD_(C)
