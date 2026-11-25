# mini-harness — Roadmap

> Bản "học khái niệm" chạy song song với OpsDesk. Học cái lõi ở đây trước, rồi mới mở milestone OpsDesk tương ứng để xem bản production bọc thêm gì quanh nó, và vì sao.
> Cover **toàn bộ** `course-notes/knowledge-map.md` (bảng đối chiếu ở cuối file).

---

## 1. Nguyên tắc

1. **Một file = một khái niệm**, chạy độc lập: `uv run python 08_router.py`.
2. **Dưới ~100 dòng mỗi file.** Dài hơn nghĩa là đang nhồi hai khái niệm → tách ra.
3. **Không import lẫn nhau**, trừ đúng một file dùng chung `common.py` (khởi tạo model + dữ liệu mẫu). Lặp code giữa các file là **cố ý**: mỗi file đọc được một mình.
4. **Tự làm tay trước, dùng framework sau.** Ví dụ 03 tự viết vòng lặp agent → 04 làm lại bằng `create_agent`. Bạn sẽ thấy framework đang làm hộ việc gì.
5. **Mỗi file chỉ thêm ít so với file trước.** Đặt hai file cạnh nhau (VS Code: *Compare Selected*) là thấy khái niệm mới nằm ở đâu.
6. **`print` thay UI.** Timeline là các dòng in ra terminal. Chỉ có một file UI ở cuối (36).
7. **Dữ liệu tí hon**, cùng domain IT Helpdesk với OpsDesk: 3 nhân viên, 4 ticket, 5 đoạn tài liệu, tất cả nằm trong `dict`/`list`. Không có database (trừ khi chính khái niệm cần, như checkpointer bền vững ở 23).
8. **Header 3 dòng** ở đầu mỗi file:
   ```python
   # Khái niệm: <một câu>
   # Layer: <Orchestration | Context | Tools | Verification | Operations>
   # Khóa học: W? L?  ·  OpsDesk: M??
   ```

## 2. Chia việc & cách học mỗi file (15–30 phút đọc)

**Claude Code làm hết phần code; Link chỉ đọc hiểu.**

| Claude Code | Link |
|---|---|
| Kiểm tra version package | — |
| Viết file `NN_*.py` | — |
| Chạy file, lấy output thật | — |
| Tự chạy thí nghiệm "Phá thử" (bản tạm, không sửa file gốc) | — |
| Viết giải thích vào `notes/NN_*.md` + hiện trong chat | Đọc giải thích |
| Commit | Hỏi lại chỗ chưa hiểu (Claude Code hoặc Claude Chat) |

Cách bắt đầu một bước: nói với Claude Code **"Làm file NN"**.

Giải thích luôn theo cùng 7 mục (template trong `CLAUDE.md`):
1. Ý chính
2. Mới so với file trước
3. Đi qua code theo thứ tự chạy
4. Kết quả khi chạy (output thật, có chú thích)
5. Phá thử (đã đổi gì → output → chứng minh điều gì)
6. Tự kiểm tra (câu hỏi + đáp án ẩn, tự nghĩ trước rồi mở ra)
7. Nối sang OpsDesk

Thứ tự đọc gợi ý: mục 1 → mở file `.py` đọc lướt → mục 2–5 → thử trả lời mục 6 trước khi mở đáp án → mục 7.
Khi xong cả một nhóm, mở milestone OpsDesk được ghi để nhận ra "cái lõi" vừa học nằm ở đâu.

Nhịp gợi ý: 3–4 file / buổi 1–2 giờ → khoảng 10–12 buổi cho cả 4 tuần.

## 3. Cấu trúc repo

```
mini-harness/
├── CLAUDE.md             # quy tắc cho Claude Code
├── roadmap.md
├── pyproject.toml        # uv; thêm package khi file nào cần tới
├── .env                  # OPENAI_BASE_URL, OPENAI_API_KEY (gateway khóa học), LANGSMITH_*, LANGFUSE_*
├── common.py             # llm() + EMPLOYEES, TICKETS, DOCS — tối đa ~40 dòng
├── 01_call_model.py
├── ...
├── 36_serve.py
└── notes/                # giải thích của từng file: 01_call_model.md, ...
```

