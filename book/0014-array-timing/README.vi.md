# 0014 — Định thời, Tải trọng Mảng và Giới hạn Mở rộng

> **English version:** [`README.md`](README.md)

Chương này nghiên cứu hành vi mở rộng vật lý và số học của mảng crossbar vi sai chế độ dòng điện (current-mode differential crossbar array) khi số hàng $N$ và số cột $M$ tăng từ các mẫu thử nhỏ ($2\times 2$, $4\times 4$) đến kích thước ô thực tế ($8\times 8$, $16\times 16$, $32\times 32$, $64\times 64$).

---

## 1. Kiến trúc Mạch & Mô hình Tải trọng TIA

![Lý thuyết Tải nút cộng và Độ lợi nhiễu](diagrams/theory.svg)

Trong phép nhân ma trận - vector lý thuyết, việc thêm số hàng không làm ảnh hưởng đến tính toán của từng cột riêng lẻ. Tuy nhiên trong mảng crossbar vật lý, mỗi ô nhớ trên cùng một bitline sẽ bổ sung thêm điện dẫn nối song song vào nút cộng đảo của mạch khuếch đại chuyển trở (TIA).

Với một cột gồm $N$ hàng và điện dẫn cân bằng danh định $G_0 = 0.1\text{ mS}$ ($10\text{ k}\Omega$):
$$G_{\text{tot}} = \sum_{i=1}^N G_i \approx N \cdot G_0$$

**Độ lợi nhiễu** vòng kín $N_G$ tác động lên op-amp TIA là:
$$N_G = 1 + R_F \cdot G_{\text{tot}} \approx 1 + N \cdot R_F \cdot G_0$$

Với $R_F = 10\text{ k}\Omega$ và $G_0 = 0.1\text{ mS}$, tích số $R_F \cdot G_0 = 1.0$, do đó:
$$N_G \approx 1 + N$$

### Ảnh hưởng tới Độ lợi Vòng lặp và Sai số DC:
Hệ số hồi tiếp $\beta = 1 / N_G$ giảm tuyến tính theo số hàng $N$, làm suy giảm độ lợi vòng lặp $T = A_{OL} \cdot \beta = A_{OL} / N_G$.
Với op-amp có độ lợi hở DC $A_{OL} = 10^4$:
$$\text{Sai số Độ lợi} \approx \frac{N_G}{A_{OL} + N_G} = \frac{1 + N}{10^4 + 1 + N}$$

| Kích thước $N$ | Độ lợi nhiễu $N_G$ | Sai số DC lý thuyết | Sai số MVM mô phỏng SPICE |
|:---:|:---:|:---:|:---:|
| **2** | 3.0 | 0.030% | $5.62\times 10^{-5}\text{ V}$ |
| **4** | 5.0 | 0.050% | $6.21\times 10^{-6}\text{ V}$ |
| **8** | 9.0 | 0.090% | $9.37\times 10^{-5}\text{ V}$ |
| **16** | 17.0 | 0.170% | $2.93\times 10^{-4}\text{ V}$ |
| **32** | 33.0 | 0.329% | $6.91\times 10^{-4}\text{ V}$ |
| **64** | 65.0 | 0.646% | $1.48\times 10^{-3}\text{ V}$ |

Khi $N$ tăng lên 64, sai số do độ lợi hữu hạn của op-amp đạt $\approx 0.65\%$, và nếu mở rộng đến $N=1024$ mà không có bù trừ thì sai số sẽ vượt quá $9\%$.

![Mô phỏng quét mở rộng số hàng và độ lợi nhiễu](diagrams/scaling_plots.svg)

---

## 2. Tải Dung Nút Cộng & Thời gian Ổn định (Settling)

Mỗi ô nhớ đóng góp một điện dung ký sinh $C_{\text{cell}}$ vào đường bitline.
Tổng điện dung ngõ vào tại nút cộng tăng tỷ lệ thuận với $N$:
$$C_{\text{in}}(N) = N \cdot C_{\text{cell}} + C_{\text{TIA}}$$

Với op-amp có tích số độ lợi - băng thông $\text{GBW}$, băng thông vòng kín hiệu dụng của tầng TIA giảm theo:
$$f_{-3\text{dB}} \approx \frac{\text{GBW}}{N_G} = \frac{\text{GBW}}{1 + N \cdot R_F \cdot G_0}$$

Hệ quả là thời gian ổn định tín hiệu (settling time) sẽ kéo dài tỷ lệ thuận với số hàng $N$.

---

## 3. Khả năng Mở rộng Trình Mô phỏng & Ngưỡng Chuyển sang Xyce

Khi mô phỏng các cột tuyến tính độc lập, thời gian giải điểm làm việc DC của SPICE tăng tuyến tính. Tuy nhiên, khi đưa điện trở đường dây ký sinh (IR drop) và hiệu ứng ghép nối giữa các cột vào mô phỏng (Gate R4), kích thước ma trận mạch tăng theo $O(N^2)$, dẫn tới độ phức tạp giải tăng phi tuyến ($O(N^2)$ đến $O(N^3)$ trong ngspice đơn luồng).

- **$N \le 64$**: `ngspice` (thông qua PySpice) giải trong vài mili-giây, rất phù hợp cho kiểm thử hồi quy nhanh.
- **$N \ge 128$**: Các mảng lớn ghép nối phức tạp đòi hỏi trình giải song song phân tán như `Xyce` để đảm bảo thời gian mô phỏng thực tế.

---

## Kiểm thử & Xác minh

Chạy quét mô phỏng SPICE và xuất kết quả:
```bash
python book/0014-array-timing/array_timing.py
```
Dữ liệu cam kết: [`verification/circuit/results/array-timing-0014-extract.json`](../../verification/circuit/results/array-timing-0014-extract.json).
Kiểm thử tự động: [`tests/test_array_timing.py`](../../tests/test_array_timing.py).
