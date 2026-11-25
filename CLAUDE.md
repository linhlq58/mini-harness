# CLAUDE.md — mini-harness

This repo is a **learning aid**, not production code. The learner (Link) is new to Python; the goal is to understand agent-harness concepts at a glance. Roadmap: `roadmap.md`.

**Division of work:** Claude Code writes, runs and explains **all** code. Link only reads and understands. Never ask Link to write, edit or run code himself.

## Workflow per step

Link says e.g. "Làm file 03". Then:

1. **Check versions** of any package the file uses (LangChain, LangGraph, MCP, A2A, DeepEval, RAGAS, Langfuse, deepagents). If the API differs from the course material, add one comment line `# Ghi chú phiên bản: ...`.
2. **Write the file** following the hard rules below.
3. **Run it** and capture the real output.
4. **Run the "Phá thử" experiment(s)** from `roadmap.md` yourself, as a temporary variant (do not leave the original file modified), and capture that output too.
5. **Write the explanation** to `notes/NN_name.md` using the template below, and show the same explanation in the reply.
6. **Commit**: `NN: <concept>` (file + notes together).

## Explanation template (`notes/NN_name.md`, Vietnamese, plain language)

```markdown
# NN — <tên khái niệm>

## 1. Ý chính (2–3 câu)
Khái niệm này là gì, giải quyết vấn đề gì. Một ví dụ đời thường nếu giúp dễ hiểu.

## 2. Mới so với file trước
Liệt kê đúng những dòng/khối mới (trích ngắn, kèm số dòng). Những gì giữ nguyên thì nói "giữ nguyên".

## 3. Đi qua code theo thứ tự chạy
Bước 1 → 2 → 3 ..., mỗi bước trích đoạn code liên quan (vài dòng) + giải thích nó làm gì và VÌ SAO cần nó.
Chỉ giải thích cú pháp Python khi cú pháp đó che mất ý (ví dụ `async`, decorator) — một câu là đủ.

## 4. Kết quả khi chạy
Output thật, kèm chú thích dòng nào tương ứng với bước nào ở mục 3.

## 5. Phá thử
Đã đổi gì → output thật → điều đó chứng minh gì về khái niệm.

## 6. Tự kiểm tra
Câu hỏi trong roadmap, kèm đáp án trong khối <details> để Link tự nghĩ trước rồi mở ra xem.

## 7. Nối sang OpsDesk
Cái lõi này nằm ở đâu trong OpsDesk (milestone, thư mục/file), và OpsDesk bọc thêm gì quanh nó cho production — vì sao.
```

## Hard rules for code
1. **One file = one concept**, numbered per `roadmap.md`, runnable on its own: `uv run python NN_name.py`.
2. **Under ~100 lines per file.** If it grows past that, the file holds two concepts. Stop and say so.
3. **No imports between numbered files.** The only shared module is `common.py` (model factory + tiny seed data, ~40 lines max). Duplicated code between files is intentional.
4. **Each file adds as little as possible over the previous one.** Keep names and structure identical where the concept doesn't change, so a side-by-side diff shows only the new idea.
5. **Start every file with the 3-line header:**
   ```python
   # Khái niệm: ...
   # Layer: ...
   # Khóa học: W? L?  ·  OpsDesk: M??
   ```
6. **Comments in simple Vietnamese**, only on lines that carry the concept. No docstrings except on `@tool` functions (where the model reads them).
7. **No production machinery**: no layers/packages, no import-linter, no abstract base classes, no dependency injection, no config files (use a dict at the top of the file), no database unless the concept itself needs it (e.g. file 23).
8. **Visible output**: `print` each meaningful step (tool calls, routes, events, verdicts) so running the file explains itself.
9. **Plain Python first.** If the concept can be shown without a framework, do that. Use the framework only when the file is about the framework.
10. Add packages to `pyproject.toml` only when a file needs them (latest versions that install together).
11. If Link asks a follow-up question about a file, answer it and append the Q&A to the end of that file's `notes/NN_name.md` under `## Hỏi thêm`.
