# Tài liệu Tầm nhìn Dự án: Analog AI Chip cho LLM

## Mục tiêu Cốt lõi
Phát triển một **Thiết bị Đầu cuối AI Độc lập (Dedicated Offline AI Text Appliance / AI Typewriter)** chuyên dụng cho tác vụ hỏi đáp và sáng tạo văn bản (chỉ gồm Màn hình, Bàn phím, và Bộ xử lý Text I/O), vận hành trên kiến trúc **Analog Compute-in-Memory (CiM)**.

Thiết bị hướng tới trải nghiệm:
1. **Hoạt động 100% Offline & Bảo mật tuyệt đối (Air-gapped)**: Toàn bộ mô hình ngôn ngữ chạy cục bộ trên phần cứng Analog, không cần kết nối Internet, không gửi dữ liệu ra ngoài.
2. **Khởi động tức thì & Phản hồi thời gian thực**: Xử lý MVM một chu kỳ bằng dòng điện vật lý, sinh token liên tục với độ trễ cực thấp.
3. **Thời lượng pin vượt trội (Cực tiết kiệm năng lượng)**: Kết hợp màn hình E-Ink / Low-Power Display với chip Analog CiM công suất thấp (nano-Watt đến sub-Watt), cho phép hoạt động liên tục trong nhiều ngày.

---

## 1. Kiến trúc Hệ thống Thiết bị Toàn diện (End-to-End Appliance Architecture)

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│             THIẾT BỊ ĐẦU CUỐI AI VĂN BẢN (ANALOG AI APPLIANCE)                 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  [ BÀN PHÍM CƠ / QWERTY ] ──────────┐                                          │
│  (Nhập Text / Prompt)               │ (Giao tiếp USB / I2C / SPI)              │
│                                     ▼                                          │
│                      ┌──────────────────────────────┐                          │
│                      │   HOST CONTROLLER (DIGITAL)  │                          │
│                      │  - MCU RISC-V / ARM SoC      │                          │
│                      │  - Tokenizer / Detokenizer   │                          │
│                      │  - Quản lý Text Buffer & UI  │                          │
│                      │  - Quản lý LayerNorm / Cache │                          │
│                      └──────────────┬───────────────┘                          │
│                                     │                                          │
│                                     │ Bus tốc độ cao (QSPI / FMC / Parallel)   │
│                                     ▼                                          │
│                      ┌──────────────────────────────┐                          │
│                      │  ANALOG CIM NEURAL ENGINE    │                          │
│                      │  - Mảng Crossbar vi sai      │                          │
│                      │  - Trọng số Ternary BitNet   │                          │
│                      │  - Subthreshold Softmax      │                          │
│                      │  - Time-Domain PWM / TDC     │                          │
│                      └──────────────┬───────────────┘                          │
│                                     │                                          │
│                                     ▼ (Token IDs)                              │
│                      ┌──────────────────────────────┐                          │
│                      │   MÀN HÌNH E-INK / MONO OLED │                          │
│                      │  (Hiển thị Text Stream)      │                          │
│                      └──────────────────────────────┘                          │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Lựa chọn Công nghệ Gia công (Node Technology)

* **Giai đoạn Thử nghiệm (PoC): 130nm**
  * **Lý do:** Chi phí tối ưu, có sẵn mã nguồn mở hoàn toàn (Open-Source PDK từ SkyWater/GlobalFoundries), dễ dàng tiếp cận mà không cần pháp nhân công ty lớn hay ngân sách hàng triệu USD.
* **Giai đoạn Thương mại (Target Node): 28nm**
  * **Lý do:** Đây là "nút giao vàng" (Sweet spot) của thiết kế Analog. Công nghệ 28nm cung cấp sự cân bằng hoàn hảo: mật độ đủ lớn để chứa tham số, chi phí mặt nạ (Mask cost) hợp lý, và quan trọng nhất là giữ được dải điện áp (Voltage headroom) đủ lớn để mạch Analog/ADC/DAC không bị suy giảm SNR nghiêm trọng do nhiễu – bài toán mà các tiến trình FinFET 7nm hay 3nm gặp phải (The Analog Scaling Wall).
* *Lưu ý về xưởng đúc thương mại:* Tối ưu chi phí khi làm dạng Startup/R&D mua slot MPW riêng (ngân sách $8K - $30K). Cần xem xét kỹ rào cản NDA/PDK đóng khi triển khai mã nguồn mở.

---

## 3. Kiến trúc & Đột phá Kỹ thuật trên Chip Analog

Để giải quyết bài toán chạy LLM trên Analog và tối ưu hệ thống, dự án nghiên cứu 4 hướng cải tiến:

1. **Kiến trúc Ternary LLM (BitNet b1.58):** 
   * Ép trọng số về 3 giá trị $W \in \{-1, 0, 1\}$.
   * Loại bỏ hoàn toàn các bộ DAC trọng số đa bit phức tạp, biến phép toán ma trận thành mạng lưới công tắc vi sai định tuyến dòng điện ($W = 1 \implies G_{pos}=G_0, G_{neg}=0$; $W = -1 \implies G_{pos}=0, G_{neg}=G_0$; $W = 0 \implies G_{pos}=0, G_{neg}=0$), kết hợp mảng SRAM-CiM đơn giản.
