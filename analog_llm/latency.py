"""System-level latency / energy model for the accelerator (measured-only inputs).

This turns the physical ledger (MACs, tile cycles, rewrites, programs) into an
explicit latency and (optional) energy *formula* from parameters the designer
supplies. The parameters are ASSUMPTIONS, not measured silicon values: the
model does not claim any real energy or wall-clock number, and it never
compares against a GPU or a fabricated baseline.

Conventions (consistent with ``tile.py`` / ``PRODUCT_SPEC.md``):
  - one DAC per input line, one ADC per output line on each physical tile, so
    a board of ``tile_count`` x ``(rows x cols)`` tiles has
    ``tile_count*(cols)`` DACs and ``tile_count*(rows)`` ADCs;
  - each block is programmed onto a tile once (``programs``); reuse beyond the
    on-board count shows up as ``rewrites``;
  - MVM time = ``tile_cycles * mvm_cycle_time`` (tiles run in parallel);
  - program time = ``programs * program_time``.

All reported numbers are model estimates built from these assumptions; they are
not measurements and carry no speed/efficiency claim.
"""

from __future__ import annotations

from dataclasses import dataclass

from .transformer import Metrics


@dataclass(frozen=True)
class PhysicsAssumptions:
    """Timing / energy parameters in relative units. ALL are designer
    assumptions (time units ``tu`` / energy units ``eu``), not measurements."""

    mvm_cycle_time: float = 1.0   # tu per tile MVM cycle
    program_time: float = 1.0     # tu per tile program
    dac_energy: float = 0.0       # eu per DAC conversion (assumed)
    adc_energy: float = 0.0       # eu per ADC conversion (assumed)
    mac_energy: float = 0.0       # eu per resolved differential MAC (assumed)
    program_energy: float = 0.0   # eu per tile program (assumed)

    def validate(self) -> None:
        if self.mvm_cycle_time <= 0 or self.program_time <= 0:
            raise ValueError("mvm_cycle_time and program_time must be positive")
        for v in (self.dac_energy, self.adc_energy, self.mac_energy, self.program_energy):
            if v < 0:
                raise ValueError("energies must be non-negative")


def system_analysis(
    metrics: Metrics,
    tile_rows: int,
    tile_cols: int,
    tile_count: int,
    phys: PhysicsAssumptions,
) -> dict[str, float]:
    """Combine the ledger with assumptions into latency / energy estimates."""
    if tile_rows <= 0 or tile_cols <= 0 or tile_count <= 0:
        raise ValueError("tile dims and count must be positive")
    phys.validate()

    dac_count = tile_count * tile_cols       # DACs on board
    adc_count = tile_count * tile_rows       # ADCs on board
    converters = dac_count + adc_count

    mvm_time = metrics.cycles * phys.mvm_cycle_time
    program_time = metrics.programs * phys.program_time
    latency = mvm_time + program_time

    energy = (metrics.macs * phys.mac_energy
              + metrics.programs * phys.program_energy
              + metrics.macs * phys.adc_energy + metrics.macs * phys.dac_energy)

    reuse = metrics.programs - metrics.rewrites  # initial (non-reuse) programs
    return {
        "mvm_cycles": float(metrics.cycles),
        "programs": float(metrics.programs),
        "rewrites": float(metrics.rewrites),
        "dac_count": float(dac_count),
        "adc_count": float(adc_count),
        "converters": float(converters),
        "reuse_programs": float(reuse),
        "mvm_time": mvm_time,
        "program_time": program_time,
        "latency": latency,
        "energy": energy,
    }


def format_system(a: dict[str, float], phys: PhysicsAssumptions) -> str:
    lines = [
        "SYSTEM ESTIMATE (model, relative units tu/eu, not measured; no GPU comparison)",
        (f"  converters on board : {int(a['dac_count'])} DACs + {int(a['adc_count'])} ADCs"
         f" = {int(a['converters'])}"),
        (f"  tile MVM cycles     : {int(a['mvm_cycles'])}   (mvm time ="
         f" {a['mvm_time']:.3g} tu @ {phys.mvm_cycle_time:g} tu/cycle)"),
        (f"  tile programs       : {int(a['programs'])}   (of which reuse {int(a['rewrites'])})"
         f"   (program time = {a['program_time']:.3g} tu @ {phys.program_time:g} tu/program)"),
        f"  latency estimate    : {a['latency']:.3g} tu",
        (f"  energy estimate     : {a['energy']:.3g} eu   (per-op energies are assumptions:"
         f" dac {phys.dac_energy:g}, adc {phys.adc_energy:g}, mac {phys.mac_energy:g},"
         f" program {phys.program_energy:g})"),
    ]
    return "\n".join(lines)
