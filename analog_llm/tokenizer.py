"""Minimal byte-level BPE tokenizer for GPT-2 (vocab.json + merges.txt).

A small, dependency-free implementation of the standard GPT-2 tokenizer so the
demo can encode and decode real text without pulling in the ``tokenizers``
package. It uses the byte->unicode mapping from the GPT-2 paper, applies the
learned merges, and maps the result to vocab ids. ``decode`` inverts ids back
to text (with ``errors='replace'`` for any id the vocabulary doesn't cover).
"""

from __future__ import annotations

import json
from pathlib import Path


def _bytes_to_unicode() -> dict[int, str]:
    bs = list(range(ord("!"), ord("~") + 1))
    bs += list(range(ord("¡"), ord("¬") + 1))
    bs += list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(2 ** 8 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))


def _get_pairs(word: list[str]) -> set[tuple[str, str]]:
    pairs = set()
    prev = word[0]
    for char in word[1:]:
        pairs.add((prev, char))
        prev = char
    return pairs


class GPT2Tokenizer:
    def __init__(self, vocab_path: str | Path, merges_path: str | Path) -> None:
        with open(vocab_path) as fh:
            self.vocab: dict[str, int] = json.load(fh)
        with open(merges_path) as fh:
            lines = [l.split() for l in fh if l.strip() and not l.strip().startswith("#")]
        self.merges = [tuple(pair) for pair in lines]
        self.merge_rank = {pair: i for i, pair in enumerate(self.merges)}
        self.b2u = _bytes_to_unicode()
        self.u2b = {v: k for k, v in self.b2u.items()}
        self.id2str = {v: k for k, v in self.vocab.items()}

    def encode(self, text: str) -> list[int]:
        b = text.encode("utf-8")
        tokens = [self.b2u[c] for c in b]
        while len(tokens) >= 2:
            pairs = _get_pairs(tokens)
            bigram = min(pairs, key=lambda p: self.merge_rank.get(p, float("inf")))
            if bigram not in self.merge_rank:
                break
            first, second = bigram
            merged: list[str] = []
            i = 0
            while i < len(tokens):
                if (tokens[i] == first and i + 1 < len(tokens)
                        and tokens[i + 1] == second):
                    merged.append(first + second)
                    i += 2
                else:
                    merged.append(tokens[i])
                    i += 1
            tokens = merged
        ids = [self.vocab[t] for t in tokens if t in self.vocab]
        if not ids:
            ids = [self.vocab.get(self.b2u[b], 0) for b in b]
        return ids

    def decode(self, ids: list[int]) -> str:
        out = bytearray()
        for i in ids:
            token = self.id2str.get(i, "")
            for ch in token:
                if ch in self.u2b:
                    out.append(self.u2b[ch])
                else:
                    out.append(ord("?"))
        return out.decode("utf-8", errors="replace")
