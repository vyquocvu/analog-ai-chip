# 0013 — Mảng crossbar vi sai 4×4 (gate exit R3)

Phóng to topology 0012 đã kiểm chứng thành mảng 4×4 đầy đủ: bốn hàng ngõ vào
dùng chung và bốn cột ngõ ra độc lập, mỗi cột là một cột 0007 lặp bốn lần.
Chương này là **gate exit R3**: nó định lượng sai số của mô hình hành vi của
*simulator kiến trúc* (CrossbarTile `analog_llm` trên profile
`crossbar-column-v1` đã kiểm chứng) so với cả mảng SPICE và tham chiếu tay, và
ghi lại các dòng điện mảng cùng một điểm dữ liệu settling với điện dung giả
định.

```
Vout_j = Rf · Σ_i u_i · (G+_ij − G−_ij) = Rf · Gscale · (W @ u)_j,
u_i = x_i − VREF,  W_ij ∈ [−1, 1],  Rf·Gscale = 1 V trên volt trên trọng số
```

Cùng hằng số với 0005/0007/0009/0010/0012: `VREF = 2.5 V`, `G0 = Gscale =
0.1 mS`, `Rf = 10 kΩ`, `HEADROOM = ±2.5 V`.

## Phương pháp

- **SPICE**: mỗi half-column TIA (tổng 8) là một mạng tuyến tính độc lập giải
  trong netlist ngspice riêng với cùng VCVS độ lợi hữu hạn (1e4) như
  0007/0012, rồi phối hợp theo nguyên lý chồng chập: `Vout_j = Vm_j − Vp_j`.
- **Tham chiếu tay**: `Vout = Rf·Gscale·(W @ u)` trong NumPy, cộng tổng dòng
  mỗi ô `Iplus_j = Σ_i u_i·G+_ij`.
- **Tile hành vi**: `analog_llm.build_tile_factory` trên
  `device_profiles/crossbar-column-v1.json` với lượng tử 16-bit
  programming/DAC/ADC — sai số của tile là sàn lượng tử của nó, không phải con
  số chỉnh tay.
- **Bộ trường hợp xác định**: 5 trường hợp `(W, u)` × 4 ngõ ra: trộn dấu,
  chéo thưa, rank-1, và ma trận zero (kiểm tra zero cân bằng).

## Kết quả (đã commit trong `verification/circuit/results/crossbar-4x4-0013-extract.json`)

| Đại lượng | Giá trị |
|---|---|
| worst \|SPICE − hand\| | 5.5e-4 V (rms 3.3e-4 V) |
| worst \|tile − hand\| | 3.8e-5 V (rms 2.8e-5 V) |
| worst \|SPICE − tile\| | 5.2e-4 V (rms 3.1e-4 V) |
| ngân sách sai số R3 đông cứng | 2e-3 V (đều đạt) |
| max \|Vout\| | 0.50 V ≪ headroom ±2.5 V |
| sai số virtual-ground tối đa | 3.0e-4 V |
| sai số dòng cột tệ nhất | 1.8e-7 A |
| dòng ô lớn nhất | 1.0e-4 A (chặn khả thi) |
| hồi quy 2×2 (so extract 0012) | 0.0e+00 V |
| ngõ ra ma trận zero | chính xác 0 V |

**Phát hiện tương đương hành vi**: tile (sàn lượng tử 3.8e-5 V) *gần* tham
chiếu tay hơn một bậc độ lớn so với chính mảng SPICE (sai số độ lợi hữu hạn
VCVS 5.5e-4 V), và cả hai đều nằm gọn trong ngân sách 2e-3 V đông cứng. Tile là
mô hình hành vi trung thực, thận trọng của mảng SPICE.

## Dòng điện và settling

- Dòng cột khôi phục từ ngõ ra half-stage SPICE, `Iplus_j = (VREF − Vp_j)/Rf`,
  khớp `Σ u_i·G+_ij` tay đến 1.8e-7 A.
- **Settling được ghi lại, không được khẳng định.** Một quá độ với điện dung
  node cộng 1 pF *giả định* cho 22.7 ns để settling trong 1 mV (chặn dưới tay
  một cực 13.2 ns), nhưng VCVS lý tưởng không có mô hình băng thông — đuôi
  dạng sóng bị mô hình chi phối, nên dữ liệu này chỉ nằm trong extract JSON và
  fail closed dưới `physical_claim`. Settling có chặn là mục gate 0014.

## Gate exit R3

Mọi mục gate đều được đánh dấu trong `docs/ROADMAP.md` với bằng chứng SPICE
đã commit, tái tạo được + báo cáo tương đương hành vi
(`verification/reports/crossbar-4x4-summary.md`). R3 **HOÀN TẤT**; R4 (device
realism conductance khả trình) là gate kế tiếp.

## Sơ đồ

- `diagrams/array_4x4.svg` — sơ đồ 4×4 đầy đủ: rail dùng chung, 32 ô vi sai,
  bus cộng Vp/Vm, tám tầng TIA với hồi tiếp Rf, node trừ.
- `diagrams/theory.svg` — lý thuyết hoạt động: phương trình MVM, ô vi sai,
  chồng chập, ví dụ tính tay, tóm tắt tương đương hành vi và mức khẳng định.
- `diagrams/make_plots.py` → `diagrams/mvm_error.svg` — SVG chỉ dùng stdlib
  được tạo lại từ extract đã commit (thanh sai số mỗi trường hợp so ngân sách
  R3; max |Vout| mỗi trường hợp so headroom kèm sai số virtual-ground).

## Chạy

```
python book/0013-crossbar-4x4/crossbar_4x4.py      # bộ SPICE + khẳng định
python verification/circuit/extract_crossbar_4x4.py # tạo lại extract JSON
python verification/reports/generate_crossbar_4x4_summary.py
python book/0013-crossbar-4x4/diagrams/make_plots.py
pytest tests/test_crossbar_4x4.py
```
