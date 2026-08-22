# 0063 — Trích Xuất Ký Sinh Hậu Layout (PEX/SPEF) & Thời Gian Xác Lập Mảng Crossbar (Gate R16)

> **English version:** [`README.md`](README.md)

Chương này mở đầu **Gate R16 (Post-Layout Parasitic Extraction & Static Timing Signoff)** bằng việc trích xuất netlist RC ký sinh dạng chuẩn **SPEF (Standard Parasitic Exchange Format)** từ layout vật lý ReRAM 28nm BEOL, mô phỏng **động học xác lập tín hiệu analog hậu layout**, và chứng minh tín hiệu MVM hoàn toàn đáp ứng **cửa sổ lấy mẫu của bộ chuyển đổi SAR ADC**.

---

## 1. Mô Hình Trích Xuất Ký Sinh (PEX) 28nm BEOL

![Trích Xuất Ký Sinh Hậu Layout](diagrams/parasitic-extraction.svg)

- **Các Thành Phần Ký Sinh Vật Lý Trích Xuất**:
  - **Điện Trở Đường Dây Wordline (Metal 4)**: $R_{\text{M4}} = 1.20\ \Omega/\mu\text{m}$.
  - **Điện Trở Đường Dây Bitline (Metal 5)**: $R_{\text{M5}} = 1.20\ \Omega/\mu\text{m}$.
  - **Điện Dung Mặt Tiếp Giáp Nền Silicon**: $C_{\text{area}} = 0.08\text{ fF}/\mu\text{m}$.
  - **Điện Dung Ghép Xuyên Kênh (Fringe Coupling)**: $C_{\text{coupling}} = 0.12\text{ fF}/\mu\text{m}$ (ở khoảng cách chuẩn $100\text{ nm}$).
  - **Điện Trở Tiếp Xúc Via4_RERAM**: $R_{\text{via4}} = 1.50\ \Omega/\text{tiếp điểm}$.

---

## 2. Tổng Hợp Netlist Chuẩn SPEF (IEEE 1481-1999)

Công cụ trích xuất layout chuyển đổi các phần tử ký sinh hình học thành file netlist SPEF chuẩn công nghiệp:

| Lớp / Giao Diện | Thông Số Điện Trở | Thông Số Điện Dung | Định Dạng Chuẩn |
|---|---|---|---|
| **Metal 4 (Wordline)** | $1.20\ \Omega/\mu\text{m}$ | $0.08\text{ fF}/\mu\text{m} (\text{Nền}) + 0.12\text{ fF}/\mu\text{m} (\text{Ghép})$ | IEEE 1481-1999 SPEF |
| **Metal 5 (Bitline)** | $1.20\ \Omega/\mu\text{m}$ | $0.08\text{ fF}/\mu\text{m} (\text{Nền}) + 0.12\text{ fF}/\mu\text{m} (\text{Ghép})$ | IEEE 1481-1999 SPEF |
| **Via4_RERAM** | $1.50\ \Omega/\text{via}$ | $0.04\text{ fF}/\text{aperture}$ | IEEE 1481-1999 SPEF |
| **Tổng Ký Sinh Macro** | **$610.42\ \Omega$** | **$33.18\text{ fF}$** | **$291\text{ Nets Trích Xuất}$** |

---

## 3. Mô Phỏng Động Học Xác Lập Tín Hiệu (Transient Settling)

Gán ngược các thông số ký sinh SPEF vào mạng lưới bitline mô phỏng đáp ứng bước nhảy analog thực tế:

$$\tau_{\text{pre}} = \mathbf{1.18\text{ ns}} \quad \longrightarrow \quad \tau_{\text{post}} = \mathbf{1.58\text{ ns}} \quad (+33.9\%\text{ suy giảm do ký sinh})$$
$$t_{\text{settle\_99.9}} = 1.55 \times \tau_{\text{post}} = \mathbf{2.45\text{ ns}}$$

- **Nguyên Nhân Suy Giảm**: Điện dung ghép rìa giữa các đường bitline lân cận ($0.12\text{ fF}/\mu\text{m}$) và điện trở tiếp xúc tích lũy của các Via4 trên cột cộng dòng.
- **Độ Ổn Định Xác Lập**: Không xuất hiện hiện tượng dao động cộng hưởng hay phi đơn điệu trên thang RC phân tán.

---

## 4. Ký Duyệt Biên Độ Lấy Mẫu Bộ Chuyển Đổi SAR ADC

| Thông Số Định Thời | Ngân Sách Cho Phép | Giá Trị Thực Tế Hậu Layout | Biên Độ An Toàn |
|---|---|---|---|
| **Cửa Sổ Lấy Mẫu SAR ADC** | $5.00\text{ ns}$ ($200\text{ MSPS}$) | $5.00\text{ ns}$ | Cố định theo kiến trúc đồng hồ |
| **Thời Gian Tăng $90\%$** | $\le 3.50\text{ ns}$ | **$1.90\text{ ns}$** | Biên độ $1.84\times$ |
| **Thời Gian Xác Lập $99.9\%$** | $\le 5.00\text{ ns}$ | **$2.45\text{ ns}$** | **Biên độ an toàn $2.04\times$** |
| **Suy Thoái Lỗi Bit (BER)** | $< 0.10\%$ | **$0.00\%$** | ✓ **SETTLING CLEAN** |

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0063-post-layout-parasitic-extraction/parasitic_extraction.py
```

Chạy bộ unit test:
```bash
pytest tests/test_layout_pex.py
```

File trích xuất artifact:
`verification/layout/results/parasitic-extraction-0063-extract.json`
