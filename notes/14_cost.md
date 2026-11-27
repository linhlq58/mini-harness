# 14 — Chi phí: token đổi ra VND, theo topology

## 1. Ý chính
Mỗi lần gọi model tốn tiền theo **số token vào (input)** và **số token ra (output)**. Token ra thường đắt hơn token vào nhiều lần, và token "suy nghĩ" ngầm (reasoning) cũng tính là token ra. Chi phí một lượt hỏi = tổng của **mọi** lần gọi model bên trong, nên **topology** (cách sắp xếp agent: một agent, router, subagent...) quyết định chi phí nhiều không kém độ dài câu hỏi. Chi phí tháng = chi phí một lượt × số lượt × hệ số retry.
Ví dụ đời thường: gửi một bưu kiện qua một hãng thì trả một lần cước. Gửi qua trạm trung chuyển, chia ra hai xe, rồi gom lại thì trả nhiều lần cước, dù món hàng vẫn vậy.

## 2. Mới so với file trước
- **Giữ nguyên:** tool `get_ticket`, `search_docs`; agent đơn giống **04** (dòng 47–50); router giống **08** (`Intent`/`Route`, specialist, tổng hợp; dòng 53–71).
- **Mới:**
  - Dòng 14–16: `PRICE` (giá **giả định**, USD/1 triệu token, tỷ giá) và `VOLUME` (số lượt/ngày, ngày/tháng, tỷ lệ retry).
  - Dòng 20–32: `CostMeter`, một **callback** cộng dồn số lần gọi, token vào, token ra, rồi đổi ra VND.
  - Dòng 79: `{"callbacks": [meter]}` truyền qua `config`.
  - Dòng 74, 80: nhân ra chi phí tháng.
- **Bỏ:** `RequestContext`, ownership, tracing code, `asyncio` của 08. Router chạy tuần tự, vì chạy song song chỉ đổi **thời gian**, không đổi **chi phí** (phá thử A của bài 08).

## 3. Đi qua code theo thứ tự chạy

**Bước 1: tạo đồng hồ đo cho mỗi topology** (dòng 78–79)
```python
meter = CostMeter()
answer = fn(QUESTION, {"callbacks": [meter]})
```
**Callback** là một object mà framework **tự gọi** vào những thời điểm nhất định. Ở đây là `on_llm_end`, chạy ngay sau mỗi lần model trả lời. Đặt nó trong `config` thì nó đi theo **xuống mọi tầng**: agent, specialist bên trong router, bước tổng hợp. Không lời gọi model nào lọt khỏi đồng hồ.

**Bước 2: cộng dồn sau mỗi lần gọi model** (dòng 24–28)
```python
usage = response.generations[0][0].message.usage_metadata
self.calls += 1; self.input += usage["input_tokens"]; self.output += usage["output_tokens"]
```
Đây là `usage_metadata` mà bạn đã thấy ở bài 01, giờ được cộng tự động.

**Bước 3: đổi ra tiền** (dòng 30–32)
```python
usd = self.input / 1e6 * PRICE["input_per_1m"] + self.output / 1e6 * PRICE["output_per_1m"]
return usd * PRICE["usd_vnd"]
```
Giá tính theo **mỗi 1 triệu token**, nên chia token cho `1e6` (một triệu). Input và output nhân **hai mức giá khác nhau**.

**Bước 4: nhân ra tháng** (dòng 74)
```python
per_month = 500 lượt/ngày × 22 ngày × 1.10
```
`× 1.10` nghĩa là 10% lượt phải chạy lại (lỗi tạm thời, timeout...). Mỗi lần chạy lại tốn **trọn** chi phí một lượt.

## 4. Kết quả khi chạy
```
>>> Ticket T-1 sao rồi, và chính sách mật khẩu là gì?

topology       lần gọi   input  output   VND/lượt     VND/tháng
agent đơn            2     414     114       43.1       521,450      ← 1 lần xin 2 tool + 1 lần trả lời
router               6     665     262       89.7     1,085,763      ← 1 route + 2×2 specialist + 1 tổng hợp
(tháng = 500 lượt/ngày × 22 ngày × 1.10 vì retry)
```
Đọc bảng:
- **Router tốn gấp ~2,1 lần**, vì 6 lần gọi model so với 2. Mỗi lần gọi đều phải gửi lại system prompt và lịch sử của riêng nó (bài 01).
- **Output ít hơn nhưng đắt hơn.** Agent đơn: input 414 token ≈ 13 VND, output 114 token ≈ 30 VND. Output chiếm **~70% chi phí** dù chỉ bằng ~1/4 số token, vì giá output gấp 8 lần input (theo giá giả định), và còn gồm cả token reasoning ngầm.
- Một lượt chỉ vài chục VND, nhưng **một tháng là hơn 1 triệu VND chỉ để chọn sai topology** (500 lượt/ngày).

## 5. Phá thử

