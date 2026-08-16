# 0033 — Nghiên Cứu Tương Đồng Đầu-Cuối Tiny Transformer (Gate R7)

> **English version:** [`README.md`](README.md)

Chương này thực hiện **đánh giá tương đồng xác định giữa đường tham chiếu dấu phẩy động và đường tính toán tương tự** trên toàn bộ mô hình **TinyGPT** ($2$ tầng, $416$ tile crossbar vật lý) sử dụng hạ tầng `analog_llm.TinyGPT` và `Accelerator` có sẵn cho **Gate R7 (Kiểm chứng Transformer và mô hình ngôn ngữ lớn)**.

---

## 1. Bản Đồ Phần Cứng Vật Lý

![Tương đồng Tiny Transformer](diagrams/tiny-transformer-0033.svg)

**TinyGPT** ($n_{\text{embd}}=64, n_{\text{layer}}=2, n_{\text{head}}=4, \text{ffn}=256, \text{vocab}=128$) ánh xạ lên $16\times 16$ tile crossbar vật lý:

| Thành Phần | Tile/Tầng | × Tầng | Tổng |
|---|---|---|---|
| $W_{QKV}$ ($192 \times 64$) | 48 | 2 | 96 |
| $W_O$ ($64 \times 64$) | 16 | 2 | 32 |
| $W_{\text{up}}$ ($256 \times 64$) | 64 | 2 | 128 |
| $W_{\text{down}}$ ($64 \times 256$) | 64 | 2 | 128 |
| $W_{\text{head}}$ ($128 \times 64$) | 32 | 1 | 32 |
| **Tổng cộng** | **192/tầng** | **2 + head** | **416 tile** |

- **Sổ cái bộ gia tốc**: 851,968 MAC, 72 chu kỳ tile, 3,328 lần lập trình tile, 0 lần ghi đè.
- **Độ phân giải bộ chuyển đổi**: DAC 4-bit / ADC 4-bit / Độ dẫn 4-bit.
- **Phi lý tưởng**: Toàn bộ 9 cơ chế `crossbar-v1` được kích hoạt.

---

## 2. Chỉ Số Tương Đồng Dấu Phẩy Động vs Tương Tự

| Chỉ Số | Tham Chiếu FP | Tương Tự | Chênh Lệch |
|---|---|---|---|
| **Sai số $L_2$ tương đối logit** | — | $115.3\%$ | — |
| **SNR logit** | — | $-1.2\text{ dB}$ | — |
| **Độ khớp token Top-1** | — | $0.0\%$ | Toàn bộ argmax token khác nhau |
| **Mất mát Cross-Entropy** | $4.850$ | $4.780$ | $-0.070$ |
| **Perplexity** | $127.7$ | $119.1$ | $-8.6$ (nhiễu tương tự hoạt động như bộ điều chuẩn) |
| **Độ khớp token sinh tự hồi quy** | — | $41.7\%$ | 5/12 token khớp |

### Nhận Xét Chính

1. **Sai số logit cao ($L_2 > 100\%$)**: Với bộ chuyển đổi 4-bit và tất cả 9 phi lý tưởng cộng dồn qua 2 tầng Transformer, đầu ra logit tương tự phân kỳ đáng kể so với tham chiếu FP.
2. **0% khớp top-1 trên forward pass**: Mặc dù các giá trị logit riêng lẻ bị sai lệch, thứ tự xếp hạng bị xáo trộn hoàn toàn ở độ phân giải 4-bit với lỗi kẹt phần cứng.
3. **41.7% khớp token sinh tự hồi quy**: Trong quá trình sinh tham lam, các token đầu khớp (token 0–3 khớp câu lệnh, token 4 bắt đầu phân kỳ), cho thấy sai số tích lũy tự hồi quy.
4. **Nghịch lý perplexity**: Đường tương tự đạt perplexity *thấp hơn* ($119.1$ so với $127.7$) trên trọng số ngẫu nhiên — các phi lý tưởng phần cứng hoạt động như bộ điều chuẩn ngầm.

---

## 3. Thực Thi & Kiểm Thử

Chạy nghiên cứu tương đồng TinyGPT:
```bash
python book/0033-tiny-transformer/tiny_transformer.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/tiny-transformer-0033-extract.json`.
