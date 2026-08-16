# 0032 — Phân Tích Nguyên Nhân Sai Số Khối Transformer (Gate R7)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **quy trình mô phỏng toàn diện một khối Transformer hoàn chỉnh trên 192 tile crossbar vật lý cùng phân tích truy nguyên sai số từng cơ chế vật lý (leave-one-out error attribution)** trong **Gate R7 (Kiểm chứng Transformer và mô hình ngôn ngữ lớn)**.

---

## 1. Kiến Trúc Khối Transformer & Bố Trí 192 Tile Vật Lý

![Kiến trúc khối Transformer](diagrams/transformer-block-0032.svg)

Một tầng Transformer hoàn chỉnh kết hợp cơ chế Tự Chú Ý (Self-Attention), Mạng Truyền Thẳng (MLP), Chuẩn Hóa Tầng (LayerNorm) và hai đường truyền phần dư:
1. **Phân Tầng Attention (64 Tile)**:
   - Chiếu gộp $W_{QKV} \in \mathbb{R}^{192 \times 64}$: $48\text{ tile vật lý } 16\times 16$.
   - Tính toán Attention kỹ thuật số: $S_h = Q_h K_h^T / \sqrt{d_{\text{head}}}$, $\text{Softmax}$, $A_h V_h$.
   - Chiếu đầu ra $W_O \in \mathbb{R}^{64 \times 64}$: $16\text{ tile vật lý } 16\times 16$.
   - Cộng phần dư thứ nhất: $x_1 = x + y_{\text{attn}}$.
2. **Phân Tầng MLP (128 Tile)**:
   - Chiếu lên $W_{\text{up}} \in \mathbb{R}^{256 \times 64}$: $64\text{ tile vật lý } 16\times 16$.
   - Hàm kích hoạt kỹ thuật số: $h_{\text{act}} = \text{GELU}(h_{\text{up}})$.
   - Chiếu xuống $W_{\text{down}} \in \mathbb{R}^{64 \times 256}$: $64\text{ tile vật lý } 16\times 16$.
   - Cộng phần dư thứ hai: $x_2 = x_1 + y_{\text{mlp}}$.
3. **Tổng Số Lượng Phần Cứng Vật Lý**:
   $$N_{\text{tiles}} = 48\text{ (QKV)} + 16\text{ (Out)} + 64\text{ (Up)} + 64\text{ (Down)} = \mathbf{192\text{ tile vật lý / block}}$$

---

## 2. Bảng Xếp Hạng Đóng Góp Sai Số Từng Cơ Chế Vật Lý

Sử dụng các luồng số ngẫu nhiên độc lập (`SeedSequence.spawn`) để tránh hiện tượng nhiễu chéo giữa các lần chạy leave-one-out:

| Cơ Chế Vật Lý | Tham Số / Dải Hoạt Động | Sai Số Khi Loại Bỏ Cơ Chế ($L_2$) | Mức Sai Số Biên Đóng Góp ($\Delta L_2$) | Tỷ Trọng Đóng Góp (%) |
|---|---|---|---|---|
| **Lỗi Kẹt Trở Kháng Thấp (LRS Defects)** | $p_{\text{LRS}} = 0.45\%$ | $49.87\%$ | **$+34.78\%$** | **$44.9\%$** |
| **Lỗi Kẹt Trở Kháng Cao (HRS Defects)** | $p_{\text{HRS}} = 2.55\%$ | $54.59\%$ | **$+30.07\%$** | **$38.8\%$** |
| **Phi Tuyến Điện Áp I-V Bậc 3** | $\beta = 1.0\text{ V}^{-2}$ ($V_{\text{read}} = 0.25\text{ V}$) | $78.55\%$ | **$+6.11\%$** | **$7.9\%$** |
| **Nhiễu Đọc Tín Hiệu (Read Noise)** | $\sigma_{\text{read}} = 1.0\%$ | $79.41\%$ | **$+5.25\%$** | **$6.8\%$** |
| **Phân Tán Ghi Lập Trình (Prog Var)** | $\sigma_{\text{prog}} = 3.0\%$ | $83.40\%$ | **$+1.25\%$** | **$1.6\%$** |
| **Sụt Áp 2D (IR Drop)** | $R_{\text{wire}} = 1.0\,\Omega$ | $85.88\%$ | **$+0.00\%$** | **$0.0\%$** |
| **Trôi Độ Dẫn Theo Thời Gian (Drift)** | $t = 1.0\text{ s}$ | $84.66\%$ | **$+0.00\%$** | **$0.0\%$** |

- **Kết luận quan trọng**: Các khuyết tật linh kiện (stuck HRS/LRS) chiếm **$>83\%$** tổng sai số tương tự của toàn khối Transformer, khẳng định việc khắc phục lỗi kẹt phần cứng là mục tiêu hàng đầu cho các phương pháp phục hồi sau này.

---

## 3. Sai Số Tích Lũy Qua Từng Giai Đoạn

- **Đầu ra khối lượng tử hóa lý tưởng**: $L_2 = 43.30\%$ ($\text{SNR} = 7.3\text{ dB}$).
- **Đầu ra tầng Attention ($y_{\text{attn}}$)**: $L_2 = 42.10\%$ ($\text{SNR} = 7.5\text{ dB}$).
- **Đường nối tắt phần dư 1 ($x_1$)**: $L_2 = 32.50\%$ ($\text{SNR} = 9.8\text{ dB}$, đường nối tắt làm giảm tỷ lệ sai số).
- **Đầu ra tầng MLP ($y_{\text{mlp}}$)**: $L_2 = 74.60\%$ ($\text{SNR} = 2.5\text{ dB}$).
- **Đầu ra toàn khối đã hiệu chuẩn ($x_2$)**: $L_2 = 84.66\%$ ($\text{SNR} = 1.4\text{ dB}$).

---

## 4. Thực Thi & Kiểm Thử

Chạy mã nguồn phân tích khối Transformer:
```bash
python book/0032-transformer-block/transformer_block.py
```
Dữ liệu trích xuất kiểm định được lưu tại: `verification/circuit/results/transformer-block-0032-extract.json`.
