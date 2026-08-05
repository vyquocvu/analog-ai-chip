import numpy as np
import pytest

from analog_llm import Accelerator, CrossbarTile
from analog_llm.report import format_report


def _acc(tr, tc, tcount):
    def factory():
        return CrossbarTile(tr, tc, g_bits=14, dac_bits=16, adc_bits=16, vout_max=64.0)
    return Accelerator(factory, tr, tc, tcount)


def _br_bc(rows, cols, tr, tc):
    return int(np.ceil(rows / tr)), int(np.ceil(cols / tc))


@pytest.mark.parametrize("rows,cols,tr,tc,tcount", [
    (4, 5, 2, 2, 1), (4, 5, 2, 2, 4), (6, 6, 3, 3, 2),
    (12, 10, 3, 3, 4), (24, 16, 8, 8, 6),
])
def test_cycles_and_rewrites_formula(rows, cols, tr, tc, tcount) -> None:
    br, bc = _br_bc(rows, cols, tr, tc)
    blocks = br * bc
    acc = _acc(tr, tc, tcount)
    acc.mvm(np.ones((rows, cols)), np.ones(cols))
    assert acc.tile_cycles == int(np.ceil(blocks / tcount))
    assert acc.rewrites == max(0, blocks - tcount)
    assert acc.programs == blocks
    assert acc.programs == acc.rewrites + min(blocks, tcount)


def test_report_exposes_scheduler_ledger() -> None:
    acc = _acc(4, 4, 2)
    acc.mvm(np.ones((6, 6)), np.ones(6))  # 2x2=4 blocks over 2 tiles
    from analog_llm import Metrics
    m = Metrics()
    m.update(acc)
    report = format_report({"matrix": "6x6"}, m, {})
    low = report.lower()
    assert "tile mvm cycles" in low and "tile rewrites" in low and "tile programs" in low
