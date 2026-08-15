# 0024 — Mô Hình Dung Lượng SRAM & Bộ Đệm (Gate R6)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **hệ thống lưu trữ SRAM on-chip, phân cấp bộ đệm staging và sổ cái lưu lượng truyền dữ liệu (traffic ledger)** cho chip tăng tốc in-memory computing tương tự trong **Gate R6 (Kiến trúc chip tăng tốc và di chuyển dữ liệu)**.

---

## 1. Phân Cấp Bộ Nhớ & Định Cỡ Bộ Đệm

![Phân cấp SRAM & Bộ đệm](diagrams/sram-buffers-0024.svg)

### Phân Bổ Bộ Đệm SRAM Cho Mỗi Tile ($R \times C$):
1. **Bộ đệm kích hoạt đầu vào (Double-Buffered)**:
   $$S_{\text{act}} = 2 \times C \times B_{\text{DAC}}\text{ bits}$$
   Cho phép chồng lấn ping-pong giữa việc nhận vector kích hoạt và cấp áp liên tục cho DAC.
2. **Bộ đệm tích lũy tổng bộ phận (Accumulator Buffer)**:
   $$S_{\text{acc}} = R \times B_{\text{acc}}\text{ bits}, \quad \text{với } B_{\text{acc}} = B_{\text{ADC}} + \lceil \log_2 K_c \rceil$$
   Được định kích thước chính xác để chống tràn số qua $K_c$ cột ghép ma trận (Chương 0022).
3. **Bộ đệm lưu trọng số (Weight Shadow Buffer)**:
   $$S_{\text{weight}} = 2 \times R \times C \times B_{\text{weight}}\text{ bits}$$
   Lưu trữ giá trị số của độ dẫn vi sai $(G^+, G^-)$ phục vụ nạp lại cấu hình ma trận khi tái sử dụng tài nguyên theo thời gian.

---

## 2. Nhu Cầu Dung Lượng SRAM Theo Kích Thước Tile

| Cấu hình Tile | SRAM Kích hoạt Đầu vào | SRAM Lưu Trọng số | SRAM Bộ tích lũy ($K_c \le 16$) | Tổng SRAM / Tile | Ước tính Diện tích ($0.12\,\mu\text{m}^2/\text{bit}$) |
|---|---|---|---|---|---|
| **Tile $16\times 16$ (4-bit)** | $128\text{ bits}$ ($16\text{ B}$) | $2.048\text{ bits}$ ($256\text{ B}$) | $128\text{ bits}$ ($16\text{ B}$) | **$2.304\text{ bits}$ ($288\text{ B}$)** | **$276.5\,\mu\text{m}^2$** |
| **Tile $32\times 32$ (4-bit)** | $256\text{ bits}$ ($32\text{ B}$) | $8.192\text{ bits}$ ($1.024\text{ B}$) | $288\text{ bits}$ ($36\text{ B}$) | **$8.736\text{ bits}$ ($1.092\text{ B}$)** | **$1.048.3\,\mu\text{m}^2$** |
| **Tile $64\times 64$ (4-bit)** | $512\text{ bits}$ ($64\text{ B}$) | $32.768\text{ bits}$ ($4.096\text{ B}$) | $640\text{ bits}$ ($80\text{ B}$) | **$33.920\text{ bits}$ ($4.240\text{ B}$)** | **$4.070.4\,\mu\text{m}^2$** |

---

## 3. Định Cỡ Dung Lượng Bộ Nhớ KV Cache

Cho quá trình sinh token tự hồi quy với độ dài chuỗi $L$:
$$S_{\text{KV}}(L) = 2 \times L \times n_{\text{layers}} \times d_{\text{model}} \times B_{\text{act}}\text{ bits}$$

| Kiến trúc Mô hình | Số lớp | $d_{\text{model}}$ | Độ dài ngữ cảnh $L$ | Độ chính xác | Tổng dung lượng KV Cache |
|---|---|---|---|---|---|
| **TinyGPT** | $4$ | $64$ | $128$ tokens | $16\text{-bit}$ | **$128\text{ KB}$** |
| **LLaMA-7B** | $32$ | $4.096$ | $2.048$ tokens | $16\text{-bit}$ | **$1.00\text{ GB}$** |
| **LLaMA-13B** | $40$ | $5.120$ | $4.096$ tokens | $16\text{-bit}$ | **$3.20\text{ GB}$** |

---

## 4. Sổ Cái Lưu Lượng & Năng Lượng Bộ Nhớ

- **Lưu lượng kích hoạt đầu vào**: $T_{\text{in}} = (C \cdot B_{\text{DAC}} / 8) \times N_{\text{mvm}}\text{ bytes}$
- **Lưu lượng kích hoạt đầu ra**: $T_{\text{out}} = (R \cdot B_{\text{ADC}} / 8) \times N_{\text{mvm}}\text{ bytes}$
- **Lưu lượng nạp trọng số**: $T_{\text{prog}} = N_{\text{rewrites}} \times S_{\text{weight}} / 8\text{ bytes}$
- **Năng lượng truy xuất SRAM**: $E_{\text{sram}} = T_{\text{total}} \times e_{\text{sram\_byte}}$ ($e_{\text{sram\_byte}} \approx 1.0\text{ pJ/byte}$, giả định rõ ràng).

---

## 5. Thực Thi & Kiểm Thử

Chạy mã nguồn tính toán định cỡ:
```bash
python book/0024-sram-buffers/sram_buffers.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/sram-buffers-0024-extract.json`.