`common.py` (dáng):
```python
EMPLOYEES = {"an": {"role": "employee", "dept": "sales"},
             "binh": {"role": "it_staff", "dept": "it"},
             "chi": {"role": "it_manager", "dept": "it"}}
TICKETS = {"T-1": {"owner": "an", "status": "open", "title": "Laptop chậm"},
           "T-2": {"owner": "binh", "status": "closed", "title": "VPN lỗi"}, ...}
DOCS = [...]   # 5 đoạn: password policy, VPN, ...

def llm(model="gpt-4.1-mini"):
    return ChatOpenAI(model=model)   # đọc base_url/key từ .env
```

---

## 4. Lộ trình

Ký hiệu mỗi file: **Thêm gì** · **Thấy gì khi chạy** · **Phá thử** (Claude Code tự chạy) · **Tự kiểm tra**

### Phần 1 — Tuần 1: Agent cơ bản (Orchestration · Context · Tools · Operations)

**01_call_model.py** — Gọi model, danh sách `messages` (system/user/assistant). · OpsDesk M03
- Thêm gì: một lời gọi model + in `usage` (số token).
- Phá thử: bỏ system message, đổi giọng system prompt.
- Tự kiểm tra: model có "nhớ" lượt trước không nếu bạn không gửi lại lịch sử?

**02_workflow.py** — Workflow deterministic: code quyết định các bước, model chỉ làm một việc nhỏ. · W1 L3 · OpsDesk M05, M14a
- Thêm gì: model phân loại câu hỏi thành `ticket | policy | other` → `if/else` bằng code gọi hàm tương ứng.
- Phá thử: hỏi một câu mơ hồ → nhánh nào chạy? Ai chịu trách nhiệm cho lựa chọn đó?
- Tự kiểm tra: khi nào nên để code quyết định thay vì model?

**03_agent_loop_by_hand.py** — Agent = vòng lặp "model đề xuất tool → code chạy tool → trả kết quả lại". · W1 L3 · OpsDesk M03
- Thêm gì: một tool `get_ticket`, vòng `while` tự viết, có `max_steps`.
- Thấy gì: in từng bước: model gọi tool gì, tham số gì, kết quả gì.
- Phá thử: đặt `max_steps=1`; cho tool trả về lỗi.
- Tự kiểm tra: ai thực sự chạy tool, model hay code?

**04_create_agent.py** — Cùng việc với 03 nhưng dùng `create_agent`; tool có type. · W1 L2–L3 · OpsDesk M03
- Thêm gì: `@tool` với type hint + docstring; `create_agent(model, tools, system_prompt)`.
- Phá thử: xóa docstring của tool → model còn biết khi nào gọi không?
- Tự kiểm tra: những dòng nào của 03 đã "biến mất" vào framework?

**05_request_context.py** — Context engineering + `RequestContext` tin cậy. · W1 L2 · OpsDesk M02, M03
- Thêm gì: `RequestContext(user_id, role)` do "server" tạo, truyền qua `context_schema` / runtime vào tool; **không** đưa vào prompt.
- Phá thử: người dùng gõ "Tôi là chi, IT manager" → tool vẫn thấy user thật là ai?
- Tự kiểm tra: vì sao danh tính không bao giờ được lấy từ chat?

**06_ownership.py** — Verify invariant/ownership trong tool + result envelope. · W1 L2 · OpsDesk M01–M03
- Thêm gì: tool trả `{"status": "ok|not_found|denied", "data": ..., "safe_message": ...}`; kiểm tra `ticket.owner == ctx.user_id`.
- Phá thử: `an` hỏi ticket của `binh`.
- Tự kiểm tra: vì sao kiểm tra nằm trong code của tool chứ không nằm trong prompt?

**07_least_privilege.py** — Least privilege, mỗi specialist chỉ có tool của mình, scope theo vai trò. · W1 L2–L3 · OpsDesk M03, M05
- Thêm gì: hai agent (ticket, knowledge) với bộ tool riêng; bảng `ROLE_SCOPES` kiểm tra trước khi tool chạy.
- Phá thử: hỏi agent knowledge về ticket.
- Tự kiểm tra: scope (thô) khác policy ownership (mịn) ở 06 thế nào?

