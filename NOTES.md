# Truck Telemetry — consolidated notes

Compiled 2026-10-24 from the ChatGPT project "Truck Telemetry" (three chats, no project files) plus prior analysis notes. Full transcripts are in `chatgpt-transcripts/`.

## The system

- **Vehicle:** 2001 Ford F-350, 7.3L Power Stroke. OBD-II over **SAE J1850 PWM** (not CAN). A generic CAN transceiver will not work by itself.
- **Computer:** Raspberry Pi Zero 2 W, hostname `truckpi.local`, dashboard software in `/opt/truck-dashboard` (written in ChatGPT; not yet reviewed here).
- **OBD adapter:** vLinker (FORScan is used on the Ford for diagnostics).
- **Power:** a 12 V → 5 V converter feeds the Pi continuously. Red → Pi 5 V, black → Pi GND and the common ground for the ignition circuit.
- **Other hardware on hand:** ~4 Raspberry Pi Picos (only a possible add-on for extra analog I/O), Arduino Uno R3, the old Edge harness pieces, assorted ¼ W resistors, 1N5408 diodes, 1.5KE18A TVS diodes, RFP30N06LE MOSFETs.
- **Hard constraint set by Ryan:** build only with parts already owned unless he explicitly says to buy something. The only purchase so far was add-a-circuit fuse taps.

## The old Edge hardware

- The display that used to be in the truck was an **Edge Evolution II programmer, P/N 15001** (1999–2003 F-Series 7.3L). Its harness plugs into the truck's OBD-II connector and reads live PCM PIDs; EGT came from a separate thermocouple on the right side of the Edge OBD-II connector assembly.
- Connectors photographed: a 4-pin 2×2 female, another 4-pin 2×2 on an Edge module/adapter, an 8-pin 2×4 female, and an OBD-II cable/module with a jump-start warning tag. Markings H00005100 and 200145962 / 31111 are not public part numbers.
- Decision: **do not cut or repurpose any Edge conductor** until its function is known. The display-side cable is probably Edge-proprietary, not plain serial. The cleaner path is a J1850-capable interface straight off the OBD port.

## Ignition-sense circuit (as designed and built)

Purpose: tell the Pi when the key is ON/OFF so Linux can shut down cleanly. The ignition wire is a **signal only**; it does not power the Pi.

```
Fuse tap (fuse 27, ignition RUN 12 V)
   |
1N5408  (anode to fuse tap, stripe/cathode toward circuit)
   |
   +---- 1.5KE18A TVS ---- GND   (stripe/cathode toward the protected node, anode to GND)
   |
3 × 100 kΩ in parallel (≈33.3 kΩ)
   |
   +---- RFP30N06LE GATE
   |
 10 kΩ
   |
  GND

Pi pin 1 (3.3 V)
   |
 10 kΩ pull-up
   |
   +---- Pi pin 11 (GPIO17) ---- MOSFET DRAIN
MOSFET SOURCE ---- Pi pin 6 (GND)
```

- Gate voltage estimate: ≈3.16 V at 14.4 V charging, ≈2.61 V at 12 V (after the 0.7 V diode drop).
- Logic is inverted: **key ON → GPIO17 LOW**, key OFF → GPIO17 HIGH.
- MOSFET pinout, flat face toward you, legs down: **Gate – Drain – Source** left to right; metal tab = drain.
- Not galvanically isolated; Pi ground and truck ground must be common, via the project's single ground point.
- Bench-test plan before connecting the Pi: gate–source ≈0 V key OFF, 2.5–3.3 V key RUN; drain node ≈3.3 V key OFF, ≈0 V key ON.
- Physical build: a generated 70 × 45 × 3 mm printed component carrier (STL + OpenSCAD in the ChatGPT thread, not saved locally), point-to-point soldered underneath. PETG/ASA preferred over PLA in the cab.
- **Fuse source:** passenger-compartment fuse 27, Ford's 10 A "Ignition Run Power Feed (Customer Access)". Verify with a meter: OFF ≈0 V, RUN ≈12 V, START ideally still ≈12 V. Fuse 30 was explicitly rejected (feeds fuel heater, wastegate solenoid, IDM relay coil). The tap's second slot takes a small 1–2 A fuse for the new wire.
- **Status per Ryan (mid Oct 2025):** board built and attached to the truck; shutdown timing not yet measured.

## Shutdown behaviour (as designed)

Key OFF → wait ~30–60 s → re-check ignition → still OFF → flush telemetry / close DB → `poweroff`. Turning the key back on during the delay cancels shutdown. Expected key-OFF-to-dark time ≈35–75 s.

**Known gap, acknowledged repeatedly in the thread but never solved:** shutting Linux down does not remove 5 V. The Pi halts with power still applied, and nothing restarts it when the key returns. A "power-control stage" (relay, delay-off module, or similar) was deferred.

## Concerns raised in prior analysis (2026-10-24, before this consolidation)

Ryan reported the circuit "doesn't function as intended"; the symptom has not been stated yet. Points already identified:

1. **GPIO17 cannot wake a halted Pi.** Only GPIO3 (physical pin 5) wakes a Pi from halt. With constant 5 V and the sense line on GPIO17, the Pi stays halted after key OFF until power is cycled.
2. **Software polarity unverified.** The circuit gives LOW = key ON; the code in `/opt/truck-dashboard` has not been checked to confirm it expects that.
3. **Gate drive is marginal.** ≈2.6–3.2 V on a MOSFET with a 1–2 V (max) threshold works for a 0.33 mA load but has little margin; a stiffer divider such as 10 k / 5.1 k was suggested.
4. **No 5 V cut** after shutdown (see above).

## Shutdown problem

See `SHUTDOWN-PROBLEM.md` (2026-10-24): the monitor stays on after key OFF because nothing ever cuts power; proposed Q1/Q2 MOSFET power-cut stage driven by the gpio-poweroff overlay.

## Open questions

- What exactly is the misbehaviour: never shuts down, shuts down instantly, never comes back, something else?
- What does the GPIO/shutdown code on the Pi look like, and which GPIO numbering does it use (BCM 17 vs BOARD 11)?
- Has fuse 27 been meter-verified in OFF / RUN / START?
- How is MPG computed in the dashboard? ChatGPT could not recover the formula; the thread only has the generic speed ÷ fuel-flow relationship, and an injector-based estimate would not see a fuel leak.
- Where are the STL/OpenSCAD files? They were download links in the ChatGPT thread only.

## References

- Datasheet facts quoted in-thread: RFP30N06LE 60 V logic-level N-MOSFET, gate ±10/−8 V max; 1.5KE18A unidirectional TVS, 15.3 V standoff, ≈25.2 V max clamp.
