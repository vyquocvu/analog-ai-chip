# 0054 — Phân Tích Suy Hao Cho Mô Hình Lớn & Phi Lý Tưởng Mở Rộng (Gate R13)

> **English version:** [`README.md`](README.md)

Chương này mở đầu cho **Gate R13 (Large-model accuracy and hardware-recovery validation)** bằng việc chuẩn hóa **mức chuẩn perplexity số tham chiếu, phân rã suy hao theo từng cơ chế vật lý, khảo sát độ phân giải bộ chuyển đổi và sự tích lũy sai số theo chiều sâu** trên các bộ giải mã transformer mở rộng.

---

## 1. Mức Chuẩn Số Tham Chiếu & Tập Dữ Liệu Đánh Giá

![Phân Tích Suy Hao Mô Hình Lớn](diagrams/large-model-attribution.svg)

- **Tập Dữ Liệu Đánh Giá Cố Định**: Các chuỗi token đánh giá đa token ($T = 16\dots 64$) với các token đích tất định.
- **Các Chỉ Số Tham Chiếu**:
  - **Độ Phức Tạp Cross-Entropy (Perplexity)**: $\text{PPL} = \exp\left(-\frac{1}{N-1} \sum_{t=0}^{N-2} \log P(x_{t+1} \mid x_{\le t})\right)$.
  - **Tỷ Lệ Khớp Token Top-1**: Tỷ lệ phần trăm các vị trí token mà $\arg\max(z_{\text{analog}}) == \arg\max(z_{\text{float}})$.
  - **Phân Kỳ KL Của Logit**: Mức phân kỳ phân phối trung bình $D_{\text{KL}}(P_{\text{float}} \parallel P_{\text{analog}})$.
  - **Tỷ Lệ Tín Hiệu Trên Nhiễu Đầu Ra (SNR)**: $10 \log_{10}(\mathbb{E}[z_{\text{float}}^2] / \mathbb{E}[(z_{\text{analog}} - z_{\text{float}})^2])$.

---

## 2. Phân Rã Cơ Chế Phi Lý Tưởng Vật Lý

Các cơ chế phần cứng phi lý tưởng được cô lập và đánh giá độc lập so với mức chuẩn float số:

1. **Lượng Tử Hóa DAC Đầu Vào**: Lượng tử hóa đều DAC 8-bit.
2. **Lượng Tử Hóa ADC Đầu Ra**: Lượng tử hóa đều ADC 8-bit với trần điện áp ray ($V_{\text{max}} = 4.0\text{ V}$).
3. **Biến Thiên Lập Trình**: Biến thiên điện dẫn Gaussian cấp độ ô nhớ ($\sigma_{\text{prog}} = 1.5\%$).
4. **Nhiễu Đọc MVM**: Nhiễu đọc quá độ ($\sigma_{\text{read}} = 0.8\%$).
5. **Trôi Điện Dẫn ($24\text{h}$)**: Suy giảm theo hàm mũ lũy thừa $G(t) = G_0 (t/t_0)^{-\nu}$ với $\nu = 0.08, t = 86400\text{ s}$.
6. **Ô Nhớ Lỗi (Defect Cells)**: $0.1\%$ ô kẹt trạng thái điện trở cao (HRS) và $0.05\%$ ô kẹt trạng thái điện trở thấp (LRS).
7. **Hồ Sơ Tổng Hợp (`crossbar-v1`)**: Mô phỏng đồng thời toàn bộ 9 cơ chế vật lý đã trích xuất từ SPICE.

---

## 3. Bảng Phân Tích Suy Hao Cơ Chế Trên Kiến Trúc T0

Được đánh giá trên mô hình decoder GPT-2 4 layer (T0) theo mô phỏng chính xác dựa trên profile:

| Cấu Hình Cơ Chế | Perplexity | Khớp Top-1 (%) | Phân Kỳ KL Trung Bình | Tỷ Lệ Tín Hiệu / Nhiễu | Mức Độ Tuyên Bố |
|---|---|---|---|---|---|
| **Digital Float Baseline** | **$139.83$** | **$100.0\%$** | **$0.000\text{e}+00$** | **$\infty\text{ dB}$** | `VERIFIED DIGITAL` |
| **`dac_quantization_8bit`** | $139.83$ | $100.0\%$ | $2.171 \times 10^{-6}$ | $37.88\text{ dB}$ | `EXACT PHYSICAL` |
| **`conductance_drift_24h`** | $134.90$ | $25.0\%$ | $1.129 \times 10^{-2}$ | $0.67\text{ dB}$ | `EXACT PHYSICAL` |
| **`adc_quantization_8bit`** | $138.83$ | $31.2\%$ | $1.471 \times 10^{-2}$ | $-0.43\text{ dB}$ | `EXACT PHYSICAL` |
| **`read_noise` ($\sigma=0.8\%$)** | $145.28$ | $25.0\%$ | $1.479 \times 10^{-2}$ | $-0.44\text{ dB}$ | `EXACT PHYSICAL` |
| **`stuck_faults` ($0.15\%$)** | $142.69$ | $25.0\%$ | $1.485 \times 10^{-2}$ | $-0.49\text{ dB}$ | `EXACT PHYSICAL` |
| **`programming_variation`** | $144.19$ | $25.0\%$ | $1.567 \times 10^{-2}$ | $-0.72\text{ dB}$ | `EXACT PHYSICAL` |
| **`composite_crossbar_v1`** | $128.55$ | $6.2\%$ | $2.386 \times 10^{-2}$ | $-2.55\text{ dB}$ | `EXACT PHYSICAL` |

---

## 4. Độ Nhạy Bit Bộ Chuyển Đổi & Tích Lũy Sai Số Theo Chiều Sâu

- **Khảo Sát Số Bit Bộ Chuyển Đổi (4-bit vs 6-bit vs 8-bit)**:
  - **DAC/ADC 4-bit**: Cắt tín hiệu nghiêm trọng và lượng tử hóa thô làm biến dạng phân phối logit.
  - **DAC/ADC 6-bit**: Cải thiện dải động, khôi phục một phần độ trung thực của logit.
  - **DAC/ADC 8-bit**: Khớp với mức chuẩn số với sàn nhiễu lượng tử hóa thấp ($> 35\text{ dB SNR}$ ở DAC).
- **Tích Lũy Sai Số Theo Chiều Sâu**:
  - Sai số tích lũy phi tuyến tính qua các layer khi phương sai kích hoạt trung gian tăng dần và làm bão hòa các tầng Softmax/LayerNorm phía sau.
  - Đặt ra yêu cầu cấp thiết cho các **kỹ thuật khôi phục phần cứng** (Chương 0055).

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0054-large-model-error-attribution/large_model_attribution.py
```

Chạy bộ unit test:
```bash
pytest tests/test_large_model_eval.py
```

File trích xuất artifact:
`verification/circuit/results/large-model-attribution-0054-extract.json`
