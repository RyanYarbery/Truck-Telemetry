# Reuse Edge Wiring

Source: ChatGPT project "Truck Telemetry", chat "Reuse Edge Wiring" (Sep–Oct 2025, main design thread). Extracted 2026-10-24 by copying the rendered chat text; speaker labels are not preserved, "User attachment" marks a photo Ryan sent, and image-only replies leave no text.

---

User attachment
User attachment
I found the manual for the old display if that helps at all
Yes, Master — this helps considerably. I found the matching Edge documentation online and it confirms exactly what that old display/harness was.
Your unit is the Edge Evolution II programmer, P/N 15001, specifically for the 1999–2003 Ford F-Series 7.3L Power Stroke. Edge’s own support page still lists P/N 15001 for that application. 
More importantly for our telemetry project, the manual confirms that the Evolution did not merely receive power through that cable. Its main harness connected directly to the truck’s OBD-II diagnostic connector, and the display could read live PCM parameters such as RPM, vehicle speed, boost, and other PIDs. The kit could also read EGT, but that came from a separate thermocouple connection rather than from the truck PCM. 
That means the mysterious old Edge cable we were examining is potentially very useful. There are effectively two paths we can take:
Ignore the Edge electronics and connect our Pi/Arduino directly to the truck's diagnostic bus. This is probably the cleanest long-term architecture.
Reuse the existing Edge wiring, particularly if the previous installation already routed the OBD connection and EGT probe wiring to a convenient location. That could save us a substantial amount of wiring work.
There is one particularly useful detail in the manual: the Edge harness plugs into the truck's OBD-II connector, and the optional EGT thermocouple connects to the right side of the Edge OBD-II connector assembly. 
 So the cable you showed me previously may contain more than just ordinary OBD conductors depending on exactly which segment of the old Edge installation it came from.
What I want from that manual
Don't photograph the whole thing, Meatbag. We can target the useful pages.
Please find and photograph the pages headed approximately “Getting Connected,” “Installing the EGT Thermocouple,” and “Installing the Evolution.” Also photograph any page that shows connectors, cables, wiring diagrams, or labeled plugs.
The online copy tells me those sections are roughly around pages 9–17, depending on the revision. 
If you give me clear pictures of those pages and the old cable/connector again, I can correlate the physical connector with the manual and determine what every part was intended to do.
And there is an even better development: we now know the exact device well enough that I can work backward from the 15001 Edge harness and determine whether we can safely repurpose that existing cable for our Raspberry Pi/Pico truck telemetry system instead of installing an entirely new run. That is the target I would pursue next.
Pin down the old Edge wiring
Plan a safe Pi/Pico interface
Map the Edge harness pins
I've got everything squared away for powering the project, now we need to move on to the ignition part. Walk me through what I need to do to get that built. You keep saying pico for some reason but we are using the zero arent we?
Yes, Master. For the truck telemetry build, the central computer is the Raspberry Pi Zero 2 W. The Pico was an earlier architecture idea for dedicated sensor acquisition; for the direction we settled on, the Zero 2 W is the main computer, and we only add a Pico later if we need extra analog/sensor I/O.
For the ignition part, there are really two separate jobs we need to solve:
detect when the truck ignition is ON
let the Pi shut down cleanly after ignition turns OFF
Do not power the Pi directly from the ignition wire. Since you already have the main project power handled, the ignition line should be treated as a signal only.
The clean architecture is:
Truck ignition-switched 12 V → protection + voltage reduction/isolation → Pi GPIO input
Then software on the Zero watches that GPIO. When ignition goes low, it starts a shutdown timer, finishes logging, closes the database/files, then runs a clean shutdown.
What you need to build
For a simple, robust input circuit I would use:
1 × automotive ignition-switched 12 V source
1 × inline fuse, around 0.5–1 A
1 × automotive-rated optocoupler, or a normal optocoupler with proper input protection
1 × series resistor sized for 12–15 V operation
1 × reverse-polarity protection diode across the optocoupler LED
1 × Pi GPIO pull-up to 3.3 V
wiring/connectors/heat shrink
The optocoupler is the important part. It gives us galvanic isolation between the nasty truck electrical environment and the Pi GPIO.
Recommended circuit
Use something like a PC817/LTV-817 class optocoupler on the ignition input.
Truck side:
IGN-switched 12V
      |
     fuse
      |
   2.2k–3.3k resistor
      |
   optocoupler LED
      |
     GND
Put a diode anti-parallel across the optocoupler LED so a reverse transient cannot kill it:
        resistor
12V ----/\/\/\----+---->|---- GND
                  |   opto LED
                  |
                  +----|<|----+
                     1N4148
Pi side:
Pi 3.3V
   |
 10k
   |
   +------ GPIO
   |
collector
 opto transistor
emitter
   |
Pi GND
That produces an inverted logic signal:
ignition ON → optocoupler conducts → GPIO LOW
ignition OFF → optocoupler stops → GPIO HIGH
That inversion is harmless; we simply account for it in software.
Why I do not want a raw resistor divider
A divider such as:
12 V
 |
 resistor
 |
 GPIO
 |
 resistor
 |
GND
would technically reduce the voltage, but I would not use that as the final design in a 2001 F-350.
Vehicle electrical systems can throw substantial transients during cranking, alternator events, inductive switching, and load dumps. A GPIO on a Pi Zero has essentially no tolerance for being driven above its rail.
The optocoupler makes the ignition detector much harder to kill.
Where to get the ignition signal
We need a circuit that is:
0 V with key OFF, ~12 V with key RUN, and preferably still ~12 V while CRANKING.
That last point matters. Some accessory circuits shut off while the starter operates.
For our telemetry system we ideally want an IGN/RUN-START circuit, not an ACC-only circuit.
On your 2001 F-350 7.3L, I would verify the exact source with a multimeter rather than trusting wire colors from a generic diagram.
Test candidate wires/fuses in four states:
KEY OFF      → 0 V
KEY ACC      → doesn't matter much
KEY RUN      → ~12–14 V
KEY START    → remains powered
The one that behaves like that is what we want.
Do not splice anything yet until we identify the correct circuit.
The shutdown behavior
The Zero should not immediately shut down the instant ignition disappears.
Instead:
Ignition ON
    ↓
Pi operates normally
    ↓
Ignition OFF
    ↓
wait ~30–60 seconds
    ↓
check ignition again
    ↓
still OFF?
    ↓
flush telemetry / close database
    ↓
sudo poweroff
If you turn the key back on during that delay, shutdown gets cancelled.
That prevents annoying shutdowns if you briefly cycle the key.
There is one important hardware issue after that: once Linux shuts down, something has to remove/reapply power or wake the Pi again.
A Pi Zero cannot reliably wake itself from a GPIO ignition input after it is fully powered down while its 5 V rail remains permanently present.
So the full design needs:
            CONSTANT VEHICLE POWER
                     |
             your 5V power system
                     |
              power-control stage
                     |
              Raspberry Pi Zero
                     ^
                     |
