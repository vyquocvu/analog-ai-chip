# 0017 — Sụt áp IR Drop & Điện trở Đường dây Kim loại

> **English version:** [`README.md`](README.md)

Chương này lượng hóa tác động của **điện trở dây dẫn kim loại** ($R_{\text{wire}}$) lên độ chính xác của mảng crossbar, mô hình hóa sự sụt áp tích lũy (IR drop) trên các đường hàng (wordline) và đường cột (bitline) khi mở rộng kích thước mảng ($N \in [2, 4, 8, 16, 32, 64]$).

---

## 1. Mạng Lưới Điện trở Phân tán 2D

![Sơ đồ mạng lưới IR drop phân tán](diagrams/ir_drop_schematic.svg)

Trong mảng crossbar vật lý, các đường kim loại kết nối có điện trở bề mặt hữu hạn. Mỗi đoạn dây giữa hai ô nhớ lân cận đóng góp điện trở ký sinh $R_{\text{wire}} \in [0.5, 5.0]\,\Omega$:
- **Sụt áp trên hàng (Wordline)**: Khi dòng điện chạy dọc theo hàng, mỗi ô nhớ trích một phần dòng điện, khiến điện áp hàng giảm dần: $V_{\text{row}}(i, j) < V_{\text{in}}(i)$.
- **Tăng thế trên cột (Bitline)**: Dòng điện từ các ô phía trên dồn dần xuống chân cột TIA, làm điện áp dây cột bị dâng cao hơn mức tham chiếu: $V_{\text{col}}(i, j) > V_{\text{REF}}$.
- **Điện áp hiệu dụng trên ô nhớ**:
  $$V_{\text{cell}}(i, j) = V_{\text{row}}(i, j) - V_{\text{col}}(i, j) < V_{\text{in}}(i) - V_{\text{REF}}$$

**Ô nhớ ở góc xa nhất** $(N-1, M-1)$ chịu mức suy giảm điện áp nghiêm trọng nhất do tổng hợp khoảng cách dài nhất trên cả đường hàng lẫn đường cột.

---

## 2. Quy luật Mở rộng Mảng & Suy giảm Phép tính MVM

![Đồ thị suy giảm sai số do IR drop](diagrams/ir_drop_scaling.svg)

Sai số tương đối của phép nhân MVM tăng xấp xỉ theo hàm bậc hai của kích thước mảng $N$ và điện trở đường dây:
$$\text{Error}_{\text{IR}} \propto N^2 \cdot R_{\text{wire}} \cdot G_{\max}$$

### Tóm tắt Quét Mở rộng (Tất cả ô ở mức $G_{\max} = 100\,\mu\text{S}$, $V_{\text{in}} = 0.25\text{ V}$):

| Kích thước mảng $N\times N$ | Sai số @ $R_{\text{wire}}=0.5\,\Omega$ | Sai số @ $R_{\text{wire}}=1.0\,\Omega$ | Sai số @ $R_{\text{wire}}=2.0\,\Omega$ | Mức hụt thế góc xa ($1.0\,\Omega$) |
|:---:|:---:|:---:|:---:|:---:|
| **$2\times 2$** | $0.025\%$ | $0.050\%$ | $0.100\%$ | $0.05\%$ |
| **$4\times 4$** | $0.076\%$ | $0.151\%$ | $0.303\%$ | $0.14\%$ |
| **$8\times 8$** | $0.259\%$ | $0.516\%$ | $1.026\%$ | $0.44\%$ |
| **$16\times 16$** | $0.941\%$ | $1.870\%$ | $3.665\%$ | $1.50\%$ |
| **$32\times 32$** | $3.490\%$ | $6.773\%$ | $12.621\%$ | $5.34\%$ |
| **$64\times 64$** | $12.164\%$ | $21.841\%$ | $35.428\%$ | $18.10\%$ |

---

## 3. Ý nghĩa Kiến trúc & Giới hạn Vật lý

1. **Giới hạn Kích thước Ô (Tile)**:
   - Với kim loại đồng tiêu chuẩn ($R_{\text{wire}} \approx 1.0\,\Omega$), kích thước mảng từ **$32\times 32$ trở xuống** duy trì sai số IR drop ở mức chấp nhận được ($< 7\%$).
   - Mở rộng lên **$64\times 64$** gây suy giảm nghiêm trọng ($> 20\%$ sai số), giải thích tại sao các chip analog IMC ưu tiên cấu trúc phân mảnh thành nhiều ô nhỏ (như $16\times 16$ hoặc $32\times 32$) thay vì một mảng khổng lồ nguyên khối.
2. **Giải pháp Giảm thiểu**:
   - Sử dụng lớp kim loại dày hơn cho wordline và bitline.
   - Điều khiển hàng từ cả hai phía (dual-sided row driving).
   - Bù trừ số học trước khi suy luận (pre-emphasis / calibration ở Cổng R5).

---

## Kiểm thử & Xác minh

Chạy phân tích nút xác định và tạo đồ thị:
```bash
python book/0017-ir-drop/ir_drop.py
python book/0017-ir-drop/diagrams/make_plots.py
```
Dữ liệu cam kết: [`verification/circuit/results/ir-drop-0017-extract.json`](../../verification/circuit/results/ir-drop-0017-extract.json).
Kiểm thử tự động: [`tests/test_ir_drop.py`](../../tests/test_ir_drop.py).
