# 0028 — Ánh Xạ Khối Perceptron Đa Tầng MLP (Gate R7)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **quy trình ánh xạ khối mạng truyền thẳng (MLP / FFN) của Transformer, ranh giới kích hoạt phi tuyến kỹ thuật số và sự lan truyền sai số tổng hợp** trong **Gate R7 (Kiểm chứng Transformer và mô hình ngôn ngữ lớn)**.

---

## 1. Kiến Trúc Khối Transformer MLP & Ranh Giới Lai

![Quy trình ánh xạ MLP](diagrams/mlp-0028.svg)

Một khối Transformer MLP tiêu chuẩn xử lý trạng thái ẩn $x \in \mathbb{R}^{d_{\text{model}}}$ qua 4 bước tuần tự:
1. **Phép Chiếu Lên Tương Tự (Up-Projection $W_{\text{up}} \in \mathbb{R}^{d_{\text{ffn}} \times d_{\text{model}}}$)**:
   - Tính toán trên $K_{r,\text{up}} \times K_{c,\text{up}}$ tile crossbar vật lý $16\times 16$.
   - Xuất trạng thái ẩn trung gian: $\tilde{h}_1 = \sum_j \text{Tile}_{\text{up}, i, j}(x_j)$.
   - Áp dụng hiệu chuẩn sau ADC: $h_{1,\text{cal}} = a^* \cdot \tilde{h}_1$.
2. **Hàm Kích Hoạt Phi Tuyến Kỹ Thuật Số**:
   - Tính toán trên đơn vị số học SIMD / ALU kỹ thuật số:
     $$h_{\text{act}} = \text{GELU}(h_{1,\text{cal}}) = 0.5 \cdot h_{1,\text{cal}} \cdot \left(1 + \tanh\left(\sqrt{2/\pi}(h_{1,\text{cal}} + 0.044715 \cdot h_{1,\text{cal}}^3)\right)\right)$$
   - Kết quả được lượng tử hóa $B_{\text{DAC}} = 4$ bits để cấp cho DAC của tầng chiếu xuống.
3. **Phép Chiếu Xuống Tương Tự (Down-Projection $W_{\text{down}} \in \mathbb{R}^{d_{\text{model}} \times d_{\text{ffn}}}$)**:
   - Tính toán trên $K_{r,\text{down}} \times K_{c,\text{down}}$ tile crossbar vật lý $16\times 16$.
   - Xuất vector chiếu: $\tilde{y} = \sum_j \text{Tile}_{\text{down}, i, j}(h_{\text{act}, j})$.
   - Áp dụng hiệu chuẩn sau ADC: $y_{\text{cal}} = a^* \cdot \tilde{y}$.
4. **Đường Nối Tắt Phần Dư (Digital Residual Connection)**:
   - Cộng vector đầu vào với kết quả chiếu: $y_{\text{out}} = x + y_{\text{cal}}$.

---

## 2. Đánh Giá Độ Chính Xác & Sai Số Lan Truyền

### Khối MLP Chuẩn TinyGPT ($d_{\text{model}} = 64, d_{\text{ffn}} = 256$, $128$ tile vật lý $16\times 16$):

| Hàm Kích Hoạt | Tổng Số Tile Vật Lý | Sai Số $L_2$ Lượng Tử Hóa Lý Tưởng (SNR) | Sai Số $L_2$ Phi Lý Tưởng Thô (SNR) | Sai Số $L_2$ Đã Hiệu Chuẩn (SNR) | Mức Phục Hồi Sau Hiệu Chuẩn |
|---|---|---|---|---|---|
| **Kích hoạt $\text{GELU}$** | $64\text{ Up} + 64\text{ Down} = 128$ | $51.76\%\text{ (}5.7\text{ dB)}$ | $78.76\%\text{ (}2.1\text{ dB)}$ | **$74.63\%\text{ (}2.5\text{ dB)}$** | **Giảm $5.2\%$ sai số** |
| **Kích hoạt $\text{SiLU}$ / Swish** | $64\text{ Up} + 64\text{ Down} = 128$ | $49.88\%\text{ (}6.0\text{ dB)}$ | $76.24\%\text{ (}2.4\text{ dB)}$ | **$72.41\%\text{ (}2.8\text{ dB)}$** | **Giảm $5.0\%$ sai số** |

---

## 3. Công Thức Sổ Cái Toán Học

- **Phép chiếu lên**: $h_1 = a^* \cdot \sum_{j=0}^{K_{c,\text{up}}-1} \text{Tile}_{\text{up}, i, j}(x_j)$
- **Hàm kích hoạt**: $h_{\text{act}} = \text{GELU}(h_1)$
- **Phép chiếu xuống**: $y = a^* \cdot \sum_{j=0}^{K_{c,\text{down}}-1} \text{Tile}_{\text{down}, i, j}(h_{\text{act}, j})$
- **Tổng phần dư**: $y_{\text{out}} = x + y$
- **Sai số $L_2$ tổng hợp**: $\text{Error}_{L_2} = \frac{\|y_{\text{pred}} - y_{\text{ref}}\|_2}{\|y_{\text{ref}}\|_2} \times 100\%$

---

## 4. Thực Thi & Kiểm Thử

Chạy mã nguồn đánh giá khối MLP:
```bash
python book/0028-mlp/mlp.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/mlp-0028-extract.json`.