IGNITION ---------- ignition detector
The ignition detector tells Linux to shut down.
The power-control stage then either cuts power after shutdown or provides a restart mechanism when ignition returns.
That is the next thing we need to settle before soldering the ignition circuit, because it depends on exactly how you have solved power.
Tell me what hardware you ended up using between the truck's 12 V and the Zero — the exact buck converter/power module and how it is wired — and I can give you the complete ignition/on-off circuit around that hardware rather than designing a second system that fights it.
Remember that we are only using stuff I already have
Confirmed, Master. For the Truck Telemetry project, we are using only parts you already have on hand unless you explicitly tell me to look for something to buy. I’ll treat that as a hard constraint going forward.
For the ignition circuit, that means I should not casually spec a PC817, automotive relay, MOSFET module, or anything else unless we’ve already established you own it. What I know you already have includes the Raspberry Pi Zero 2 W, Arduino Uno R3, several Raspberry Pi Picos, and the old Edge Evolution/OBD wiring and connectors.
So our next move should be to inventory the actual electrical parts you have available for the ignition-sense circuit, then design around those exact parts. If you send me a picture of your resistors, diodes, transistors/MOSFETs, relays, optocouplers, buck modules, and miscellaneous boards/connectors, I can identify what is usable and give you the exact wiring diagram from your existing pile.
We already inventoried my electronic parts. Maybe it was somewhere else in this project
You’re right, Master. I checked the project history I can recover, and I found some of the earlier hardware inventory, but not the full small-component inventory we apparently did.
What I can verify from the project history is that you already have the Raspberry Pi Zero 2 W as the truck computer, about four Raspberry Pi Picos, and the old Edge Products OBD-II/interface harness pieces. We also explicitly decided not to cut or repurpose unknown Edge conductors until we knew exactly what they were doing.
What I did not recover was the detailed inventory of your resistors, diodes, transistors/MOSFETs, relays, optocouplers, buck modules, etc. That likely lives in an older project conversation that did not come back in the context search.
So I should not make you inventory everything again. I can keep searching the project history for that exact parts list and then build the ignition circuit only from those parts.
Let's do that
I searched the project history and the project/library files, Master. I recovered some hardware context, but not the detailed small-component inventory we did earlier. The search found the Zero/Pi/Pico/Arduino/Edge hardware, but nothing containing the resistor/diode/transistor/relay/optocoupler inventory.
What I can recover reliably is:
Raspberry Pi Zero 2 W — this is the truck telemetry computer.
~4 Raspberry Pi Picos.
Arduino Uno R3.
Old Edge Products interface hardware, including the OBD-II/J1850 cable/module and the Edge display harness/connectors.
The truck-dashboard software is already running on the Pi under /opt/truck-dashboard.
The detailed inventory of your discrete electronic parts does not appear in the retrievable project history or project files I can access right now.
So I don't want to pretend I found it when I didn't.
The best next move is still to avoid re-inventorying everything from scratch. Send me one photo of the parts assortment/container you inventoried before. I can identify the relevant components from the image and we only need to extract the handful that matter for ignition control: likely a transistor/MOSFET or relay, a few resistors, and perhaps a diode or optocoupler depending on what is actually in your stock. From there I can give you the exact ignition circuit using only what you already own.
User attachment
User attachment
User attachment
User attachment
User attachment
User attachment
Yes, Master. These photos give us enough to build the ignition-sense portion from parts you already have.
The useful parts I can positively identify are:
RFP30N06LE logic-level N-channel MOSFET
1N5408 rectifier diodes
1.5KE18A TVS diodes
assorted ¼ W resistors, including 10 kΩ and 100 kΩ values
the Raspberry Pi Zero 2 W GPIO itself
The RFP30N06LE is a 60 V N-channel MOSFET with roughly a 1–2 V threshold, so it is suitable as a simple level-shifting switch for an ignition input. Its gate rating is only +10/-8 V, though, so we need to protect and divide the truck voltage before it reaches the gate. 
The 1.5KE18A TVS is also useful here. It is a unidirectional transient suppressor with a 15.3 V standoff and roughly 25.2 V maximum clamping voltage at its rated pulse current, which makes it appropriate for suppressing positive spikes on a nominal 12–14.5 V ignition line before our divider. 
Build this circuit
Use the truck ignition wire only as a signal. Do not power the Pi from it.
TRUCK IGNITION +12 V
        |
        |
     1N5408
   anode   cathode/stripe
        --->|----
              |
              +--------------------+
              |                    |
              |                1.5KE18A
              |                 TVS diode
              |                    |
              |                    |
          33.3 kΩ                  |
      (3 x 100kΩ                   |
       in parallel)                |
              |                    |
              +---- MOSFET GATE    |
              |                    |
            10 kΩ                  |
              |                    |
TRUCK/Pi GND--+--------------------+
The TVS orientation is important:
Protected ignition line ----|<|---- Ground
                             TVS
For the 1.5KE18A, the striped end/cathode goes toward the positive ignition line, and the non-striped end/anode goes to ground.
Then wire the MOSFET output side like this:
Pi 3.3 V
   |
  10 kΩ
   |
   +---------- GPIO input
   |
 MOSFET DRAIN
      |
 RFP30N06LE
      |
 MOSFET SOURCE
      |
     GND
So the complete function is:
Ignition OFF
MOSFET off
10k pull-up raises GPIO to 3.3 V
GPIO = HIGH
Ignition ON
MOSFET turns on
MOSFET pulls GPIO to ground
GPIO = LOW
That means LOW = ignition ON in software.
Why three 100 kΩ resistors in parallel
Three 100 kΩ resistors in parallel give:
33.3 kΩ
With the 10 kΩ resistor from gate to ground, we get a divider.
At approximately 14.4 V charging voltage, minus roughly 0.7 V through the 1N5408:
13.7 × 10 / (33.3 + 10) ≈ 3.16 V at the MOSFET gate
That's plenty for this application because we're only asking the MOSFET to sink a few tenths of a milliamp from the Pi pull-up, not drive a large load.
At 12 V:
11.3 × 10 / 43.3 ≈ 2.61 V
Still comfortably above the MOSFET's specified 1–2 V threshold. 
The TVS keeps a large positive automotive transient from simply appearing across that divider. The 1N5408 also blocks a reverse-polarity excursion from reaching the divider.
RFP30N06LE pinout
Looking at the flat labeled face of the TO-220 MOSFET with the legs pointing downward:
LEFT     CENTER     RIGHT
Gate      Drain     Source
 G         D          S
The metal tab is also electrically connected to Drain.
For our circuit:
Gate   → resistor divider
Drain  → Pi GPIO
Source → Ground
Do not accidentally swap drain and source.
Grounding
Unlike an optocoupler arrangement, this circuit is not galvanically isolated. The Pi ground and truck ground must therefore be common.
That's fine for this architecture because your Pi power system is already ultimately referenced to vehicle ground.
Connect the ignition circuit's ground to the same project ground used by the Pi power supply, rather than finding some random second chassis grounding point. That reduces ground-offset problems.
Before connecting it to the Pi
We are going to bench-test the circuit first.
Build only this part:
IGN input
   ↓
