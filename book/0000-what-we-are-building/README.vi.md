# 0000 — Chúng ta đang xây gì

Mục tiêu không phải là chế tạo một con chip AI hiện đại trong gara. Mục tiêu là xây một cỗ máy neural mô-đun nhỏ, trong đó phép nhân ma trận-véc-tơ **diễn ra về mặt vật lý** thông qua điện áp, độ dẫn và dòng điện được cộng dồn.

## Cỗ máy

```text
Máy tính chủ (Host)
    |
    | USB / serial
    v
Controller ---- lưu trữ hiệu chuẩn
    |
    v
DAC / bộ điều khiển đầu vào
    |
    v
Tile độ dẫn analog
    |
    v
Tầng dòng-điện-thành-điện-áp
    |
    v
ADC / đo lường
    |
    +----> activation digital, điều khiển, và lớp tiếp theo
```

Cỗ máy đầu tiên là **hybrid**. Trọng số tĩnh nằm trong một mạng điện trở hoặc điện trở lập trình được. Phép nhân ma trận-véc-tơ là analog. Việc điều khiển, hiệu chuẩn, hàm kích hoạt phi tuyến, lập lịch và cộng dồn partial sum ban đầu có thể giữ ở dạng digital.

## Điều gì thực sự là analog

Với một mảng độ dẫn lý tưởng, điện áp đầu vào biểu diễn `x`, độ dẫn được lập trình biểu diễn `W`, và dòng điện của cột biểu diễn `W @ x`. Mạch vật lý thực hiện phép nhân qua **Định luật Ohm** và phép cộng dồn qua **Định luật Kirchhoff (KCL)**.

## Đây chưa phải là ReRAM

Phần cứng đầu tiên dùng các linh kiện dễ kiếm như điện trở chính xác, biến trở, công tắc analog, hoặc chiết áp số (digital potentiometer). Những linh kiện này tái hiện được bài toán ánh xạ độ dẫn nhưng **không có đủ mọi tính chất của một cell ReRAM**. Sau này, một module bộ nhớ có thể thay thế tile độ dẫn mà không làm thay đổi các hợp đồng của controller và phần mềm.

## Ranh giới mô-đun

Dự án tách biệt:

- công nghệ lưu trữ trọng số;
- bộ chuyển đổi đầu vào;
- mảng analog;
- bộ chuyển đổi đầu ra;
- controller;
- việc biên dịch và hiệu chuẩn phía host.

Điều này cho phép người xây bắt đầu với một mảng 2×2 cố định và sau này chỉ thay thế đúng module liên quan.

## Định nghĩa thành công

Homebrew Analog AI v0.1 được coi là thành công khi một người xây thứ hai có thể:

1. lắp ráp các module theo tài liệu từ BOM;
2. chạy được self-test;
3. hiệu chuẩn được tile;
4. lập trình được một ma trận có dấu nhỏ;
5. gửi được một véc-tơ đầu vào;
6. đo được kết quả trong phạm vi sai số đã ghi;
7. chạy một bộ phân loại nhỏ mà các phép nhân ma trận vật lý dùng tile analog.

## Dự án này không tuyên bố điều gì

- Không phải là tutorial chế tạo bán dẫn.
- Ban đầu không phải là một mạng neural toàn analog.
- Không tự động nhanh hơn hay tiết kiệm hơn CPU/GPU.
- Một thao tác crossbar không làm cho toàn bộ LLM trở thành hằng số thời gian.
- Một mạng điện trở không giống hệt một mảng ReRAM.

## Trước khi tiếp tục

Đọc [`docs/SAFETY.md`](../../docs/SAFETY.md) và [`docs/MODULE_STANDARD.md`](../../docs/MODULE_STANDARD.md). Sau đó tiếp tục đọc book theo thứ tự: các chương lý thuyết 0001–0004 xây dựng nền tảng toán học có thể thực thi, và chương 0005 biến một tổng có trọng số thành một mạch analog đo được.
