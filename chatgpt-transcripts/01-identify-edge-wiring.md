# Identify Edge Wiring

Source: ChatGPT project "Truck Telemetry", chat "Identify Edge Wiring" (Sep 15, 2025). Extracted 2026-10-24 by copying the rendered chat text; speaker labels are not preserved, "User attachment" marks a photo Ryan sent, and image-only replies leave no text.

---


User attachment
User attachment
User attachment
Observation: these three photos are useful, Meatbag. They show that you do not just have a simple OBD-II-to-display cable. You appear to have part of an older Edge Products Juice/Attitude-style wiring system, which is much more interesting for our truck telemetry project.

The connectors visible are:

Photo 1: a 4-pin 2×2 female connector.
Photo 2: another 4-pin 2×2 connector/interface, apparently on an Edge-related module or adapter.
Photo 3: an 8-pin 2×4 female connector.
Edge's older 7.3L Power Stroke Juice systems used a separate engine-mounted module and an optional Attitude display, with wiring between the module, sensors, and display. Edge's own legacy documentation specifically shows the 7.3L system having an “Attitude Display Module” and a dedicated “connection to Edge Attitude or level selector switch.” 
 Their later 1999–2003 7.3L Juice/Attitude system likewise used a separate Juice module, harness, and Juice Attitude Bridge. 

What this means for our Raspberry Pi telemetry plan
Do not cut these wires yet.

There is a decent possibility that one of these cables carries power plus serial/digital communications from the Edge module, rather than raw analog sensor signals. If so, identifying the protocol could let us extract information the old Edge display used to show.

That could potentially include things such as:

ICP-related information
throttle position
MAP/boost data
EGT, if the Edge thermocouple system is still present
Edge power-level/status information
possibly other values computed by the Juice module
The original 7.3 Juice documentation confirms that the module interfaces with the truck's ICP sensor, throttle position sensor, MAP-related wiring, MAT connection, and optional EGT sensor, among other connections. 

But there is an important distinction: we cannot assume the 4-pin or 8-pin connector pinout just from its shape. Edge used several generations of displays and harnesses, and pin assignments changed. Feeding 5 V, 12 V, or Pi GPIO into the wrong conductor could destroy either the Edge module or the Pi.

So our next target is very specific:

Find exactly where the other end of each of these three connectors goes.

In particular, I want to know whether the cable in photo 3 ultimately goes to the truck's OBD-II connector, an Edge box/module under the dash or hood, or directly to the old display harness.

If you send me a photo showing the entire cable from one end to the other, especially any labels or numbers molded into the Edge module/display/connector, I can start pinning down the exact Edge generation and determine whether we can interface it safely with the Pi. For now, preserve all three connectors intact. They may be substantially more useful than cutting them off.

Identify the Edge harness safely

Plan safe electrical tests
Make a connector tracing checklist