1N5408
   ↓
TVS + 33.3k/10k divider
   ↓
MOSFET gate
Then use your multimeter to measure:
MOSFET Gate → Source
With ignition OFF, we want approximately:
0 V
With ignition RUN, we should see approximately:
2.5–3.3 V
Then check MOSFET Drain → Ground while using the 10 kΩ pull-up to 3.3 V:
Ignition OFF: ~3.3 V
Ignition ON: very close to 0 V
Only after those two tests pass do we attach the drain to the Pi GPIO.
One thing we still need to identify
We need the actual ignition-switched wire in your truck.
For the telemetry system I want a source that behaves like this:
Key position	Signal
OFF	0 V
ACC	either is acceptable
RUN	~12–14 V
START/CRANK	preferably remains powered
That last condition matters. We don't want the Pi thinking you turned the truck off every time you crank it.
Since you already have the old Edge Evolution installation, there is a decent chance we can use an existing ignition-switched lead from that harness rather than running a new wire. The manual you found may help us identify exactly which Edge conductor handled switched ignition.
So I would not solder the truck-side connection yet.
First, build this little ignition detector on the bench. After that, we'll identify the correct ignition source in your 2001 F-350 and connect it to this circuit.
Can we 3d print a board to hold these components in a more organized way?
Yes, Master. We can 3D print something to hold the parts in an orderly fashion — but with one important correction:
You cannot 3D print a real PCB with conductive traces using an ordinary printer.
What you can print is one of these:
a component carrier / fixture
holds the MOSFET, resistors, and diodes in fixed positions
keeps spacing neat
gives you mounting holes and wire strain relief
a perfboard holder / enclosure
best option if you have any perfboard, protoboard, or a scrap PCB
printed part holds the board and protects it from vibration
a point-to-point soldering jig
parts mount into a printed plate
you solder the leads together underneath with wire jumpers
good if you do not have perfboard
My recommendation
For a truck environment, the cleanest option is:
3D print a small mounting tray or enclosure, then build the circuit with soldered components inside it.
That gives you:
organization
repeatable layout
less chance of shorts
better vibration resistance
What I would not do
I would not rely on:
loose component leads hanging in the air
friction-fit parts only
PLA if this lives in a hot cab, dash cavity, or near the windshield
In a vehicle, heat and vibration are the enemy.
Best filament choice
For automotive use:
ASA / ABS = best of the common home-print materials
PETG = acceptable and much better than PLA
PLA = only acceptable for temporary bench testing
If this module is going in the truck permanently, I would avoid PLA.
A good printed layout for your circuit
For the ignition-sense board, the printed holder only needs to organize a few parts:
1 × RFP30N06LE MOSFET
3 × 100k resistors in parallel
1 × 10k resistor
1 × 1N5408 diode
1 × 1.5KE18A TVS diode
wire entry/exit points
mounting holes or zip-tie slots
A smart layout would include:
a TO-220 slot for the MOSFET body
labeled channels for:
IGN IN
GND
GPIO OUT
3.3V
shallow troughs or holes to route component leads
tie-down points for the input and output wires
a lid or cover so nothing metallic can short against it
The most practical design choices
Option A — Printed tray + point-to-point wiring
Good if you do not have perfboard.
print a flat tray with holes
insert each component in its assigned spot
bend leads underneath
solder leads and small jumper wires together
secure the finished assembly with hot glue, epoxy, or silicone after testing
This is the best “use what we already have” approach.
Option B — Printed enclosure + tiny perfboard
Best if you already have any perfboard.
solder the circuit on perfboard
print a case around it
include standoffs and mounting ears
This is mechanically superior.
Important warning
The printed part should provide mechanical organization, not electrical trust.
Meaning:
the electrical connections must still be soldered
the plastic should not be the only thing preventing a broken wire from flexing the component leads
add strain relief for the truck-side wires
A good simple enclosure size
For this circuit, a very small module is enough. Something around:
60 mm × 40 mm × 20 mm
would probably be plenty.
Inside it, keep:
truck-side high/noisy input on one side
Pi-side GPIO wiring on the other side
common ground clearly labeled
My tactical recommendation
Yes — we should print a small ignition interface module, not a fake PCB.
The best structure is:
printed base
components soldered in a fixed layout
printed lid
two mounting holes or zip-tie slots
wire exit holes with strain relief
If you want, Master, I can do the next step and lay out a very specific printable design plan:
exact component placement
exact labels
suggested dimensions
where each wire enters and exits
how to assemble it
And if you want maximum precision, I can even write you an OpenSCAD model for the printed holder so you can generate the STL yourself.
Find or generate a stl for me to print
Yes, Master. I generated one specifically for the ignition interface using the parts you showed me.
It is a 70 × 45 × 3 mm component carrier with dedicated holes for the RFP30N06LE MOSFET, 1N5408 diode, 1.5KE18A TVS diode, three 100 kΩ resistors, two 10 kΩ resistors, extra jumper holes, M3 mounting holes, and strain-relief slots on both ends. It is meant for point-to-point soldering underneath.
Download the STL
I also made the editable OpenSCAD source in case we want to change spacing after a test fit:
Download the OpenSCAD source
Print it flat as-is. I’d use PETG if you have it; PLA is fine for the initial fit/test. Before soldering anything permanently, put the components into the printed carrier and send me a photo. I want to verify the physical fit and orientation before we commit the wiring. 
I'm going to Klamath Falls and I'm going to stop at some auto parts stores. If there's any components that would make the rest of this ignition stuff much easier, let me know and I may be able to pick them up.
Yes, Master. Since you’re stopping at auto-parts stores anyway, there are a few things that would make the ignition side much cleaner and more reliable than forcing everything through loose discrete parts.
The highest-value item is an add-a-circuit fuse tap for the fuse style in your 2001 F-350. That gives us a clean, fused ignition-switched signal without cutting factory wiring. Make sure it matches the truck’s actual fuse type before buying; the add-a-circuit must also be installed in the correct orientation relative to the hot side of the fuse slot. 
Second, I would grab a standard 12 V Bosch-style 5-pin SPDT relay plus a matching prewired socket/pigtail. We may not ultimately need the relay for the GPIO sense circuit itself, but it gives us a very useful automotive-rated switching element for the Pi’s eventual shutdown/power-control logic. O’Reilly carries universal 5-pin 12 V relays such as the Dorman 88069, and their own documentation confirms the standard use of accessory/ignition power to control a relay while constant power feeds the load. 
I’d prioritize your shopping like this:
Add-a-circuit/fuse tap matching your F-350 fuse box — highest priority.
5-pin Bosch-style 12 V relay, SPDT, 30–40 A.
Matching 5-wire relay socket/pigtail — much better than individual female spade terminals.
Small inline blade-fuse holder and a few 2–5 A fuses for our electronics branch. Inline holders with weather covers are readily available.
18–20 AWG automotive primary wire, ideally red, black, and one other color.
Heat-shrink butt connectors / ring terminals / female spades, depending on what you’re low on.
If you happen to see one: 12 V adjustable delay-off timer relay/module. This is the interesting one. A proper delay-off module could substantially simplify keeping the Pi alive long enough to shut Linux down gracefully after the key is turned off. I would not buy a random one blindly, though—send me a picture/model number and I’ll tell you immediately whether it will work.
You do not need to buy more MOSFETs, rectifier diodes, TVS diodes, or resistors; you already have appropriate ones. The relay also does not replace our protected ignition-sense circuit by itself—we still need to keep raw vehicle voltage away from the Pi GPIO.
For Klamath Falls specifically, you have several useful stops clustered around Washburn Way: O'Reilly Auto Parts, AutoZone Auto Parts, and NAPA Auto Parts - Cascade Automotive Inc. Baxter is also a good local option if the chains don’t have an oddball electrical part: Baxter Auto Parts.
Use two fingers to move the mapUse ctrl + scroll to zoom the map
If you only buy two things, Meatbag: get the correct fuse tap and the 5-pin relay with socket. Those give us the biggest improvement in installation quality and flexibility.
The tape are in the mail. Ended up not getting anything else. Break down how to build what i need again and the components we will use
Absolutely, Master. Since the fuse taps are already on the way and you didn’t buy anything else, we’ll build the ignition system from what you already have.
The goal is simple: the Pi Zero 2 W stays powered from your existing power setup, and the truck’s ignition circuit is used only as a logic signal so the Pi knows when the key is ON or OFF. When the key turns off, software can wait briefly and shut down cleanly.
We’ll build a protected ignition-sense circuit using these parts you already showed me:
Raspberry Pi Zero 2 W
1 × RFP30N06LE N-channel MOSFET
1 × 1N5408 rectifier diode
1 × 1.5KE18A TVS diode
3 × 100 kΩ, ¼ W resistors
2 × 10 kΩ, ¼ W resistors
wire
your incoming add-a-circuit fuse tap
the 3D-printed component carrier we made
The circuit has two sections: the truck side and the Pi GPIO side.
TRUCK IGNITION SIGNAL
        |
      1N5408
        |
        +------ TVS diode ------ GND
        |
   3 x 100kΩ parallel
      = 33.3kΩ
        |
        +------ MOSFET Gate
        |
      10kΩ
        |
       GND
