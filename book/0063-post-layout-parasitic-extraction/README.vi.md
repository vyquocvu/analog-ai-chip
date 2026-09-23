# 0063 — Trích xuất ký sinh và ước lượng xác lập một cực

> **English version:** [`README.md`](README.md)

Chương này tính tổng RC từ hình học và **ước lượng giải tích một cực** cho đáp ứng bước. Các hệ số công nghệ và hằng số thời gian nền đều là **giả định (`assumed`)**. Không chạy ngspice, không giải mạng RC phân tán và không xác minh vật lý hay ký duyệt Gate R16.

## 1. Mô hình RC từ hình học

![Ước lượng RC](diagrams/parasitic-extraction.svg)

`analog_layout.pex` nhóm hình theo tên net và tính tổng RC tập trung. Bộ xuất SPEF không chứng minh kết nối điện hay cấu trúc bitline phân tán đã được kiểm chứng.

Các hệ số giả định gồm điện trở M4/M5 1.20 ohm/µm, điện dung nền 0.08 fF/µm, điện dung ghép 0.12 fF/µm mỗi cạnh và điện trở Via4 1.50 ohm/tiếp điểm. Đây không phải số liệu đo hoặc thông số được nhà máy xác nhận. Bộ trích xuất không tính điện dung via.

Ví dụ 16×16 tạo ra 291 net, tổng điện trở 610.42 ohm và tổng điện dung 33.18 fF. Đây là tổng của mô hình, không phải phép đo.

## 2. Ước lượng xác lập một cực

![Đáp ứng giải tích](diagrams/transient-settling-waveform.svg)

Với điện trở R và điện dung C trung bình mỗi net, mô hình giả định điện dung nội tại 20 fF, điện trở bộ lái 50 ohm và hệ số ghép 1.5:

`tau_post = 1.18 ns + 0.40 ns + R_driver × (1.5 C) + 0.5 R × (20 fF + 1.5 C)`

Tích RC được đổi từ ohm·fF sang ns. **Nền 1.18 ns và phần tăng 0.40 ns là giả định**, không phải hằng số thời gian trích xuất từ mạch. Phép lấy trung bình không giữ lại đường tín hiệu xấu nhất. Tau thu được khoảng 1.58003 ns; phần lớn mức tăng 33.9% đến từ giả định 0.40 ns.

Đáp ứng bước chuẩn hóa bắt đầu từ 0:

`y(t) = 1 − exp(−t/tau)`

`t(f) = −tau × ln(1 − f)`

Do đó 90% cần `ln(10) × tau`, còn 99.9% cần `ln(1000) × tau`, không phải 1.20 và 1.55 lần tau. Tính đơn điệu là đặc tính áp đặt của mô hình, không chứng minh mạch thật không dao động.

## 3. So sánh cửa sổ lấy mẫu giả định — KHÔNG ĐẠT

| Đại lượng | Ước lượng giải tích |
|---|---:|
| Xác lập 90% | 3.64 ns |
| Xác lập 99.9% | 10.91 ns |
| Cửa sổ lấy mẫu giả định | 5.00 ns |
| Cửa sổ / thời gian xác lập mục tiêu | 0.458× |
| Đạt mục tiêu mặc định 99.9% | Không |

`target_accuracy_pct` quyết định tỷ số biên và kết quả đạt/không đạt; các đầu ra 90% và 99.9% luôn giữ đúng ngưỡng tham chiếu. Cấu hình yêu cầu giá trị hữu hạn `0 < target_accuracy_pct < 100` và `sampling_window_ns` hữu hạn, dương. Thời gian bằng đúng cửa sổ chỉ được coi là đạt trong phép so sánh giải tích.

Không xác minh BER, độ chính xác ADC, PVT, nhiễu, xác lập phân tán hay tính khả thi vật lý. Trường cấu hình điện trở ReRAM chưa được sử dụng không phải mô hình thiết bị. Khóa JSON cũ `transient_settling_signoff` chỉ chứa ước lượng giải tích; toàn bộ kết quả mang `evidence_class: assumed` và `physical_verified: false`. Không công bố hay nâng cấp bằng chứng cho device profile.

## 4. Tái tạo

```bash
python book/0063-post-layout-parasitic-extraction/parasitic_extraction.py
pytest tests/test_layout_pex.py
```

Script tái tạo hai hình SVG và `verification/layout/results/parasitic-extraction-0063-extract.json` một cách xác định. Kiểm thử bao gồm đẳng thức hàm mũ, mục tiêu thay thế, biên cửa sổ, cấu hình không hợp lệ và nhãn bằng chứng. Bản sửa giới hạn này không sửa STA/LVS hoặc cập nhật tuyên bố về gate ở nơi khác.
