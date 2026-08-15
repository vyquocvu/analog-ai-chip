# 0030 — Báo Cáo Ranh Giới Tương Tự / Kỹ Thuật Số Trong Attention (Gate R7)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **ranh giới kiến trúc minh bạch giữa tính toán tương tự trong bộ nhớ (Analog IMC) và tính toán attention động kỹ thuật số (Digital Attention)** trong **Gate R7 (Kiểm chứng Transformer và mô hình ngôn ngữ lớn)**.

---

## 1. Phân Tách Miền Kiến Trúc

![Sơ đồ ranh giới attention](diagrams/attention-boundary-0030.svg)

Cơ chế Tự Chú Ý (Self-Attention) phân chia rành mạch thành hai miền dựa trên tính biến động của toán hạng:

### Miền A: Trọng Số Cố Định Tĩnh (Mảng Analog IMC)
- **Các phép toán**:
  - $Q = X W_Q \quad (d_{\text{model}} \to d_{\text{model}})$
  - $K = X W_K \quad (d_{\text{model}} \to d_{\text{model}})$
  - $V = X W_V \quad (d_{\text{model}} \to d_{\text{model}})$
  - $O = \text{Context} \cdot W_O \quad (d_{\text{model}} \to d_{\text{model}})$
- **Tại sao tính trên mạch Tương Tự?**:
  - Các ma trận trọng số $W_Q, W_K, W_V, W_O$ giữ nguyên không đổi trong toàn bộ quá trình suy luận.
  - Loại bỏ hoàn toàn lưu lượng truyền tải trọng số từ SRAM/DRAM.
  - Năng lượng tính toán: $50.0\text{ fJ/MAC}$ (trích xuất từ hồ sơ mạch).
  - Độ trễ tính toán: $20.05\text{ ns}$ mỗi bước MVM trên tile.

### Miền B: Trạng Thái Động Giữa Các Token (Đơn Vị Số Kỹ Thuật Số SIMD / SRAM)
- **Các phép toán**:
  - Điểm chú ý: $S_h = \frac{Q_h K_h^T}{\sqrt{d_{\text{head}}}}$
  - Mặt nạ nhân quả & Softmax: $A_h = \text{Softmax}(S_h + M_{\text{causal}})$
  - Tổng hợp ngữ cảnh: $\text{Context}_h = A_h V_h$
- **Tại sao tính trên mạch Kỹ Thuật Số?**:
  - Cả hai toán hạng ($Q, K, V$) đều là các kích hoạt động thay đổi liên tục theo từng token được sinh ra.
  - Việc ghi lập trình lại các tile crossbar không bay hơi cho mỗi token tiêu tốn $t_{\text{prog}} = 8.0\,\mu\text{s}$ và $E_{\text{prog}} = 2.56\text{ nJ/tile}$.
  - **Lập trình lại tương tự động tiêu tốn năng lượng gấp $71.2\times$ và chậm hơn $>400\times$ so với tính trên SRAM + SIMD kỹ thuật số.**
  - Phép tính Softmax đòi hỏi hàm mũ và dải động lớn, vốn phù hợp tuyệt đối với số học kỹ thuật số.

---

## 2. Sổ Cái Định Lượng Theo Độ Dài Ngữ Cảnh ($L$)

### Mô Hình TinyGPT Attention ($d_{\text{model}} = 64, n_{\text{heads}} = 4, 64\text{ Tile Crossbar Tĩnh}$):

| Độ Dài Ngữ Cảnh ($L$) | FLOPs Tương Tự ($8 L d^2$) | FLOPs Kỹ Thuật Số ($4 L^2 d + 3 h L^2$) | Lưu Lượng Qua Ranh Giới | Năng Lượng Chiếu Tương Tự | Năng Lượng Attention Kỹ Thuật Số | Hệ Số Phạt Năng Lượng Nếu Dùng Mạch Tương Tự Động |
|---|---|---|---|---|---|---|
| **$L = 16$** | $524.3\text{ KFLOPs}$ | $68.4\text{ KFLOPs}$ | $1.5\text{ KB}$ | **$0.0135\text{ nJ}$** | **$0.0078\text{ nJ}$** | **Phạt $328\times$ năng lượng** |
| **$L = 64$** | $2.097\text{ MFLOPs}$ | $1.098\text{ MFLOPs}$ | $6.1\text{ KB}$ | **$0.0526\text{ nJ}$** | **$0.1197\text{ nJ}$** | **Phạt $86\times$ năng lượng** |
| **$L = 128$** | $4.194\text{ MFLOPs}$ | $4.391\text{ MFLOPs}$ | $12.3\text{ KB}$ | **$0.1048\text{ nJ}$** | **$0.4746\text{ nJ}$** | **Phạt $44\times$ năng lượng** |
| **$L = 512$** | $16.777\text{ MFLOPs}$ | $70.255\text{ MFLOPs}$ | $49.2\text{ KB}$ | **$0.4182\text{ nJ}$** | **$7.5305\text{ nJ}$** | **Phạt $12\times$ năng lượng** |
| **$L = 2048$** | $67.109\text{ MFLOPs}$ | $1.124\text{ GFLOPs}$ | $196.6\text{ KB}$ | **$1.6716\text{ nJ}$** | **$119.98\text{ nJ}$** | **Phạt $3\times$ năng lượng** |

---

## 3. Công Thức Sổ Cái Toán Học

- **Khối lượng tính tương tự**: $\text{FLOPs}_{\text{analog}} = 8 \cdot L \cdot d_{\text{model}}^2$
- **Khối lượng tính kỹ thuật số**: $\text{FLOPs}_{\text{digital}} = 4 \cdot L^2 \cdot d_{\text{model}} + 3 \cdot n_{\text{heads}} \cdot L^2$
- **Dữ liệu qua ranh giới**: $T_{\text{boundary}} = \frac{3 \cdot L \cdot d_{\text{model}} \cdot B_{\text{ADC}}}{8} + \frac{L \cdot d_{\text{model}} \cdot B_{\text{DAC}}}{8}\text{ bytes}$
- **Năng lượng tương tự**: $E_{\text{analog}} = \frac{\text{FLOPs}_{\text{analog}}}{2} \cdot E_{\text{analog\_mac}}$
- **Năng lượng kỹ thuật số**: $E_{\text{digital}} = \frac{\text{FLOPs}_{\text{digital}}}{2} \cdot E_{\text{digital\_mac}} + S_{\text{SRAM}} \cdot E_{\text{sram\_byte}}$

---

## 4. Thực Thi & Kiểm Thử

Chạy mã nguồn phân tích ranh giới:
```bash
python book/0030-attention-boundary/attention_boundary.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/attention-boundary-0030-extract.json`.
