# 0046 — Manifest mô hình độc lập kiến trúc

Gate R10 bắt đầu bằng hợp đồng chức năng, không tạo thêm tuyên bố vật lý.
`ModelManifest` mô tả rõ kích thước, dtype, kiểu normalization/vị trí/MLP,
MHA/GQA/MQA, bias và weight tying. Ma trận tuyến tính chuẩn hóa theo `[out, in]`;
adapter checkpoint phải khai báo phép chuyển vị tại biên.

![Luồng kiểm tra manifest](diagrams/manifest-flow.svg)

Ví dụ kiểm tra bằng tay dùng `V=5`, `H=4`, một layer, hai query head, một KV
head, `I=6`, context 3, FP16, RMSNorm, RoPE, SwiGLU và MQA. Kết quả là **152
tham số**, **120 MAC projection/layer/token**, và **24 byte KV cache**. Attention
token-token vẫn là phép toán số; MAC động của nó không nằm trong con số 120.

Đây chỉ là số liệu inventory chức năng/giải tích, không phải bằng chứng về mạch,
độ trễ, năng lượng, diện tích hoặc khả năng model nằm trên accelerator. Chạy
`pytest tests/test_model_manifest.py` để tái tạo các assertion và các ca lỗi.
