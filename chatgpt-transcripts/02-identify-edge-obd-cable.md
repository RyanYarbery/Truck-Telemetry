# Identify Edge OBD Cable

Source: ChatGPT project "Truck Telemetry", chat "Identify Edge OBD Cable" (Sep 15, 2025). Extracted 2026-10-24 by copying the rendered chat text; speaker labels are not preserved, "User attachment" marks a photo Ryan sent, and image-only replies leave no text.

---


User attachment
User attachment
User attachment
User attachment
User attachment
User attachment
User attachment
Identification: that is an Edge Products OBD-II interface cable/module from the display that used to be in your truck, Meatbag. The rectangular plug in your hand is the standard 16-pin OBD-II connector, and the warning tag confirms it: “UN-PLUG PRODUCT FROM OBDII PORT BEFORE JUMP STARTING VEHICLE.” The Edge manual describes this type of cable as the communication, power, and ground link between the vehicle and the Edge display. 

For our truck-telemetry project, this is potentially very useful, but I would not cut it open yet. The important distinction is that the vehicle side is standard OBD-II/J1850, while the cable running from this Edge module to the old display is likely an Edge-proprietary electrical/protocol interface. In other words, exposing those wires does not necessarily give us simple TX/RX serial that a Raspberry Pi or Pico can understand.

Because your truck is the 2001 F-350 7.3L Power Stroke, the OBD-II network we're interested in is primarily SAE J1850 PWM, not modern CAN bus. That matters considerably. A generic modern CAN transceiver will not work by itself.

The best route is therefore:

Keep this Edge cable intact.
Plug its OBD-II end back into the truck only when we are ready to test.
Determine what the connector at the other end of the cable is electrically carrying.
In parallel, we can access the truck directly from the OBD-II port with a J1850-capable interface, which is likely cleaner and much easier to document.
Once we have communication working, a Raspberry Pi can collect PID data and serve it to your phone over Wi-Fi/Bluetooth just like we discussed for the telemetry system.
Your photos also give us two potentially useful identification numbers: H00005100 and 200145962 / 31111. I searched those exact markings; they do not appear to be public Edge retail part numbers, so they are likely internal cable/manufacturing identifiers rather than something we can use to obtain a pinout.

One other useful detail: Edge's older displays explicitly used an OBD-II-to-display cable carrying vehicle communication plus power/ground, so the little Edge box is not merely an extension cord. 

The next thing I want, Master, is a clear photo of the very end of the cable that used to plug into the display—straight at the connector so I can count the contacts and identify the connector family. Do not cut or strip anything yet. Once I see that end, I can tell you whether this cable is worth reverse-engineering or whether we should leave it alone and connect our Pi directly to the truck's diagnostic bus.





