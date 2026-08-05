# 0007 — Cột crossbar vi sai kiểu dòng (current-mode differential crossbar column)

Nâng cấp từ **summer điện áp** (0005/0006) lên đúng kiến trúc mà simulator
(`analog_llm/crossbar.py`, `tile.py`) mô hình: một **cột crossbar vi sai theo
dòng với các ô conductance** và bộ đọc transimpedance. Đây là hiện thân vật lý
của một hàng của phép `y = W @ x` mà simulator tính.

## Vì sao (nâng cấp này)

- **0005/0006** học summer khuếch đại có trọng số: `Vout = VREF − Σ w_i·x_i`
  với trọng số là điện trở (`Rf/R = w`). Nó mô hình *phép toán* của một neuron,
  nhưng chưa phải ô *in-memory-computing*: conductance khả trình `G` sinh dòng
  `I = V·G`, và các cột cộng dòng, không phải tỉ số điện trở.
- **0007** dựng cột đó: trọng số có dấu bằng conductance vi sai `G+`/`G-`,
  dòng được cộng tại virtual ground, và bộ đọc transimpedance + vi sai cho ra
  `Σ w_i·(x_i − VREF)`.

## Đơn vị và giả định

| Đại lượng | Giá trị | Đơn vị |
|---|---|---|
| `VREF` | 2.5 | V (điện áp tham chiếu ảo) |
| `G0` | 0.1 | mS (conductance zero cân bằng) |
| `GSCALE` | 0.1 | mS trên đơn vị trọng số |
| `RF` | 10 | kΩ (hồi tiếp transimpedance) |
| trọng số `w` | ±0.5, ±0.25 | không thứ nguyên (trong [-1,1]) |
| ngõ vào `x` | quanh 2.5 | V |

Lớp tín hiệu: `Vout = RF·GSCALE·Σ w_i·(x_i−VREF)`. Mọi giá trị là mục tiêu mô
phỏng; không phải kết quả silicon đo thật.

## Mạch

- Mỗi `w_i` hiện thực bằng hai conductance: `G+_i − G-_i = w_i·GSCALE`
  (zero cân bằng tại `G0`, đúng như `map_differential`).
- Ngõ vào lái cả hai ô; dòng cộng tại các node virtual-ground `np` (plus) và
  `nm` (minus).
- Hai tầng transimpedance op-amp: `Vp = VREF − RF·Iplus`, `Vm = VREF − RF·Iminus`.
- Tầng vi sai: `Vout = Vm − Vp = RF·(Iplus − Iminus)`.

Chạy: `book/0007-crossbar-column/crossbar_column.py`

## Kiểm chứng

- **SPICE** (`run_column`): `Vout = 0.1501 V` so với tính tay `0.1500 V`
  (sai số `1e-4` V); trọng số âm đảo dấu đúng.
- **Ánh xạ vi sai**: `G+_i − G-_i = w_i·GSCALE` đúng tới `7e-21 S`.
- Test dữ liệu chạy luôn + test engine tùy chọn trong `tests/test_crossbar_column.py`.

## Ledger

Một cột crossbar với `M` ngõ vào dùng `2M` ô conductance (vi sai) và `3` op-amp
(hai TIA + một vi sai). Đây là đơn vị vật lý mà simulator báo là
`macs`/`tiles`/`programs` khi phóng to.

Ghi chú ngspice: hai tầng TIA là các mạng tuyến tính độc lập nên `Vout = Vm − Vp`
theo nguyên lý chồng chập. DC operating point của ngspice nhạy số khi có hai
vòng khuếch đại lý tưởng trong cùng một netlist, nên mỗi tầng được giải trong
netlist riêng rồi phối hợp — chính xác, vì hai tầng không ghép với nhau.
