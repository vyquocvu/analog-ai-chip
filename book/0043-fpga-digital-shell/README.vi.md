# 0043 — FPGA / Digital Shell (Gate R9, WP9.1)

> **English version:** [`README.md`](README.md)

Chương này cung cấp một **mô hình tham chiếu kỹ thuật số độc lập, chính xác theo chu kỳ** của hệ thống điều khiển (control-plane digital shell) chạy trên FPGA kết hợp với các tile crossbar memristor vật lý.

---

## 1. Kiến Trúc Hệ Thống & Thời Gian

![FPGA Digital Shell](diagrams/fpga-digital-shell-0043.svg)

Digital shell mô hình hóa 4 khối phối hợp:
1. **Scheduler FSM**: điều phối tuần tự các trạng thái tile (`FETCH_ACT` → `PROGRAM` → `COMPUTE` → `ACCUMULATE` → `WRITEBACK` → `IDLE`).
2. **Buffer Controller**: quản lý SRAM đệm đôi đầu vào, RAM bóng trọng số (weight shadow RAM), và bộ tích lũy đầu ra.
3. **Partial-Sum Accumulator**: mô hình hóa cây cộng số học kỹ thuật số với kiểm soát độ rộng bit chống tràn.
4. **Control Ledger**: nhật ký thực thi chính xác theo chu kỳ ghi nhận mọi chuyển trạng thái và điểm nghẽn bộ đệm.

### Các Hệ Số Thời Gian (Đối chiếu với Chương 0038)
| Tham Số | Ký Hiệu | Giá Trị | Lớp Bằng Chứng | Mô Tả |
|---|---|---|---|---|
| Thiết Lập DAC | $t_{\text{dac}}$ | $10.0\text{ ns}$ | `spice` | Nạp điện áp DAC 4-bit và driver wordline |
| Ổn Định Crossbar | $t_{\text{settle}}$ | $15.0\text{ ns}$ | `spice` | Ổn định dòng quá độ lưới RC 2D |
| Chuyển Đổi SAR ADC | $t_{\text{adc}}$ | $75.0\text{ ns}$ | `spice` | Chuyển đổi SAR ADC 4-bit (4 chu kỳ) |
| **Chu Kỳ Tile MVM** | $t_{\text{tile}}$ | $\mathbf{100.0\text{ ns}}$ | `derived` | $t_{\text{dac}} + t_{\text{settle}} + t_{\text{adc}}$ |
| Truy Xuất SRAM | $t_{\text{sram}}$ | $2.0\text{ ns}$ | `derived` | Độ trễ đọc/ghi SRAM 28nm |
| Pipeline SIMD | $t_{\text{simd}}$ | $5.0\text{ ns}$ | `derived` | Chi phí tính toán SIMD số cho mỗi token |
| Bước Nhảy NoC | $t_{\text{noc}}$ | $3.0\text{ ns}$ | `assumed` | Độ trễ bước nhảy NoC lưới 2D (flit 128-bit) |
| Xung Ghi NVM | $t_{\text{prog}}$ | $10.0\ \mu\text{s}$ | `assumed` | Xung ghi lập trình ô memristor |
| Cây Cộng | $t_{\text{add}}$ | $2.0\text{ ns}$ | `assumed` | Độ trễ cây cộng giảm tổng từng phần |

---

## 2. Phân Tích Trạng Thái FSM

![FSM States](diagrams/fpga-fsm-states-0043.svg)

Với ma trận tham chiếu $192 \times 64$ (gồm $48$ khối tile trên mảng $16 \times 18$):
- **Thời Gian Ghi Chiếm Ưu Thế**: Xung ghi NVM ($10\ \mu\text{s}$ giả định) chiếm $>98\%$ tổng thời gian lập trình ban đầu/viết lại.
- **Lõi Tính Toán**: $t_{\text{tile}} = 100.0\text{ ns}$ mỗi khối khớp hoàn toàn với sổ cái độ trễ Chương 0038 (sai số <1%).

---

## 3. Quản Lý Bộ Đệm & Định Cỡ Bộ Tích Lũy

![Buffer Controller](diagrams/fpga-buffer-model-0043.svg)

- **Bộ Đệm Activation**: Đệm đôi $S_{\text{act}} = 2 \times C \times B_{\text{DAC}} = 144\text{ bit} = 18\text{ B}$ mỗi tile.
- **Bộ Tích Lũy Tổng Từng Phần**: $B_{\text{acc}} = B_{\text{ADC}} + \lceil \log_2 K_c \rceil = 4 + 2 = 6\text{ bit}$. Giá trị tích lũy tối đa $60 \le 63$ (an toàn không tràn).
- **Bộ Đệm Bóng Trọng Số**: $S_{\text{weight}} = 2 \times R \times C \times B_{\text{weight}} = 288\text{ B}$.
- **Tỷ Lệ Nghẽn Bộ Đệm**: $\approx 0.02\%$ nhờ cơ chế nạp trước qua bộ đệm đôi.

---

## 4. Nhật Ký Thực Thi

![Execution Trace](diagrams/fpga-execution-trace-0043.svg)

Biểu đồ dạng Gantt theo chu kỳ ghi nhận toàn bộ chuỗi trạng thái từ nạp dữ liệu SRAM đến ghi ngược kết quả đầu ra.

---

## 5. Kiểm Thử & Trạng Thái Cổng

- **Mức Công Bố**: `FUNCTIONAL_DIGITAL_SHELL`
- Đạt kiểm thử tự động: `tests/test_fpga_digital_shell.py`
- Tệp trích xuất kết quả: `verification/circuit/results/fpga-digital-shell-0043-extract.json`
