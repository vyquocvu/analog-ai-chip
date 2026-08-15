# 0019 — Trôi Điện dẫn, Lỗi Kẹt Cố định & Bất tuyến tính I-V

> **English version:** [`README.md`](README.md)

Chương này tách biệt và mô hình hóa ba phi lý tưởng vật lý dài hạn và lỗi chế tạo quan trọng trong mảng crossbar bộ nhớ bất biến (NVM / ReRAM / PCM): **sự trôi điện dẫn theo hàm mũ thời gian**, **phân bố lỗi kẹt cố định (stuck-at fault)**, và **tính bất tuyến tính $I-V$ dưới mức Ohm (sub-Ohmic)**.

---

## 1. Cơ chế Vật lý & Công thức Toán học

![Cơ chế trôi điện dẫn, lỗi kẹt và bất tuyến tính](diagrams/drift_faults_schematic.svg)

### A. Trôi Điện dẫn theo Thời gian (Suy giảm Lưu giữ - Retention Decay)
Trong bộ nhớ đổi pha (PCM) và memristor oxit kim loại, sự tái tổ chức nguyên tử liên tục và triệt tiêu khuyết tật vi mô khiến điện dẫn giảm dần theo thời gian theo quy luật hàm mũ:
$$G(t) = G(t_0) \cdot \left(\frac{t}{t_0}\right)^{-\nu(G_0)}, \quad t \ge t_0 = 1\text{ s}$$

- **Số mũ Trôi $\nu$**: Phụ thuộc vào mức điện dẫn được nạp, tăng từ $\nu_{\min} = 0.02$ tại $G_{\min} = 10.0\,\mu\text{S}$ (HRS) lên đến $\nu_{\max} = 0.06$ tại $G_{\max} = 100.0\,\mu\text{S}$ (LRS).
- **Tác động Dài hạn**: Sau 1 năm ($3.15 \times 10^7\text{ s}$), các trạng thái điện dẫn cao bị mất tới **$64.5\%$** giá trị ban đầu, làm suy giảm biên độ trọng số và co cụm tín hiệu kích hoạt mạng nơ-ron.

### B. Lỗi Kẹt Cố định (Stuck-at Faults & Tỷ lệ Sản lượng)
Sai hỏng trong quá trình quang khắc và đánh thủng điện môi làm một tỷ lệ nhỏ các ô nhớ bị kẹt vĩnh viễn:
- **Kẹt ở Trạng thái Trở cao (Stuck-at-HRS / Hở mạch / $p_{\text{HRS}} \approx 1\%\dots 5\%$)**: Ô nhớ bị cố định ở $G_{\min} = 10.0\,\mu\text{S}$.
- **Kẹt ở Trạng thái Trở thấp (Stuck-at-LRS / Ngắn mạch / $p_{\text{LRS}} \approx 0.1\%\dots 1\%$)**: Ô nhớ bị cố định ở $G_{\max} = 100.0\,\mu\text{S}$.
- **Tác động MVM**: Lỗi kẹt LRS bơm dòng điện ký sinh rất lớn vào cột tương ứng, gây sai số nghiêm trọng cho phép tính ma trận-vector (ví dụ **sai số MVM $9.21\%$ khi tỷ lệ lỗi là $1.0\%$**).

### C. Tính Bất tuyến tính I-V
Tại các điện áp đọc khác 0 trong phạm vi $|V_{\text{read}}| \le 0.25\text{ V}$, hiệu ứng phát xạ trường Poole-Frenkel tạo ra độ lệch bậc ba so với định luật Ohm tuyến tính:
$$I(V) = G_0 \cdot V \cdot \left(1 + \beta \cdot |V|^2\right)$$

- **Hệ số Bất tuyến tính**: $\beta = 1.0\text{ V}^{-2}$.
- **Méo hài**: Tại điện áp đọc cực đại $V_{\text{read,max}} = 0.25\text{ V}$, mức méo dòng điện phi tuyến đạt $\Delta I / I_{\text{linear}} = +6.25\%$.

---

## 2. Lượng hóa & Đồ thị Mở rộng

![Đồ thị tác động phi lý tưởng lượng hóa](diagrams/drift_and_fault_effects.svg)

### Bảng Tổng hợp Chỉ số Phi lý tưởng:

| Cơ chế Phi lý tưởng | Chỉ số Chính | Tác động Cơ bản | Giải pháp Kiến trúc |
|---|---|---|---|
| **Trôi Điện dẫn** | Mức mất mát sau 1 năm | Giảm $-64.5\%$ điện dẫn trên LRS | Bù trôi định kỳ / tái co giãn trọng số toàn cục |
| **Lỗi Kẹt HRS** | $p_{\text{HRS}} = 2.55\%$ ($85\%$ tổng lỗi) | Mất khả năng biểu diễn trọng số dương | Huấn luyện thích ứng lỗi / ánh xạ cột dự phòng |
| **Lỗi Kẹt LRS** | $p_{\text{LRS}} = 0.45\%$ ($15\%$ tổng lỗi) | Tạo độ lệch tĩnh $\approx 25\,\mu\text{A}$ trên cột | Trừ nền số học / cô lập cột lỗi |
| **Bất tuyến tính I-V** | Độ méo cực đại $\beta = 1.0\text{ V}^{-2}$ | Méo $+6.25\%$ dòng điện @ $0.25\text{ V}$ | Giới hạn điện áp đọc thấp ($V_{\text{read}} \le 0.25\text{ V}$) |

---

## 3. Phân loại Bằng chứng & Quy tắc Kỹ thuật

Theo quy định nghiêm ngặt của `AGENTS.md`:
- Mọi thông số số mũ trôi ($\nu$), xác suất lỗi kẹt ($p_{\text{HRS}}, p_{\text{LRS}}$), và hệ số bất tuyến tính ($\beta$) đều được gắn nhãn **thông số khảo sát độ nhạy** (`evidence_class: "assumed"`).
- Các thông số này hỗ trợ đánh giá độ nhạy độc lập và kiểm định fail-closed trước khi áp dụng vào phần cứng vật lý.

---

## Kiểm thử & Xác minh

Chạy trích xuất đặc tính và tạo đồ thị:
```bash
python book/0019-drift-faults/drift_faults.py
python book/0019-drift-faults/diagrams/make_plots.py
```
Dữ liệu cam kết: [`verification/circuit/results/drift-faults-0019-extract.json`](../../verification/circuit/results/drift-faults-0019-extract.json).
Kiểm thử tự động: [`tests/test_drift_faults.py`](../../tests/test_drift_faults.py).