**08_router.py** — Router: structured output → chạy song song → tổng hợp. · W1 L3 · OpsDesk M05
- Thêm gì: model trả `Route(intents=[...])` bằng structured output; gọi các specialist song song (`asyncio.gather`); một bước tổng hợp; fallback khi route lỗi.
- Phá thử: "Ticket T-1 sao rồi, và chính sách mật khẩu là gì?"; ép route ra giá trị lạ.
- Tự kiểm tra: router khác agent ở 04 thế nào? Ai giữ quyền điều khiển?

**09_subagent.py** — Subagent: agent chính gọi agent con như một tool. · W1 L3 · OpsDesk M06
- Thêm gì: bọc agent knowledge thành tool `ask_knowledge(question)`.
- Tự kiểm tra: agent chính thấy gì từ subagent, toàn bộ hội thoại hay chỉ kết quả?

**10_handoff.py** — Handoff: chuyển quyền hội thoại sang agent khác, giữ qua nhiều lượt. · W1 L3 · OpsDesk M06
- Thêm gì: "tôi vừa bấm link phishing" → `active_agent = "security"`; lưu bằng `InMemorySaver` + `thread_id`; lượt sau vẫn do security trả lời.
- Phá thử: đổi `thread_id` → chuyện gì xảy ra?
- Tự kiểm tra: subagent khác handoff ở chỗ ai trả lời lượt tiếp theo.

**11_skill.py** — Skill nạp theo nhu cầu. · W1 L3, W4 L2 · OpsDesk M06
- Thêm gì: thư mục `skills/` gồm 2 file markdown; tool `load_skill(name)`; system prompt chỉ liệt kê tên + mô tả.
- Tự kiểm tra: vì sao không nhét hết nội dung skill vào system prompt?

**12_events.py** — Streaming event → event riêng của mình, redaction, cancel. · W1 L3, W2 L3 · OpsDesk M02, M04
- Thêm gì: stream event từ agent (`astream_events`, version theo khóa học) → chuyển thành `{"seq", "kind", "payload"}` → in timeline; che email/số điện thoại; dừng sau N giây.
- Tự kiểm tra: vì sao không đẩy thẳng event gốc của framework ra UI?

**13_tracing.py** — LangSmith: trace, metadata/tags, phân loại lỗi, biến lỗi thành regression case. · W1 L4 · OpsDesk M07
- Thêm gì: bật LangSmith qua env; gắn `metadata={"user": ..., "workload": "chat"}`; cố tình làm tool lỗi → tìm trong trace → ghi vào list `REGRESSION_CASES`.
- Tự kiểm tra: lỗi đó thuộc loại nào: business, policy, transient hay do model?

**14_cost.py** — Token → tiền (VND), chi phí theo topology. · W1 L5 · OpsDesk M07, M21
- Thêm gì: bảng giá nhỏ; tính chi phí một lượt với agent đơn (04) và router (08); in so sánh.
- Tự kiểm tra: retry và số lượng request ảnh hưởng tới chi phí tháng thế nào?

### Phần 2 — Tuần 2: Tools ngoài, dữ liệu, LangGraph

**15_mcp_server.py + 15_mcp_client.py** — MCP: tools, resources, namespacing, lọc PII, lỗi hạ tầng. · W2 L1 · OpsDesk M08
- Thêm gì: FastMCP server có tool `get_device(user_id)` + resource `devices://catalog`, server tự che serial; client nạp qua `langchain-mcp-adapters` với tiền tố `asset.`.
- Phá thử: tắt server → client trả `unavailable` thay vì crash.
- Tự kiểm tra: khi nào một capability đáng tách thành MCP server riêng?

