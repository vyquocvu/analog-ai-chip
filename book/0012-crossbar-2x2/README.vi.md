# 0012 — Crossbar vi sai 2×2

Chương này mở rộng cột current-mode đã được kiểm chứng ở 0007 thành mảng thật nhỏ
nhất: **hai hàng input dùng chung cho hai cột output độc lập**. Mục tiêu hiện tại
là kiểm chứng topology, chưa phải mô hình vật liệu nhớ lập trình thực tế.

## Điều cần chứng minh

Theo convention `W[output, input]`, mạch phải thực hiện:

```text
y = RF · GSCALE · W @ (x − VREF)
```

Mỗi trọng số có dấu được mã hóa bằng cặp conductance vi sai:

```text
G+ = G0 + max(w, 0) · GSCALE
G- = G0 + max(-w, 0) · GSCALE
G+ - G- = w · GSCALE
```

Hai cột output nhận cùng các điện áp input nhưng có cell conductance và TIA riêng,
vì vậy chúng phải tạo ra hai dot-product độc lập.

## Ví dụ tính tay

```text
x = [3.0, 2.1] V
VREF = 2.5 V
x - VREF = [0.5, -0.4] V

W = [[ 0.50, 0.25],
     [-0.50, 0.25]]
```

Vì `RF · GSCALE = 1`:

```text
y0 =  0.50·0.50 + 0.25·(-0.40) =  0.15 V
y1 = -0.50·0.50 + 0.25·(-0.40) = -0.35 V
```

`ideal_mvm()` là oracle NumPy cho phép so trực tiếp với SPICE.

## Mô hình mạch

Mỗi cột output có hai nhánh dòng:

- mặt phẳng conductance dương `G+` → TIA `Vp`;
- mặt phẳng conductance âm `G-` → TIA `Vm`;
- output vi sai `Vout = Vm - Vp`.

Giống 0007, từng TIA branch được giải độc lập. Trong mô hình hiện tại các nhánh
không coupling với nhau ngoài các nguồn điện áp input lý tưởng dùng chung, nên
phép tách này giữ nguyên nghiệm DC.

SPICE hiện dùng operating point DC và op-amp VCVS gain lớn. Chương này chưa mô
phỏng ReRAM/memristor physics, line resistance, parasitic RC, drift hay settling
bandwidth; các hiệu ứng đó thuộc các package R3/R4 phía sau.

## Headroom

`headroom_report()` kiểm tra cả bốn điện áp nội bộ `Vp0`, `Vp1`, `Vm0`, `Vm1`
trước khi trừ vi sai. Điều này quan trọng vì output cuối có thể vẫn nhìn hợp lý
trong khi một TIA branch đã vượt rail.

Case danh định nằm trong envelope `[0, 5] V`. Test cũng có một case cố ý overdrive
với full-rail input và trọng số cực đại; code phải báo `within_rails = false`
thay vì âm thầm clip.

## Chạy

```bash
pytest tests/test_crossbar_2x2.py -q
```

Để chạy SPICE:

```bash
python -m pip install -e '.[dev,sim]'
python book/0012-crossbar-2x2/crossbar_2x2.py
pytest tests/test_circuit_sim.py -q
```

## Bằng chứng TDD

Commit đầu tiên của PR chỉ thêm contract tests. CI đã RED đúng vì module
`book/0012-crossbar-2x2/crossbar_2x2.py` chưa tồn tại. Implementation chỉ được
thêm sau khi failure dự kiến này đã được quan sát.

## Giới hạn hoàn thành

Chương chỉ được đánh hoàn thành khi:

- shared-row/two-column functional tests xanh;
- signed, zero/balanced, invalid shape/range và headroom boundary đều xanh;
- SPICE 2×2 khớp hand/NumPy reference trong tolerance đã khai báo trên runner có
  ngspice shared library hoạt động;
- ROADMAP trỏ vào executable evidence thay vì chỉ dựa vào prose.

Một crossbar 2×2 với conductance lý tưởng chạy đúng **không chứng minh** ReRAM
thật hoặc khả năng scale lên array lớn. Package kế tiếp sau khi hoàn thành 0012
là topology 4×4.
