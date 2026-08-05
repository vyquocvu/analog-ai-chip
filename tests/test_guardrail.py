from pathlib import Path

import pytest

from analog_llm.guardrail import check_python_files, check_text_claims

ROOT = Path(__file__).resolve().parent.parent


def test_all_our_python_files_are_clean() -> None:
    for sub in ("analog_llm", "scripts", "tests"):
        assert check_python_files(ROOT / sub) == 0


def test_honest_disclaimer_passes() -> None:
    check_text_claims("This is a simulator. No GPU comparison is made; not "
                      "wall-clock or energy; no energy/GPU claim.")


def test_claim_is_rejected() -> None:
    fast, target = "faster", "a gpu"
    claim = f"crossbar is {fast} than {target} for the multiply"
    with pytest.raises(ValueError, match="not backed by measurement"):
        check_text_claims(claim)


def test_oo1_claim_is_rejected() -> None:
    bigo, what = "O(1)", "inference"
    claim = f"achieves {bigo} {what} cost"
    with pytest.raises(ValueError, match="not backed by measurement"):
        check_text_claims(claim)
