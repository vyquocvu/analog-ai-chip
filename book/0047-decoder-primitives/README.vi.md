# 0047 — Các primitive decoder tái sử dụng được

Phần WP10.2 này tách các phép toán **chức năng** khỏi TinyGPT: LayerNorm,
RMSNorm, GELU, SwiGLU, RoPE và causal attention MHA/GQA/MQA. TinyGPT sử dụng lại
LayerNorm, GELU và attention chung để giữ parity GPT-2.

![Biên primitive decoder](diagrams/decoder-primitives.svg)

Các ma trận projection tĩnh vẫn là biên có thể đưa vào consumer analog mô phỏng;
normalization, RoPE, activation và attention token-token vẫn chạy số bằng NumPy.
Đây không phải là bằng chứng tăng tốc analog hay phần cứng.

Ví dụ tính tay gồm RMSNorm `[3,4]` với `RMS²=12.5`, RoPE quay `[1,0]` thành
`[cos(1),sin(1)]`, và SwiGLU tại `ln(3)`. Test so sánh MHA/GQA/MQA với vòng lặp
scalar độc lập và đường KV-cache, đồng thời kiểm tra các đầu vào biên không hợp
lệ. WP10.2 chỉ được đánh dấu hoàn tất sau khi decoder tổng quát theo manifest
được lắp ráp ở phần tiếp theo.
