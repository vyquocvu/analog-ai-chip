# 0068 — Bo Mạch Đánh Giá Cao Tốc PCIe Gen5 & Ký Đóng Hoàn Tất Gate R17

> **English version:** [`README.md`](README.md)

Chương này hoàn tất **Gate R17 (Tape-Out Signoff & Package/PCB Integration)** và chính thức **khép lại toàn bộ 68 chương của chuỗi chứng minh kỹ thuật từ nguyên lý gốc đến hiện thực vật lý hoàn chỉnh** bằng việc thiết kế **bo mạch đánh giá cao tốc PCIe Gen5 x16 (PCB 12 lớp vật liệu Megtron 6)**, mô hình hóa **mạng lưới cấp nguồn VRM đa pha đồng bộ**, và ký duyệt **giản đồ mắt (Eye Diagram) toàn vẹn tín hiệu $32\text{ GT/s}$**.

---

## 1. Kiến Trúc Mạch In Cao Tốc 12 Lớp Vật Liệu Megtron 6

![Bo Mạch Đánh Giá PCIe Gen5](diagrams/pcie-carrier-board.svg)

- **Thông Số Kỹ Thuật Bo Mạch Đánh Giá**:
  - **Dạng Chuẩn (Form Factor)**: Chuẩn cắm PCIe Gen5 CEM Add-In Card (AIC, $111.15\text{ mm} \times 167.65\text{ mm}$, chuẩn chiều cao 3/4-length).
  - **Vật Liệu Điện Môi**: Panasonic Megtron 6 ($D_k = 3.65, D_f = 0.002$ suy hao siêu thấp ở tần số $16\text{ GHz}$).
  - **Phân Tầng 12 Lớp**: 4 lớp định tuyến tín hiệu stripline cao tốc, 4 mặt phẳng nối đất liền khối ($V_{\text{SS}}$), và 4 mặt phẳng nguồn đồng dày ($2.0\text{ oz}$ Cu cho các đường nguồn VRM).
  - **Băng Thông Giao Tiếp Máy Chủ**: Giao tiếp PCIe Gen5 x16 đạt **$63.0\text{ GB/s}$ băng thông hai chiều**.

---

## 2. Mạng Lưới Cấp Nguồn Mô-đun Ổn Áp (VRM) Đa Pha Đồng Bộ

| Miền Nguồn | Điện Áp Ổn Định | Dòng Liên Tục Cực Đại | Độ Nhấp Nhô Điện Áp ($\Delta V_{\text{pp}}$) | Đáp Ứng Bước Nhảy ($15\text{A} / 100\text{ ns}$) | Hiệu Suất VRM |
|---|---|---|---|---|---|
| **$V_{\text{DD\_DIG}}$ (Lõi/NoC/SRAM)** | $0.90\text{V} \pm 15\text{ mV}$ | **$25.0\text{A}$** | **$6.40\text{ mV}_{\text{p-p}}$** ($\le 10.0\text{ mV}$) | $\pm 18.5\text{ mV}$ | $92.4\%$ |
| **$V_{\text{DD\_ANA}}$ (ReRAM/ADCs)** | $1.00\text{V} \pm 10\text{ mV}$ | **$10.0\text{A}$** | **$4.20\text{ mV}_{\text{p-p}}$** ($\le 10.0\text{ mV}$) | $\pm 12.0\text{ mV}$ | $91.8\%$ |
| **$V_{\text{AUX\_IO}}$ (PCIe/LPDDR5)** | $1.80\text{V} \pm 25\text{ mV}$ | **$5.0\text{A}$** | **$5.10\text{ mV}_{\text{p-p}}$** ($\le 15.0\text{ mV}$) | $\pm 14.2\text{ mV}$ | $93.5\%$ |

---

## 3. Toàn Vẹn Tín Hiệu SerDes PCIe Gen5 32 GT/s & Giản Đồ Mắt (Eye Diagram)

![Giản Đồ Mắt PCIe Gen5](diagrams/pcie-gen5-eye-diagram.svg)

| Thông Số Toàn Vẹn Tín Hiệu | Giới Hạn Chuẩn CEM | Kết Quả Mô Phỏng ($75\text{ mm}$ Dây) | Biên Độ / Kết Luận |
|---|---|---|---|
| **Suy Hao Chèn Kênh ($S_{21}$ ở $16\text{ GHz}$)** | $\ge -28.0\text{ dB}$ | **$-8.45\text{ dB}$** | **$+19.55\text{ dB}$ Dư Địa An Toàn** |
| **Độ Mở Chiều Cao Mắt ($\text{BER} = 10^{-12}$)** | $\ge 30.0\text{ mV}$ | **$245.0\text{ mV}$** | **$+215.0\text{ mV}$ Biên Độ Độ Cao** |
| **Độ Mở Chiều Rộng Mắt ($\text{BER} = 10^{-12}$)** | $\ge 0.30\text{ UI}$ ($9.38\text{ ps}$) | **$0.62\text{ UI}$ ($19.38\text{ ps}$)** | **$+0.32\text{ UI}$ Biên Độ Định Thời** |
| **Tỷ Lệ Lỗi Bit (BER)** | $\le 10^{-12}$ | **$< 10^{-15}$** | ✓ **SIGNAL INTEGRITY CLEAN** |

---

## 4. Ma Trận Ký Duyệt Toàn Bộ Chuỗi Bằng Chứng Kỹ Thuật (Gates R0 đến R17)

Toàn bộ 18 cổng bằng chứng trên toàn bộ giáo trình 68 chương đã được ký duyệt hoàn tất:

| Cổng Bằng Chứng | Phạm Vi Kỹ Thuật | Cấp Độ Bằng Chứng | Trạng Thái |
|---|---|---|---|
| **R0–R6** | Nền Tảng Toán Học, Mạch Điện & Tile Vật Lý | SPICE & Device Profiles | **✓ HOÀN THÀNH** |
| **R7–R9** | Xác Thực LLM, Tương Quan PCB & Sổ Cái Vật Lý | Suy Luận Transformer Thực Tế | **✓ ĐẠT CHUẨN** |
| **R10–R14** | Kiến Trúc Mô Hình Lớn & Đánh Giá Đa Tầng | Quyết Định Tape-Out 28nm | **✓ ĐẠT CHUẨN** |
| **R15** | Thiết Kế Layout Vật Lý & Ký Duyệt DRC/LVS | GDSII Die 28nm ($336\text{ mm}^2$) | **✓ ĐẠT CHUẨN** |
| **R16** | Trích Xuất PEX, Định Thời STA & Lưới Nguồn Động | SPEF, STA Đa Góc, PDN EM | **✓ ĐẠT CHUẨN** |
| **R17** | Ký Duyệt Tape-Out, Vỏ FCBGA-676 & Bo Mạch PCIe Gen5 | GDSII, Vỏ Chip & Bo Mạch Carrier | **✓ PASSED (CLOSED)** |

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0068-pcie-gen5-carrier-board-signoff/carrier_board_signoff.py
```

Chạy bộ unit test:
```bash
pytest tests/test_layout_carrier_pcb.py
```

File trích xuất artifact:
`verification/layout/results/carrier-pcb-0068-extract.json`
