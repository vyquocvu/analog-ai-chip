"""M5 — run a real pretrained GPT-2 checkpoint through the simulator.

Loads a real open checkpoint (``pszemraj/tiny-gpt2-magicprompt``, a trained
tiny GPT-2) from safetensors via ``load_gpt2``, encodes a real prompt with a
minimal byte-level BPE tokenizer, and runs it both as the float baseline and
through the simulated tile accelerator at a high- and a budget- resolution.

Reports the accuracy-vs-baseline table (token agreement + max logit error) and
a short failure analysis: which configuration degrades, which positions flip,
and the physical ledger. All numbers are simulation metrics; no energy/GPU
advantage is claimed.

The checkpoint is downloaded once into ``data/gpt2-tiny`` if not present.
"""

import json
import urllib.request
from pathlib import Path

import numpy as np

from analog_llm import Accelerator, CrossbarTile
from analog_llm.gpt_loader import load_gpt2
from analog_llm.report import max_abs_logit_error, token_agreement
from analog_llm.tokenizer import GPT2Tokenizer

REPO = "pszemraj/tiny-gpt2-magicprompt"
DATA = Path(__file__).resolve().parents[1] / "data" / "gpt2-tiny"
FILES = ["model.safetensors", "config.json", "vocab.json", "merges.txt"]

PROMPT = "Once upon a time,"
MAX_NEW = 8

TILE_ROWS, TILE_COLS, TILE_COUNT = 1024, 8, 4


def ensure_checkpoint() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        if not (DATA / f).exists():
            print(f"downloading {f} ...")
            url = f"https://huggingface.co/{REPO}/resolve/main/{f}"
            urllib.request.urlretrieve(url, DATA / f)


def build_acc(**kw) -> Accelerator:
    def factory() -> CrossbarTile:
        return CrossbarTile(TILE_ROWS, TILE_COLS, **kw)
    return Accelerator(factory, TILE_ROWS, TILE_COLS, TILE_COUNT)


def main() -> None:
    ensure_checkpoint()
    with open(DATA / "config.json") as fh:
        cfg = json.load(fh)
    block = 64
    model = load_gpt2(DATA, block_size=block)
    tk = GPT2Tokenizer(DATA / "vocab.json", DATA / "merges.txt")

    tokens = np.asarray(tk.encode(PROMPT), dtype=np.int64)[:block - MAX_NEW]
    print("prompt tokens:", tokens.tolist(), "->", repr(tk.decode(tokens.tolist())))

    float_seq = model.generate(tokens, max_new=MAX_NEW, greedy=True)
    float_logits = model.forward_logits(float_seq)

    high = build_acc(g_bits=14, dac_bits=16, adc_bits=16, vout_max=8.0)
    hi_seq = model.generate(tokens, max_new=MAX_NEW, greedy=True, accelerator=high)
    hi_logits = model.forward_logits(hi_seq, accelerator=high)

    low = build_acc(g_bits=4, dac_bits=6, adc_bits=6, vout_max=8.0,
                    adc_noise_std=0.05, adc_gain=1.05, adc_offset=0.05,
                    rng=np.random.default_rng(0))
    lo_seq = model.generate(tokens, max_new=MAX_NEW, greedy=True, accelerator=low)
    lo_logits = model.forward_logits(lo_seq, accelerator=low)

    print("=" * 70)
    print("M5 — real pretrained GPT-2 through the simulated accelerator")
    print("=" * 70)
    print(f"model: tiny-gpt2 ({cfg['n_layer']}L {cfg['n_embd']}D {cfg['n_head']}H, "
          f"vocab {cfg['vocab_size']}); tile {TILE_ROWS}x{TILE_COLS} x{TILE_COUNT}")
    print("-" * 70)
    print("float baseline  :", repr(tk.decode(float_seq.tolist())))
    print("analog high-prec:", repr(tk.decode(hi_seq.tolist())))
    print("analog budget   :", repr(tk.decode(lo_seq.tolist())))
    print("-" * 70)
    print("accuracy vs float baseline (full sequence)")
    print(f"  high-precision: agreement {token_agreement(float_seq, hi_seq):.3f}, "
          f"max logit err {max_abs_logit_error(float_logits, hi_logits):.4f}")
    print(f"  budget        : agreement {token_agreement(float_seq, lo_seq):.3f}, "
          f"max logit err {max_abs_logit_error(float_logits, lo_logits):.4f}")
    print("-" * 70)
    print("failure analysis (budget config):")
    flip = [i - tokens.size for i in range(tokens.size, float_seq.size)
            if float_seq[i] != lo_seq[i]]
    print(f"  generated positions that flipped vs float: {flip or 'none'}")
    print(f"  ledger: macs={low.macs} cycles={low.tile_cycles} rewrites={low.rewrites}")

    # guardrails: high-precision should be at least as accurate as budget
    assert token_agreement(float_seq, hi_seq) >= token_agreement(float_seq, lo_seq)
    assert max_abs_logit_error(float_logits, hi_logits) <= \
        max_abs_logit_error(float_logits, lo_logits) + 1e-6
    assert model.cfg.n_layer == cfg["n_layer"] and model.cfg.vocab_size == cfg["vocab_size"]


if __name__ == "__main__":
    main()