That divider reduces the truck’s roughly 12–14.5 V ignition signal down to around 2.5–3.3 V at the MOSFET gate. The TVS absorbs positive spikes, and the 1N5408 helps block reverse-polarity excursions.
Then the Pi side is:
Pi 3.3V
   |
  10kΩ
   |
   +------ GPIO INPUT
   |
MOSFET Drain
MOSFET Source
   |
  GND
The RFP30N06LE pinout, with the flat labeled face toward you and legs pointing downward, is:
LEFT      CENTER      RIGHT
Gate       Drain       Source
 G           D           S
So wire it like this:
Gate   -> ignition divider
Drain  -> Pi GPIO input
Source -> ground
The logic will be inverted:
Ignition OFF -> MOSFET OFF -> GPIO pulled HIGH to 3.3 V
Ignition ON  -> MOSFET ON  -> GPIO pulled LOW to ground
So in software:
GPIO LOW  = ignition ON
GPIO HIGH = ignition OFF
For the resistor divider, use three 100 kΩ resistors in parallel. Three equal resistors in parallel gives:
100k / 3 ≈ 33.3kΩ
Then use one 10 kΩ resistor from the MOSFET gate to ground.
The other 10 kΩ resistor is the Pi-side pull-up from 3.3 V to the GPIO/drain node.
For the TVS diode, use the 1.5KE18A you showed me. Its striped/cathode end goes toward the positive ignition signal, and the other end goes to ground:
IGNITION + ----|<|---- GND
              TVS
For the 1N5408:
Fuse tap ignition output
        |
      anode
        |
      1N5408
        |
     cathode
   striped end
        |
   protected circuit
So the stripe points toward the circuit, away from the fuse tap.
Your grounding should all come back to the project’s common ground:
Pi ground
buck-converter ground
MOSFET source
10k gate resistor
TVS ground
Those should all be electrically common.
The fuse tap will go into a fuse position that behaves like this:
KEY OFF   -> 0 V
KEY RUN   -> about 12–14 V
KEY START -> ideally still powered
That last one matters because we do not want the Pi thinking the ignition turned off every time you crank the engine.
When the taps arrive, we should verify the correct fuse slot with your multimeter before connecting the circuit.
The physical order I would build it on the printed carrier is:
Truck-side end
Fuse-tap wire
   |
1N5408
   |
TVS diode
   |
33.3k divider
   |
MOSFET gate
       RFP30N06LE
Pi-side end
Drain -> GPIO
Source -> GND
10k pull-up -> Pi 3.3V
Keep the noisy 12 V input parts on one side of the board and the Pi wiring on the other.
Before connecting anything to the Pi, bench-test it.
With the truck ignition OFF, measure MOSFET gate to source. You should see approximately:
0 V
With ignition RUN:
roughly 2.5–3.3 V
Then test the drain node with the Pi-side 10 kΩ pull-up to 3.3 V:
Ignition OFF -> about 3.3 V
Ignition ON  -> close to 0 V
Only after those measurements are correct do we connect that drain node to a Raspberry Pi GPIO.
For the GPIO itself, I would use GPIO17, physical pin 11 unless you already use that pin for something else. Then:
Pin 1  -> 3.3 V
Pin 6  -> GND
Pin 11 -> GPIO17 ignition sense
So the entire finished system becomes:
TRUCK IGNITION
      |
   fuse tap
      |
 protected ignition detector
      |
  RFP30N06LE
      |
   GPIO17
      |
 Raspberry Pi Zero 2 W
      |
 software detects key OFF
      |
 wait ~30–60 sec
      |
 clean shutdown
There is one separate issue we will handle after this: shutdown is not the same thing as physically removing power. The Pi can shut Linux down cleanly while your existing 5 V supply remains energized. Once we get ignition detection working, we can decide whether we want the Pi merely halted or whether we also want automatic power cut/restart behavior.
The first build target is just the ignition detector above. That gets the hard part—safe vehicle-to-GPIO interfacing—done.
Try to draw a diagram with the components
Now i want one with actual pictures of components in the layout they need to be in with wires and wverythinf
How reliable is this image? Can i reference it while building?
Use it as a physical-layout reference, Master, but do not build by blindly copying every pixel of that generated image. I’d rate it about 8/10 as a visual guide, 5/10 as an authoritative wiring document.
The good news is that the main topology in the image is correct: ignition input → 1N5408 → protected node → TVS to ground → 3×100 kΩ in parallel → MOSFET gate; 10 kΩ gate pull-down to ground; MOSFET source to ground; drain to GPIO17; and a 10 kΩ pull-up from that GPIO node to Pi 3.3 V. The RFP30N06LE pin order shown as Gate–Drain–Source, left-to-right with the flat face toward you is also the intended orientation.
There are two image-generation artifacts I do not want you trusting. First, the TVS body in the picture is marked “1.5KE18A CA”; your actual part is 1.5KE18A, not the bidirectional 1.5KE18CA. Your real 1.5KE18A is polarized, so orientation matters: stripe/cathode toward the protected ignition node, anode toward ground. The 1.5KE18A family has a 15.3 V standoff and is intended for transient suppression. 
 Second, the generated solder joints and perfboard traces are illustrative—the image generator can invent a connection that merely looks connected.
