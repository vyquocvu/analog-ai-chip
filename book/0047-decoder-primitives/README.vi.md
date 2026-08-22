# 0047 — Các Primitive Decoder Tái Sử Dụng Được (Gate R10)

> **English version:** [`README.md`](README.md)

Chương này chuẩn hóa **các primitive decoder số tái sử dụng được** được tách ra từ Transformer tham chiếu trong khuôn khổ **Gate R10 (Scalable model semantics & sharded checkpoints)**. Chương thiết lập công thức toán học chính xác cho RMSNorm, LayerNorm, SwiGLU, Rotary Position Embeddings (RoPE), và Multi-Head/Grouped-Query/Multi-Query Attention (MHA/GQA/MQA) dưới một biên lai ghép analog/digital chặt chẽ.

---

## 1. Kiến Trúc Biên Phân Định Tính Toán Lai Ghép

![Biên Primitive Decoder Lai Ghép](diagrams/decoder-primitives.svg)

- **Biên Có Thể Dùng Cho Analog**: Các ma trận trọng số projection tĩnh ($W_Q, W_K, W_V, W_O$ và $W_{\text{gate}}, W_{\text{up}}, W_{\text{down}}$) là khối lượng tính toán ứng viên cho các crossbar tile analog cố định trọng số.
- **Tham Chiếu Số NumPy**: Normalization, phép quay tọa độ RoPE, hàm kích hoạt phi tuyến, lũy thừa softmax và attention token-token động vẫn được giữ nguyên ở dạng số thuần túy.
- **Cấp độ Tuyên bố**: `THAM CHIẾU PHẦN MỀM / CHỨC NĂNG` — việc tái cấu trúc và trích xuất toán học chỉ nhằm bảo đảm tính tương đương của decoder; không phải bằng chứng về gia tốc phần cứng vật lý.

---

## 2. Công Thức Toán Học & Tính Toán Bằng Tay

### 1. Root Mean Square Normalization (RMSNorm)
$$\text{RMSNorm}(x, w, \epsilon) = \frac{x}{\sqrt{\frac{1}{d}\sum_{i=1}^d x_i^2 + \epsilon}} \odot w$$
* **Kiểm tra Bằng tay**: Với $x = [3.0, 4.0]$, $\text{RMS}^2 = \frac{9 + 16}{2} = 12.5$. Với $w = [1.0, 2.0]$ và $\epsilon = 10^{-6}$, sai số tối đa so với $\frac{[3, 4]}{\sqrt{12.5 + 10^{-6}}} \odot [1, 2]$ là $< 1.11 \times 10^{-16}$.

### 2. Layer Normalization (LayerNorm)
$$\text{LayerNorm}(x, w, b, \epsilon) = \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} \odot w + b$$
* **Kiểm tra Bằng tay**: Với $x = [1.0, 3.0]$, $\mu = 2.0$, $\sigma^2 = 1.0$. Với trọng số đơn vị và bias bằng 0, đầu ra chuẩn hóa bằng $\frac{[-1.0, 1.0]}{\sqrt{1.0 + 10^{-5}}}$ (khớp tuyệt đối, sai số $= 0.0$).

### 3. Hàm Kích Hoạt Gated SwiGLU
$$\text{SwiGLU}(\text{gate}, \text{up}) = \text{SiLU}(\text{gate}) \odot \text{up} = \left(\text{gate} \cdot \frac{1}{1 + e^{-\text{gate}}}\right) \odot \text{up}$$
* **Kiểm tra Bằng tay**: Tại $\text{gate} = \ln(3) \approx 1.0986$, $\text{sigmoid}(\ln(3)) = \frac{3}{4} = 0.75$. Với $\text{gate} = [0, \ln(3)]$ và $\text{up} = [4.0, 2.0]$, kết quả là $[0.0, 1.5 \ln(3)]$ (khớp tuyệt đối, sai số $= 0.0$).

### 4. Rotary Position Embedding (RoPE)
Đối với các cặp tọa độ liền kề $(x_{2i}, x_{2i+1})$ tại vị trí chuỗi $m$ với tần số $\theta_i = b^{-2i/d}$:
$$\begin{pmatrix} x'_{2i} \\ x'_{2i+1} \end{pmatrix} = \begin{pmatrix} \cos(m\theta_i) & -\sin(m\theta_i) \\ \sin(m\theta_i) & \cos(m\theta_i) \end{pmatrix} \begin{pmatrix} x_{2i} \\ x_{2i+1} \end{pmatrix}$$
* **Kiểm tra Bằng tay**: Với $[1.0, 0.0]$ tại vị trí $m=1$ với $\theta_0=1.0$, vector sau quay là $[\cos(1), \sin(1)]$ (khớp tuyệt đối, sai số $= 0.0$).

---

## 3. Các Dạng Attention (MHA, GQA, MQA) & Parity Với KV-Cache

Hợp đồng causal attention nhận Query $[T, Q_H, D]$ và Key/Value $[T, KV_H, D]$, tự động lặp lại các head KV qua các nhóm query khi $Q_H > KV_H$:

| Chế Độ Attention | Head Query ($Q_H$) | Head KV ($KV_H$) | Tỷ Lệ Nhóm ($Q_H / KV_H$) | Sai Số Max So Với Vòng Lặp Scalar | Sai Số Max So Với Step KV-Cache |
|---|---|---|---|---|---|
| **MHA ($4 \times 4$)** | 4 | 4 | 1 | $4.44 \times 10^{-16}$ | $0.00 \times 10^{00}$ |
| **GQA ($4 \times 2$)** | 4 | 2 | 2 | $4.44 \times 10^{-16}$ | $0.00 \times 10^{00}$ |
| **MQA ($4 \times 1$)** | 4 | 1 | 4 | $2.78 \times 10^{-16}$ | $0.00 \times 10^{00}$ |

- **Toàn Cảnh vs Từng Bước**: Attention từng bước qua lịch sử KV-cache tích lũy (`cached_attention_step`) khớp tuyệt đối với tính toán cả chuỗi (`causal_attention`) tới độ chính xác máy tính ($0.0$ delta).

---

## 4. Cơ Chế Bảo Vệ Fail-Closed & Biên Kiểm Tra

1. **Chiều Head Chẵn Cho RoPE**: Từ chối các chiều head lẻ ($d \pmod 2 \neq 0$) do phép quay RoPE bắt buộc các cặp trực giao 2D.
2. **Kích Thước Khớp Trong SwiGLU**: Từ chối các tensor gate và up có kích thước không khớp nhau.
3. **Nhóm Attention Chia Hết**: Bắt buộc $Q_H \pmod{KV_H} == 0$. Từ chối tỷ lệ số nguyên tố không chia hết hoặc không hợp lệ.
4. **Tham Số Hữu Hạn & Dương**: Bắt buộc epsilon và hệ số cơ sở RoPE phải hữu hạn và dương.

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0047-decoder-primitives/decoder_primitives.py
```

Chạy bộ unit test:
```bash
pytest tests/test_decoder_primitives.py
```

File trích xuất artifact:
`verification/circuit/results/decoder-primitives-0047-extract.json`
