# 0056 — Sổ Cái Vật Lý Tham Số Hóa Cho Suy Luận Mô Hình Lớn (Gate R14)

> **English version:** [`README.md`](README.md)

Chương này mở đầu cho **Gate R14 (Multi-tier physical feasibility and design decision)** bằng việc chuẩn hóa một **sổ cái vật lý tham số hóa theo kiến trúc mô hình**, thay thế hoàn toàn các hằng số vô hướng cố định bằng các phép tính chi tiết về năng lượng từng phân hệ, độ trễ, mật độ công suất và tản nhiệt trên các bậc T0–T3.

---

## 1. Kiến Trúc Tham Số Hóa & Kế Toán Năng Lượng

![Sổ Cái Vật Lý Tham Số Hóa](diagrams/physical-ledger.svg)

- **Sổ Cái Dựa Trên Kiến Trúc (Manifest-Driven)**: Mọi chỉ số về độ trễ, năng lượng và công suất đều được suy xuất động từ topo kiến trúc mô hình, phân bổ tile, dung lượng KV-cache và các tuyến truyền dữ liệu thay vì các ước tính phỏng đoán cố định.
- **Gắn Nhãn Nguồn Gốc Vật Lý (Provenance Tagging)**:
  - `analog_mvm`: **`spice_extracted`** ($0.12\text{ pJ / MAC}$ trên mảng ReRAM BEOL tiến trình 28nm).
  - `adc_dac`: **`measured/spice_correlated`** ($0.45\text{ pJ / phép đổi}$ cho ADC SAR 8-bit, $0.08\text{ pJ / phép đổi}$ cho DAC 8-bit).
  - `sram_noc`: **`derived`** ($0.25\text{ pJ / Byte}$ đệm SRAM, $0.80\text{ pJ / Byte}$ mỗi chặng NoC lưới 2D).
  - `ucie_link`: **`derived`** ($12.0\text{ pJ / Byte} = 1.5\text{ pJ / bit}$ liên kết interposer UCIe 2.5D).
  - `package_hbm`: **`derived`** ($28.0\text{ pJ / Byte} = 3.5\text{ pJ / bit}$ ngăn xếp JEDEC HBM3e).
  - `digital_attention`: **`derived`** ($0.85\text{ pJ / FLOP}$ khối tính attention số SIMD/systolic FP16).

---

## 2. Công Thức Độ Trễ & Năng Lượng

Với mô hình có $N_{\text{macs}}$ tham số chiếu analog, chiều dài ngữ cảnh $T$, kích thước ẩn $H$, và $L$ layer:

$$\text{Năng Lượng}_{\text{decode}} = E_{\text{mvm}} + E_{\text{adc\_dac}} + E_{\text{sram\_noc}} + E_{\text{ucie}} + E_{\text{hbm}} + E_{\text{attn}}$$

$$\text{Độ Trễ}_{\text{decode}} = t_{\text{mvm}} + t_{\text{attn\_compute}} + t_{\text{kv\_memory\_read}} + t_{\text{inter\_die}}$$

$$\text{Mật Độ Công Suất} = \frac{\text{Năng Lượng}_{\text{decode}} / \text{Độ Trễ}_{\text{decode}}}{A_{\text{silicon}}}$$

Ngưỡng giới hạn nhiệt: Làm mát bằng không khí $\le 150\text{ W/cm}^2$, Làm mát bằng chất lỏng $\le 350\text{ W/cm}^2$.

---

## 3. Thang Đo Sổ Cái Vật Lý Workload (T0–T3)

| Bậc Mô Hình | TTFT (ms) | Thông Lượng Decode | Năng Lượng Decode / Token | Công Suất Hoạt Động | Mật Độ Công Suất | Phân Loại Tản Nhiệt |
|---|---|---|---|---|---|---|
| **Hand-Calc ($2\text{L}$)** | $< 0.01\text{ ms}$ | $4,156,690\text{ TPS}$ | $0.01\ \mu\text{J}$ | $0.03\text{ W}$ | $2.68\text{ W/cm}^2$ | `PASS_AIR_COOLED` |
| **T0 (GPT-2 124M)** | $1.41\text{ ms}$ | $244,247\text{ TPS}$ | $26.38\ \mu\text{J}$ | $6.44\text{ W}$ | $1.92\text{ W/cm}^2$ | `PASS_AIR_COOLED` |
| **T1 (LLaMA-1B)** | $23.96\text{ ms}$ | $69,685\text{ TPS}$ | $439.66\ \mu\text{J}$ | $30.64\text{ W}$ | $0.75\text{ W/cm}^2$ | `PASS_AIR_COOLED` |
| **T2 (LLaMA-3B)** | $1,293.65\text{ ms}$ | $3,132\text{ TPS}$ | $11,411.06\ \mu\text{J}$ | $35.74\text{ W}$ | $0.31\text{ W/cm}^2$ | `PASS_AIR_COOLED` |
| **T3 (LLaMA-2 7B)** | $7,468.50\text{ ms}$ | $547\text{ TPS}$ | $62,752.97\ \mu\text{J}$ | $34.34\text{ W}$ | $0.13\text{ W/cm}^2$ | `PASS_AIR_COOLED` |

---

## 4. Phân Tích Năng Lượng Từng Phân Hệ

| Phân Hệ | Năng Lượng T0 (124M) | Năng Lượng T1 (1.1B) | Quy Luật Mở Rộng | Nguồn Gốc Dữ Liệu |
|---|---|---|---|---|
| **MVM ReRAM Analog** | $10.19\ \mu\text{J}$ ($38.6\%$) | $124.13\ \mu\text{J}$ ($28.2\%$) | Tỉ lệ thuận $\mathcal{O}(N_{\text{weights}})$ | `spice_extracted` |
| **Chuyển Đổi ADC / DAC** | $14.73\ \mu\text{J}$ ($55.8\%$) | $144.18\ \mu\text{J}$ ($32.8\%$) | Tỉ lệ thuận $\mathcal{O}(\text{activations})$ | `measured/spice` |
| **SRAM & NoC Trên Chip** | $1.46\ \mu\text{J}$ ($5.5\%$) | $14.28\ \mu\text{J}$ ($3.2\%$) | Tỉ lệ thuận $\mathcal{O}(\text{bytes kích hoạt})$ | `derived` |
| **UCIe Liên Die (2.5D)** | $0.00\ \mu\text{J}$ ($0.0\%$) | $1.08\ \mu\text{J}$ ($0.2\%$) | Chỉ áp dụng cho đa chiplet | `derived` |
| **Đọc KV Từ Package HBM3e**| $0.00\ \mu\text{J}$ ($0.0\%$) | $0.00\ \mu\text{J}$ ($0.0\%$) | Kích hoạt khi $M_{\text{KV}} > \text{SRAM}$ | `derived` |
| **Attention Vector Số** | $0.00\ \mu\text{J}$ ($0.0\%$) | $156.00\ \mu\text{J}$ ($35.5\%$) | Tỉ lệ thuận $\mathcal{O}(T \cdot H \cdot L)$ | `derived` |

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0056-parametric-physical-ledger/parametric_ledger.py
```

Chạy bộ unit test:
```bash
pytest tests/test_physical_ledger.py
```

File trích xuất artifact:
`verification/circuit/results/parametric-ledger-0056-extract.json`
