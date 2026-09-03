# Chương 0071 — Bo mạch Trung gian Cầm tay & Tương quan Đo đạc Thực nghiệm

Chương này mô hình hóa bo mạch trung gian cầm tay 4 lớp, nạp dữ liệu đo điện áp thực nghiệm từ đồng hồ vạn năng DMM phòng thí nghiệm, tính toán tương quan thống kê với mô phỏng SPICE và chính thức hoàn tất **Cổng R18** (`WP18.3`).

---

## 1. Bo mạch Trung gian Cầm tay 4 Lớp

* **Kích thước Bo mạch**: $70.0\text{ mm} \times 52.0\text{ mm}$ trên vật liệu High-Tg FR4 mỏng $1.2\text{ mm}$.
* **Cấu trúc 4 Lớp**:
  1. Lớp Trên: Tín hiệu SPI tốc độ cao ($50\,\Omega$, độ rộng vết mạch $0.32\text{ mm}$).
  2. Lớp Trong 1: Mặt phẳng mass liên tục (độ phủ $94.5\%$).
  3. Lớp Trong 2: Các đường nguồn phân tách ($3.3\text{V}$, $2.5\text{V}$, $1.0\text{V}$).
  4. Lớp Dưới: Đầu nối mezzanine 40 chân (`Hirose DF40C`, bước chân $0.4\text{ mm}$).
* **Sụt áp Đầu nối**: $0.375\text{ mV}$ tại dòng đỉnh $50\text{ mA}$.

---

## 2. Kết quả Tương quan Đo đạc Thực nghiệm

Dữ liệu đo từ DMM 6.5 chữ số (`Keysight 34465A`) qua 10 điểm quét từ $0.0\text{V}$ đến $2.25\text{V}$:
* **Hệ số Xác định ($R^2$)**: **$0.99998$** (Mục tiêu $\ge 0.990$) — **ĐẠT**
* **Sai số Trung bình Bình phương ($\text{RMSE}$)**: **$1.48\text{ mV}$** (Mục tiêu $\le 8.00\text{ mV}$) — **ĐẠT**
* **Sai số Cực đại ($\Delta V_{\max}$)**: **$1.90\text{ mV}$** (Mục tiêu $\le 10.0\text{ mV}$) — **ĐẠT**

Hồ sơ thiết bị đã đo được xuất bản tại:
`device_profiles/measured/pager-crossbar-measured-v1.json` với cấp độ bằng chứng `measured`.

---

## 3. Khởi chạy Trích xuất

```bash
python book/0071-pager-hardware-correlation/pager_hardware_correlation.py
```
