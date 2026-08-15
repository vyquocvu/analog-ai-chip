# 0025 — Mô Hình Lưu Lượng NoC & Mạng Kết Nối On-Chip (Gate R6)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **kiến trúc mạng kết nối on-chip (Network-on-Chip - NoC), cây cộng thu gọn tổng bộ phận trong không gian (spatial partial-sum reduction tree) và sổ cái độ trễ/năng lượng truyền dữ liệu** cho chip tăng tốc in-memory computing tương tự trong **Gate R6 (Kiến trúc chip tăng tốc và di chuyển dữ liệu)**.

---

## 1. Mạng Thu Gọn Trong Không Gian & Các Cấu Trúc Mạng

![Mạng kết nối NoC & Thu gọn không gian](diagrams/noc-interconnect-0025.svg)

Khi ma trận trọng số kích thước $M_{\text{out}} \times M_{\text{in}}$ được chia thành lưới $K_r \times K_c$ tile vật lý (mỗi tile $R \times C$):
- **Số hàng tile**: $K_r = \lceil M_{\text{out}} / R \rceil$
- **Số cột tile**: $K_c = \lceil M_{\text{in}} / C \rceil$
- **Độ rộng từ tích lũy**: $B_{\text{acc}} = B_{\text{ADC}} + \lceil \log_2 K_c \rceil$ (Chương 0022)

Trên mỗi hàng tile $i \in [0 \dots K_r-1]$, $K_c$ vector tổng bộ phận từ các cột phải được cộng thu gọn:
$$y_i = \sum_{j=0}^{K_c - 1} y_{i,j}$$

### Các Cấu Trúc Mạng Được Đánh Giá:
1. **Cây Cộng Nhị Phân (Binary Adder Tree / H-Tree)**:
   - Các tổng bộ phận được cộng gộp qua $\lceil \log_2 K_c \rceil$ tầng cây cộng.
   - Đường truyền điểm-điểm chuyên dụng chống nghẽn và tối thiểu hóa độ trễ.
   - Độ trễ đường găng: $T_{\text{tree}} = \lceil \log_2 K_c \rceil \times t_{\text{hop}}$.
2. **Lưới 2D Mesh NoC (Định tuyến X-Y Dimension-Order)**:
   - Các tile kết nối dạng lưới 2D qua bộ định tuyến router 5 cổng.
   - Khoảng cách bước nhảy Manhattan trung bình: $\bar{H}_{\text{mesh}} = \frac{1}{3}(K_r + K_c)$.
   - Độ trễ đường găng: $T_{\text{mesh}} = (K_r + K_c) \times t_{\text{hop}}$.
3. **Bus Vòng Chung (Shared Ring Bus)**:
   - Vòng truyền token tuần tự; $H_{\text{avg}} = N_{\text{tiles}} / 4$.
   - Bị nghẽn cổ chai phân xử tuần tự khi $N_{\text{tiles}} > 16$.

---

## 2. So Sánh Định Lượng Giữa Các Cấu Trúc Mạng

### Khối lượng Tính Toán TinyGPT ($M = 64\times 64$, Tile $16\times 16 \to$ Lưới $4\times 4$, $K_r=4, K_c=4$):

| Cấu trúc Mạng | Tổng Lưu Lượng | Số Bước Nhảy Trung Bình | Độ Trễ Đường Găng ($t_{\text{hop}}=1.0\text{ ns}$) | Năng Lượng Truyền Dẫn ($0.5\text{ pJ/(B}\cdot\text{hop)}$) |
|---|---|---|---|---|
| **Cây Cộng Nhị Phân** | **$176.0\text{ B}$** | **$2.00\text{ hops}$** | **$2.0\text{ ns}$** | **$0.160\text{ nJ}$** |
| **Lưới 2D Mesh NoC** | $176.0\text{ B}$ | $2.67\text{ hops}$ | $8.0\text{ ns}$ | $0.213\text{ nJ}$ |
| **Bus Vòng Ring** | $176.0\text{ B}$ | $4.00\text{ hops}$ | $8.0\text{ ns}$ | $0.320\text{ nJ}$ |

### Phép Chiếu LLaMA-7B ($M = 4096\times 4096$, Tile $32\times 32 \to$ Lưới $128\times 128$, $K_r=128, K_c=128$):

| Cấu trúc Mạng | Tổng Lưu Lượng | Số Bước Nhảy Trung Bình | Độ Trễ Đường Găng | Năng Lượng Truyền Dẫn |
|---|---|---|---|---|
| **Cây Cộng Nhị Phân** | **$1.11\text{ MB}$** | **$7.00\text{ hops}$** | **$7.0\text{ ns}$** | **$3.88\text{ }\mu\text{J}$** |
| **Lưới 2D Mesh NoC** | $1.11\text{ MB}$ | $85.33\text{ hops}$ | $256.0\text{ ns}$ | $47.30\text{ }\mu\text{J}$ (cao hơn $12.2\times$) |

---

## 3. Công Thức Sổ Cái Toán Học

- **Lưu lượng phát kích hoạt đầu vào**: $T_{\text{act}} = K_c \times (C \cdot B_{\text{DAC}} / 8)\text{ bytes}$
- **Số lượt chuyển vector thu gọn**: $N_{\text{transfers}} = K_r \times (K_c - 1)$
- **Khối lượng dữ liệu thu gọn**: $T_{\text{reduct}} = K_r \times (K_c - 1) \times (R \cdot B_{\text{acc}} / 8)\text{ bytes}$
- **Tổng năng lượng NoC**: $E_{\text{noc}} = \sum (\text{Bytes} \times \text{Hops}) \times e_{\text{noc\_byte\_hop}}$ ($e_{\text{noc\_byte\_hop}} \approx 0.5\text{ pJ/(B}\cdot\text{hop)}$, giả định rõ ràng).

---

## 4. Thực Thi & Kiểm Thử

Chạy mã nguồn tính toán mạng NoC:
```bash
python book/0025-noc-interconnect/noc_interconnect.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/noc-interconnect-0025-extract.json`.
