# 0005 — Xây một neuron analog

> **Thời gian đọc:** ~15 phút · **Mô phỏng:** `python book/0005-one-analog-neuron/sim_neuron.py`

## Mục tiêu

Xây và đo một mạch điện áp thấp tính một tổng có trọng số:

```text
y = w1*x1 + w2*x2 + b
```

Bản sửa đầu tiên có thể bỏ qua ngõ vào bias và thêm nó sau khi đã xác nhận tổng có trọng số hai ngõ vào.

## Mô phỏng trước khi xây

Chương này giờ kiểm chứng mạch trong SPICE (qua PySpice + ngspice) *trước khi*
bạn chạm vào breadboard. Mạch đề xuất đầu tiên là một **bộ khuếch đại cộng đảo**
hai ngõ vào trên nguồn 5 V:

![Bộ khuếch đại cộng đảo](diagrams/summer.svg)

```text
         Rf = 1 k
x1 ── R1=2k ──(+)── out      với  w1 = Rf/R1 = 0.50
x2 ── R2=4k ──(+)              w2 = Rf/R2 = 0.25
               (op-amp)        Vout = −(w1·x1 + w2·x2)
```

Với hợp đồng tính tay `x = [0.5, 1.0]`:

```text
|Vout| = 0.5·0.5 + 0.25·1.0 = 0.25 + 0.25 = 0.5 V
```

Cài engine và chạy phép kiểm chứng:

```bash
brew install ngspice                # engine SPICE (macOS/Homebrew)
python -m pip install -e '.[sim]'   # PySpice + package
python book/0005-one-analog-neuron/sim_neuron.py
```

Kết quả (6 case đầu vào đều khớp phép toán bằng tay):

```text
  x1     x2    |Vout|(sim)  y(hand)   match
 0.50  1.00     0.5000     0.50    OK
 0.20  0.80     0.3000     0.30    OK
 1.00  0.00     0.5000     0.50    OK
 0.00  2.00     0.5000     0.50    OK
 0.60  1.20     0.6000     0.60    OK
 0.80  0.40     0.5000     0.50    OK
```

> Mô phỏng dùng **model op-amp lý tưởng** — nó kiểm chứng *quan hệ cộng*, không
> phải saturation/common-mode/offset của linh kiện thật. Những giới hạn đó
> chính là thứ mà trình tự đưa mạch vào hoạt động (§ dưới) phải xác nhận trên
> phần cứng thật. Nếu chưa cài ngspice, script thông báo và bỏ qua một cách
> sạch sẽ thay vì lỗi.

### Op-amp phi lý tưởng: một chip thật thực sự làm gì

Model lý tưởng không bao giờ bão hoà và không có offset — chip thật thì có.
Chương giờ cũng kiểm chứng một model **phi lý tưởng** (độ lợi vòng hở hữu hạn,
một offset ngõ vào `Vos`, và một rail đầu ra `0..5 V`) trong `sim_neuron_nonideal.py`:

```bash
python book/0005-one-analog-neuron/sim_neuron_nonideal.py
```

Đo được (tất cả đều tường minh, không giấu gì):

| Kịch bản | Kết quả |
|---|---|
| 1 — tuyến tính @ mức chuẩn 2.5 V | `out = 2.3496` vs lý tưởng `2.3500` (lỗi 0.4 mV) |
| 2 — đầu ra vượt rail 5 V | lý tưởng `5.875` → **bão hoà tại `5.000`** |
| 3 — tham chiếu đất, nguồn đơn 5 V | đầu vào dương → **bão hoà tại `0`** (đúng cảnh báo chương) |
| 4 — `Vos = 10 mV` | dịch đầu ra lên `+0.0175 V` |

Kết quả then chốt của Kịch bản 3 là cảnh báo của chương trở thành con số đo
được: một bộ cộng **đảo** trong sách giáo khoa tham chiếu xuống đất không thể
xuất giá trị âm trên nguồn đơn 5 V, nên nó bão hoà tại `0 V`. Đó là lý do bản
build kiểm chứng phải dùng một **mức chuẩn ảo** (vd. VDD/2) như kịch bản 1–2 —
và vì sao trình tự đưa mạch vào hoạt động thật phải ghi lại nơi saturation thực
sự xảy ra.

### DC sweep: nhìn thấy vùng tuyến tính và các rail

Quét một đầu vào trên toàn dải nguồn biến "vùng tuyến tính" thành thứ bạn đọc
được trực tiếp từ đồ thị:

```bash
python book/0005-one-analog-neuron/sweep_neuron.py
```

![Vout vs x1: vùng tuyến tính và điểm bão hoà rail](diagrams/sweep.svg)

Giữ mức chuẩn 2.5 V ở đầu vào kia (nên `x2` không đóng góp), đầu ra tuân theo
`Vout = 2.5 − 0.5·(x1 − 2.5)`:

- **độ dốc vùng tuyến tính = −0.500**, khớp `−w1 = −0.5`;
- **bão hoà tại rail 5 V** khi `x1 ≤ −2.5 V`;
- **bão hoà tại rail 0 V** khi `x1 ≥ 7.5 V`.

**Headroom** quanh mức chuẩn 2.5 V là `2.5 V` lên rail 5 V và `2.5 V` xuống đất —
nên đầu vào phải làm đầu ra dao động trong ±2.5 V quanh mức chuẩn để giữ tuyến
tính. Đây chính là đại lượng cần ghi lại trên phần cứng thật (task A3), nơi dao
động sẽ nhỏ hơn lý tưởng.

### Virtual ground và rail headroom

Hai tính chất mà người xây kiểm tra lúc đưa mạch vào hoạt động — giờ đã kiểm
chứng trong mô phỏng:

```bash
python book/0005-one-analog-neuron/headroom_neuron.py
```

![Virtual-ground error theo độ lợi vòng hở](diagrams/virtual_ground.svg)

**Virtual ground.** Trong vùng tuyến tính, nút tổng `n` phải nằm tại mức chuẩn
2.5 V. Với model độ lợi hữu hạn, sai số nhỏ và tăng theo `1/Aol`:

- `Aol = 1e4`: `max |n − VREF| = 0.37 mV`
- `Aol = 1e3`: `max |n − VREF| = 3.74 mV`

Đây là lý do chất lượng op-amp/nguồn chuẩn (độ lợi vòng hở, offset) hiện ra như
một độ lệch nhỏ ở nút tổng — đo được, nhưng thường nhỏ so với dung sai điện
trở.

**Rail headroom.** Trên nguồn 5 V với mức chuẩn 2.5 V:

```text
headroom lên  = VDD − VREF = 2.5 V
headroom xuống = VREF − 0   = 2.5 V
```

Giữ `|Vout − VREF| ≤ 2.5 V` để còn tuyến tính. Với cấu hình tham chiếu đất,
`headroom xuống = 0`, đúng là lý do nó bão hoà với mọi đầu vào dương.

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
