# 0038 — Sổ Cái Độ Trễ Vật Lý (Gate R8)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **mô hình định thời vật lý và sổ cái độ trễ toàn diện** cho bộ tăng tốc tính toán trong bộ nhớ tương tự (IMC), trong đó mỗi hệ số định thời đều mang nhãn nguồn gốc vật lý rõ ràng (`measured`, `spice`, `derived`, hoặc `assumed`) cho **Gate R8 (Báo cáo tính khả thi vật lý)**.

---

## 1. Tổng Quan Mô Hình Định Thời & Nguồn Gốc

![Sổ cái độ trễ vật lý](diagrams/latency-ledger-0038.svg)

| Tham Số | Ký Hiệu | Giá Trị | Lớp Bằng Chứng | Nguồn Gốc Vật Lý |
|---|---|---|---|---|
| **Thiết Lập DAC** | $t_{\text{dac}}$ | $10.0\text{ ns}$ | `spice` | Mô phỏng quá độ SPICE cho bộ đệm PWM / R-2R 4-bit |
| **Xác Lập RC Dây Dẫn** | $t_{\text{settle}}$ | $15.0\text{ ns}$ | `spice` | Mô phỏng SPICE lưới RC 2D ($R_{\text{wire}} = 1.0\,\Omega, C_{\text{line}} = 50\text{ fF}$) |
| **Chuyển Đổi ADC** | $t_{\text{adc}}$ | $75.0\text{ ns}$ | `spice` | Mô phỏng SPICE SAR ADC 4-bit (4 chu kỳ @ 18.75 ns) |
| **Chu Kỳ Tile IMC** | $t_{\text{tile}}$ | **$100.0\text{ ns}$** | `derived` | $t_{\text{dac}} + t_{\text{settle}} + t_{\text{adc}}$ (Xung nhịp tương tự $10\text{ MHz}$) |
| **Truy Cập SRAM** | $t_{\text{sram}}$ | $2.0\text{ ns}$ | `derived` | Truy cập ô chuẩn SRAM mật độ cao 28nm |
| **Phép Tính SIMD Số** | $t_{\text{simd}}$ | $5.0\text{ ns}$ | `derived` | ALU vector số 32-bit đường ống @ 200 MHz |
| **Chuyển Tiếp NoC** | $t_{\text{noc}}$ | $3.0\text{ ns}$ | `assumed` | Định tuyến NoC lưới 2D (ô chuẩn 28nm) |

---

## 2. Thác Thời Gian Gantt Giải Mã Đơn Token Tự Hồi Quy

![Thác thời gian giải mã](diagrams/latency-waterfall-0038.svg)

- **Tổng độ trễ giải mã một token**: $t_{\text{decode}} = \mathbf{998.0\text{ ns}}$ ($0.998\,\mu\text{s}$).
- **Thông lượng giải mã đỉnh**: **$1,002,004\text{ token/giây}$** qua 2 tầng Transformer + LM Head ($416$ tile vật lý).
- **Phân chia thời gian thực thi**:
  - 9 lượt tile IMC tương tự: $900.0\text{ ns}$ ($90.2\%$).
  - 18 phép tính SIMD số (LayerNorm, Softmax, GELU, Cộng phần dư): $90.0\text{ ns}$ ($9.0\%$).
  - Định tuyến NoC & Đệm SRAM: $8.0\text{ ns}$ ($0.8\%$).

---

## 3. Phân Phối Độ Trễ Giữa Các Phân Hệ

![Phân phối phân hệ](diagrams/latency-subsystem-breakdown-0038.svg)

- **Chiếm ưu thế bởi tính toán IMC**: Nhân ma trận - vector tương tự chiếm $>90\%$ tổng thời gian, với toàn bộ trọng số được lưu giữ thường trú trên các ô memristor bất biến.
- **Không nghẽn bộ nhớ DRAM**: Thường trú không gian hoàn toàn loại bỏ lưu lượng truy xuất bộ nhớ ngoài, đảm bảo thời gian suy luận ổn định và không biến thiên.

---

## 4. Mở Rộng Theo Độ Dài Ngữ Cảnh & Kích Thước Lô

![Mở rộng ngữ cảnh](diagrams/latency-scaling-0038.svg)

- **$T = 1\dots 16$ Token**: Độ trễ duy trì $<1.0\,\mu\text{s}$ ($\approx 1.0\text{M token/s}$), thời gian xử lý attention rất nhỏ so với tính toán crossbar tĩnh.
- **$T = 128\dots 1024$ Token**: Attention Softmax tăng tuyến tính trên SIMD ($O(T)$), dần chuyển trọng tâm sang tính toán số ở ngữ cảnh dài.

---

## 5. Thực Thi & Kiểm Thử

Chạy mô phỏng tạo sổ cái độ trễ:
```bash
python book/0038-latency-ledger/latency_ledger.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/latency-ledger-0038-extract.json`.
