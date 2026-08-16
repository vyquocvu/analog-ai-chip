# 0031 — Mô Hình Dung Lượng & Lưu Lượng Bộ Nhớ Đệm KV Cache (Gate R7)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **mô hình dung lượng lưu trữ trạng thái token động, sự mở rộng lưu lượng tự hồi quy (autoregressive traffic), chính sách phân trang bộ nhớ (paging) và sổ cái năng lượng truy xuất bộ nhớ** cho cơ chế attention trong **Gate R7 (Kiểm chứng Transformer và mô hình ngôn ngữ lớn)**.

---

## 1. Dung Lượng Chiếm Dụng Của KV Cache

![Mô hình KV Cache](diagrams/kv-cache-0031.svg)

Trong quá trình sinh tự hồi quy, các vector Key và Value của các token quá khứ phải được lưu trong bộ nhớ để tính toán attention mà không cần tính lại toàn bộ các token trước:
1. **Công Thức Dung Lượng Bộ Nhớ**:
   $$S_{\text{KV}}(L) = 2 \cdot n_{\text{layers}} \cdot L \cdot d_{\text{model}} \cdot \frac{B_{\text{act}}}{8}\text{ bytes}$$
2. **Đo Lường Chuẩn Trên TinyGPT ($n_{\text{layers}}=4, d_{\text{model}}=64$, Ngữ cảnh $L=128\text{ tokens}$)**:
   - **Lượng tử hóa 4-bit ($B_{\text{act}}=4$)**: $32.0\text{ KB}$ ($32,768\text{ bytes}$) $\implies$ Vừa vặn hoàn toàn trong vùng đệm SRAM on-chip nội bộ.
   - **Lượng tử hóa 8-bit ($B_{\text{act}}=8$)**: $64.0\text{ KB}$ ($65,536\text{ bytes}$) $\implies 2.0\times$ dung lượng.
   - **Chuẩn FP16 (16-bit)**: $128.0\text{ KB}$ ($131,072\text{ bytes}$) $\implies 4.0\times$ dung lượng.
   - **Chuẩn FP32 (32-bit)**: $256.0\text{ KB}$ ($262,144\text{ bytes}$) $\implies 8.0\times$ dung lượng.

---

## 2. Quy Mô Lưu Lượng & Băng Thông Tự Hồi Quy

Với quá trình sinh chuỗi từ độ dài câu lệnh ban đầu $L_{\text{prompt}}$ đến tổng độ dài $L$:
- **Lưu lượng ghi mỗi bước**: $T_{\text{write}} = 2 \cdot n_{\text{layers}} \cdot d_{\text{model}} \cdot \frac{B_{\text{act}}}{8} = 256\text{ bytes/token}$ (hằng số $O(1)$).
- **Lưu lượng đọc tại bước $t$**: $T_{\text{read}}(t) = 2 \cdot n_{\text{layers}} \cdot t \cdot d_{\text{model}} \cdot \frac{B_{\text{act}}}{8} = 256 \cdot t\text{ bytes/token}$ (tuyến tính $O(t)$).
- **Tổng lưu lượng tích lũy (Prompt=32, Gen=96 $\to$ 128 Tokens)**:
  - Tổng lưu lượng ghi: $32.0\text{ KB}$ ($32,768\text{ bytes}$).
  - Tổng lưu lượng đọc: $1908.0\text{ KB}$ ($1,953,792\text{ bytes}$).
  - Tổng lưu lượng KV tích lũy: **$1940.0\text{ KB}$** ($1,986,560\text{ bytes}$).
  - Lưu lượng đọc áp đảo lưu lượng ghi gấp **$59.6\times$**.

---

## 3. Chính Sách Phân Trang & Năng Lượng Phân Cấp Bộ Nhớ

| Khối Lượng Tính Toán | Chuỗi Ngữ Cảnh ($L$) | Dung Lượng Đỉnh KV Cache | Tổng Lưu Lượng Truy Xuất | Năng Lượng SRAM On-Chip ($1.0\text{ pJ/B}$) | Năng Lượng DRAM Off-Chip ($20.0\text{ pJ/B}$) | Phân Mảnh Paged KV ($B_{\text{block}}=16$) |
|---|---|---|---|---|---|---|
| **Sinh Ngắn (Short)** | $16\text{ Prompt} + 16\text{ Gen} = 32$ | $8.0\text{ KB}$ | $98.0\text{ KB}$ | **$100.4\text{ nJ}$** | $2007.0\text{ nJ}$ | **$0.0\%$ (Khớp khối)** |
| **Sinh Vừa (Medium)** | $32\text{ Prompt} + 32\text{ Gen} = 64$ | $16.0\text{ KB}$ | $392.0\text{ KB}$ | **$401.4\text{ nJ}$** | $8028.2\text{ nJ}$ | **$0.0\%$ (Khớp khối)** |
| **Đầy Ngữ Cảnh (Full)** | $32\text{ Prompt} + 96\text{ Gen} = 128$ | $32.0\text{ KB}$ | $1940.0\text{ KB}$ | **$1986.6\text{ nJ}$** | $39731.2\text{ nJ}$ | **$0.0\%$ (Khớp khối)** |

- **Ưu thế năng lượng**: Lưu trữ KV cache trên SRAM on-chip tiết kiệm **$20.0\times$** năng lượng truy xuất so với việc phải đọc/ghi từ DRAM ngoài chip.

---

## 4. Thực Thi & Kiểm Thử

Chạy mã nguồn mô phỏng KV cache:
```bash
python book/0031-kv-cache/kv_cache.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/kv-cache-0031-extract.json`.
