# 0020 — Xuất bản Hồ sơ `crossbar-v1` & Đóng Cổng R4

> **English version:** [`README.md`](README.md)

Chương này xuất bản hồ sơ mảng crossbar 2D hợp nhất [`device_profiles/crossbar-v1.json`](../../device_profiles/crossbar-v1.json) và chính thức đóng **Cổng R4 (Mô hình Thiết bị Thực tế & `crossbar-v1`)**, chuyển đổi từ mô hình cột đơn sơ khai sang một giao ước vật lý hoàn chỉnh cho toàn bộ mảng 2D.

---

## 1. Kiến trúc Ô nhớ 2D Vật lý & Sổ cái Bằng chứng

![Kiến trúc ô nhớ Crossbar-v1 và Sổ cái bằng chứng](diagrams/crossbar_v1_summary.svg)

`crossbar-v1` tổng hợp toàn bộ bằng chứng vật lý và mạch từ Chương 0015 đến 0019 vào một hồ sơ duy nhất có phiên bản:

### Các Thông số Vật lý Chính:
| Lĩnh vực / Thông số | Trường Hồ sơ | Giá trị | Phân loại Bằng chứng | Gói Công việc Nguồn |
|---|---|---|---|---|
| **Dải Điện dẫn** | `gmin_s` / `gmax_s` | $10.0\,\mu\text{S} \dots 100.0\,\mu\text{S}$ ($10\times$ on/off) | `assumed` | Chương 0015 (Mô hình rút gọn) |
| **Vùng Tuyến tính Đọc** | `v_read_max_v` | $0.25\text{ V}$ (không phá hủy) | `derived` | Chương 0015 (Chế độ đọc) |
| **Nhiễu Ghi/Đọc** | `sigma_prog_rel` / `sigma_read_rel` | $3.0\%$ ghi / $1.0\%$ đọc ($\sigma_{\text{tot}} = 3.16\%$) | `assumed` | Chương 0016 (Monte Carlo) |
| **Sàn Nhiễu Trọng số** | `zero_weight_noise_floor_std` | $0.497\%$ @ $w=0$ ($3.53\%$ @ $|w|=1$) | `derived` | Chương 0016 (SNR Vi sai) |
| **Điện trở Đường dây** | `r_wire_ohm` | $1.0\,\Omega$ mỗi đoạn | `assumed` | Chương 0017 (Lưới nút) |
| **Sai số Sụt áp IR** | `mvm_error_32x32_1ohm_pct` | $6.77\%$ @ $32\times 32$ ($21.84\%$ @ $64\times 64$) | `derived` | Chương 0017 (Mở rộng Mảng) |
| **Giới hạn Kích thước Ô** | `recommended_max_tile_dim` | $32\times 32$ ô nhớ | `derived` | Chương 0017 (Giới hạn Kích thước) |
| **Điện dung Ký sinh** | `c_seg_ff` | $1.5\text{ fF}$ mỗi bước ô | `derived` | Chương 0018 (Điện dung Ký sinh) |
| **Thời gian Ổn định RC** | `t_settle_1pct_ps` / `f_max_ghz` | $20.5\text{ ps}$ (ổn định $1\%$, $f_{\max} = 48.8\text{ GHz}$) | `spice` | Chương 0018 (Động học Quá độ) |
| **Trôi theo Thời gian** | `max_drift_loss_1year_pct` | Mất $-64.5\%$ điện dẫn LRS sau 1 năm | `derived` | Chương 0019 (Trôi Hàm Mũ) |
| **Sai số Lỗi Kẹt Cố định** | `mvm_error_1pct_faults_pct` | $9.21\%$ sai số @ tỷ lệ lỗi $1.0\%$ | `derived` | Chương 0019 (Lỗi Chế tạo) |
| **Bất tuyến tính I-V** | `max_iv_distortion_pct` | Méo $+6.25\%$ bậc ba @ $0.25\text{ V}$ | `derived` | Chương 0019 (Poole-Frenkel) |

---

## 2. Phân bổ Ngân sách Sai số Phi lý tưởng

![Phân bổ ngân sách sai số](diagrams/error_budget_breakdown.svg)

### Bài học Kiến trúc cho Tích hợp Hệ thống (Phần VI):
1. **Phân mảnh Ô (Tiling)**: Các mảng crossbar nguyên khối lớn hơn $32\times 32$ bị suy giảm nghiêm trọng do sụt áp IR ($>20\%$). Kiến trúc vật lý bắt buộc phải phân mảnh ma trận thành các ô nhỏ $16\times 16$ hoặc $32\times 32$.
2. **Phân cấp Điểm nghẽn Tốc độ**: Thời gian ổn định RC của mảng crossbar ($\sim 20\text{ ps}$) không làm nghẽn xung nhịp. Tần số hoạt động ($100\dots 500\text{ MHz}$) bị chi phối bởi các mạch ngoại vi: DAC, TIA GBW, và SAR ADC.
3. **Bù trừ Sai lệch Dài hạn**: Trôi điện dẫn và lỗi chế tạo cần được bù trừ thông qua việc tái chuẩn hóa trọng số định kỳ, lượng tử hóa thích ứng lỗi, hoặc trừ nền dòng điện rò.

---

## 3. Tiêu chí Đóng Cổng R4

Toàn bộ các hạng mục kiểm tra của Cổng R4 đã hoàn tất và được xác minh:
- [x] Chọn mô hình rút gọn điện dẫn lập trình được (`0015`)
- [x] Thiết lập `gmin`, `gmax`, mức rời rạc và giả định nạp (`0015`)
- [x] Mô phỏng Monte Carlo biến thiên nạp và nhiễu đọc (`0016`)
- [x] Sụt áp IR drop và điện trở đường dây theo kích thước mảng (`0017`)
- [x] Điện dung ký sinh RC và thời gian ổn định quá độ (`0018`)
- [x] Trôi điện dẫn, lỗi kẹt và bất tuyến tính I-V (`0019`)
- [x] Xuất bản hồ sơ `crossbar-v1` và giới hạn sử dụng (`0020`)

**Cổng R4 CHÍNH THỨC ĐÓNG. Chuyển sang Phần VI: Kiến trúc bộ tăng tốc điều khiển bởi hồ sơ thiết bị.**

---

## Kiểm thử & Xác minh

Chạy kiểm tra chéo hồ sơ và tạo báo cáo:
```bash
python book/0020-crossbar-v1/crossbar_v1.py
python verification/reports/generate_crossbar_v1_summary.py
python book/0020-crossbar-v1/diagrams/make_plots.py
```
Hồ sơ cam kết: [`device_profiles/crossbar-v1.json`](../../device_profiles/crossbar-v1.json).
Báo cáo kiểm thử: [`verification/reports/crossbar-v1-summary.md`](../../verification/reports/crossbar-v1-summary.md).
Kiểm thử tự động: [`tests/test_crossbar_v1_profile.py`](../../tests/test_crossbar_v1_profile.py).