So while you build, use this exact connection list as the authority:
Fuse-tap IGN 12V
    |
1N5408 ANODE
1N5408 CATHODE / STRIPE
    |
    +---- 1.5KE18A CATHODE / STRIPE
    |          |
    |       1.5KE18A
    |          |
    |         GND
    |
3 x 100kΩ in parallel
    |
MOSFET GATE
    |
10kΩ
    |
   GND
Pi 3.3V
   |
 10kΩ
   |
   +---------- GPIO17
   |
MOSFET DRAIN
MOSFET SOURCE
   |
  GND
And for the MOSFET, flat printed face toward you, legs down:
LEFT      CENTER      RIGHT
Gate       Drain      Source
The safest way to use the picture is: place the components approximately as shown, but before soldering each connection, compare it against that netlist above.
If you want, I can also make you a second image that is much more useful for actual assembly: an exact hole-by-hole layout for the 3D-printed carrier we generated, with each component lead and jumper numbered so you can literally build it one connection at a time.
Awesome. Try to make an even better image. I have a hard time understanding your flowcharts so images help a lot
What is this process called that we are doing to turn the ignition voltage into a signal?
Master, what we’re doing is generally called signal conditioning.
More specifically, this circuit is doing three things at once:
Voltage level shifting: converting the truck’s roughly 12–14 V ignition signal into something the Pi can safely interpret.
Input protection: the 1N5408 and TVS diode protect against reverse polarity and automotive transients/spikes.
Logic interfacing: the MOSFET turns that conditioned vehicle signal into a clean 3.3 V digital logic signal for the Raspberry Pi GPIO.
So the most precise name would be:
Automotive ignition signal conditioning and level shifting
or, shorter:
12 V-to-3.3 V GPIO interface
The resistor network by itself is a voltage divider, while the MOSFET stage is acting as a low-side logic switch / inverter.
Do some research for diagrams of people doing the same thing just for my reference
Yes, Master. I found several references that are genuinely close to what we’re doing. None is an exact clone of our circuit, but together they show the same underlying techniques: automotive transient protection, 12 V-to-3.3 V interfacing, MOSFET switching, pull-up/pull-down logic, and ignition sensing.
The closest conceptual match is a current automotive Raspberry Pi supervisor project called PCG-PSM. Its design explicitly includes an ACC / ignition sense input, safe open-drain transistor stages or level shifters, and automotive input protection including a source fuse, reverse-polarity protection, TVS transient suppression, and filtering. That is almost exactly the design philosophy we’re following. 
A second useful reference is the Carberry automotive Raspberry Pi board. Its published hardware spec includes a +12 V ignition signal input, controlled Raspberry Pi power, and a logic shutdown signal. It’s a commercial-style implementation of the same general problem: safely taking vehicle ignition state and presenting it to a Pi. 
For a simpler low-voltage logic example, this AskElectronics discussion shows people converting a 12 V input to a 3.3 V MCU/GPIO signal, including an inverting transistor/MOSFET-style approach where a pull-up makes the GPIO high until the 12 V signal causes the transistor stage to pull it low. That behavior is directly analogous to our ignition ON → GPIO LOW arrangement. 
This other AskElectronics example is also useful because it shows someone sensing a 12 V signal with a 3.3 V Pico using a voltage divider and MOSFET logic, and the discussion revolves around exactly the sort of protection questions we’ve been accounting for. 
For the MOSFET side specifically, the Raspberry Pi forum has a classic diagram/discussion using an N-channel MOSFET with a 10 kΩ gate resistor/pull-down concept, zener/transient protection, common ground, and 3.3 V GPIO logic. It’s aimed at switching a 12 V load rather than sensing ignition, but electrically the MOSFET behavior is the same. 
The automotive dash-cam design references are useful for seeing what a more production-grade vehicle input stage looks like. They show vehicle 12 V → TVS protection → filtering → protected bus, with additional load-dump and transient handling. That is more elaborate than we need, but it confirms why putting a TVS ahead of sensitive electronics is standard automotive practice. 
One caution: many generic “Raspberry Pi + 12 V MOSFET” diagrams are the opposite direction from our use case. They show the Pi driving a 12 V load, whereas we are sensing a 12 V ignition signal. The useful parts to compare are the MOSFET pin relationships, pull-up/pull-down behavior, and transient protection—not the direction of current through the load.
The most useful three references for you to visually compare against our circuit are the PCG-PSM automotive supervisor, the Carberry automotive Pi board, and the AskElectronics 12 V-to-3.3 V input discussion. Together they’re the closest match to what we’re building. 
If you want, I can next find actual circuit-diagram images from these sources and put together a side-by-side explanation of “their circuit vs ours” so you can visually see what each part corresponds to.
See if any of them have pictures of the finished product
Yes, Master. I found finished hardware photos, and they’re useful because they show what this kind of ignition/power interface looks like once it’s turned into a proper board.
The closest finished-product examples are these:
The first two are Mausberry automotive Raspberry Pi power/switch boards. They use a dedicated BAT / GND / ACC input arrangement and manage Raspberry Pi startup/shutdown from the vehicle ignition signal. Physically, this is very close to the role our little ignition-sense board is performing, except theirs also integrates the power-supply/control hardware on the same PCB.
The third is a Carberry Pi automotive shield mounted on a Raspberry Pi. Carberry explicitly supports a +12 V ignition input, controlled Pi power, and a shutdown signal, so it is another good example of the same overall system being implemented as a finished PCB. 
The Mausberry photo is probably the most useful reference for your build because you can clearly see the design philosophy: vehicle-side wiring comes into a terminal block, the conditioning/control electronics stay together on one compact board, and only safe low-voltage signals leave toward the Pi. That is essentially what we’re trying to recreate with your printed carrier and discrete parts.
One important difference, Meatbag: those commercial boards are more integrated and likely use dedicated regulators/controllers internally. Our circuit is simpler because you already solved the Pi’s main power supply separately; we only need the ignition-sense/logic interface now.
The PCG-PSM project I mentioned earlier does not appear to have a finished custom board photo yet. Its current documented stage is still an Arduino Uno prototype, with a custom HAT planned later. 
If you want, I can next search specifically for DIY perfboard or hand-soldered versions of 12 V automotive ignition-to-Raspberry-Pi interfaces. Those would look much closer to what your finished board will actually look like than these polished commercial PCBs.
I want to see something more similar to what I am doing
Yes, Master. I found a few references that are much closer to what you’re actually building: hand-built automotive electronics on perfboard/protoboard, using discrete resistors, transistors/MOSFETs, diodes, and jumper wires rather than a polished commercial PCB.
This one is probably the closest visual match to what your finished module will look like:
The first photo is an older rusEFI low-side driver prototype built on perfboard. It has exactly the kind of construction style we’re talking about: through-hole resistors, semiconductors, colored jumper wires, soldered connections, and automotive circuitry built by hand before becoming a PCB.
The second is a PiCar Raspberry Pi automotive prototype built on perfboard with terminal blocks, modules, wiring, and power-management components. It is more complicated than ours, but physically it’s very similar to the style of build we’re heading toward.
I also found a Raspberry Pi automotive project where the Pi monitors the vehicle accessory/ignition line specifically for safe shutdown. The design uses an optocoupler between the automotive side and Raspberry Pi GPIO, plus a timed power arrangement. Electrically it solves essentially the same problem as our MOSFET interface, just with isolation instead.
There are also multiple DIY car-Pi projects where people explicitly describe taking the 12 V accessory/ignition state and turning it into a safe GPIO signal so Linux can perform a graceful shutdown. One uses a voltage divider down to about 3 V; another uses a relay to pull a GPIO low when ignition changes. 
What this tells me about your build is reassuring: the physical style we’re using is completely normal for a prototype. Yours will actually be simpler than most of these. You only have roughly:
1 diode + 1 TVS + 5 resistors + 1 MOSFET + a few wires.
So your finished carrier should look more like a small, clean subsection of the rusEFI perfboard photo than that larger PiCar assembly.
The image I generated for you is therefore a pretty reasonable representation of the physical construction style. The main thing I would change for the real build is to make the wiring shorter and more compact than in the illustration. We don’t need long decorative runs; short soldered connections and a solid ground bus will be better mechanically.
If you want, I can search specifically for small perfboard 12 V-to-3.3 V transistor/MOSFET interface modules, rather than whole Raspberry Pi automotive systems. That should get us even closer to the exact little board you’re making.
User attachment
I'm a bit confused about this part. Specifically the part with the resistor and the 3.3 v and the gpio. What is the 3.3v mentioned? and why is the resitor after the gpio pin?
Exactly, Master. The diagram makes this look more confusing than it actually is. The key is that the 10 kΩ resistor is not “after” the GPIO pin. The GPIO, resistor, and MOSFET drain all meet at the same electrical junction.
The 3.3 V is supplied by the Raspberry Pi itself. On the Zero 2 W, physical pin 1 provides a regulated 3.3 V supply. We use that voltage only to establish what the GPIO sees when the MOSFET is turned off.
Think of the actual wiring like this:
Raspberry Pi
┌─────────────────────────────┐
 Pin 1
  3.3V
   │
 10kΩ
   │
   ├──────────── Pin 11 / GPIO17
   │
   │
 MOSFET
 DRAIN
   │
 SOURCE
   │
 Pin 6 / GND
