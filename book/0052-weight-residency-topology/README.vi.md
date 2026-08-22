# 0052 — Khả Năng Thường Trú Trọng Số, Khảo Sát Kiến Trúc & Mở Rộng Chiplet (Gate R12)

> **English version:** [`README.md`](README.md)

Chương này mở đầu cho **Gate R12 (Large-model accelerator capacity and data movement)** bằng việc chuẩn hóa **dung lượng tile crossbar vật lý, cấu hình cặp ô nhớ vi sai, quy mô diện tích silicon và tính khả thi đóng gói chiplet đa die** trên các bậc khối lượng công việc T0–T3.

---

## 1. Kiến Trúc Phần Cứng & Mở Rộng Topo Crossbar

![Dung Lượng Thường Trú & Topo Trọng Số](diagrams/residency-topology.svg)

- **Crossbar Analog Cố Định (Stationary)**: Kiến trúc tính toán trong bộ nhớ analog đạt hiệu suất năng lượng tối đa khi ma trận trọng số được lập trình cố định trong điện dẫn ReRAM không bay hơi, loại bỏ hoàn toàn việc nạp lại trọng số từ DRAM/HBM trong khi suy luận.
- **Giới Hạn Silicon Vật Lý**:
  - Giới hạn reticle chuẩn cho một die đơn: $400.0\text{ mm}^2$.
  - Giới hạn đóng gói interposer 2.5D/3D tiên tiến: tối đa $12\text{ chiplet}$ kết nối qua chuẩn UCIe băng thông cao ($512\text{ GB/s}$).
- **Báo Cáo Bất Khả Thi Tường Minh**: Các mô hình vượt quá dung lượng đóng gói (T2/T3) được báo cáo rõ ràng là bất khả thi về mặt vật lý để lưu trữ thường trú cố định thay vì che giấu đằng sau các giả định vô lý về bộ nhớ vô hạn.

---

## 2. Cặp Ô Nhớ Vi Sai & Công Thức Diện Tích Silicon

Mỗi trọng số có dấu $W_{i,j}$ yêu cầu một cặp ô ReRAM vật lý ($G_{i,j}^+, G_{i,j}^-$) trong tile $16 \times 16$:

$$N_{\text{tiles}} = \sum_{p \in \text{projections}} \left\lceil \frac{\text{out}_p}{16} \right\rceil \times \left\lceil \frac{\text{in}_p}{16} \right\rceil$$

$$A_{\text{silicon}} = \left(N_{\text{tiles}} \times 256 \times 2 \times p_{\text{cell}}^2\right) + \left(N_{\text{tiles}} \times A_{\text{peripheral}}\right)$$

Trong đó khoảng cách ô nhớ $p_{\text{cell}} = 160\text{ nm}$ (ReRAM BEOL tiến trình 28nm) và diện tích mạch ngoại vi hỗn hợp $A_{\text{peripheral}} = 1000.0\ \mu\text{m}^2$ mỗi tile (SAR ADC, DAC, TIA và logic điều khiển).

---

## 3. Thang Đo Workload Thường Trú & Phân Tích Diện Tích (T0–T3)

| Bậc / Mô Hình | Tổng Tham Số | Tham Số Proj Analog | Số Tile Vật Lý ($16 \times 16$) | Tổng Diện Tích Silicon | Số Chiplet Cần Thiết | Khả Thi Thường Trú Đầy Đủ |
|---|---|---|---|---|---|---|
| **Hand-Calc ($2\text{L}$)** | $18.2\text{K}$ | $16.4\text{K}$ | $64$ | $0.1\text{ mm}^2$ | $1$ | **CÓ (Die Đơn)** |
| **T0 (GPT-2 124M)** | $124.4\text{M}$ | $84.9\text{M}$ | $331,776$ | $336.1\text{ mm}^2$ | $1$ | **CÓ (Die Đơn)** |
| **T1 (LLaMA-1B)** | $1.10\text{B}$ | $1.03\text{B}$ | $4,040,704$ | $4,093.7\text{ mm}^2$ | $11$ | **CÓ (Đóng Gói 11 Chiplet)** |
| **T2 (LLaMA-3B)** | $2.97\text{B}$ | $2.87\text{B}$ | $11,222,016$ | $11,369.1\text{ mm}^2$ | $29$ | **KHÔNG (Vượt Trần Đóng Gói)** |
| **T3 (LLaMA-2 7B)** | $6.74\text{B}$ | $6.61\text{B}$ | $25,808,896$ | $26,147.2\text{ mm}^2$ | $66$ | **KHÔNG (Vượt Trần Đóng Gói)** |

---

## 4. So Sánh Lịch Trình: Thường Trú Toàn Phần vs Nạp Theo Layer vs Streaming

| Chiến Lược Lập Lịch | Trọng Số Nạp Lại / Token | Độ Trễ Nạp Lại / Token | Năng Lượng Ghi ReRAM / Token | Đánh Giá Tính Khả Thi Vật Lý |
|---|---|---|---|---|
| **`FULLY_RESIDENT`** | $0\text{ B}$ | $0.0\ \mu\text{s}$ | $0.0\ \mu\text{J}$ | **Khả thi cho T0 & T1**; xóa bỏ nút thắt bộ nhớ DRAM. |
| **`LAYER_RESIDENT`** | $2.07\text{ GB}$ (T1) / $13.2\text{ GB}$ (T3) | $1.72\text{ ms}$ (T1) / $11.0\text{ ms}$ (T3) | $10.3\text{ mJ}$ (T1) / $66.1\text{ mJ}$ (T3) | Cần HBM3e ($1.2\text{ TB/s}$) & kiểm soát độ bền ghi ReRAM. |
| **`STREAMED_WEIGHT`** | $2.07\text{ GB}$ (T1) / $13.2\text{ GB}$ (T3) | $32.3\text{ ms}$ (T1) / $206.5\text{ ms}$ (T3) | $0.0\ \mu\text{J}$ (Buffer SRAM) | Bị thắt cổ chai bởi đường truyền PCIe Gen5 ($64\text{ GB/s}$). |

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0052-weight-residency-topology/residency_topology.py
```

Chạy bộ unit test:
```bash
pytest tests/test_residency.py
```

File trích xuất artifact:
`verification/circuit/results/residency-topology-0052-extract.json`
