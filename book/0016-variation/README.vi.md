# 0016 — Biến thiên Lập trình và Nhiễu Đọc

> **English version:** [`README.md`](README.md)

Chương này mô tả đặc tính biến thiên ngẫu nhiên của các ô nhớ bán dẫn bất biến (NVM / ReRAM / Flash), lượng hóa mức độ **sai lệch lập trình (ghi)** và **nhiễu đọc (thời gian)** tác động lên từng mức điện dẫn cũng như cách chúng lan truyền vào các trọng số có dấu vi sai.

---

## 1. Cơ chế Nhiễu trong Ô Điện dẫn Vật lý

![Cơ chế nhiễu trong NVM](diagrams/variation_mechanisms.svg)

Các phần tử nhớ analog tồn tại hai thành phần nhiễu ngẫu nhiên rõ rệt:

1. **Biến thiên Lập trình (Ghi)**:
   - Sự hình thành vi sợi dẫn điện ngẫu nhiên trong quá trình phát xung SET/RESET tạo ra độ phân tán giữa các chu kỳ (C2C) và giữa các linh kiện (D2D).
   - Trạng thái nạp: $G_{\text{prog}} = G_k \cdot (1 + \delta_{\text{prog}})$, với $\delta_{\text{prog}} \sim \mathcal{N}(0, \sigma_{\text{prog}}^2)$ (giả định $\sigma_{\text{prog}} = 3.0\%$).
   - Biến thiên này có tính chất tĩnh trong suốt quá trình suy luận và chỉ thay đổi khi ô nhớ được nạp lại.

2. **Nhiễu Đọc (Thời gian)**:
   - Nhiễu điện báo ngẫu nhiên (Random Telegraph Noise - RTN) do bẫy điện tử trong lớp oxit và nhiễu nhiệt Johnson-Nyquist.
   - Trạng thái đọc: $G_{\text{read}} = G_{\text{prog}} \cdot (1 + \delta_{\text{read}})$, với $\delta_{\text{read}} \sim \mathcal{N}(0, \sigma_{\text{read}}^2)$ (giả định $\sigma_{\text{read}} = 1.0\%$).
   - Nhiễu này có tính chất động và không tương quan giữa các phép tính MVM liên tiếp.

3. **Độ lệch chuẩn tương đối tổng thể**:
   $$\sigma_{\text{tot}} = \sqrt{\sigma_{\text{prog}}^2 + \sigma_{\text{read}}^2} = \sqrt{0.03^2 + 0.01^2} \approx 3.16\%$$

---

## 2. Phương sai Trọng số Vi sai & Lan truyền Sai số

![Mô phỏng quét biến thiên Monte Carlo](diagrams/monte_carlo_distribution.svg)

Với một cặp ô vi sai $(G^+, G^-)$ biểu diễn trọng số có dấu $w \in [-1, 1]$ trên dải điện dẫn $\Delta G = G_{\max} - G_{\min} = 90.0\,\mu\text{S}$:
$$w_{\text{eff}} = \frac{G^+ - G^-}{\Delta G}$$

Vì biến thiên trên $G^+$ và $G^-$ là độc lập, phương sai của chúng cộng theo bình phương:
$$\sigma_w^2(w) = \frac{\sigma_{G^+}^2 + \sigma_{G^-}^2}{\Delta G^2} = \frac{(G^+ \cdot \sigma_{\text{tot}})^2 + (G^- \cdot \sigma_{\text{tot}})^2}{\Delta G^2}$$

### Các Giới hạn Biên Chính:
- **Sàn Nhiễu Điểm Không ($w = 0$)**:
  Cả hai ô đều ở trạng thái HRS ($G^+ = G^- = G_{\min} = 10.0\,\mu\text{S}$):
  $$\sigma_w(0) = \frac{\sqrt{2} \cdot G_{\min} \cdot \sigma_{\text{tot}}}{\Delta G} = \frac{\sqrt{2} \times 10\,\mu\text{S} \times 0.03162}{90\,\mu\text{S}} \approx 0.497\%$$
- **Trọng số Cực đại Toàn dải ($|w| = 1$)**:
  Một ô ở mức LRS ($G_{\max} = 100.0\,\mu\text{S}$) trong khi ô còn lại ở $G_{\min}$:
  $$\sigma_w(1) = \frac{\sqrt{G_{\max}^2 + G_{\min}^2} \cdot \sigma_{\text{tot}}}{\Delta G} = \frac{\sqrt{100^2 + 10^2} \times 0.03162}{90} \approx 3.531\%$$

---

## 3. Tóm tắt Thống kê Monte Carlo (1000 Mẫu, Seed=42)

| Trọng số mục tiêu $w$ | Ô tích cực $G^+$ | Ô không tích cực $G^-$ | $\sigma_w$ lý thuyết | $\sigma_w$ thực nghiệm (1000 mẫu) | SNR thực nghiệm |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **0.00** | $10.0\,\mu\text{S}$ | $10.0\,\mu\text{S}$ | $0.497\%$ | $0.489\%$ | Sàn nhiễu |
| **0.25** | $32.5\,\mu\text{S}$ | $10.0\,\mu\text{S}$ | $1.194\%$ | $1.182\%$ | $26.5\text{ dB}$ |
| **0.50** | $55.0\,\mu\text{S}$ | $10.0\,\mu\text{S}$ | $1.963\%$ | $1.948\%$ | $28.2\text{ dB}$ |
| **0.75** | $77.5\,\mu\text{S}$ | $10.0\,\mu\text{S}$ | $2.744\%$ | $2.719\%$ | $28.8\text{ dB}$ |
| **1.00** | $100.0\,\mu\text{S}$ | $10.0\,\mu\text{S}$ | $3.531\%$ | $3.498\%$ | $29.1\text{ dB}$ |

---

## Kiểm thử & Xác minh

Chạy mô phỏng Monte Carlo xác định và tạo đồ thị:
```bash
python book/0016-variation/variation.py
python book/0016-variation/diagrams/make_plots.py
```
Dữ liệu cam kết: [`verification/circuit/results/variation-0016-extract.json`](../../verification/circuit/results/variation-0016-extract.json).
Kiểm thử tự động: [`tests/test_variation.py`](../../tests/test_variation.py).
