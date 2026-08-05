# 0005 — Xây một neuron analog

Trạng thái: chương thiết kế. Việc chọn linh kiện và bằng chứng đo đạc chưa hoàn tất.

## Mục tiêu

Xây và đo một mạch điện áp thấp tính một tổng có trọng số:

```text
y = w1*x1 + w2*x2 + b
```

Bản sửa đầu tiên có thể bỏ qua ngõ vào bias và thêm nó sau khi đã xác nhận tổng có trọng số hai ngõ vào.

## Kết quả học được

Đến cuối chương này, người xây phải giải thích và đo được:

- điện áp biểu diễn một giá trị đầu vào như thế nào;
- điện trở/độ dẫn biểu diễn một trọng số như thế nào;
- dòng điện cộng lại tại một nút tổng như thế nào;
- một op-amp chuyển dòng tổng thành điện áp đầu ra như thế nào;
- vì sao dấu, độ lợi, headroom, offset và bão hòa lại quan trọng;
- vì sao đầu ra đo được khác với phép toán lý tưởng.

## Các khối đề xuất

```text
Input x1 -- conductance G1 --+
                            +-- summing node -- op-amp -- Vout
Input x2 -- conductance G2 --+
```

Sơ đồ đã kiểm chứng phải dùng một cấu trúc tương thích với op-amp nguồn đơn đã chọn và điện áp ảo chuẩn. Đừng sao chép nguyên một mạch cộng đảo (inverting summer) nguồn kép trong sách giáo khoa lên breadboard 5 V nếu chưa tính đến dải common-mode ngõ vào và headroom đầu ra.

## Hợp đồng tính tay

Chương sẽ chốt một ví dụ nhỏ trước khi hoàn tất mạch. Một ứng viên là:

```text
x = [0.5, 1.0]
w = [0.5, 0.25]
ideal weighted sum = 0.5
```

Ánh xạ vật lý phải ghi lại:

- tỷ lệ giá-trị-sang-điện-áp;
- tỷ lệ trọng-số-sang-độ-dẫn;
- điện trở hồi tiếp;
- cực tính;
- điện áp đầu ra dự kiến;
- khoảng sai số chấp nhận được.

## Vật phẩm bắt buộc

- `schematic/` nguồn và bản xuất PDF/PNG;
- `breadboard.md` với cách nối dây theo từng chân;
- `bom.csv` với linh kiện chính hãng cụ thể và lựa chọn thay thế;
- `measurements.csv` từ bản build đã đo;
- `verify.py` tái hiện phép toán dự kiến;
- bảng test-point cho nguồn, mức chuẩn, ngõ vào, nút tổng và đầu ra;
- quy trình hiệu chuẩn và tắt nguồn;
- ảnh hoặc sơ đồ khớp với bản sửa đã kiểm chứng.

## Trình tự đưa mạch vào hoạt động

1. Đọc hướng dẫn an toàn.
2. Chỉ xây và đo riêng tầng nguồn/mức chuẩn.
3. Xác nhận sơ đồ chân op-amp đã chọn từ datasheet.
4. Cấp nguồn cho op-amp không tín hiệu và kiểm tra điều kiện tĩnh.
5. Thêm một nhánh đầu vào và so sánh một điểm đo.
6. Thêm nhánh đầu vào thứ hai.
7. Quét vài đầu vào trong phạm vi an toàn.
8. Ghi đầu ra dự kiến và đo được.
9. Cố tình tiến đến bão hòa và ghi lại hiện tượng lỗi.
10. Tắt nguồn trước khi đổi giá trị linh kiện.

## Các phép đo cần ghi lại

| Phép đo | Dự kiến | Thực tế | Đơn vị | Dụng cụ |
|---|---|---:|---:|---|---|
| Nguồn | TBD |  | V | multimeter |
| Mức chuẩn analog | TBD |  | V | multimeter |
| Đầu vào 1 | TBD |  | V | multimeter |
| Đầu vào 2 | TBD |  | V | multimeter |
| Đầu ra | TBD |  | V | multimeter/scope |
| Nhiễu đầu ra | TBD |  | mV RMS | scope |

## Thí nghiệm

- thay điện trở 1% bằng điện trở 5%;
- làm ấm nhẹ một điện trở bằng cách cầm bình thường và quan sát trôi;
- lặp lại cùng một đầu vào 100 lần;
- tăng đầu vào đến khi đầu ra clip;
- so sánh phép đo bằng multimeter và oscilloscope;
- tính riêng sai số lý tưởng, sai số theo dung sai linh kiện và sai số đo được.

## Bản build này không chứng minh điều gì

Một mạch tổng có trọng số thành công không chứng minh việc lưu trữ ReRAM, khả năng co giãn mảng lớn, hiệu suất năng lượng cạnh tranh, độ chính xác mạng neural, hay suy luận nhanh hơn phần cứng digital. Nó chứng minh rằng một mạch analog thật có thể mã hóa và đo một tổng có trọng số nhỏ — đó là nguyên bản vật lý mà cỗ máy sau này sẽ nhân rộng và tự động hóa.
