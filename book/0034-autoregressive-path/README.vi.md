# 0034 — Sổ Cái Kiến Trúc Đường Tự Hồi Quy Toàn Diện (Gate R7)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **sổ cái kiến trúc từng bước token theo dõi phép tính MAC, lưu lượng bộ nhớ, phân rã năng lượng và độ trễ qua hai pha prefill và decode** trên **TinyGPT** ($416$ tile crossbar vật lý) cho **Gate R7 (Kiểm chứng Transformer và mô hình ngôn ngữ lớn)**.

---

## 1. Sổ Cái Kiến Trúc Tự Hồi Quy Toàn Diện

![Sổ cái kiến trúc tự hồi quy](diagrams/autoregressive-path-0034.svg)

---

## 2. Lịch Trình Thực Thi Tuyến Ống & Phân Rã Độ Trễ

![Lịch trình thực thi tuyến ống](diagrams/autoregressive-timeline-0034.svg)

Lịch trình thực thi chỉ ra rằng các phép nhân ma trận tương tự trên tile cố định chiếm **$92.8\%$** ($900\text{ ns}$) tổng độ trễ mỗi bước decode ($970\text{ ns}$), trong khi các thao tác số (Softmax attention, LayerNorm, GELU và truyền bus SRAM) chỉ chiếm **$7.2\%$** ($70\text{ ns}$).

---

## 3. Phân Tích Mở Rộng: KV Cache So Với Tính Lại Toàn Bộ

![Đồ thị mở rộng lưu lượng KV](diagrams/autoregressive-kv-traffic-0034.svg)

- **Khi dùng KV Cache**: Tăng trưởng tuyến tính $O(L)$ về phép tính và năng lượng ($\approx 6.5\text{ nJ/bước}$, độ trễ cố định $970\text{ ns/bước}$).
- **Không dùng KV Cache**: Bùng nổ bậc hai $O(L^2)$ về phép tính, năng lượng và độ trễ (thiệt hại $64.0\times$ tại $L=128$).

---

## 4. Bố Trí Mặt Bằng & 416 Tile Crossbar Thường Trú

![Bố trí mặt bằng 416 tile](diagrams/autoregressive-hardware-mapping-0034.svg)

- **Tầng 0 (192 Tile)**: $W_{QKV}$ ($48$) + $W_O$ ($16$) + $W_{\text{up}}$ ($64$) + $W_{\text{down}}$ ($64$).
- **Tầng 1 (192 Tile)**: $W_{QKV}$ ($48$) + $W_O$ ($16$) + $W_{\text{up}}$ ($64$) + $W_{\text{down}}$ ($64$).
- **Đầu ra LM Head (32 Tile)**: $W_{\text{head}}$ (Chiếu từ vựng $128\times 64$).
- **Hệ thống trung tâm**: Vùng đệm SRAM On-Chip $32\text{ KB}$ ($3.0\text{ KB}$ KV cache tại $L=12$) và các khối vector số SIMD.

---

## 5. Vết Từng Token (Prefill $t=0\dots 3 \to$ Decode $t=4\dots 11$)

| Bước ($t$) | Token ID | Pha | Độ Dài Ngữ Cảnh | MAC Tương Tự | MAC Số | Tổng MAC | Lưu Lượng SRAM | Năng Lượng Bước (nJ) | Độ Trễ Bước (ns) |
|---|---|---|---|---|---|---|---|---|---|
| **0** | `115` | **PREFILL** | 1 | 106,496 | 256 | **106,752** | 544 B | **5.92 nJ** | 962.0 ns |
| **1** | `10` | **PREFILL** | 2 | 106,496 | 512 | **107,008** | 672 B | **6.10 nJ** | 964.0 ns |
| **2** | `17` | **PREFILL** | 3 | 106,496 | 768 | **107,264** | 800 B | **6.28 nJ** | 966.0 ns |
| **3** | `86` | **PREFILL** | 4 | 106,496 | 1,024 | **107,520** | 928 B | **6.46 nJ** | 968.0 ns |
| **4** | `112` | **DECODE** | 5 | 106,496 | 1,280 | **107,776** | 1,056 B | **6.64 nJ** | 970.0 ns |
| **5** | `93` | **DECODE** | 6 | 106,496 | 1,536 | **108,032** | 1,184 B | **6.82 nJ** | 972.0 ns |
| **6** | `82` | **DECODE** | 7 | 106,496 | 1,792 | **108,288** | 1,312 B | **7.00 nJ** | 974.0 ns |
| **7** | `21` | **DECODE** | 8 | 106,496 | 2,048 | **108,544** | 1,440 B | **7.18 nJ** | 976.0 ns |
| **8** | `37` | **DECODE** | 9 | 106,496 | 2,304 | **108,800** | 1,568 B | **7.36 nJ** | 978.0 ns |
| **9** | `112` | **DECODE** | 10 | 106,496 | 2,560 | **109,056** | 1,696 B | **7.54 nJ** | 980.0 ns |
| **10** | `112` | **DECODE** | 11 | 106,496 | 2,816 | **109,312** | 1,824 B | **7.72 nJ** | 982.0 ns |
| **11** | `82` | **DECODE** | 12 | 106,496 | 3,072 | **109,568** | 1,952 B | **7.90 nJ** | 984.0 ns |

---

## 6. Hiệu Quả Khi Dùng KV Cache So Với Tính Lại Toàn Bộ

| Chỉ Số | Dùng KV Cache (Mặc Định Phần Cứng) | Không Dùng KV Cache (Tính Lại Toàn Bộ) | Ưu Thế Hiệu Quả |
|---|---|---|---|
| **Tổng Số Phép Tính MAC** | **$1,297,920\text{ MAC}$** | $8,326,656\text{ MAC}$ | **Ít hơn $6.4\times$ phép tính** |
| **Tổng Năng Lượng Tiêu Thụ** | **$82.87\text{ nJ}$** | $420.06\text{ nJ}$ | **Tiết kiệm $5.1\times$ năng lượng** |
| **Tổng Độ Trễ Sinh Chuỗi** | **$11.68\,\mu\text{s}$** | $71.14\,\mu\text{s}$ | **Nhanh hơn $6.1\times$** |
| **Thông Lượng Sinh Token** | **$1,027,749\text{ token/giây}$** | $168,681\text{ token/giây}$ | **Tăng tốc thông lượng $6.1\times$** |
| **Dung Lượng Đỉnh KV SRAM** | **$3,072\text{ bytes}$ ($3.0\text{ KB}$)** | $0\text{ bytes}$ | Vừa vặn trong bộ nhớ đệm SRAM L1 |

---

## 7. Thực Thi & Kiểm Thử

Chạy mã nguồn xuất sổ cái tự hồi quy:
```bash
python book/0034-autoregressive-path/autoregressive_path.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/autoregressive-path-0034-extract.json`.
