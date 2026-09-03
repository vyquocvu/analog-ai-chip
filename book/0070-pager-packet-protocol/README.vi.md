# Chương 0070 — Giao thức Gói Nhị phân Host-CiM & Trình Giả lập Pager Ảo

Chương này thiết kế giao thức truyền thông nhị phân giữa vi điều khiển chủ và bộ tăng tốc tương tự, định dạng khung gói tin, kiểm tra tính toàn vẹn CRC-16 và trình quản lý bộ đệm hiển thị màn hình cho **Máy Nhắn tin AI Tương tự Cầm tay (Pager-1)**, đóng lại **Cổng R18** (`WP18.2`).

---

## 1. Cấu trúc Giao thức & Khung Gói tin

Giao tiếp qua giao diện ngoại vi nối tiếp (SPI / QSPI) đảm bảo không có lệnh ghi điện dẫn nào bị lỗi:

* `0x01`: `CMD_HELLO` — Kiểm tra phiên bản phần cứng và trạng thái kết nối.
* `0x02`: `CMD_CALIBRATE` — Khởi động chu kỳ tự động hiệu chuẩn offset DAC/ADC.
* `0x10`: `CMD_PROGRAM_WEIGHTS` — Ghi trọng số điện dẫn vào các ô nhớ ReRAM.
* `0x20`: `CMD_RUN_VECTOR` — Truyền vector điện áp kích hoạt vào hàng crossbar.
* `0x21`: `CMD_READ_OUTPUT` — Đọc kết quả dòng điện cột đã số hóa về bộ nhớ vi điều khiển.

---

## 2. Trình Hiển thị Pager Ảo

`PagerTextBuffer` mô phỏng màn hình đơn sắc $400 \times 240$ pixel với cơ chế tự động xuống dòng và cuộn mượt mà.

---

## 3. Khởi chạy Trích xuất

```bash
python book/0070-pager-packet-protocol/pager_packet_protocol.py
```
