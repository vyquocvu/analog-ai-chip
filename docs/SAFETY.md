# Safety

This project is designed for low-voltage educational electronics.

## Allowed power sources

Use only one of these unless a chapter explicitly requires otherwise:

- USB 5 V from a protected development board;
- a current-limited bench supply set to the documented voltage;
- low-voltage battery power with appropriate regulation and protection.

Never connect a breadboard, exposed PCB, or project wire directly to mains electricity.

## Before powering a build

1. Disconnect power while changing wiring.
2. Confirm supply polarity and voltage with a multimeter.
3. Set a conservative current limit when using a bench supply.
4. Inspect for shorts between power and ground.
5. Verify IC orientation and pinout from the exact datasheet.
6. Begin with no external load and monitor component temperature.

## Analog measurement rules

- Keep input voltages within the documented common-mode range.
- Do not exceed ADC, DAC, op-amp, digital-pot, or microcontroller pin ratings.
- Avoid driving two active outputs against each other.
- Discharge capacitors before rewiring.
- Stop immediately if a component becomes hot, smells unusual, or draws unexpected current.

## Scope

This repository does not provide instructions for semiconductor fabrication, high-voltage forming of experimental memory devices, handling hazardous chemicals, or modifying mains-powered equipment. Experimental ReRAM modules must use commercially packaged evaluation devices and their manufacturer-approved programming equipment.

Every hardware chapter must state its expected supply voltage, maximum current, test points, and safe power-down procedure.