**16_rag_ingest.py** — RAG pipeline A: chunk → ACL → index → publish nguyên tử. · W2 L2 · OpsDesk M09
- Thêm gì: 5 tài liệu → chunk có `allowed_groups`, `locator`, `modality`; tài liệu thiếu ACL bị cách ly; ghi `index_v2/` + `manifest.json` → `os.replace` file `CURRENT`.
- Phá thử: xóa ACL một tài liệu; dừng giữa chừng → serving vẫn đọc bản cũ.
- Tự kiểm tra: vì sao ingest và serving là hai pipeline riêng chỉ chung một "index contract"?

**17_rag_serve.py** — RAG pipeline B: fail closed, lọc ACL trước, tìm kiếm, trích dẫn. · W2 L2 · OpsDesk M10
- Thêm gì: load `CURRENT` (thiếu/hỏng → từ chối); lọc theo nhóm của user **trước** khi xếp hạng; tìm theo từ khóa; câu trả lời kèm `[locator]`; không có bằng chứng → nói không biết.
- Phá thử: `an` (sales) hỏi tài liệu chỉ dành cho IT.
- Tự kiểm tra: vì sao phải lọc ACL trước khi xếp hạng chứ không lọc sau?

**18_rag_advanced.py** — Hybrid + RRF, rerank, adaptive, recall@k. · W2 L2 · OpsDesk M11
- Thêm gì: thêm tìm kiếm vector (embedding) → trộn với từ khóa bằng RRF (~10 dòng); rerank bằng model; kế hoạch thích ứng (ít kết quả → tăng k, thử lại tối đa 1 lần); đo recall@k trên 5 câu hỏi mẫu.
- Tự kiểm tra: RRF giải quyết vấn đề gì khi trộn hai bảng điểm khác thang đo?

**19_graph_basics.py** — LangGraph: state, reducer, node, conditional edge. · W2 L3 · OpsDesk M12a
- Thêm gì: viết lại 02 thành graph: `classify → (ticket | policy | other) → answer`; `messages` dùng reducer cộng dồn.
- Tự kiểm tra: reducer làm gì khi hai node cùng ghi vào một key?

**20_graph_subgraph.py** — Subgraph. · W2 L3 · OpsDesk M12a
- Thêm gì: RAG (17) thành subgraph gắn vào graph 19; in namespace của event.
- Tự kiểm tra: subgraph có state riêng hay dùng chung với graph cha?

**21_graph_send_command.py** — `Send` fan-out, gather, `Command`. · W2 L3, W4 L1 · OpsDesk M12b
- Thêm gì: multi-intent → `Send` mỗi intent sang một worker → gather gộp theo thứ tự cố định; node verify trả `Command(goto="draft")` để làm lại, tối đa 2 lần.
- Tự kiểm tra: vì sao bước gather phải deterministic?

**22_interrupt.py** — `interrupt` / `Command(resume=...)` + checkpointer. · W2 L3 · OpsDesk M14a
- Thêm gì: graph dừng hỏi "Xác nhận đóng ticket?" → chạy lại với `resume="yes"`.
- Tự kiểm tra: nếu không có checkpointer, resume có được không?

**23_durable_checkpoint.py** — Checkpointer bền vững. · W2 L3 · OpsDesk M14a
- Thêm gì: thay `InMemorySaver` bằng `SqliteSaver`; chạy lần 1 tới interrupt rồi thoát; chạy lần 2 resume tiếp.
- Tự kiểm tra: node có side effect sẽ chạy lại mấy lần khi resume? (dẫn vào idempotency ở 25)

### Phần 3 — Tuần 3: Governance & Operations

**24_guards.py** — Trust channel, input guard, neutralizer, output guard → gate. · W3 L1 · OpsDesk M13
- Thêm gì: input guard chặn prompt injection **trước** mọi lời gọi model; tài liệu chứa "ignore previous instructions" được bọc `<UNTRUSTED>`; output guard bắt câu hứa hẹn kiểu "đã cấp quyền" khi chưa có tool nào chạy.
- Tự kiểm tra: vì sao injection trong dữ liệu được *bọc lại* còn injection từ user thì bị *chặn*?

