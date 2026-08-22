# 0051 — Bộ Đánh Giá Mô Hình Khả Năng Tiếp Tục & Giới Hạn Thực Thi (Hoàn Thành Gate R11)

> **English version:** [`README.md`](README.md)

Chương này khép lại **Gate R11 (Memory-bounded large-model simulator)** bằng việc chuẩn hóa **cơ chế thực thi mô hình theo từng layer có checkpoint, khả năng khôi phục sau gián đoạn với xác thực toàn vẹn mật mã SHA256, sổ cái phần cứng chống đếm lặp, và giới hạn tài nguyên host** trên các bậc thiết kế T0–T3.

---

## 1. Pipeline Checkpoint Từng Layer & Kiến Trúc Trạng Thái

![Pipeline Đánh Giá Khả Năng Tiếp Tục](diagrams/resumable-execution.svg)

- **Tuần Tự Hóa Từng Layer**: Thay vì lưu giữ toàn bộ đồ thị kích hoạt đa layer trong bộ nhớ RAM của host, mỗi decoder layer $l \in [0, L-1]$ tuần tự hóa tensor kích hoạt đầu ra xuống đĩa (`layer_XXXX_state.npy`) cùng siêu dữ liệu thực thi (`layer_XXXX_meta.json`).
- **Logic Tiếp Tục (Resumption)**: Khi khởi động, [`ResumableModelEvaluator`](../../analog_llm/resumable_evaluator.py) kiểm tra thư mục checkpoint. Mọi layer đã hoàn thành khớp mã băm mật mã SHA256 của kích hoạt đầu vào sẽ được nạp tức thì mà không cần tính toán lại.

---

## 2. Toàn Vẹn Mật Mã & Sổ Cái Chống Đếm Lặp

- **Phát Hiện Sai Lệch Trạng Thái & Can Thiệp**: Trước khi tiếp tục từ trạng thái đã lưu, bộ đánh giá xác minh:
  $$\text{SHA256}(x_{\text{input}}) == \text{checkpoint.input\_sha256}$$
  Nếu kích hoạt đầu vào sai lệch (ví dụ đổi prompt hoặc sửa trọng số), quá trình thực thi lập tức dừng và báo lỗi (fail closed).
- **Tính Bất Biến Của Sổ Cái (Ledger Idempotency)**: Các chỉ số phần cứng tích lũy (MAC, chu kỳ tile, năng lượng analog) được khôi phục từ metadata thay vì cộng dồn lại, ngăn chặn việc tính toán trùng lặp khi chạy lại.

---

## 3. Thang Đo Quy Mô Khối Lượng Công Việc & Giới Hạn Tài Nguyên (T0–T3)

Khung thực thi đặt ra các trần giới hạn bộ nhớ host và thời gian thực thi cho từng tier mô hình:

| Bậc (Tier) | Quy Mô Tham Số | Thiết Kế Ngữ Cảnh | Trần Bộ Nhớ RSS Host | Ngân Sách Thời Gian | Độ Sâu Kiểm Chứng |
|---|---|---|---|---|---|
| **T0** | Đến $150\text{M}$ | $2,048\text{ token}$ | $2\text{ GB}$ | $60.0\text{ s}$ | Chạy float đầy đủ + analog vật lý đầu cuối |
| **T1** | $1\text{--}1.5\text{B}$ | $4,096\text{ token}$ | $8\text{ GB}$ | $300.0\text{ s}$ | Nạp checkpoint & giải mã giới hạn |
| **T2** | $\approx 3\text{B}$ | $8,192\text{ token}$ | $16\text{ GB}$ | $900.0\text{ s}$ | Nạp checkpoint & giải mã giới hạn |
| **T3** | $7\text{--}8\text{B}$ | $8,192\text{ token}$ | $32\text{ GB}$ | $1,800.0\text{ s}$ | Giải mã streaming & khảo sát sai số mẫu |

---

## 4. Kết Quả Khôi Phục Sau Gián Đoạn & Kiểm Chứng

Trong một lần thực thi mô hình LLaMA GQA 4 layer ($Q_H=4, KV_H=2$, SwiGLU, RoPE) bị gián đoạn sau Layer 1:

- **Lần Chạy Đầy Đủ Cơ Sở**: Tính 4 layer, ghi nhận $32,768\text{ MAC}$.
- **Lần Chạy Bị Gián Đoạn**: Tính layer 0 và 1, lưu trạng thái checkpoint, dừng an toàn.
- **Lần Chạy Tiếp Tục**: Nạp layer 0 và 1 từ đĩa ($0\text{ MAC tính toán mới}$), tính tiếp layer 2 và 3.
- **Độ Tương Đương Số Học**: Sai số logit tuyệt đối tối đa $\Delta = 0.000\text{e}+00$ (khớp bit tuyệt đối).
- **Độ Tương Đương Sổ Cái**: Tổng số MAC khi chạy tiếp tục khớp chính xác với lần chạy cơ sở ($32,768\text{ MAC}$, $0\text{ đếm lặp}$).

---

## 5. Thực Thi & Artifacts

Chạy script kiểm tra độc lập của chương:
```bash
python book/0051-resumable-evaluator/resumable_evaluator.py
```

Chạy bộ unit test:
```bash
pytest tests/test_resumable_evaluator.py
```

File trích xuất artifact:
`verification/circuit/results/resumable-evaluator-0051-extract.json`
