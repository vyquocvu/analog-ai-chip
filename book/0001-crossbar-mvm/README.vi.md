# 0001 — Ohm + Kirchhoff = phép nhân ma trận-véc-tơ

> **Thời gian đọc:** ~15 phút · **Chạy:** `python book/0001-crossbar-mvm/train.py`

Một crossbar biến hai định luật mạch điện kinh điển thành một phép nhân
ma trận-véc-tơ. Một **cell độ dẫn lập trình được** lưu một giá trị không âm
`G`. Đặt một điện áp `V` lên nó và Định luật Ohm cho dòng điện của cell

```text
I = V × G
```

Nơi các dòng điện của một cột gặp nhau, Định luật Kirchhoff (KCL) nói rằng
chúng **cộng lại**. Do đó một cột tạo ra một tích vô hướng giữa các độ dẫn của
nó với điện áp được áp. Một lưới các cột như vậy tính được `I = G @ V`.

## 1. Hình ảnh

![Crossbar 2×2: I = G·V](diagrams/crossbar.svg)

- **Hàng** = đầu vào: mỗi hàng được kéo bởi một điện áp `V_i`, biểu diễn một
  giá trị activation `x_i`.
- **Cột** = đầu ra: mỗi cột gom các dòng điện của các cell và cộng chúng lại,
  tạo ra một đầu ra `I_j`.
- **Cell** = trọng số: mỗi giao điểm lưu một độ dẫn `G[j, i]`.

Điều sơ đồ giấu đi là mỗi cell là một **độ dẫn được lập trình riêng**. Trong
một cỗ máy, đó là điện trở chính xác trên bảng cố định; trong cỗ máy lập trình
được, đó là chiết áp số hoặc, sau này, một cell ReRAM. Phép toán không đổi.

## 2. Quy ước (đọc kỹ hai lần)

Repo lưu mọi ma trận trọng số dạng `[output, input]`, tức là

```text
G[j, i]  nối đầu vào i (hàng)  →  đầu ra j (cột)
```

và tính

```text
I_j = Σ_i  G[j,i] · V_i        (từng cột, là tổng KCL)
```

Theo các mảng đã thấy ở trên:

```text
V = [0.2, 0.5]                  (V0 trên hàng 0, V1 trên hàng 1)
G = [[2.0, 1.0],                G[0] = cột "đầu ra 0"
     [0.5, 3.0]]                 G[1] = cột "đầu ra 1"
```

Vì theo hướng này `cột = đầu ra`, nên **đặt điện áp trên hàng, đọc dòng trên
cột**. Nếu đảo ngược, bạn phải chuyển vị (transpose) tại đúng một ranh giới đã
đặt tên (xem `docs/MODULE_STANDARD.md`).

## 3. Tính bằng tay

Đầu vào `V = [0.2, 0.5]`, độ dẫn như trên.

**Đầu ra 0** (cột của `G[0] = [2.0, 1.0]`):

```text
I0 = G[0,0]·V0 + G[0,1]·V1 = 2.0×0.2 + 1.0×0.5 = 0.4 + 0.5 = 0.9
```

**Đầu ra 1** (cột của `G[1] = [0.5, 3.0]`):

```text
I1 = G[1,0]·V0 + G[1,1]·V1 = 0.5×0.2 + 3.0×0.5 = 0.1 + 1.5 = 1.6
```

```text
I = G @ V = [0.9, 1.6]
```

Giờ chạy phép kiểm chứng:

```bash
python book/0001-crossbar-mvm/train.py
```

Câu assertion `assert_allclose(actual, [0.9, 1.6])` chính là **hợp đồng** giữa
số học viết tay này và `analog_ai.crossbar.ideal_mvm`. Đọc lại §2 và đối chiếu
sơ đồ: đầu vào 0 (hàng) mang 0.2 V, và đầu ra 0 (cột) tính tổng
`2.0×0.2 + 1.0×0.5`.

## 4. Ví dụ thứ hai để tin vào trực giác

Lấy một ma trận gần như đường chéo và kiểm tra nhanh:

```text
V = [1.0, 0.0]          G = [[0.5, 0.0],
                              [0.0, 0.7]]
I = G @ V = [0.5, 0.0]
```

Vì `V1 = 0` nên hàng dưới không đóng góp gì; cột 0 chỉ đọc cell trên của nó,
`0.5×1.0 = 0.5`. Đây chỉ là định nghĩa của một tích vô hướng — chẳng có gì
thần kỳ. Hãy đổi một giá trị và tự tính tay trước khi tin vào code.

## 5. Điều gì thực sự là analog ở đây

- **Phép nhân** xảy ra trong mỗi cell qua Định luật Ohm: `I = V × G`.
- **Phép cộng dồn** xảy ra "miễn phí" qua KCL: các dòng điện cộng vật lý trên
  dây dẫn. Không cần bộ cộng riêng và không cần vòng lặp qua các đầu vào cho
  một MVM cư trú.

Đó chính là toàn bộ ý tưởng. Mọi thứ khác trong một lớp LLM — bộ chuyển đổi,
activation, partial sum qua các tile, lập lịch — là *công việc bổ sung* mà các
chương sau và simulator `analog_llm` làm rõ.

## 6. Các non-ideality bạn chưa thấy

`ideal_mvm` cố tình lý tưởng. Một mảng thật còn có:

- **độ phân giải độ dẫn hữu hạn** — không thể lập trình `G` tới độ chính xác
  tùy ý (đây chính là `g_bits` trong `analog_llm`/chuyển đổi);
- **độ phân giải và clipping của DAC/ADC** — điện áp không thể chính xác tuyệt
  đối, và đầu ra bão hòa;
- **nhiễu và gain/offset** trên đường đọc;
- **sụt parasitic/IR và cell kẹt**, bỏ qua ở đây.

Không có non-ideality nào bị giấu trong ví dụ đầu tiên; chúng được nêu tên ở
đây để chương 0003 (`converters-and-noise`) và simulator thêm chúng như các
đặc trưng tường minh thay vì một "error" mơ hồ.

## 7. Phá vỡ nó có chủ đích

Đổi một độ dẫn thành giá trị âm, ví dụ `G = [[2.0, -1.0], ...]`. Code sẽ từ
chối:

```text
ValueError: physical conductance cannot be negative
```

Một độ dẫn thụ động thật luôn `G ≥ 0`, nên một trọng số âm không thể nằm trong
một cell duy nhất. Đó chính là lý do chương 0002 dùng **cặp vi phân** để biểu
diễn trọng số có dấu bằng hai mảng không âm.

## 8. Ranh giới của chương này

Phép nhân NumPy chỉ là một kiểm tra **chức năng** của phương trình. Nó không
mô phỏng động thái transistor, điện trở dây, năng lượng chuyển đổi, hay thời
gian (xem ba mức khẳng định trong `AGENTS.md`). Một thao tác crossbar cư trú
đầy đủ, lý tưởng không phải là LLM `O(1)` end-to-end — chương 0004 cho thấy vì
sao tiling và cộng dồn phá vỡ cách đơn giản hóa đó.

## 9. Bài tập

1. Tự tính `I0` bằng tay với `V = [0.5, 0.5]` và cùng `G`. Kiểm chứng với
   `ideal_mvm` trước khi chạy.
2. Viết một crossbar 1×3 (`G` một hàng, `V` ba phần tử) và tính đầu ra duy nhất
   bằng tay.
3. Đảo hướng: dùng `G.T @ V` và xác nhận số *không* khớp với `G @ V`. Giải
   thích vì sao (xem §2).
4. Dự đoán điều gì đổi khi độ dẫn một cell tăng gấp đôi; kiểm chứng bằng code.

## 10. Tiếp theo

Tiếp tục với `book/0002-differential-pairs/`, nơi hai mảng không âm `(G+, G−)`
khôi phục các trọng số mạng neural có dấu. Simulator `analog_llm`
(`scripts/run_llm_sim.py`) cho thấy cùng crossbar này được nhân rộng và dùng để
chạy một transformer nhỏ.