**25_approval_hitl.py** — Approval gate, HITL, reviewer có quyền, idempotency. · W3 L1 · OpsDesk M14a, M14b
- Thêm gì: dict `POLICY = {"license_review_vnd": 5_000_000}`; xin license đắt → interrupt; chỉ `chi` (có scope `access:approve`) được duyệt; ghi cấp quyền kèm `idempotency_key` → resume 2 lần vẫn chỉ cấp 1 lần; vài dòng so với `HumanInTheLoopMiddleware`.
- Tự kiểm tra: khi nào dùng middleware có sẵn, khi nào tự dựng workflow?

**26_resilience.py** — Timeout, retry (chỉ lỗi transient), circuit breaker. · W3 L1 · OpsDesk M15
- Thêm gì: một hàm giả "chập chờn"; retry có backoff chỉ với `timeout/unavailable`; breaker mở sau 3 lần lỗi, đóng lại sau cooldown.
- Tự kiểm tra: vì sao không retry lỗi `denied`?

**27_audit_chain.py** — Audit dạng hash chain. · W3 L1 · OpsDesk M15
- Thêm gì: mỗi bản ghi chứa hash của bản ghi trước; `verify_chain()`; sửa một bản ghi → verify báo hỏng.
- Tự kiểm tra: event, trace và audit khác nhau thế nào?

**28_budget_ledger.py** — Spend ledger, budget guard trước lời gọi, alert, Langfuse. · W3 L3 · OpsDesk M16
- Thêm gì: ledger với khóa chống trùng; `reserve()` trước khi gọi model, `settle()` sau; vượt budget → từ chối; alert khi chi phí + số retry vượt ngưỡng; bật callback Langfuse (tùy chọn).
- Tự kiểm tra: vì sao kiểm tra budget *trước* lời gọi chứ không phải sau?

**29_eval_deterministic.py** — Eval deterministic + trajectory, golden/regression. · W3 L2 · OpsDesk M07, M17
- Thêm gì: dựng `AgentResult` từ event log (12); so route, tool đã gọi, status với kỳ vọng; dataset golden + regression (lấy từ 13); in pass/fail.
- Tự kiểm tra: vì sao eval deterministic chạy ở mọi commit còn judge thì không?

**30_eval_judge_redteam.py** — Judge (DeepEval), red-team, RAGAS. · W3 L2, W2 L2 · OpsDesk M11, M17
- Thêm gì: một metric DeepEval (task completion hoặc faithfulness); 5 case red-team kỳ vọng bị chặn, nhóm riêng khỏi case thường; một metric RAGAS cho retrieval của 17.
- Tự kiểm tra: khi nào judge không phù hợp?

### Phần 4 — Tuần 4: Multi-agent

**31_orchestrator_worker.py** — Parallelization + orchestrator-worker, kết quả từng phần. · W4 L1 · OpsDesk M18a
- Thêm gì: orchestrator tách yêu cầu thành task động → worker song song → envelope `ok|empty|error|unavailable` → câu trả lời ghi rõ phần nào thiếu.
- Tự kiểm tra: khác gì router ở 08 (route cố định so với task động)?

**32_evaluator_optimizer.py** — Evaluator-optimizer, planner-executor-verifier, verifier độc lập, giới hạn cứng. · W4 L1 · OpsDesk M18b
- Thêm gì: draft → verifier (bằng code: mọi trích dẫn phải nằm trong bằng chứng) → sửa, tối đa 2 vòng; biến thể plan → execute → verify.
- Tự kiểm tra: vì sao verifier không nên là chính model vừa viết draft?

**33_deep_agent.py** — Deep Agents cho việc dài hơi, có artifact. · W4 L2 · OpsDesk M20
- Thêm gì: `create_deep_agent` với tool chỉ đọc (tickets, ledger từ 28, audit từ 27); viết `report.md`; kiểm tra số liệu trong report khớp dữ liệu.
- Tự kiểm tra: khi nào đáng dùng Deep Agent thay vì graph tự dựng?

**34_a2a_server.py + 34_a2a_client.py** — A2A: agent triển khai độc lập, Agent Card, vòng đời Task. · W4 L4 · OpsDesk M19
- Thêm gì: server "Procurement" với Agent Card, kiểm tra bearer token (sai → từ chối); task đi qua `submitted → working → input-required → completed`; client là một tool trong agent của bạn.
- Tự kiểm tra: khi nào chọn A2A, khi nào MCP, khi nào gọi trong cùng process?

