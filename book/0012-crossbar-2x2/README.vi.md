# 0012 — Mảng crossbar vi sai kiểu dòng 2×2

Phóng to thiết kế một cột 0007 thành một **mảng** nhỏ: hai hàng ngõ vào dùng
chung cho hai cột ngõ ra độc lập. Đây là chương đầu tiên có bằng chứng SPICE là
một phép nhân ma trận-véc-tơ thật — `y = W @ u` với `W` ma trận `[outputs,
inputs]` — chính xác phép toán `analog_llm` ánh xạ lên tile.

## Lý thuyết

![Sơ đồ mảng 2×2](diagrams/array_schematic.svg)

Mỗi ô là một cặp conductance vi sai hiện thực trọng số có dấu

```text
w_ij · GSCALE = G+_ij − G−_ij,      zero cân bằng tại G0
```

Ngõ vào `x_i` lái cả hai ô của mọi cột; mỗi cột ngõ ra `j` cộng dòng ô của nó
tại hai node virtual-ground (một cho `G+`, một cho `G−`) và chuyển đổi bằng một
tầng transimpedance:

```text
Iplus_j  = Σ_i u_i · G+_ij        u_i = x_i − VREF
Iminus_j = Σ_i u_i · G−_ij
Vout_j   = Vm_j − Vp_j
         = RF · GSCALE · Σ_i u_i · w_ij
         = RF · GSCALE · (W @ u)_j
```

Hai hàng ngõ vào **dùng chung**; hai cột ngõ ra **độc lập** — các ô của mỗi
cột chỉ nối vào node cộng của cột đó, nên đổi trọng số cột này không bao giờ
đổi ngõ ra cột kia (khẳng định trong SPICE: `|ΔVout_0| = 0` khi chỉ đổi cột 1).

![Lý thuyết và luồng tín hiệu](diagrams/theory.svg)

## Đơn vị và giả định

| Đại lượng | Giá trị | Đơn vị |
|---|---|---|
| `VREF` | 2.5 | V (khớp 0005/0007/0009/0010) |
| `G0` | 0.10e-3 | S (conductance zero cân bằng) |
| `GSCALE` | 0.10e-3 | S trên đơn vị trọng số |
| `RF` | 10 | kΩ (hồi tiếp transimpedance) |
| `RF·GSCALE` | 1.0 | V trên volt trên trọng số |
| headroom vi sai | ±2.5 | V (crossbar-column-v1, derived) |
| op-amp | VCVS độ lợi 1e4 | mô hình lý tưởng, 0005/0007 |

Mọi giá trị là mục tiêu mô phỏng; không phải kết quả silicon đo thật.

## Mạch → các lần giải

`crossbar_2x2.py` là nguồn sự thật duy nhất cho các giải SPICE. Mỗi một trong
bốn tầng TIA (`Vp_0, Vm_0, Vp_1, Vm_1`) là một mạng tuyến tính độc lập chỉ
dùng chung các nguồn ngõ vào lý tưởng và tham chiếu, nên `Vout_j = Vm_j −
Vp_j` đúng theo nguyên lý chồng chập — mỗi tầng được giải trong netlist riêng
rồi phối hợp (đúng quy trình 0007, giờ cho bốn tầng).

## Kiểm chứng

- **MVM so với tham chiếu tay**: 5 trường hợp xác định × 2 ngõ ra — trọng số
  trộn dấu, vi sai full-scale, zero cân bằng, một zero mỗi hàng, và bọc biên —
  `worst |SPICE − hand| = 1.0e-3 V` (VCVS độ lợi 1e4; nhất quán với 8e-4 V của
  0007 cho biên độ nhỏ hơn). Zero cân bằng cho chính xác `0 V`.
- **Độc lập cột**: chỉ đổi trọng số cột 1 để `Vout_0` không đổi đến
  `0.0e+00 V`.
- **Headroom output-stage**: mọi ngõ ra vi sai nằm trong bọc `±2.5 V`
  (`max |Vout| = 2.499 V` tại trường hợp biên).
- **Virtual ground / loading**: mọi node cộng nằm trong `3.5e-4 V` của `VREF`
  (chặn `|Vhalf|/Aol` độ lợi hữu hạn của VCVS 1e4), thỏa kiểm tra loading
  0.05 V.
- **Phát hiện rail half-stage**: mỗi half-stage là một summer đảo *một rail*
  (0..5 V). Với trọng số full-scale tại biên bọc ngõ vào, half-stage `G+` của
  cột biên chạm **−2.5 V — dưới rail 0 V**. Mô hình VCVS lý tưởng không có
  clipping, nên ngõ ra vi sai vẫn chính xác, nhưng một TIA một rail thật sẽ
  clip tại đó. Điều này chặn bọc ngõ vào dùng được mỗi đầu vào cho `|w| = 1`:

  ```text
  |u| ≤ VREF / (RF·(G0 + GSCALE)) = 1.25 V
  ```

  tức là rail half-stage, không phải headroom vi sai ±2.5 V, đặt bọc mỗi ngõ
  vào. Được báo là phát hiện (không che giấu) và đưa vào extract; đây đúng
  kiểu ràng buộc mà công việc headroom và khả thi R4/R8 phải tôn trọng.

![Đồ thị MVM và headroom](diagrams/mvm_cases.svg) — được tạo lại từ extract đã
commit bởi `book/0012-crossbar-2x2/diagrams/make_plots.py`.

## Tạo phẩm (artifacts)

- `book/0012-crossbar-2x2/crossbar_2x2.py` — nguồn sự thật duy nhất cho các
  giải SPICE (chạy `python book/0012-crossbar-2x2/crossbar_2x2.py`).
- `verification/circuit/extract_crossbar_2x2.py` — trích xuất xác định; phát
  ra `verification/circuit/results/crossbar-2x2-0012-extract.json` (đặc tuyến
  từng trường hợp, headroom, virtual-ground, độc lập, phát hiện rail).
  Chạy: `python verification/circuit/extract_crossbar_2x2.py`.
- `tests/test_crossbar_2x2.py` — test mô hình tay và extract đã commit chạy
  luôn + test SPICE gated theo engine.
- `diagrams/array_schematic.svg`, `diagrams/theory.svg` — sơ đồ lý thuyết;
  `diagrams/make_plots.py` tạo lại `diagrams/mvm_cases.svg` từ extract đã commit.

Không có profile device mới được xuất bản ở đây: `crossbar-v1` (device realism)
là mốc R4. Chương này là **bằng chứng ánh xạ hành vi** rằng mảng 2×2 tính
`W @ u` đúng trong SPICE.

## Chương này CHƯA làm gì

- So sánh tương đương hành vi với mô hình tile của `analog_llm` và báo cáo sai
  số định lượng — đó là 0013 (4×4) / gate exit R3.
- Loading các hàng ngõ vào dùng chung bởi trở kháng driver hữu hạn (ngõ vào là
  nguồn lý tưởng ở đây); IR drop và RC ký sinh là mục R4.
- Mạch output-stage thật: TIA là mô hình VCVS lý tưởng 0005/0007, và clipping
  half-stage một rail tại `|u| > 1.25 V` (trọng số full-scale) được ghi nhận,
  không mô hình như clipping.

Những mục này được theo dõi là mục mở trong gate R3.
