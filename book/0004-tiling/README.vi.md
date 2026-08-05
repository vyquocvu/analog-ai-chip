# 0004 — Chia ma trận (tiling) lên nhiều mảng vật lý

> **Thời gian đọc:** ~10 phút · **Chạy:** `python book/0004-tiling/train.py`

Một lớp LLM thật có các ma trận lớn hơn hẳn bất kỳ crossbar vật lý nào. Chương
này trình bày câu trả lời chuẩn: **tách cả hàng đầu ra lẫn cột đầu vào thành
các tile**, tính một tích ma trận-véc-tơ cục bộ cho mỗi tile, và **cộng dồn
partial sum** qua các tile cột đầu vào để khôi phục đầu ra logic.

## 1. Ánh xạ

Lấy một ma trận trọng số `4 × 5` và tile vật lý `2 × 3`:

![Chia ma trận 4×5 lên tile 2×3](diagrams/tiling.svg)

Có `2 nhóm-hàng × 2 nhóm-cột = 4` tile:

```text
rows 0:2, cols 0:3    rows 0:2, cols 3:5     (T00, T01)
rows 2:4, cols 0:3    rows 2:4, cols 3:5     (T10, T11)
```

Véc-tơ đầu vào cũng được tách tương tự: `x = [1, −1, 0.5, 2, −0.25]` trở thành
`x[0:3] = [1, −1, 0.5]` cho các tile cột-trái và `x[3:5] = [2, −0.25]` cho các
tile cột-phải.

## 2. Partial sum tính tay (hàng 0)

`matrix = [[1..5],[6..10],[11..15],[16..20]]` đầy đủ. Cho hàng đầu ra 0:

```text
T00 (cols 0:3): 1×1 + 2×(−1) + 3×0.5 = 1 − 2 + 1.5 = 0.5
T01 (cols 3:5): 4×2 + 5×(−0.25)      = 8 − 1.25   = 6.75
output[0] = T00 + T01                = 7.25
```

Các hàng khác cho `[7.25, 18.5, 29.75, 41]`. Lặp lại việc tách cho mọi dải
hàng và **cộng hai partial cột** khôi phục chính xác `matrix @ x`.

## 3. Chạy nó

```bash
python book/0004-tiling/train.py
```

`tiled_mvm(matrix, vector, 2, 3)` duyệt các tile một cách tường minh và khẳng
định kết quả bằng phép nhân dày đặc `matrix @ vector`. Tiling là một quyết định
*lập lịch phần mềm*, không phải vật lý — điểm mấu chốt là một MVM logic lớn có
thể được phủ bởi các mảng vật lý hữu hạn.

## 4. Vì sao "O(1)" cần được bổ chính

Một mảng vật lý có thể đánh giá MVM *cư trú* của nó trong một thao tác analog.
Nhưng đó không phải khẳng định end-to-end. Một lớp lớn cần:

- **nhiều tile** — ma trận quá lớn cho một mảng;
- **nhiều chu kỳ chuyển đổi** — kết quả mỗi tile được đọc qua một ADC;
- **cộng dồn partial sum** — kết quả các nhóm cột phải được cộng;
- **truyền thông và lập lịch** — di chuyển đầu vào/đầu ra quanh máy.

Vì vậy thời gian/năng lượng xử lý một lớp end-to-end tăng theo kích thước mô
hình; không phải hằng số. Đây chính là lý do simulator `analog_llm` giữ một
**physical ledger** (MACs, tile MVM cycles, rewrites) thay vì tuyên bố `O(1)`
miễn phí, và `Accelerator` của nó chia ma trận tùy ý trên một lưới tile trong
khi cộng dồn partial sum.

> **Cầu nối với simulator:** `analog_llm.accelerator.Accelerator.mvm` làm chính
> điều này: chia ma trận lên các tile, pad các block biên, cộng dồn partial cột
> bằng digital, và tính vào ledger số MACs/cycles/rewrites. Chạy
> `scripts/run_llm_sim.py` để thấy một transformer nhỏ hoàn chỉnh được tiling
> và chạy.

## 5. Block biên

Khi một chiều của ma trận không phải bội số của kích thước tile (ở đây 5 cột
với tile 3 cột), tile cột cuối nhỏ hơn (`2 × 2`). Trong simulator, block được
**pad bằng số 0** lên đúng kích thước tile vật lý để mọi tile chạy đồng đều;
các cell 0 không đóng góp công việc hữu ích, và ledger chỉ tính các cell thật.

## 6. Bài tập

1. Tự tiling một ma trận `3 × 6` với tile `2 × 2`: có bao nhiêu nhóm-hàng,
   nhóm-cột và tile? Vẽ sơ đồ.
2. Tự tính lại `output[3] = 41` bằng tay qua hai partial cột (hàng 2 của T10 và
   T11 với `x`), như §2 đã làm cho hàng 0.
3. Điều gì xảy ra với số tile nếu tile là `4 × 5` thay vì `2 × 3`, với cùng ma
   trận `4 × 5`?
4. Giải thích vì sao các partial sum phải được **cộng**, không phải ghi đè,
   khi nhiều tile phủ cùng các hàng đầu ra.

## 7. Tiếp theo

Đây là chương kết track lý thuyết (0001–0004). Chương 0005 (`one-analog-neuron`)
biến một tổng có trọng số thành phần cứng thật. Hoặc chuyển sang simulator sản
phẩm `analog_llm` (`scripts/run_llm_sim.py`), nơi kết hợp *cả bốn* ý tưởng —
crossbar, trọng số vi phân, bộ chuyển đổi, và tiling — để chạy một transformer
nhỏ và báo cáo ledger cùng accuracy.
