# 0015 — Mô hình Rút gọn Điện dẫn Lập trình được

> **English version:** [`README.md`](README.md)

Chương này mở đầu **Cổng R4 (Mô hình Thiết bị Thực tế)** bằng việc chuyển đổi từ các điện trở lý thuyết liên tục sang **mô hình rút gọn bộ nhớ bất biến (NVM / ReRAM / 1T1R)** với các mức điện dẫn rời rạc và giới hạn điện áp đọc an toàn.

---

## 1. Cấu trúc Ô nhớ Vật lý & Các Chế độ Hoạt động

![Mô hình ô nhớ vật lý và các chế độ điện áp](diagrams/cell_model.svg)

Trong phần cứng thực tế, các ô tính toán analog trong bộ nhớ (IMC) là các phần tử bất biến (như memristor oxit kim loại, bộ nhớ đổi pha PCM, hoặc transistor cổng trôi) được điều khiển bởi một transistor truy xuất (cấu hình 1T1R).

### Các thông số vật lý chính:
| Thông số | Ký hiệu | Giá trị | Ghi chú / Nguồn gốc |
|---|---|---|---|
| Trạng thái Điện trở Cao (HRS) | $G_{\min}$ | $10.0\,\mu\text{S}$ ($100\text{ k}\Omega$) | Mức rò rỉ / sàn điện dẫn |
| Trạng thái Điện trở Thấp (LRS) | $G_{\max}$ | $100.0\,\mu\text{S}$ ($10\text{ k}\Omega$) | Điện dẫn lập trình tối đa |
| Dải Điện dẫn (Span) | $\Delta G_{\text{span}}$ | $90.0\,\mu\text{S}$ | $G_{\max} - G_{\min}$ |
| Tỷ số Dải Động | $G_{\max}/G_{\min}$ | $10.0\times$ | Cửa sổ bật/tắt đo được |
| Điện áp Đọc Tối đa | $V_{\text{read,max}}$ | $0.25\text{ V}$ | Vùng tuyến tính Ohm không gây nhiễu trạng thái |
| Ngưỡng Lập trình | $V_{\text{prog}}$ | $\ge 1.2\text{ V}$ | Biên độ xung SET / RESET |

---

## 2. Rời rạc hóa Mức Điện dẫn & Ánh xạ Trọng số Vi sai

![Rời rạc hóa mức trạng thái và ánh xạ trọng số](diagrams/state_levels.svg)

### Rời rạc hóa trạng thái ($2^B$ mức):
Thiết bị được nạp thông qua thuật toán xung và kiểm tra (pulse-and-verify) thành $K = 2^B$ mức rời rạc:
$$G_k = G_{\min} + \frac{k}{2^B - 1} (G_{\max} - G_{\min}), \quad k \in \{0, 1, \dots, 2^B - 1\}$$

- **Lập trình 4-Bit ($K=16$)**: Bước nhảy $\Delta G = 6.00\,\mu\text{S}$ mỗi mức ($6.67\%$ toàn dải).
- **Lập trình 6-Bit ($K=64$)**: Bước nhảy $\Delta G = 1.429\,\mu\text{S}$ mỗi mức ($1.58\%$ toàn dải).

### Phân giải Trọng số Có dấu Vi sai:
Một trọng số ma trận $w \in [-1, 1]$ được ánh xạ trên một cặp ô nhớ vật lý $(G^+, G^-)$:
$$w_{\text{eff}} = \frac{G^+ - G^-}{G_{\max} - G_{\min}}$$

- Trọng số dương ($w > 0$): $G^+ = \text{quantize}(G_{\min} + w \cdot \text{Span})$, $G^- = G_{\min}$.
- Điểm 0 Cân bằng ($w = 0$): $G^+ = G_{\min}$, $G^- = G_{\min} \implies w_{\text{eff}} = 0.0$ chính xác.
- Trọng số âm ($w < 0$): $G^+ = G_{\min}$, $G^- = \text{quantize}(G_{\min} + |w| \cdot \text{Span})$.

---

## 3. Dòng điện Đọc và Vùng Tuyến tính

Trong giới hạn $|V_{\text{read}}| \le 0.25\text{ V}$, ô nhớ hoạt động như một điện trở tuyến tính với dòng điện tối đa mỗi ô:
$$I_{\text{cell,max}} = V_{\text{read,max}} \cdot G_{\max} = 0.25\text{ V} \times 100\,\mu\text{S} = 25.0\,\mu\text{A}$$
$$I_{\text{cell,min}} = V_{\text{read,max}} \cdot G_{\min} = 0.25\text{ V} \times 10\,\mu\text{S} = 2.5\,\mu\text{A}$$

---

## Kiểm thử & Xác minh

Chạy kiểm thử đặc tính mô hình rút gọn và xuất kết quả:
```bash
python book/0015-conductance-model/conductance_model.py
python book/0015-conductance-model/diagrams/make_plots.py
```
Dữ liệu cam kết: [`verification/circuit/results/conductance-model-0015-extract.json`](../../verification/circuit/results/conductance-model-0015-extract.json).
Kiểm thử tự động: [`tests/test_conductance_model.py`](../../tests/test_conductance_model.py).