2. **Khối Analog Subthreshold (Cho Softmax):** 
   * Khai thác dòng rò rỉ dưới ngưỡng của MOSFET ($I_{DS} \propto \exp\left(\frac{V_{GS}-V_{th}}{n V_T}\right)$) để tính toán hàm số mũ tự nhiên, hướng tới tiêu thụ điện năng ở mức nano-Watt.
3. **Tính toán Miền Thời gian (Time-Domain Computing):** 
   * Sử dụng điều chế độ rộng xung (PWM) để truyền tải giá trị kích hoạt thay vì biên độ điện áp, dùng tụ điện để tích lũy điện tích kết quả, kết hợp bộ TDC (Time-to-Digital Converter) thay cho ADC truyền thống.
4. **Kiến trúc Lai (Hybrid Pipeline):** 
   * Dùng Analog Crossbar để xử lý khối lượng tính toán nặng (Nhân ma trận Q, K, V, MLP up/down).
   * Dùng bộ điều khiển Digital (VD: RISC-V VexRiscv) nhỏ gọn xử lý luồng dữ liệu, điều phối chu kỳ, và hàm phi tuyến (RMSNorm, LayerNorm, Top-p/Top-k Sampler).

---

## 4. Hình thái Thiết bị & Trải nghiệm Người dùng (Form Factor & UX)

Sản phẩm cuối cùng là một **Máy Soạn thảo / Trợ lý AI Cầm tay (AI Communicator / Cyberdeck)**:
* **Giao diện Phần cứng:**
  * **Bàn phím:** Bàn phím cơ thu gọn (40%/60% hoặc Ortholinear) hoặc bàn phím chiclet gõ êm.
  * **Màn hình:** Màn hình E-Paper (E-Ink 4.2" - 6.0") hoặc OLED đơn sắc độ tương phản cao, tối ưu hiển thị văn bản không mỏi mắt.
  * **Vỏ thiết bị:** Khung nhôm CNC hoặc vỏ in 3D công nghiệp nguyên khối, tích hợp pin Li-ion / 18650 và mạch sạc Type-C.
* **Trải nghiệm Phần mềm:**
  * Không hệ điều hành nặng nề: Bật công tắc là sẵn sàng gõ (Boot time < 1 giây).
  * Chế độ làm việc tập trung: Chỉ có màn hình nhắc lệnh (prompt) và dòng text phản hồi từ mô hình AI tuôn ra theo thời gian thực.
  * Tùy chọn lưu trữ: Lưu các đoạn hội thoại, bài viết vào thẻ nhớ SD dạng text/markdown thuần túy.

---

## 5. Lộ trình Mở rộng cho Siêu mô hình (7B, 70B)

Để chạy các LLM quy mô lớn trên tiến trình 28nm mà không bị giới hạn bởi diện tích die đơn lẻ:

1. **Bộ nhớ eNVM (ReRAM / MRAM):** Nghiên cứu thay thế SRAM bằng ReRAM trên 28nm để đạt mật độ lưu trữ gấp 3-5 lần và triệt tiêu điện năng rò rỉ (leakage power) ở trạng thái chờ.
2. **Đóng gói Chiplet 2.5D:** Sản xuất hàng loạt các viên Chiplet chuẩn hóa và ghép nối qua Silicon Interposer (chuẩn UCIe) để mở rộng dung lượng tham số theo dạng module.
3. **Pipeline Parallelism (Mở rộng theo chiều ngang):** Thiết kế bo mạch chuẩn PCIe. Mỗi thẻ xử lý một số Layer nhất định, nối tiếp các thẻ trên hệ thống qua giao thức truyền dữ liệu tốc độ cao.

---

## 6. Ngăn xếp Công cụ Thử nghiệm (Open-Source EDA Stack)

* **Xschem:** Vẽ sơ đồ mạch nguyên lý (Schematic Capture).
* **Ngspice / Xyce:** Mô phỏng mạch điện cấp độ Transistor để đo dòng điện/điện áp và trích xuất tham số sang `device_profiles/`.
* **Magic VLSI / KLayout:** Thiết kế Layout vật lý cho khối Analog/Mixed-signal.
* **Netgen:** Kiểm tra LVS (Layout vs Schematic).
* **KiCad:** Thiết kế bo mạch chủ PCB cho thiết bị hoàn chỉnh (gắn MCU, bàn phím, màn hình E-Ink và slot cắm chip Analog).
* **Phương án Tape-out:** Bắt đầu bằng **Tiny Tapeout** (PDK Sky130 Analog) cho các mạch cell thử nghiệm, tiến tới **Efabless ChipIgnite** (~$9,750 cho bản PoC diện tích lớn kèm bo mạch kiểm thử).
