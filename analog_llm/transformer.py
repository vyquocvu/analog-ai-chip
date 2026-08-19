"""A small decoder-only transformer (nanoGPT-style) that can run in pure numpy.

The transformer is deliberately small and deterministic (seeded weights) so
the analog-mapped path is reproducible on any machine with numpy installed.

Hybrid scope
------------
Only the linear layers (attention QKV, attention output, MLP up/down, and the
head) are matrix-vector multiplications and are routed through the analog
tile accelerator. Layer-norm, softmax, GELU, residual adds, bias adds, and the
embedding lookup are computed digitally. This is the honest hybrid split: the
analog crossbar accelerates dense matmuls, everything else stays digital.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from .accelerator import Accelerator
from .decoder_primitives import cached_attention_step, causal_attention, gelu, layer_norm


@dataclass
class TinyGPTConfig:
    vocab_size: int = 128
    n_embd: int = 64
    n_layer: int = 2
    n_head: int = 4
    block_size: int = 16
    ffn_mult: int = 4
    seed: int = 0


@dataclass
class Metrics:
    macs: int = 0
    cycles: int = 0
    rewrites: int = 0
    programs: int = 0

    def update(self, acc: Accelerator) -> None:
        self.macs += acc.macs
        self.cycles += acc.tile_cycles
        self.rewrites += acc.rewrites
        self.programs += acc.programs


@dataclass
class TinyGPT:
    cfg: TinyGPTConfig
    weights: dict[str, NDArray[np.float64]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.weights:
            self._init_weights()

    # -- weight initialization (deterministic) -------------------------------
    def _init_weights(self) -> None:
        cfg = self. cfg
        rng = np.random.default_rng(cfg.seed)
        std = 0.02
        w = self.weights
        w["tok_emb"] = rng.normal(0, std, (cfg.vocab_size, cfg.n_embd))
        w["pos_emb"] = rng.normal(0, std, (cfg.block_size, cfg.n_embd))
        for i in range(cfg.n_layer):
            p = f"{i}."
            sd = 1.0 / math.sqrt(cfg.n_embd)
            w[p + "ln1"] = np.ones(cfg.n_embd)
            w[p + "ln1b"] = np.zeros(cfg.n_embd)
            w[p + "wqkv"] = rng.normal(0, sd, (3 * cfg.n_embd, cfg.n_embd))
            w[p + "wqkvb"] = np.zeros(3 * cfg.n_embd)
            w[p + "wo"] = rng.normal(0, sd, (cfg.n_embd, cfg.n_embd))
            w[p + "wob"] = np.zeros(cfg.n_embd)
            w[p + "ln2"] = np.ones(cfg.n_embd)
            w[p + "ln2b"] = np.zeros(cfg.n_embd)
            ffn = cfg.n_embd * cfg.ffn_mult
            w[p + "wup"] = rng.normal(0, sd, (ffn, cfg.n_embd))
            w[p + "wupb"] = np.zeros(ffn)
            w[p + "wdown"] = rng.normal(0, sd, (cfg.n_embd, ffn))
            w[p + "wdownb"] = np.zeros(cfg.n_embd)
        w["lnf"] = np.ones(cfg.n_embd)
        w["lnfb"] = np.zeros(cfg.n_embd)
        w["head"] = rng.normal(0, 0.02, (cfg.vocab_size, cfg.n_embd))
        w["headb"] = np.zeros(cfg.vocab_size)

    # -- ops -----------------------------------------------------------------
    @staticmethod
    def _layernorm(x: NDArray[np.float64], g: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.float64]:
        return layer_norm(x, g, b)

    @staticmethod
    def _gelu(x: NDArray[np.float64]) -> NDArray[np.float64]:
        return gelu(x)

    # -- linear backends -----------------------------------------------------
    def _bound_lin(self, accelerator: Accelerator | None):
        if accelerator is None:
            return self._float_lin
        return lambda name, h: self._analog_lin(accelerator, name, h)

    def _float_lin(self, name: str, h: NDArray[np.float64]) -> NDArray[np.float64]:
        return h @ self.weights[name].T + self.weights[name + "b"]

    def _analog_lin(self, acc: Accelerator, name: str, h: NDArray[np.float64]) -> NDArray[np.float64]:
        w = self.weights[name]
        bias = self.weights[name + "b"]
        out = np.zeros((h.shape[0], w.shape[0]), dtype=np.float64)
        for i in range(h.shape[0]):
            out[i] = acc.mvm(w, h[i]) + bias
        return out

    # -- forward -------------------------------------------------------------
    def forward_logits(
        self, tokens: NDArray[np.int64], accelerator: Accelerator | None = None
    ) -> NDArray[np.float64]:
        """Returns logits ``[seq, vocab]``; if accelerator is None, runs float."""
        lin = self._bound_lin(accelerator)
        cfg = self.cfg
        w = self.weights
        tokens = np.asarray(tokens, dtype=np.int64).reshape(-1)
        if tokens.size == 0 or tokens.size > cfg.block_size:
            raise ValueError(f"sequence length must be in [1, {cfg.block_size}]")
        B = tokens.size

        tok = w["tok_emb"][tokens]                      # [B, C]
        pos = w["pos_emb"][:B]                          # [B, C]
        x = tok + pos

        for i in range(cfg.n_layer):
            p = f"{i}."
            # attention
            h = self._layernorm(x, w[p + "ln1"], w[p + "ln1b"])
            qkv = lin(p + "wqkv", h)  # [B, 3C]
            C = cfg.n_embd
            q, k, v = qkv[:, :C], qkv[:, C:2 * C], qkv[:, 2 * C:]
            nh, hd = cfg.n_head, C // cfg.n_head
            q = q.reshape(B, nh, hd)
            k = k.reshape(B, nh, hd)
            v = v.reshape(B, nh, hd)
            attn = causal_attention(q, k, v).reshape(B, C)
            attn = lin(p + "wo", attn)
            x = x + attn

            # mlp
            h2 = self._layernorm(x, w[p + "ln2"], w[p + "ln2b"])
            up = lin(p + "wup", h2)
            act = self._gelu(up)
            down = lin(p + "wdown", act)
            x = x + down

        x = self._layernorm(x, w["lnf"], w["lnfb"])
        logits = lin("head", x)  # [B, vocab]
        return logits

    # -- generation ----------------------------------------------------------
    def generate(
        self, prompt: NDArray[np.int64], max_new: int = 8, greedy: bool = True,
        accelerator: Accelerator | None = None, rng: np.random.Generator | None = None,
    ) -> NDArray[np.int64]:
        """Autoregressive generation without a KV cache (simple, honest reference)."""
        prompt = np.asarray(prompt, dtype=np.int64).reshape(-1)
        out = list(prompt.tolist())
        for _ in range(max_new):
            ctx = np.asarray(out[-self.cfg.block_size:], dtype=np.int64)
            logits = self.forward_logits(ctx, accelerator=accelerator)
            logit = logits[-1]
            if greedy:
                nxt = int(np.argmax(logit))
            else:
                if rng is None:
                    raise ValueError("rng required for sampling")
                p = np.exp(logit - logit.max())
                p = p / p.sum()
                nxt = int(rng.choice(len(p), p=p))
            out.append(nxt)
        return np.asarray(out, dtype=np.int64)

    # -- KV-cache generation (no full-context recompute) ---------------------
    def _init_kv_cache(self) -> dict[str, list]:
        return {"k": [None] * self.cfg.n_layer, "v": [None] * self.cfg.n_layer}

    def _step(self, token: int, pos: int, cache, accelerator: Accelerator | None) -> NDArray[np.float64]:
        """One position's forward using the running K/V cache; returns logits."""
        cfg = self.cfg
        if pos >= cfg.block_size:
            raise ValueError(f"position {pos} exceeds block_size {cfg.block_size}")
        w = self.weights
        lin = self._bound_lin(accelerator)
        x = w["tok_emb"][token] + w["pos_emb"][pos]  # [C]
        for i in range(cfg.n_layer):
            p = f"{i}."
            h = self._layernorm(x[None, :], w[p + "ln1"], w[p + "ln1b"])[0]
            qkv = lin(p + "wqkv", h[None, :])[0]  # [3C]
            C = cfg.n_embd
            q, k, v = qkv[:C], qkv[C:2 * C], qkv[2 * C:]
            nh, hd = cfg.n_head, C // cfg.n_head
            q = q.reshape(nh, hd)
            k = k.reshape(nh, hd)
            v = v.reshape(nh, hd)
            if cache["k"][i] is None:
                cache["k"][i] = k[None, :, :]
                cache["v"][i] = v[None, :, :]
            else:
                cache["k"][i] = np.concatenate([cache["k"][i], k[None, :, :]], axis=0)
                cache["v"][i] = np.concatenate([cache["v"][i], v[None, :, :]], axis=0)
            K = cache["k"][i]  # [pos+1, nh, hd]
            V = cache["v"][i]
            attn = cached_attention_step(q, K, V).reshape(C)
            x = x + lin(p + "wo", attn[None, :])[0]
            h2 = self._layernorm(x[None, :], w[p + "ln2"], w[p + "ln2b"])[0]
            up = lin(p + "wup", h2[None, :])[0]
            x = x + lin(p + "wdown", self._gelu(up)[None, :])[0]
        x = self._layernorm(x[None, :], w["lnf"], w["lnfb"])[0]
        return lin("head", x[None, :])[0]

    def generate_kvcache(
        self, prompt: NDArray[np.int64], max_new: int = 8, greedy: bool = True,
        accelerator: Accelerator | None = None, rng: np.random.Generator | None = None,
    ) -> NDArray[np.int64]:
        """Autoregressive generation with a KV cache (no per-step full-ctx recompute).

        Matches ``generate`` (same math); each new token runs a single-position
        forward that reuses cached keys/values instead of re-embedding and
        re-attending over the whole context.
        """
        prompt = np.asarray(prompt, dtype=np.int64).reshape(-1)
        cfg = self.cfg
        if prompt.size == 0 or prompt.size > cfg.block_size:
            raise ValueError(f"sequence length must be in [1, {cfg.block_size}]")
        cache = self._init_kv_cache()
        out = list(prompt.tolist())
        pos = 0
        logits: NDArray[np.float64] = np.zeros(cfg.vocab_size)
        for tok in prompt:
            logits = self._step(int(tok), pos, cache, accelerator)
            pos += 1
        for _ in range(max_new):
            if greedy:
                nxt = int(np.argmax(logits))
            else:
                if rng is None:
                    raise ValueError("rng required for sampling")
                p = np.exp(logits - logits.max())
                p = p / p.sum()
                nxt = int(rng.choice(len(p), p=p))
            out.append(nxt)
            if pos < cfg.block_size:
                logits = self._step(nxt, pos, cache, accelerator)
                pos += 1
        return np.asarray(out, dtype=np.int64)
