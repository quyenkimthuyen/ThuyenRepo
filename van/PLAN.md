# Kế hoạch phát triển — App Ôn Văn vào 10

Mục tiêu: App ôn luyện cá nhân, AI chấm điểm qua **Cursor API** (`CURSOR_API_KEY`).

---

## Cấu trúc thư mục mục tiêu

```
van/
├── PLAN.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                 # FastAPI entry
│   ├── config.py               # Cấu hình từ .env
│   ├── models/schemas.py       # Pydantic request/response
│   ├── graders/
│   │   ├── rules.py            # Rule: đếm từ, hình thức
│   │   ├── cursor_client.py    # Gọi Cursor SDK
│   │   ├── paragraph.py        # Chấm đoạn 200 chữ
│   │   ├── reading.py          # Chấm đọc hiểu
│   │   └── essay.py            # Chấm NL xã hội
│   ├── rubrics/                # Biểu điểm JSON
│   ├── exams/                  # Đề mẫu JSON
│   ├── db/history.py           # SQLite lưu lịch sử
│   └── api/routes.py           # Tất cả endpoints
├── static/
│   ├── index.html
│   ├── css/app.css
│   └── js/app.js
└── data/                       # SQLite DB (tự tạo)
```

---

## Các phase

| Phase | Nội dung | Trạng thái |
|-------|----------|------------|
| **0** | Prototype đoạn 200 chữ | ✅ Xong |
| **1** | Tái cấu trúc code + config + schemas | ✅ Xong |
| **2** | Rubric + grader: đọc hiểu, NL xã hội | ✅ Xong |
| **3** | API đầy đủ + lưu lịch sử SQLite | ✅ Xong |
| **4** | UI đa tab + đề mẫu | ✅ Xong |
| **5** | Chế độ thi thử 120 phút | ✅ Cơ bản (timer + chấm từng phần) |
| **6** | Thống kê tiến bộ theo dạng bài | ✅ Cơ bản (tab Lịch sử) |

---

## Chi tiết từng phase

### Phase 1 — Nền tảng
- [x] `config.py` — đọc `CURSOR_API_KEY`, `CURSOR_MODEL`
- [x] `schemas.py` — model request/response thống nhất
- [x] `cursor_client.py` — tách logic gọi API
- [x] `api/routes.py` — gom endpoints

### Phase 2 — Chấm đủ 3 dạng bài
- [x] Đoạn văn ~200 chữ (2đ)
- [x] Đọc hiểu (nhiều câu, tổng 1–3đ/câu)
- [x] Nghị luận xã hội (4đ)

### Phase 3 — Lịch sử
- [x] SQLite: lưu bài, điểm, loại bài, thời gian
- [x] API `GET /api/history`, `GET /api/stats`

### Phase 4 — Giao diện
- [x] Tab: Đoạn văn | Đọc hiểu | NL xã hội | Thi thử
- [x] Load đề mẫu từ `exams/`
- [x] Hiển thị kết quả thống nhất

### Phase 5 — Thi thử
- [x] Đề 10 điểm (2 phần, 120 phút)
- [x] Đồng hồ đếm ngược
- [x] Chấm tuần tự từng phần (tiết kiệm API)

### Phase 6 — Thống kê
- [x] Điểm trung bình theo dạng (tab Lịch sử)
- [x] Biểu đồ tiến bộ theo dạng bài (tab Tiến độ)

---

## Quy ước kỹ thuật

1. **Rule trước, AI sau** — hình thức (đếm từ, xuống dòng) không gọi API.
2. **`Agent.prompt()` one-shot** — mỗi lần chấm một prompt, trả JSON.
3. **Chấm chặt** — prompt luôn ghi “như thi thật”.
4. **Không viết hộ** — chỉ `next_steps`, không full bài mẫu.

---

## Chạy app

```bash
cp .env.example .env   # điền CURSOR_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Mở: http://127.0.0.1:8000
