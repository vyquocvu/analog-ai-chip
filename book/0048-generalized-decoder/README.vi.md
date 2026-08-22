# 0048 — Tham Chiếu Chức Năng Decoder Tổng Quát (Gate R10)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **engine tham chiếu decoder tổng quát theo manifest (`GeneralizedDecoder`)** trong khuôn khổ **Gate R10 (Scalable model semantics & sharded checkpoints)**. Engine hợp nhất các hợp đồng schema từ Chương 0046 ([`ModelManifest`](../0046-model-manifest/)) và các primitive toán học từ Chương 0047 ([`decoder_primitives`](../0047-decoder-primitives/)) thành một engine thực thi độc lập kiến trúc, có khả năng đánh giá các biến thể Transformer hiện đại (GPT-2 MHA, LLaMA GQA, Hand-Calc MQA) dưới cả chế độ tham chiếu float thuần túy và gia tốc analog hướng profile.

---

## 1. Kiến Trúc Decoder Tổng Quát & Biên Tính Toán Lai Ghép

![Kiến Trúc Decoder Tổng Quát](diagrams/generalized-decoder.svg)

- **Cấu Hình Theo Manifest**: Tự động cấu hình normalization (`layernorm` / `rmsnorm`), embedding vị trí (`learned` / `rope`), hàm kích hoạt (`gelu` / `swiglu`), cơ chế attention (`mha` / `gqa` / `mqa`), và weight tying mà không ép các mô hình hiện đại vào cấu trúc cũ của GPT-2.
- **Biên Tính Toán Lai Ghép Nghiêm Ngặt**:
  - **Gia Tốc Bằng Analog**: Các ma trận trọng số projection tuyến tính ($W_Q, W_K, W_V, W_O$ và $W_{\text{gate}}, W_{\text{up}}, W_{\text{down}}$, cùng $W_{\text{head}}$ không buộc) được định tuyến qua các tile crossbar cố định thông qua [`Accelerator`](../../analog_llm/accelerator.py).
  - **Tham Chiếu Số NumPy**: Normalization, phép quay tọa độ RoPE, hàm kích hoạt phi tuyến, lũy thừa softmax và attention token-token động được giữ nguyên dưới dạng số thuần túy.
- **Cấp độ Tuyên bố**: `THAM CHIẾU PHẦN MỀM & CHỨC NĂNG` — thiết lập tính tương đương mô hình và định tuyến lai ghép; không chứng minh khả năng chứa toàn bộ mô hình lớn trên phần cứng.

---

## 2. Các Họ Kiến Trúc Được Hỗ Trợ

| Họ Kiến Trúc | Normalization | Mã Hóa Vị Trí | Kích Hoạt MLP | Chế Độ Attention | Weight Tying |
|---|---|---|---|---|---|
| **Dòng GPT-2** | LayerNorm (có bias) | Bảng Học Được | GELU | MHA ($Q_H = KV_H$) | Tied / Untied |
| **LLaMA / Mistral** | RMSNorm (không bias) | RoPE (Rotary) | SwiGLU (Gated) | GQA ($1 < KV_H < Q_H$) | Untied |
| **Mobile / Hand-Calc** | RMSNorm (không bias) | RoPE (Rotary) | SwiGLU (Gated) | MQA ($KV_H = 1$) | Tied |

---

## 3. Kiểm Tra Tính Tương Đương & Nhất Quán Với KV-Cache

Engine cung cấp cả phương thức lan truyền thuận toàn cảnh (`forward_logits`) và giải mã từng bước tích lũy KV-cache (`forward_step` / `generate_kvcache`):

| Mô Hình Benchmark | Cấu Hình Kiến Trúc | Số Tham Số | Độ Lệch Logit Max So Với Cache | Tính Tương Đương Greedy |
|---|---|---|---|---|
| **Hand-Calc MQA** | $1\text{L}, 4\text{D}, 2\text{Q}/1\text{KV}$, RMSNorm, RoPE, SwiGLU | $152$ | $6.94 \times 10^{-18}$ | **TRÙNG KHỚP** |
| **GPT-2 Style MHA** | $2\text{L}, 64\text{D}, 4\text{Q}/4\text{KV}$, LayerNorm, Learned, GELU | $109,312$ | $4.72 \times 10^{-16}$ | **TRÙNG KHỚP** |
| **LLaMA Style GQA** | $2\text{L}, 64\text{D}, 4\text{Q}/2\text{KV}$, RMSNorm, RoPE, SwiGLU | $115,008$ | $2.78 \times 10^{-16}$ | **TRÙNG KHỚP** |

*Tất cả các kiến trúc đều đạt độ chính xác máy tính ($\Delta < 10^{-12}$) giữa tính toán lại toàn bộ chuỗi và giải mã từng bước với KV-cache.*

---

## 4. Tích Hợp Tile Analog & Sổ Cái Thực Thi

Khi cung cấp một thực thể [`Accelerator`](../../analog_llm/accelerator.py), các phép chiếu tuyến tính được phân mảnh qua các tile crossbar $16 \times 16$:
- **Kiểm Tra LLaMA GQA (Prompt 3 token)**:
  - **Số Phép Tính Analog MAC Thực Thi**: $319,488\text{ MAC}$
  - **Kích Thước Tile**: Crossbar tile $16 \times 16$
  - **Tính Nhất Quán Của Sổ Cái**: Mọi bước MVM đều được đếm và kiểm tra vật lý qua sổ cái accelerator.

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0048-generalized-decoder/generalized_decoder.py
```

Chạy bộ unit test:
```bash
pytest tests/test_generalized_decoder.py
```

File trích xuất artifact:
`verification/circuit/results/generalized-decoder-0048-extract.json`
