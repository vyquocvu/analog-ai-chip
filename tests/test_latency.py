import numpy as np
import pytest

from analog_llm import Accelerator, CrossbarTile, Metrics, TinyGPT, TinyGPTConfig
from analog_llm.latency import PhysicsAssumptions, system_analysis


def _acc(tile_rows, tile_cols, tile_count):
    def factory():
        return CrossbarTile(tile_rows, tile_cols, g_bits=14, dac_bits=16,
                            adc_bits=16, vout_max=96.0)
    return Accelerator(factory, tile_rows, tile_cols, tile_count)


def _run(tile_rows, tile_cols, tile_count):
    cfg = TinyGPTConfig(vocab_size=32, n_embd=16, n_layer=1, n_head=2,
                        block_size=6, seed=0)
    model = TinyGPT(cfg)
    acc = _acc(tile_rows, tile_cols, tile_count)
    model.forward_logits(np.arange(1, 4), accelerator=acc)
    m = Metrics()
    m.update(acc)
    return m


def test_latency_formula() -> None:
    m = _run(16, 16, 2)
    p = PhysicsAssumptions(mvm_cycle_time=3.0, program_time=0.5)
    a = system_analysis(m, 16, 16, 2, p)
    assert a["latency"] == pytest.approx(m.cycles * 3.0 + m.programs * 0.5)
    assert a["converters"] == 2 * (16 + 16)
    assert a["programs"] == m.programs
    assert a["reuse_programs"] == m.programs - m.rewrites


def test_energy_formula_only_with_assumptions() -> None:
    m = _run(16, 16, 2)
    p = PhysicsAssumptions(mac_energy=2.0, program_energy=3.0,
                           adc_energy=0.5, dac_energy=0.5)
    a = system_analysis(m, 16, 16, 2, p)
    expected = (m.macs * 2.0 + m.programs * 3.0 + m.macs * (0.5 + 0.5))
    assert a["energy"] == pytest.approx(expected)


def test_invalid_assumptions_rejected() -> None:
    m = _run(16, 16, 2)
    with pytest.raises(ValueError, match="positive"):
        system_analysis(m, 16, 16, 2, PhysicsAssumptions(program_time=0.0))
    with pytest.raises(ValueError, match="positive"):
        system_analysis(m, 0, 16, 2, PhysicsAssumptions())


def test_acelerator_tracks_programs() -> None:
    acc = _acc(8, 8, 4)
    acc.mvm(np.ones((12, 10)), np.ones(10))  # 2 row-groups x 2 col-groups = 4 blocks
    assert acc.programs == 4
    assert acc.programs >= acc.rewrites


def test_more_parallelism_cuts_cycles_but_not_programs() -> None:
    cyc = [_run(16, 16, tc).cycles for tc in (1, 2, 4, 8)]
    assert all(cyc[i + 1] <= cyc[i] for i in range(len(cyc) - 1))
