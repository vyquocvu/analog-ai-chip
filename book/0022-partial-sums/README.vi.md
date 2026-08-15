# 0022 — Tổng Thành phần & Phân mảnh Không gian Đa Ô (Cổng R5)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa các nền tảng toán học và vật lý của **kỹ thuật phân mảnh ma trận không gian và tích lũy tổng thành phần (partial sums) bằng số** trong **Cổng R5 (Ô tính toán vật lý điều khiển bởi hồ sơ)**.

---

## 1. Phân mảnh Không gian & Kiến trúc Tổng Thành phần

![Phân mảnh không gian ma trận và tổng thành phần](diagrams/partial_sums_architecture.svg)

### Vì sao Phân mảnh Ô là Bắt buộc:
Trong Chương 0017, chúng ta đã chứng minh các mảng crossbar nguyên khối chịu sự suy giảm sai số bậc hai do điện trở đường dây:
$$\text{Error}_{\text{IR}} \propto N^2 \cdot R_{\text{wire}} \cdot G_{\max}$$
Tại kích thước $N=64$, sai số nguyên khối lên tới **$21.84\%$**, và tại $N=256$, nó bùng nổ thảm họa lên **$>400\%$**. Các bộ tăng tốc analog thực tế bắt buộc phải phân mảnh ma trận lớn thành các ô nhỏ vật lý ($R \times C \le 32 \times 32$) và tích lũy tổng thành phần trong miền số:

$$y_i = \sum_{j=0}^{K_c - 1} y_{i,j}, \quad y_{i,j} = \text{TileForward}(W_{i,j}, x_j)$$

---

## 2. Quy luật Mở rộng & Quy tắc Độ chính xác

![Quy luật mở rộng tổng thành phần](diagrams/partial_sums_scaling.svg)

### A. So sánh Kiến trúc Phân mảnh vs Mảng Nguyên khối:

| Kích thước Ma trận $N$ | Sai số Sụt áp IR Nguyên khối | Sai số Phân mảnh $32\times 32$ | Sai số Phân mảnh $16\times 16$ | Ưu thế Kiến trúc |
|---|---|---|---|---|
| **$16\times 16$ ($K_c=1$)** | $1.87\%$ | $3.58\%$ | $3.58\%$ | Độ chính xác ô cơ sở |
| **$32\times 32$ ($K_c=2$)** | $6.77\%$ | $6.77\%$ | $5.12\%$ | Tương đương nguyên khối |
| **$64\times 64$ ($K_c=4$)** | $27.09\%$ | $15.44\%$ | $15.44\%$ | **Phân mảnh triệt tiêu sụt áp IR** |
| **$128\times 128$ ($K_c=8$)** | $108.36\%$ | $16.10\%$ | $15.82\%$ | **Sai số duy trì ổn định & có giới hạn** |
| **$256\times 256$ ($K_c=16$)** | $433.45\%$ | $16.30\%$ | $16.30\%$ | **Cho phép mở rộng quy mô Transformer** |

### B. Lan truyền Nhiễu & Lượng tử hóa:
Khi cộng $K_c$ khối cột, các sai số lượng tử hóa độc lập của bộ chuyển đổi cộng dồn theo phương sai:
$$\sigma_{\text{accum}}^2 = \sum_{j=0}^{K_c - 1} \sigma_{\text{ADC}, j}^2 = K_c \cdot \sigma_{\text{ADC}}^2 \implies \sigma_{\text{accum}} = \sqrt{K_c} \cdot \sigma_{\text{ADC}}$$

### C. Quy tắc Độ dài Từ Bộ tích lũy Số:
Để tránh tràn số số học khi cộng $K_c$ tổng thành phần từ các bộ ADC $B_{\text{ADC}}$-bit, độ dài bit của bộ cộng tích lũy số phải thỏa mãn:
$$B_{\text{acc}} \ge B_{\text{ADC}} + \lceil \log_2 K_c \rceil \text{ bits}$$
- Với $K_c = 4$ ($64\times 64$ dùng ô $16\times 16$): $B_{\text{acc}} \ge 4 + 2 = 6\text{ bits}$.
- Với $K_c = 16$ ($256\times 256$ dùng ô $16\times 16$): $B_{\text{acc}} \ge 4 + 4 = 8\text{ bits}$.
- Với $K_c = 64$ ($1024\times 1024$ cho phép chiếu LLM): $B_{\text{acc}} \ge 4 + 6 = 10\text{ bits}$.

---

## 3. Tích hợp Mô hình

Bộ thực thi đa ô tự động phân mảnh bất kỳ kích thước ma trận nào, đệm các khối biên, tính toán qua `CrossbarTile`, và cộng dồn tổng thành phần:
```python
executor = TiledMatrixExecutor(tile_rows=16, tile_cols=16, g_bits=4)
res = executor.execute_mvm(W, x)
# res.y_actual chứa kết quả đã tích lũy tổng thành phần
```

---

## Kiểm thử & Xác minh

Chạy trích xuất đặc tính và tạo đồ thị:
```bash
python book/0022-partial-sums/partial_sums.py
python book/0022-partial-sums/diagrams/make_plots.py
```
Dữ liệu cam kết: [`verification/circuit/results/partial-sums-0022-extract.json`](../../verification/circuit/results/partial-sums-0022-extract.json).
Kiểm thử tự động: [`tests/test_partial_sums.py`](../../tests/test_partial_sums.py).
