# Source and evidence notes

Reviewed for Rev A on 2026-09-11:

- KiCad 10.0.6 release and CLI documentation:
  <https://www.kicad.org/blog/2026/08/KiCad-10.0.6-Release/> and
  <https://docs.kicad.org/10.0/en/cli/cli.html>.
- STM32U575VGT6 product information and datasheet:
  <https://www.st.com/en/microcontrollers-microprocessors/stm32u575vg.html>.
- BQ25120A charger/power-path PMIC datasheet:
  <https://www.ti.com/lit/ds/symlink/bq25120a.pdf>.
- Sharp memory-LCD selection table for LS027B7DH01:
  <https://global.sharp/products/device/lineup/selection/lcd/mobile/index.html>.

The Sharp listing's 175 µW value applies to its specified update pattern. It is
not treated as a universal static-hold measurement. BQ25120A SYS buck and LS/LDO
outputs are software-configurable resources with a documented startup sequence,
not three independently verified fixed rails.

The 0.32 mm nominal 50-ohm geometry is an IPC-style preliminary calculation.
Material Dk, copper thickness, dielectric height, etch, and soldermask require a
selected fabricator stackup; controlled impedance remains `assumed` until then.

The connector land pattern and board outline are project-local design sources.
Before ordering assembled boards, independently compare every land pattern,
polarity mark, connector mating orientation, and component suffix against the
supplier's current mechanical drawing and the assembler's library.

## Electrical completeness review — 2026-09-23

The generated carrier is not build-ready. The following manufacturer requirements
are not implemented by the placeholder sheets, net connections and footprints:

- TI BQ25120A SLUSD08A, pp. 4–5 and 47–48: YFP is a 25-ball DSBGA;
  SW–SYS requires a 2.2 µH inductor plus specified input, output and battery
  capacitors. The current BOM has no inductors or capacitors. Pages 18–19,
  30–31 and 41 describe CD, ship-mode and LS/LDO state constraints; a default
  1.8 V SYS alone does not prove MCU startup or battery-only I²C access.
- [Sharp LS027B7DH01 specification](https://cdn-learn.adafruit.com/assets/assets/000/094/215/original/LS027B7DH01_Rev_Jun_2010.pdf?1597872422),
  printed pp. 8–14, 19 and 24: VDD and VDDA require 4.8–5.5 V, while
  VIH is at least 2.70 V. Five-volt logic translation is not inherently required;
  VOL, power-off limits, sequencing and COM inversion still need verification.
- [Hirose DF40 catalog](https://www.hirose.com/en/product/document?clcode=&productname=&series=DF40&documenttype=Catalog&lang=en&documentid=en_DF40_CAT),
  p. 14: DF40C-40DP dimensions and recommended retention lands do not match
  the generated connector footprint. Replace it from the manufacturer drawing,
  not by renaming the footprint identifier.

The ST datasheet could not be retrieved during this review. MCU supply pins,
decoupling, alternate-function mapping and 1.8 V startup/BOR compatibility remain
unverified. No research finding here constitutes circuit or bench verification.
