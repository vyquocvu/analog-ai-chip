# 0009 — DAC thang R-2R (R-2R ladder DAC)

Ứng viên thiết kế đầu tiên cho đường tín hiệu converter (R2): một **thang
R-2R có trọng số nhị phân**. Đường activation cần `x (digital) → V (analog)`,
và thang R-2R hiện thực nó chỉ với hai giá trị điện trở, `R` và `2R`.

## Vì sao chọn thang R-2R

- Chỉ dùng đúng hai giá trị điện trở bất kể độ phân giải (`R`, `2R`) — một
  khối thực tế, chế tạo được.
- Ngõ ra chỉ phụ thuộc vào **tỉ số** điện trở và `VREF`, nên độ lợi và dải
  được đặt bởi thiết kế, không phải bởi linh kiện đặc biệt.
- Mô hình tay đơn giản và chính xác dưới switch lý tưởng:

  ```text
  Vout(code) = VREF * code / 2^N ,   code = Σ bit_i · 2^i
  ```

## Đơn vị và giả định

| Đại lượng | Giá trị | Đơn vị |
|---|---|---|
| `BITS` | 4 | bề rộng thang (nguyên mẫu) |
| `VREF` | 2.5 | V (tham chiếu; khớp tham chiếu 0007/0005) |
| `R` | 10 | kΩ (điện trở đơn vị) |
| `2R` | 20 | kΩ (nhánh bit / điện trở kết thúc) |
| full scale | `VREF·15/16 = 2.34375` | V (code 15) |
| LSB | `VREF/16 = 0.15625` | V trên mỗi code |

Mọi giá trị là mục tiêu mô phỏng; không phải kết quả silicon đo thật.

## Mạch

![Sơ đồ thang R-2R](diagrams/ladder_schematic.svg)

- Mỗi node `n_i` có một nhánh `2R` được chuyển giữa `VREF` (bit = 1) và ground
  (bit = 0). Bit 0 nằm ở đầu kết thúc (nhánh `2R` xuống GND); ngõ ra lấy tại
  `out`.
- Thang chia dòng theo cấp số nhân, nên mỗi bit đóng góp
  `VREF · 2^i / 2^N` tại ngõ ra.

Chạy: `book/0009-dac-r2r/r2r_dac.py`

### Đặc tuyến mẫu

![Đặc tuyến DAC: Vout theo code](diagrams/transfer.svg)

Đặc tuyến bậc thang 4-bit tăng một LSB (`0.15625 V`) mỗi code, chồng khít lên
đường lý tưởng `Vout = VREF·code/16`. Đồ thị được tạo lại từ extract đã commit
(`verification/circuit/results/dac-r2r-v1-extract.json`) bởi
`book/0009-dac-r2r/diagrams/make_transfer.py`, nên luôn hiển thị đúng các số
mà test kiểm chứng.

## Kiểm chứng

- **SPICE so với tay**: toàn bộ 16 code, `worst |SPICE − ideal| = 4.44e-16 V`
  (giải DC operating point với nguồn switch lý tưởng).
- `Vout(0) = 0`, đơn điệu theo cấu trúc, `Vout(15) = 2.34375 V`.
- **Điện trở ngõ ra**: đường tải DC hai điểm cho `Rth = 2R = 20 kΩ`, độc lập
  với code (hướng thang — kết thúc tại đầu LSB, ngõ ra tại đầu MSB — đặt
  `Rth = R + Z` với `Z = 2R ‖ (R + Z)`).
- **Settling quá độ**: với tải *giả định* `CL = 1 pF` và băng 0.5 LSB, một bước
  full-scale settling trong 68.7 ns (SPICE) so với 68.0 ns từ mô hình tay một
  cực `t = 2R·CL·ln(ΔV/band)`. Giá trị `CL` chưa có bằng chứng device, nên
  settling chỉ là nghiên cứu độ nhạy: nó nằm trong extract JSON và cố ý KHÔNG
  phải trường profile (sẽ fail `physical_claim` khi validate).
- **Độ nhạy nguồn VREF**: thang dựa trên tỉ số, nên lệch VREF là *sai số độ
  lợi thuần* — đo (SPICE) `gain_error` bằng `dVREF/VREF` tại ±10% trong sai số
  `1e-9`, offset giữ chính xác `0`, và đặc tuyến lệch tái hiện mô hình tay
  `Vout = VREF'·code/2^N` từng code một. Nhiệt độ và process corner **không**
  có hiệu ứng mô hình được trên điện trở lý tưởng theo cấu trúc; điều đó được
  ghi là ngoài phạm vi, không quét như bằng chứng giả. Lệch nguồn trên mô hình
  lý tưởng là điều kiện thiết kế, không phải bằng chứng device mới, nên nghiên
  cứu chỉ nằm trong extract JSON và không phải trường profile.
- Test dữ liệu chạy luôn + test engine tùy chọn trong `tests/test_dac_r2r_profile.py`.

## Chương này CHƯA làm gì

- Mismatch điện trở / Monte Carlo — được giao cho chương 0011 (biến thiên
  converter): độ nhạy số của thang tỉ số dưới mismatch, dưới dạng nghiên cứu
  độ nhạy `sigma` giả định (fail closed dưới `physical_claim`).
- Điện trở switch khác 0 — switch thật thêm offset và INL; nguồn lý tưởng là
  mô hình DC ở đây.
- Điện dung tải có bằng chứng device cho settling — `CL` được giả định; một
  `CL` đo được (ngõ vào ADC / ký sinh) sẽ nâng settling thành khẳng định vật lý.

Những mục này được theo dõi là mục mở trong gate R2.