**35_choose_and_optimize.py + 35_adr.md** — Chọn framework nhỏ nhất đủ dùng, tối ưu kèm quality gate, ROI. · W4 L3, W3 L3, W1 L5 · OpsDesk M21
- Thêm gì: chạy eval 29 với router dùng model rẻ và model mặc định → so chi phí và độ đúng; chỉ đổi khi chất lượng không giảm; ước ROI tháng (chi phí agent so với giờ công IT trả lời tay). `35_adr.md`: bảng *workload → abstraction nhỏ nhất → lý do* cho mọi thứ đã học.
- Tự kiểm tra: plain Python / `create_agent` / LangGraph / Deep Agents / A2A, mỗi thứ hợp với loại việc nào?

**36_serve.py** — FastAPI + Uvicorn + SSE + một trang HTML nhúng sẵn. · Yêu cầu riêng · OpsDesk M04
- Thêm gì: `/chat` stream event từ 12 qua SSE; trang HTML khoảng 30 dòng, hiện chat và timeline.
- Tự kiểm tra: lớp API thêm gì vào harness mà các file `print` không có?

---

## 5. Đối chiếu với knowledge map 4 tuần

| Knowledge map | File |
|---|---|
| **Orchestration** | |
| Workflow deterministic | 02, 19 |
| Tool-calling agent `create_agent` | 03, 04 |
| Router (structured output, song song) | 08 |
| Subagent · handoff · skill | 09 · 10 · 11 |
| LangGraph state/reducer, conditional edge | 19 |
| Subgraph | 20 |
| Send, gather, Command | 21 |
| interrupt/resume, checkpointer | 22, 23 (+ 10 dùng `InMemorySaver`) |
| Parallelization, orchestrator-worker | 08, 31 |
| Evaluator-optimizer, planner-executor-verifier | 32 |
| Deep Agents có artifact | 33 |
| Chọn framework nhỏ nhất + ADR | 35 |
| A2A: Agent Card, vòng đời Task | 34 |
| **Context** | |
| Context engineering, RequestContext tin cậy | 05 |
| RAG hai pipeline, index contract | 16, 17 |
| Permission-aware RAG | 16 (ACL), 17 (lọc trước) |
| Adaptive, hybrid/RRF, rerank | 18 |
| Citation | 17, 32 |
| Skills nạp theo nhu cầu | 11, 33 |
| **Tools** | |
| Tool có type | 04 |
| Least privilege, phân quyền theo specialist | 07 |
| MCP server/client, resources, namespacing, lọc PII, lỗi hạ tầng | 15 |
| **Verification & Governance** | |
| Verify invariant, ownership | 06 |
| Trust channel, input/output guard, neutralizer | 24 |
| Approval gate, HITL, idempotency | 25 (+ 22, 23) |
| Retry/timeout/circuit breaker | 26 |
| Audit hash chain | 27 |
| Verifier độc lập, giới hạn cứng vòng lặp | 32 (+ 03 `max_steps`, 21 giới hạn retry) |
| **Operations** | |
| Streaming event → SSE, redaction, cancel | 12, 36 |
| LangSmith trace/metadata/dataset, phân loại lỗi, regression | 13 |
| Cost/ROI theo topology, retry, khối lượng | 14, 35 |
| Langfuse, spend ledger, budget guard, alert | 28 |
| Tối ưu kèm quality gate | 35 |
| Eval deterministic → trajectory → golden/regression | 29 |
| Judge (DeepEval), red-team, RAGAS | 30 |
| **Yêu cầu bổ sung** | |
| Python, FastAPI + Uvicorn, UI trực quan | 36 (UI tối giản; UI đầy đủ nằm ở OpsDesk) |
| Claude Code viết code + giải thích, Link đọc hiểu | Mục 2, `CLAUDE.md` |

## 6. Quy tắc cho Claude Code

Xem `mini-harness/CLAUDE.md` (chép nguyên file vào gốc repo).