└─────────────────────────────┘
That junction here:
        10kΩ
          │
          ●──── GPIO17
          │
       MOSFET
        DRAIN
is one point electrically.
Why connect 3.3 V through a resistor?
That 10 kΩ resistor is called a pull-up resistor.
When the MOSFET is OFF, its drain is essentially disconnected from ground:
3.3V
 │
10kΩ
 │
 ●──── GPIO17
 │
 X     MOSFET OFF
 │
GND
Because nothing is pulling that node down, the resistor gently pulls it toward 3.3 V.
So:
GPIO17 sees HIGH ≈ 3.3 V.
That corresponds to:
Ignition OFF → GPIO HIGH
Then ignition turns ON
Our truck-side circuit turns the MOSFET on.
Now the circuit looks like:
3.3V
 │
10kΩ
 │
 ●──── GPIO17
 │
 MOSFET ON
 │
GND
The MOSFET provides a very low-resistance path to ground.
Therefore the junction gets pulled to approximately:
0 V
and GPIO17 sees:
LOW
So:
Ignition ON → GPIO LOW
Why doesn't this short 3.3 V directly to ground?
This is exactly why the 10 kΩ resistor is there.
Without it:
3.3V
 │
 MOSFET
 │
GND
When the MOSFET turned on, we'd essentially short the Pi's 3.3 V rail to ground. Very bad, Meatbag.
With the resistor:
3.3V
 │
10,000 Ω
 │
 MOSFET
 │
GND
The current is only about:
3.3 V ÷ 10,000 Ω = 0.00033 A = 0.33 mA
That's tiny.
And the GPIO isn't actually “in the current path”
This is probably the part that caused the confusion.
A GPIO input doesn't work like this:
3.3V → resistor → GPIO → MOSFET → ground
Instead, the GPIO is more like a voltmeter attached to the junction:
                   GPIO17
                     │
                     │
3.3V ── 10kΩ ───────●──── MOSFET
                           │
                          GND
GPIO17 simply asks:
“What voltage is this point?”
If MOSFET OFF:
● ≈ 3.3V
GPIO = HIGH
If MOSFET ON:
● ≈ 0V
GPIO = LOW
That's the entire trick.
And importantly, we never put the truck's 12–14 V anywhere near GPIO17. The truck voltage only controls the MOSFET's gate through the conditioning circuit we built. The Pi side creates its own safe 0–3.3 V signal.
That 10 kΩ resistor between Pi 3.3 V and GPIO17 is therefore doing a very important job: it gives GPIO17 a definite HIGH state whenever the MOSFET isn't deliberately pulling it LOW. Without a pull-up, the GPIO could float and randomly read HIGH or LOW from electrical noise.
Give me the pinout for my pi
Master, your Raspberry Pi Zero 2 W uses the standard 40-pin Raspberry Pi GPIO header.
For our ignition-sense circuit, the three pins we care about are:
Pin 1 = 3.3 V
Pin 6 = GND
Pin 11 = GPIO17
Here is the full header, viewed from above with the USB/HDMI ports at the bottom edge of the board:
                Raspberry Pi Zero 2 W
              40-pin GPIO header
      3.3V   1  ● ●  2   5V
     GPIO2   3  ● ●  4   5V
     GPIO3   5  ● ●  6   GND   ← use this GND
     GPIO4   7  ● ●  8   GPIO14
       GND   9  ● ● 10   GPIO15
    GPIO17  11  ● ● 12   GPIO18   ← ignition signal here
    GPIO27  13  ● ● 14   GND
    GPIO22  15  ● ● 16   GPIO23
      3.3V  17  ● ● 18   GPIO24
    GPIO10  19  ● ● 20   GND
     GPIO9  21  ● ● 22   GPIO25
    GPIO11  23  ● ● 24   GPIO8
       GND  25  ● ● 26   GPIO7
     GPIO0  27  ● ● 28   GPIO1
     GPIO5  29  ● ● 30   GND
     GPIO6  31  ● ● 32   GPIO12
    GPIO13  33  ● ● 34   GND
    GPIO19  35  ● ● 36   GPIO16
    GPIO26  37  ● ● 38   GPIO20
       GND  39  ● ● 40   GPIO21
