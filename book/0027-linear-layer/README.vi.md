# 0027 — Ánh Xạ Tầng Tuyến Tính (Gate R7)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **quy trình ánh xạ tầng tuyến tính dense ($y = W x$), tính toán MVM đa-tile vật lý, mô phỏng cơ chế phi lý tưởng và hiệu chuẩn đầu ra** cho các tầng mạng nơ-ron trong **Gate R7 (Kiểm chứng Transformer và mô hình ngôn ngữ lớn)**.

---

## 1. Kiến Trúc Ánh Xạ Phép Chiếu Tuyến Tính

![Ánh xạ tầng tuyến tính](diagrams/linear-layer-0027.svg)

Cho ma trận trọng số $W \in \mathbb{R}^{M_{\text{out}} \times M_{\text{in}}}$ và vector kích hoạt đầu vào $x \in \mathbb{R}^{M_{\text{in}}}$:
1. **Phân Rã Không Gian**:
   - Chia thành lưới $K_r \times K_c$ tile crossbar vật lý kích thước $R \times C$ ($16\times 16$):
     $$K_r = \lceil M_{\text{out}} / R \rceil, \quad K_c = \lceil M_{\text{in}} / C \rceil$$
   - Mỗi khối $W_{i,j}$ được ánh xạ thành cặp độ dẫn vi sai $(G^+, G^-)$ với điểm 0 cân bằng ($w = 0 \implies G^+ = G^- = G_{\min}$).
2. **Định Cỡ Kích Hoạt Đầu Vào**:
   - $x$ được chia thành $K_c$ khối $x_j \in \mathbb{R}^C$ và chuyển thành điện áp DAC trong dải $[0, V_{\text{in,max}}]$ ($V_{\text{in,max}} = 2.34375\text{ V}$, $B_{\text{DAC}} = 4$).
3. **Tính Toán MVM Tương Tự Trên Tile Vật Lý**:
   - Mô phỏng với toàn bộ 9 cơ chế phi lý tưởng `crossbar-v1` (sụt áp IR drop 2D, phân tán ghi $\sigma_{\text{prog}}=3\%$, nhiễu đọc $\sigma_{\text{read}}=1\%$, trôi độ dẫn retention drift, lỗi kẹt stuck-at HRS/LRS và phi tuyến $I-V$ bậc 3).
4. **Thu Gọn Không Gian & Hiệu Chuẩn Sau ADC**:
   - Số hóa bằng SAR ADC ($B_{\text{ADC}} = 4$, $V_{\text{out,max}} = 2.5\text{ V}$).
   - Cộng thu gọn tổng bộ phận dọc theo các cột: $\tilde{y}_i = \sum_{j=0}^{K_c - 1} y_{i,j}$.
   - Áp dụng hệ số hiệu chuẩn sau thu gọn: $y_{\text{cal}, i} = a^* \cdot \tilde{y}_i$ ($a^* = 0.9795135$).

---

## 2. Đánh Giá Độ Chính Xác Trên Các Phép Chiếu Chuẩn

| Khối Lượng Tính Toán | Kích Thước Ma Trận | Lưới Tile Vật Lý | Sai Số $L_2$ Lượng Tử Hóa Lý Tưởng (SNR) | Sai Số $L_2$ Phi Lý Tưởng Thô (SNR) | Sai Số $L_2$ Đã Hiệu Chuẩn (SNR) | Mức Phục Hồi Sau Hiệu Chuẩn |
|---|---|---|---|---|---|---|
| **TinyGPT Attention QKV** | $192 \times 64$ | $12 \times 4 = 48\text{ tiles}$ | $25.84\%\text{ (}11.8\text{ dB)}$ | $41.18\%\text{ (}7.7\text{ dB)}$ | **$40.33\%\text{ (}7.9\text{ dB)}$** | **Giảm $2.1\%$ sai số** |
| **TinyGPT MLP Up** | $256 \times 64$ | $16 \times 4 = 64\text{ tiles}$ | $27.02\%\text{ (}11.4\text{ dB)}$ | $42.27\%\text{ (}7.5\text{ dB)}$ | **$41.44\%\text{ (}7.7\text{ dB)}$** | **Giảm $2.0\%$ sai số** |
| **Ma Trận Thưa (80% Sparse)** | $64 \times 64$ | $4 \times 4 = 16\text{ tiles}$ | $23.18\%\text{ (}12.7\text{ dB)}$ | $38.92\%\text{ (}8.2\text{ dB)}$ | **$37.89\%\text{ (}8.4\text{ dB)}$** | **Giảm $2.6\%$ sai số** |

---

## 3. Công Thức Sổ Cái Toán Học

- **Phân rã không gian**: $K_r = \lceil M_{\text{out}} / R \rceil, \quad K_c = \lceil M_{\text{in}} / C \rceil$
- **Thu gọn tổng bộ phận**: $\tilde{y}_i = \sum_{j=0}^{K_c - 1} \text{Tile}_{i,j}(x_j)$
- **Hiệu chuẩn đầu ra**: $y_{\text{cal}, i} = a^* \cdot \tilde{y}_i$ ($a^* = 0.9795135$)
- **Sai số $L_2$ tương đối**: $\text{Error}_{L_2} = \frac{\|y_{\text{pred}} - y_{\text{ref}}\|_2}{\|y_{\text{ref}}\|_2} \times 100\%$

---

## 4. Thực Thi & Kiểm Thử

Chạy mã nguồn đánh giá tầng tuyến tính:
```bash
python book/0027-linear-layer/linear_layer.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/linear-layer-0027-extract.json`.
