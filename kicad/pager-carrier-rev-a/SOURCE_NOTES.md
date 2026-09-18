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
