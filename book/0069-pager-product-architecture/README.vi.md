# Chương 0069 — Kiến trúc Sản phẩm Máy Nhắn tin AI Tương tự Cầm tay (Pager-1)

Chương này xác định chi tiết kiến trúc phần cứng, kích thước vật lý, danh mục linh kiện (BOM) và hệ thống phân phối nguồn điện cho thiết bị văn bản độc lập chạy pin **Máy Nhắn tin AI Tương tự Cầm tay ("AI Pager / Beeper")**, mở đầu cho **Cổng R18** (`WP18.1`).

---

## 1. Tầm nhìn Sản phẩm & Khái niệm

**Pager-1** là một thiết bị liên lạc ngôn ngữ cầm tay, hoạt động độc lập không cần mạng (air-gapped), được tối ưu hóa cho ghi chép phòng thí nghiệm và hỗ trợ văn bản tại hiện trường:
1. **Màn hình Memory LCD / E-Paper phản xạ**: Hiển thị rõ dưới ánh nắng mặt trời, tiêu thụ chỉ $15\,\mu\text{W}$ ở trạng thái tĩnh.
2. **Lõi Nơ-ron Tính toán Trong Bộ nhớ Tương tự (CiM)**: Các ma trận crossbar ReRAM không bay hơi tính toán phép nhân ma trận - vector (MVM) ngay tại ô nhớ.
3. **Bàn phím Ngón cái Xúc giác**: Đầy đủ 35 phím QWERTY với switch vòm kim loại và con lăn xoay cạnh bên (jog dial) tiện dụng.
4. **Thời lượng Pin Chờ Hơn 1 Tháng**: Pin Li-Po $1200\text{ mAh}$ tích hợp và IC quản lý nguồn PMIC tiêu thụ tĩnh cực thấp ($700\text{ nA}$ $I_q$), mang lại $>30\text{ ngày}$ pin chờ.

---

## 2. Bảng Cân đối Năng lượng

* **Chế độ Chờ (Standby)**: $35.6\,\mu\text{W}$ tổng công suất $\implies \mathbf{216\text{ ngày}}$ pin chờ (Mục tiêu $\ge 30\text{ ngày}$).
* **Chế độ Suy luận Liên tục**: $44.8\text{ mW}$ tổng công suất $\implies \mathbf{99\text{ giờ}}$ phát sinh token liên tục (Mục tiêu $\ge 40\text{ giờ}$).
* **Sử dụng Hỗn hợp Hàng ngày**: $\mathbf{41.5\text{ ngày}}$ (với 2 giờ sử dụng mỗi ngày).
* **Nhiệt độ Bề mặt**: Tản nhiệt đối lưu tự nhiên thụ động, nhiệt độ bề mặt đạt $25.4^\circ\text{C}$ ($< 45^\circ\text{C}$ ngưỡng an toàn tiếp xúc).

---

## 3. Khởi chạy Trích xuất

```bash
python book/0069-pager-product-architecture/pager_product_architecture.py
```
