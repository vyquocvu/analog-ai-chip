# 0057 — Xác Định Điểm Nghẽn, Khảo Sát Pareto & Điểm Hòa Vốn Số (Gate R14)

> **English version:** [`README.md`](README.md)

Chương này thúc đẩy **Gate R14 (Multi-tier physical feasibility and design decision)** bằng việc chuẩn hóa **xác định tài nguyên vật lý giới hạn đầu tiên, khảo sát không gian tối ưu Pareto kiến trúc, và phân tích điểm hòa vốn so với mạch số** trên các bậc T0–T3.

---

## 1. Bản Đồ Điểm Nghẽn Phần Cứng Trên Các Bậc Mô Hình

![Xác Định Điểm Nghẽn & Khảo Sát Pareto](diagrams/bottleneck-pareto.svg)

- **Tài Nguyên Giới Hạn Theo Từng Bậc**:
  - **T0 (GPT-2 124M)**: **`adc_area_bandwidth_limit`** — Ở ngữ cảnh ngắn ($T \le 128$), năng lượng chuyển đổi ADC và diện tích mạch ngoại vi chiếm $> 55\%$ tổng tiêu thụ năng lượng chip.
  - **T1 (LLaMA-1B)**: **`digital_attention_compute_limit`** / **`inter_die_ucie_limit`** — Định tuyến interposer 2.5D qua 11 chiplet và tính toán vector attention số chi phối quá trình giải mã ngữ cảnh dài.
  - **T2 (3B) & T3 (7B)**: **`crossbar_capacity_limit`** — Vượt quá giới hạn đóng gói 12 chiplet, bắt buộc phải nạp động từng layer từ bộ nhớ ngoài HBM.

---

## 2. Tối Ưu Hóa Pareto Đa Biến & Công Thức EDP

Các khảo sát kiến trúc khám phá không gian đánh đổi giữa kích thước tile ($R \times C$), hệ số chia sẻ cột ADC ($1:1, 1:4, 1:8$), và số bit chuyển đổi ($4, 6, 8\text{-bit}$):

$$\text{EDP} = \text{Energy}_{\text{decode}}\ [\text{pJ}] \times \text{Latency}_{\text{decode}}\ [\text{s}]$$

Một điểm thiết kế $P$ được gọi là **tối ưu Pareto** nếu không có cấu hình nào khác đạt được mức tiêu thụ năng lượng thấp hơn đồng thời có thông lượng sinh token cao hơn:

$$\nexists P' \mid \left(E(P') \le E(P) \land \text{TPS}(P') \ge \text{TPS}(P)\right) \land \left(E(P') < E(P) \lor \text{TPS}(P') > \text{TPS}(P)\right)$$

---

## 3. Kết Quả Khảo Sát Pareto & Điểm Thiết Kế Tối Ưu

| Bậc Mô Hình | Điểm Nghẽn Chính | Kích Thước Tile Tối Ưu | Chia Sẻ ADC Tối Ưu | EDP Tối Ưu (pJ·s) | Tăng Tốc vs Số 28nm | Hệ Số Tiết Kiệm Năng Lượng |
|---|---|---|---|---|---|---|
| **Hand-Calc ($2\text{L}$)** | `digital_attention_compute_limit` | $16 \times 16$ | $1:1$ (Riêng biệt) | $1.55 \times 10^{-3}$ | $489.0\times$ | $1,500.0\times$ |
| **T0 (GPT-2 124M)** | `adc_area_bandwidth_limit` | $16 \times 16$ | $1:1$ (Riêng biệt) | $2.19 \times 10^{1}$ | **$66.4\times$** | **$24.2\times$** |
| **T1 (LLaMA-1B)** | `digital_attention_compute_limit` | $16 \times 16$ | $1:1$ (Riêng biệt) | $2.43 \times 10^{3}$ | **$13.7\times$** | **$4.3\times$** |
| **T2 (LLaMA-3B)** | `crossbar_capacity_limit` | $16 \times 16$ | $1:1$ (Riêng biệt) | $3.64 \times 10^{6}$ | $0.4\times$ (Giới hạn HBM) | $0.8\times$ |
| **T3 (LLaMA-2 7B)** | `crossbar_capacity_limit` | $16 \times 16$ | $1:1$ (Riêng biệt) | $4.55 \times 10^{8}$ | $0.0\times$ (Giới hạn HBM) | $0.1\times$ |

---

## 4. Ranh Giới Điểm Hòa Vốn Số & Phương Pháp Luận So Sánh

- **Mức Chuẩn Cùng Tiến Trình Đã Xác Thực (`28nm digital standard-cell ASIC`)**:
  - Năng lượng MAC FP16 số chuẩn: $15.0\text{ pJ / MAC}$.
  - IMC analog cố định chứng minh khả năng **tăng tốc $66.4\times$** và **giảm năng lượng $24.2\times$** cho T0, và **tăng tốc $13.7\times$** cho T1.
- **Ranh Giới Điểm Chuyển Giao Hòa Vốn**:
  - **IMC Analog Thắng Thế**: Khi trọng số vừa vặn trên chip/trong package ($T0, T1$) và chiều dài ngữ cảnh $T \le 2048\text{ token}$.
  - **Mạch Số Chi Phối**: Khi chiều dài chuỗi $T > 4096$ chạm Bức Tường Attention Số, hoặc khi mô hình quá lớn ($T2, T3$) buộc phải nạp lại trọng số liên tục từ DRAM/HBM.

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0057-bottleneck-pareto-analysis/bottleneck_pareto.py
```

Chạy bộ unit test:
```bash
pytest tests/test_bottleneck_analysis.py
```

File trích xuất artifact:
`verification/circuit/results/bottleneck-pareto-0057-extract.json`