For our circuit specifically:
Pi pin 1  → 3.3V → 10k pull-up resistor
Pi pin 6  → GND → common ground
Pi pin 11 → GPIO17 → MOSFET drain / signal node
One important detail, Meatbag: physical pin number and GPIO number are not the same thing.
For example:
Physical pin 11 = GPIO17
So when we write software, we need to know whether the GPIO library expects BCM numbering or physical BOARD numbering. For our documentation, I’d keep referring to it as:
GPIO17, physical pin 11
That removes ambiguity.
So for clarification, I will have a 10k resistor from pin 1 to pin 6 and a line going from the resistor to pin 11?
Not quite, Master. Do not put the 10 kΩ resistor from pin 1 to pin 6. That would just place a resistor directly between 3.3 V and ground.
The correct Pi-side wiring is:
Pi pin 1 (3.3V)
      |
     10kΩ
      |
      +---------- Pi pin 11 (GPIO17)
      |
   MOSFET Drain
MOSFET Source
      |
Pi pin 6 (GND)
So the resistor goes from:
Pin 1 → 10 kΩ resistor → junction
And that same junction connects to both:
Pin 11 / GPIO17
MOSFET drain
Then separately:
MOSFET source → Pin 6 / GND
The easiest way to picture it is:
PIN 1 (3.3V)
     |
   [10k]
     |
     ●──────── PIN 11 (GPIO17)
     |
   DRAIN
   MOSFET
   SOURCE
     |
PIN 6 (GND)
So yes, there is a line from the resistor to pin 11, but pin 6 is not connected to the resistor directly. Pin 6 is ground and connects to the MOSFET source/common ground.
Ok, that helps a lot
Good, Master. That exact junction is the key idea:
Pin 1 → 10 kΩ → shared node → Pin 11 + MOSFET drain
and separately:
MOSFET source → Pin 6 / ground
Once you think of GPIO17 as merely measuring the voltage at that shared node, the whole pull-up arrangement makes a lot more sense.
Can you show me a diagram of my mosfet so I know which lead is which?
Where does the black line from the voltage converter go?
Yes, Master. If you mean the black output wire from the 12 V → 5 V voltage converter that powers the Pi, that is the 5 V negative/ground wire.
For our build, it goes to the common ground, which includes the Raspberry Pi ground:
Voltage converter BLACK (- / GND)
              |
              +──────── Pi GND (Pin 6)
              |
              +──────── MOSFET Source
              |
              +──────── 10k gate pull-down
              |
              +──────── 1.5KE18A TVS ground side
              |
              +──────── Vehicle/project GND
So electrically, these are all the same ground node.
The Pi power side should therefore be:
VOLTAGE CONVERTER OUTPUT
Red +5V  ─────────→ Pi 5V input
Black GND ────────→ Pi GND
                       |
                       └──→ ignition circuit common GND
One important distinction: do not connect that black wire to GPIO17 or to Pi pin 1 (3.3 V). It goes to a GND pin, such as physical pin 6.
If your converter has two black wires—one on its 12 V input side and one on its 5 V output side—show me which converter you're using and I’ll mark exactly where all four converter wires go.
User attachment
Why are there 2 slots for fuses?
Because that’s an add-a-circuit fuse tap, Master. The two fuse slots protect two different circuits.
One slot keeps the original factory circuit protected. The other slot protects the new accessory wire you’re adding for the ignition-sense signal.
Conceptually:
Fuse box slot
    |
    +---- Fuse #1 → original truck circuit
    |
    +---- Fuse #2 → your new ignition-sense wire
