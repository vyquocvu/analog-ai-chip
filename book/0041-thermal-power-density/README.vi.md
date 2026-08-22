# 0041 — Kiểm Tra Tính Khả Thi Nhiệt & Mật Độ Công Suất (Gate R8)

> **English version:** [`README.md`](README.md)

Chương này kiểm chứng **khung giới hạn nhiệt độ và mật độ công suất** của bộ tăng tốc IMC analog, tham chiếu toàn bộ bằng chứng vật lý từ Chương 0038–0040. Mọi tham số nhiệt đều mang nhãn nguồn gốc minh bạch (`derived` hoặc `assumed`) phục vụ cho **Gate R8 (Physical feasibility report)**.

---

## 1. Tham Số Nhiệt & Nguồn Gốc Bằng Chứng

![Tổng Quan Tham Số Nhiệt](diagrams/thermal-power-density-0041.svg)

| Tham Số | Ký Hiệu | Giá Trị | Phân Loại | Nguồn Gốc Dữ Liệu |
|---|---|---|---|---|
| **Công Suất Tiêu Thụ Chip** | $P_{\text{chip}}$ | $29.35\text{ mW}$ | `derived` | Sổ cái độ trễ + năng lượng Chương 0038+0039 |
| **Diện Tích Die** | $A_{\text{die}}$ | $1.412\text{ mm}^2$ | `derived` | Floorplan CMOS 28nm Chương 0040 |
| **Nhiệt Trở Tiếp Giáp - Môi Trường** | $\theta_{ja}$ | $200\text{ °C/W}$ | `assumed` | Die trần / đối lưu tự nhiên (JEDEC JESD51) |
| **Nhiệt Độ Môi Trường (Tiêu Chuẩn)** | $T_{\text{amb}}$ | $25\text{ °C}$ | `assumed` | Điều kiện phòng lab / trung tâm dữ liệu |
| **Nhiệt Độ Tiếp Giáp Tối Đa** | $T_{j,\text{max}}$ | $125\text{ °C}$ | `assumed` | Giới hạn tiến trình TSMC CMOS 28nm |
| **Năng Lượng Kích Hoạt Arrhenius** | $E_a$ | $0.6\text{ eV}$ | `assumed` | Độ lưu trữ memristor HfO₂ (tài liệu chuyên ngành) |
| **Số Mũ Trôi Dẫn Nạp** | $\nu_{\text{drift}}$ | $0.08$ | `derived` | `crossbar-v1.json` (Chương 0036) |

---

## 2. Kết Quả Kiểm Tra An Toàn Nhiệt (5 / 5 Đạt)

![Kiểm Tra Nhiệt](diagrams/thermal-sanity-checks-0041.svg)

Cả 5 tiêu chí kiểm tra nhiệt đều **ĐẠT (PASSED)**:

| Tiêu Chí | Giá Trị Tính Toán | Ngưỡng Cho Phép | Kết Quả |
|---|---|---|---|
| Độ Tăng Nhiệt Tiếp Giáp | **30.87°C** | $<125\text{ °C}$ | ✓ AN TOÀN |
| Mật Độ Công Suất | **20.79 mW/mm²** | $<100\text{ mW/mm}^2$ | ✓ Thấp hơn giới hạn 79 lần |
| Tản Nhiệt Bức Xạ | **~0.12 µW** | $\ll P_{\text{chip}}$ | ✓ Không đáng kể |
| Biên Độ An Toàn Nhiệt đến $T_{j,\text{max}}$ | **94.13°C** khoảng trống | $>20\text{ °C}$ | ✓ Rất an toàn |
| Trường Hợp Nóng (70°C môi trường) | **75.87°C** | $<125\text{ °C}$ | ✓ An toàn |

---

## 3. Kịch Bản Nhiệt Độ Hoạt Động

![Kịch Bản Nhiệt Độ](diagrams/thermal-scenarios-0041.svg)

| Kịch Bản | $T_{\text{amb}}$ | $T_j$ (Tính Toán) | Hệ Số Gia Tốc Arrhenius | Trạng Thái |
|---|---|---|---|---|
| Lưu Trữ Lạnh (0°C) | 0°C | 5.87°C | 0.15× chậm hơn | ✓ AN TOÀN |
| **Hoạt Động Chuẩn (25°C)** | 25°C | **30.87°C** | **1.00× (chuẩn đối chiếu)** | ✓ AN TOÀN |
| Môi Trường Công Nghiệp (55°C) | 55°C | 60.87°C | 2.09× | ✓ AN TOÀN |
| Trường Hợp Khắc Nghiệt / Ô Tô (70°C) | 70°C | 75.87°C | 3.76× | ✓ AN TOÀN |
| Công Nghiệp Mở Rộng (85°C) | 85°C | 90.87°C | 6.54× | ✓ AN TOÀN |

---

## 4. Mô Hình Độ Tin Cậy Nhiệt Memristor

![Mô Hình Độ Tin Cậy](diagrams/thermal-memristor-reliability-0041.svg)

**Độ Trôi Dẫn Nạp**: $G(t) = G_0 \cdot (1 - \nu \cdot \log t)$, $\nu = 0.08$ (`derived`)

- Tại nhiệt độ danh định $T_j = 30.87\text{ °C}$: hiện tượng trôi dẫn nạp hoàn toàn có thể kiểm soát thông qua chu kỳ làm mới write-verify định kỳ (khoảng 1–10 giờ).
- Hệ số gia tốc Arrhenius (GIẢ ĐỊNH: $E_a = 0.6\text{ eV}$) cho thấy tốc độ trôi tăng gấp đôi ở $\approx 55\text{ °C}$ — vẫn nằm trong dải công nghiệp an toàn.

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0041-thermal-power-density/thermal_power_density.py
```

File trích xuất artifact:
`verification/circuit/results/thermal-power-density-0041-extract.json`
