# 0023 — Bộ Điều phối & Tái sử dụng theo Thời gian (Cổng R5/R6)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **mô hình điều phối ô phần cứng và tái sử dụng theo thời gian (temporal reuse)** cho các bộ tăng tốc analog đa ô trong **Cổng R5 & Cổng R6 (Kiến trúc bộ tăng tốc và di chuyển dữ liệu)**.

---

## 1. Đánh đổi giữa Song song Không gian vs Tái sử dụng Thời gian

![Kiến trúc bộ điều phối và dòng thời gian thực thi](diagrams/scheduler_architecture.svg)

### Điểm Khảo sát Giả định Đọc-Ghi:
- **Độ trễ Đọc Analog / Chu kỳ MVM**: $t_{\text{mvm}} = 20\text{ ns}$ (`assumed`; thời gian từ profile đang chờ).
- **Độ trễ Ghi / Nạp Ô NVM**: $t_{\text{prog}} = 10\,\mu\text{s}$ (`assumed`; bằng chứng nạp đang chờ).
- **Tỷ lệ Suy ra**: $t_{\text{prog}}/t_{\text{mvm}} = 500$. Đây là khảo sát độ nhạy kiến trúc, không phải hiệu năng vật lý đã xác minh.

### Các Chiến lược Điều phối:
1. **Trọng số Tĩnh (Weight-Stationary / Cố định Không gian)**:
   - Toàn bộ trọng số các tầng được ánh xạ cố định lên $N_{\text{tiles}} \ge K_{\text{total}}$ ô nhớ vật lý trên chip.
   - Nạp **một lần duy nhất** khi khởi tạo mô hình.
   - Không tốn chi phí nạp lại (zero rewrites) trong suốt quá trình sinh token.
2. **Ghép kênh Thời gian theo Tầng (Temporal Multiplexing)**:
   - Các ô vật lý được dùng chung lần lượt qua các tầng ($N_{\text{tiles}} < K_{\text{total}}$).
   - Tiết kiệm diện tích silicon, nhưng phải trả giá bằng $N_{\text{rewrites}} = \max(0, K_{\text{layer}} - N_{\text{tiles}})$ chu kỳ ghi trên mỗi token.
3. **Phân bổ Lai (Hybrid)**:
   - Giữ cố định các phép chiếu kích thước nhỏ, độ trễ khắt khe (Attention QKV & Out); ghép kênh thời gian cho các tầng mở rộng lớn (MLP Up & Down).

---

## 2. Quy mô Dung lượng & Sổ cái Thực thi

![Mở rộng dung lượng và độ trễ bộ điều phối](diagrams/scheduler_scaling.svg)

### Khối lượng Công việc Chuẩn (Tầng Transformer: $d_{\text{model}} = 128, d_{\text{ffn}} = 512$, Ô $16\times 16$):
- **Phép chiếu Attention QKV ($384\times 128$)**: $192$ khối ô vật lý ($25.0\%$).
- **Phép chiếu Attention Out ($128\times 128$)**: $64$ khối ô vật lý ($8.3\%$).
- **Phép chiếu MLP Up ($512\times 128$)**: $256$ khối ô vật lý ($33.3\%$).
- **Phép chiếu MLP Down ($128\times 512$)**: $256$ khối ô vật lý ($33.3\%$).
- **Tổng Khối lượng Một Tầng**: **$768$ khối ô $16\times 16$** ($196,608$ phép tính MAC).

### Sổ cái Thực thi theo Dung lượng Ô trên Chip:

| Dung lượng Ô $N_{\text{tiles}}$ | Chu kỳ MVM / Tầng | Số lần Ghi lại / Tầng | Độ trễ 100 Token (Ghép kênh) | Độ trễ 100 Token (Trọng số Tĩnh) | Tăng tốc (Trọng số Tĩnh) |
|---|---|---|---|---|---|
| **$16$ ô** | $48$ | $704$ | $768.1\text{ ms}$ | $768.1\text{ ms}$ (Dự phòng) | $1.0\times$ |
| **$32$ ô** | $24$ | $640$ | $768.0\text{ ms}$ | $768.0\text{ ms}$ (Dự phòng) | $1.0\times$ |
| **$64$ ô** | $12$ | $512$ | $768.0\text{ ms}$ | $768.0\text{ ms}$ (Dự phòng) | $1.0\times$ |
| **$128$ ô** | $7$ | $320$ | $768.0\text{ ms}$ | $768.0\text{ ms}$ (Dự phòng) | $1.0\times$ |
| **$256$ ô** | $4$ | $0$ | $768.0\text{ ms}$ | $768.0\text{ ms}$ (Dự phòng) | $1.0\times$ |
| **$768$ ô (Cố định)** | $4$ | **$0$** | $768.0\text{ ms}$ | **$7.7\text{ ms}$** | **Nhanh hơn $99.9\times$** |
| **$1024$ ô (Cố định)** | $4$ | **$0$** | $768.0\text{ ms}$ | **$7.7\text{ ms}$** | **Nhanh hơn $99.9\times$** |

---

## 3. Công thức Toán học của Sổ cái

Với các tầng tuần tự $l$, mỗi tầng có $K_l$ khối được lập lịch trên $N_{\text{tiles}}$ ô vật lý:
- **Chu kỳ MVM Song song**: $T_{\text{cycles}} = \sum_l \lceil K_l/N_{\text{tiles}} \rceil$
- **Số lần Ghi lại**: $N_{\text{rewrites}} = \sum_l \max(0,K_l-N_{\text{tiles}})$
- **Hiệu suất Sử dụng Ô**:
  $$\eta_{\text{util}} = \frac{\sum_l K_l}{N_{\text{tiles}} \cdot T_{\text{cycles}}} \in (0, 1]$$
- **Tổng Độ trễ Sinh $N_{\text{tokens}}$ Token**:
  $$T_{\text{stationary}} = \left(\sum_l K_l\right)t_{\text{prog}} + N_{\text{tokens}}T_{\text{cycles}}t_{\text{mvm}}$$
  $$T_{\text{temporal}} = N_{\text{tokens}}\left[T_{\text{cycles}}t_{\text{mvm}} + \left(\sum_l K_l\right)t_{\text{prog}}\right]$$

Kiểm tra tay nhỏ: một tầng $2\times10$ trên ô $2\times2$ có $K=5$. Với hai ô vật lý, $T_{\text{cycles}}=\lceil5/2\rceil=3$, $N_{\text{rewrites}}=5-2=3$, và $\eta=5/(2\cdot3)=5/6$.

---

## Kiểm thử & Xác minh

Chạy trình điều phối và tạo đồ thị:
```bash
python book/0023-scheduler/scheduler.py
python book/0023-scheduler/diagrams/make_plots.py
```
Dữ liệu cam kết: [`verification/circuit/results/scheduler-0023-extract.json`](../../verification/circuit/results/scheduler-0023-extract.json).
Kiểm thử tự động: [`tests/test_scheduler.py`](../../tests/test_scheduler.py).