So you typically:
move the truck’s original fuse into one slot,
put a small fuse for your new circuit into the other slot.
For our ignition-sense circuit, the new branch draws almost nothing, so a small fuse is appropriate. If you have something like 1 A or 2 A, that’s plenty. You do not need a large fuse for this signal wire.
The exact which slot is original vs new depends on the orientation/design of that tap, so before I tell you “top slot” or “bottom slot,” I’d rather verify it from the specific tap you bought. Send me a photo of the other side or any markings/package info, and I can tell you which fuse goes where and which direction the tap should face in the fuse box.
User attachment
Which fuse is where my ignition so should go?
Yes, Master. For your 2001 F-350, the best factory fuse position for our ignition-sense tap is Fuse 27 in the passenger-compartment fuse panel.
Ford identifies Fuse 27 as a 10 A “Ignition Run Power Feed (Customer Access)”. That is exactly what we want: a factory-provided ignition-run source intended for customer-added equipment. 
In the factory layout, fuse 27 is in the lower half of the panel. Based on your photo and the 2001 F-350 fuse numbering diagram, it should be the empty position just below the blue 15 A fuse in the middle column, directly above the lower green 30 A fuse area. I would not insert the tap until we verify that exact cavity with a meter, because orientation in a photograph can be deceptive.
The verification is simple:
Fuse 27 cavity
Key OFF  → ~0 V
Key RUN  → ~12 V
Key START → ideally still ~12 V
Ford specifically calls it Ignition Run Power Feed, so RUN behavior is confirmed by the manual; we should still test what happens during CRANK before committing, because that matters to our shutdown logic. 
Also, do not use Fuse 30 just because it is ignition-related. Fuse 30 feeds important engine electronics on the diesel—fuel heater, wastegate solenoid, IDM relay coil, etc.—and there is no reason for us to piggyback that circuit when Ford gave us Fuse 27 specifically for customer ignition power. 
So the target is:
Passenger fuse panel → Fuse position 27 → add-a-circuit → ignition-sense board
If you want, take a straight-on photo of the entire fuse panel and I can mark the exact Fuse 27 cavity on your picture.
What formula did we end up on for calculating miles per gallon?
Master, I checked the Truck Telemetry history I can recover, and I couldn’t find the exact MPG formula we previously settled on. I don’t want to invent it.
For a diesel telemetry system like yours, the usual instantaneous MPG relationship is:
MPG
=
Vehicle Speed (mph)
Fuel Flow (gal/hr)
MPG= 
Fuel Flow (gal/hr)
Vehicle Speed (mph)
​
So the real question is how we were deriving fuel flow from the 7.3L Power Stroke data. If we were using injector data, the formula would have been based on something like injector pulse width × engine RPM × injector flow/calibration, then converted to gallons per hour.
If you want, I can reconstruct the exact formula we should use for your 7.3L from the PIDs we actually have available in the truck-dashboard project and make sure it matches what FORScan/Edge-style devices would do.
Is there an OBD device for a 2002 Dodge Ram 2500?
Yes, Master. A 2002 Dodge Ram 2500 sold in the U.S. is OBD-II, so there are adapters that will read it. OBDLink explicitly lists U.S.-market 1996+ light trucks as supported, and period Chrysler/Dodge documentation confirms the truck uses older Chrysler diagnostic buses rather than modern CAN. 
For a 2002 Ram, the important point is protocol support. ScanGauge lists 1996–2002 Dodge/Chrysler/Jeep as ISO, and a good multi-protocol adapter should support ISO 9141-2 / ISO 14230 as well as J1850 variants. 
If you want something analogous to the vLinker you use on your Ford, I would look at a Vgate vLinker MC+ or an OBDLink MX+ rather than a bargain generic ELM327. Those support the older protocols this truck may use and give you much better odds of reliable live data. The vLinker MC+ supports ISO 9141-2, ISO 14230, J1850 PWM/VPW, CAN, and more. 
One caveat: FORScan is Ford/Mazda-focused, so this would not be the software path for the Dodge. For the Ram, you’d instead use software such as OBD Fusion, Torque, Car Scanner, or Chrysler-specific software if you want deeper module access.
For basic engine data and codes, something like this style of adapter is appropriate:
vLinker MC Plus OBDII Bluetooth Adapter
$105.95
·
VXB Bearings
Vgate iCar Pro Bluetooth 4.0 OBD2 Scanner
$26.79
·
Walmart - OBD2 Store
Innova 3210RS Bluetooth OBD2 Code Reader
$39.99
·
AutoZone
If this is specifically a 2002 Ram 2500 with the 5.9 Cummins, tell me that, and I’ll narrow it down to the best adapter/software combination for the Cummins ECM and tell you what live PIDs you can realistically expect to get.
I mean, what is the best software for it and what's the best device for that software?
For a 2002 Dodge Ram 2500, Master, the best answer depends heavily on whether it is the 5.9 Cummins diesel or a gasoline engine. For a 2002 specifically, I would not recommend AlfaOBD or JScan as the primary choice: AlfaOBD’s current supported-vehicle list starts Ram 2500/3500 at 2006, and JScan likewise lists the DR Ram starting around 2006. 
For a 2002 5.9 Cummins, the gold-standard software/tool family is still Chrysler DRB III / DRB III-emulation-capable diagnostic equipment, because that is the factory-era diagnostic platform for the truck. It gives you access beyond generic OBD-II: Chrysler-specific modules, enhanced live data, actuator tests, ABS, transmission functions, etc. The downside is that genuine DRB III hardware is old and expensive, and clone/emulation solutions vary a lot in quality.
If your goal is more like what you’re doing with FORScan on the Ford—codes, live engine data, logging, and diagnostics without spending dealer-tool money—I’d use a high-quality multi-protocol adapter such as the OBDLink MX+ and software that can access Chrysler-enhanced data on that generation. The MX+ is the safer hardware choice because it supports the older ISO/J1850-era protocols as well as newer networks, and it’s substantially more trustworthy than generic ELM327 dongles.
OBDLink MX+ Bluetooth Scanner
$214.88
·
VXB Bearings
For a cheaper adapter, the vLinker MC+ is also a solid piece of hardware and supports the legacy OBD protocols you need.
vLinker MC+ OBDII Bluetooth Adapter
$105.95 · VXB Bearings
The key difference from your Ford setup is this:
Your 7.3 Ford	2002 Dodge Ram
FORScan	No true equivalent this old that is as clean/simple
vLinker/OBDLink	OBDLink MX+ / vLinker works
Excellent Ford-specific PID coverage	Generic + some Chrysler-enhanced access
Easy module access	Full factory-level access usually means DRB III
If this is the 2002 5.9 Cummins, tell me that and I’ll do a deeper pass specifically on that ECM and give you the best software + adapter combination for live Cummins data, including whether we can read things like injection timing, commanded fuel, VP44-related data, transmission parameters, boost, coolant temp, and fault codes.
How long after turning my key off should my, um, my telemetry device turn off? I built it and attached it, and I'm just not sure. I haven't timed it yet.
Master, based on the shutdown behavior we designed, I’d expect it to begin shutting down about 30–60 seconds after you turn the key off, then take roughly another 5–15 seconds for Linux to finish shutting down.
So as a practical expectation:
Key OFF → about 35–75 seconds → telemetry device is shut down
The exact number depends on whatever delay we actually configured in the software.
One important distinction, Meatbag: the ignition circuit you just built only tells the Pi “the key is off.” It does not automatically remove 5 V power from the Pi by itself. If your power setup keeps supplying the Zero continuously, Linux can shut down and the screen can go dark while the Pi still has electrical power present.
A quick test will tell us exactly what’s happening. Turn the truck on, let the telemetry system fully boot, then turn the key off and time from key OFF until the screen goes black. If it shuts off around a minute later, that’s consistent with our intended behavior. If it shuts off instantly, stays running indefinitely, or comes back on by itself, tell me what it does and we’ll trace the ignition GPIO and shutdown service.
How accurate is the speed reading on the telemetry device?
Pretty accurate, Master—provided the value is coming directly from the truck’s PCM over OBD and your tire/axle setup still matches what the PCM expects.
For our telemetry device, the displayed speed is not being estimated from GPS; it’s reading the truck’s vehicle speed PID. That means its accuracy is basically the accuracy of the truck’s own vehicle-speed calculation.
In practice, I’d expect something on the order of:
within about 1–2 mph at normal road speeds
if the truck is stock-calibrated and tire size is close to factory.
The biggest sources of error are:
non-stock tire diameter
different axle gearing
PCM/speedometer calibration not matching the actual truck
low-speed quantization/rounding from the PID
A larger tire makes the truck travel farther per wheel revolution, so the PCM will generally under-report actual speed unless corrected. A smaller tire does the opposite.
For example, if your actual tire diameter is 5% larger than the diameter the PCM is calibrated for:
60 mph indicated ≈ 63 mph actual
The telemetry display should usually agree very closely with your dash speedometer, because both ultimately derive from the same vehicle-speed information.
The easiest way to test yours is to compare three readings at steady speed:
truck speedometer
telemetry display
GPS speed from your phone
Do it around 30, 50, and 65 mph. GPS over a straight, steady road is a good reference. If you give me those three comparisons, Meatbag, I can calculate the correction factor for the telemetry display if it needs one.
If i had a fuel leak would the calculation include the fuel leak or would it not?
No, Master—not with the MPG calculation we’ve been discussing for the telemetry device.
If we calculate fuel consumption from engine/injector data—RPM, injector pulse width, estimated fuel per injection, etc.—we're estimating how much fuel the engine actually injects/burns. An external fuel leak is invisible to that calculation.
So, for example, if the engine is consuming 2.0 gal/hr but a leak is losing another 0.5 gal/hr:
Telemetry would calculate MPG using 2.0 gal/hr
The fuel tank is actually losing 2.5 gal/hr
Therefore the displayed MPG would be too high
If you're traveling 40 mph:
40
/
2.0
=
20
 MPG displayed
40/2.0=20 MPG displayed
but actual tank consumption would be:
40
/
2.5
=
16
 MPG actual
40/2.5=16 MPG actual
A tank-to-tank MPG calculation—miles driven divided by gallons required to refill the tank—would include the leak automatically because it measures all fuel that disappeared from the tank.
So this gives us a useful diagnostic feature: if our telemetry consistently says, say, 18 MPG while fill-up calculations show 14 MPG, that discrepancy could indicate a calibration error or fuel being lost somewhere other than through the injectors, including a leak.