**A. Chạy lặp lại 3 lần mỗi topology**
```
>>> Ticket T-1 sao rồi, và chính sách mật khẩu là gì?
  agent đơn  (lần gọi, input, output, VND): [(2, 414, 109, 41.8), (2, 414, 113, 42.8), (2, 414, 108, 41.5)]
  router     (lần gọi, input, output, VND): [(6, 670, 288, 96.7), (6, 662, 256, 88.1), (6, 665, 283, 95.2)]
```
- **Input gần như cố định** (414, 414, 414): input phụ thuộc vào prompt, tức thứ **mình** kiểm soát.
- **Output dao động ~10%** (256–288): output phụ thuộc vào model "nói" bao nhiêu và "nghĩ" bao nhiêu.
- Muốn dự đoán chi phí thì phải đo **nhiều lượt rồi lấy trung bình**, không dựa vào một lần chạy.

**B. Câu hỏi chỉ một ý: "Ticket T-1 sao rồi?"**
```
  agent đơn  (lần gọi, input, output, VND): [(2, 300, 43, 20.9), (2, 300, 50, 22.7), (2, 300, 44, 21.2)]
  router     (lần gọi, input, output, VND): [(4, 367, 165, 54.8), (4, 366, 169, 55.8), (4, 361, 150, 50.7)]
```
Router vẫn tốn **gấp ~2,5 lần**, dù chỉ gọi một specialist. Bước **route** và bước **tổng hợp** là chi phí cố định, kể cả khi chẳng có gì để tách hay để gộp. Câu càng đơn giản, phần cố định này càng chiếm tỷ lệ lớn.

**Điều này chứng minh:** chi phí do **số lần gọi model** quyết định nhiều nhất, và số lần gọi do **topology** quyết định. Router mua được sự **kiểm soát** (route cố định, song song, fallback, bài 08) bằng **tiền**. Đáng mua hay không phải đo, không đoán.

## 6. Tự kiểm tra
**Câu hỏi:** Retry và số lượng request ảnh hưởng tới chi phí tháng thế nào?

<details><summary>Đáp án</summary>

- **Số lượng request:** chi phí tăng **tuyến tính**. Gấp đôi số lượt/ngày thì gấp đôi chi phí. Chênh lệch nhỏ mỗi lượt (43 so với 90 VND) thành chênh lệch lớn mỗi tháng (0,5 so với 1,1 triệu VND ở 500 lượt/ngày, và 10 so với 21 triệu ở 10.000 lượt/ngày).
- **Retry:** mỗi lần chạy lại tốn **trọn** chi phí của phần được chạy lại. 10% lượt retry một lần thì +10%. Nhưng nếu 10% lượt lỗi và mỗi lượt lỗi retry **3 lần** thì +30%. Nếu retry **cả lượt router** (6 lần gọi) chỉ vì một specialist lỗi thì phí cả 5 lần gọi đã thành công.
- Vì vậy: chỉ retry lỗi **tạm thời** (không retry `denied`, file 26), retry **đúng bước bị lỗi** chứ không chạy lại cả lượt, và đặt **giới hạn** số lần retry. File 28 sẽ thêm ngân sách để chặn trước khi tiêu.
</details>

**Câu hỏi thêm:** Muốn giảm chi phí router mà vẫn giữ kiểm soát, có những hướng nào?

<details><summary>Đáp án</summary>

1. **Model rẻ cho bước đơn giản:** route và tổng hợp là việc dễ, dùng model nhỏ hơn (file 35 đo việc này kèm quality gate).
2. **Bỏ tổng hợp khi chỉ có một ý:** trả thẳng câu trả lời của specialist (phá thử B cho thấy đây là phần phí lớn).
3. **Fast path bằng code:** câu khớp mẫu rõ ràng (có mã `T-số`, không có ý khác) thì đi thẳng vào specialist ticket, khỏi gọi router.
4. **Prompt ngắn và giới hạn output:** input là thứ mình kiểm soát hoàn toàn. Output thì giới hạn bằng "trả lời ngắn gọn" hoặc `max_tokens`.
Mọi thay đổi đều phải đo lại **cả chi phí lẫn chất lượng**. Rẻ hơn mà trả lời sai thì không đáng.
</details>

## 7. Nối sang OpsDesk
- **Ở đâu:** **M07** (đo token và chi phí từ trace/callback, gắn vào metadata) và **M21** (so sánh chi phí theo topology và model, tối ưu kèm quality gate, ROI).
- **OpsDesk bọc thêm gì và vì sao:**
  - **Bảng giá theo từng model, lấy từ cấu hình**, không cứng trong code. Router/specialist/synthesizer có thể dùng model khác nhau (`OPSDESK_MODEL_*`), giá khác nhau.
  - **Chi phí ghi theo request** (`request_id`, user, workload, route) vào trace và **ledger** (file 28), để trả lời được "tháng này workload nào tốn nhất", "user nào dùng nhiều nhất".
  - **Phân biệt token cache** (`cache_read` trong `usage_metadata`): token đọc từ cache thường rẻ hơn nhiều, nên system prompt dài nhưng cố định có thể không đắt như tưởng.
  - **Budget guard trước khi gọi** (file 28): đo sau khi tiêu chỉ để báo cáo; chặn trước khi tiêu mới bảo vệ được ngân sách.
  - **Quyết định topology dựa trên eval + chi phí** (file 35, ADR), không theo cảm tính.
