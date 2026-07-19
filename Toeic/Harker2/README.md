# Harker TOEIC Listening App

Ứng dụng luyện nghe TOEIC thuần frontend, dựa trên sách **Hacker TOEIC 1000 Vol.2 Listening**.

## Tính năng

- **10 đề thi** (Test 01 – 10) với audio MP3
- **Chế độ Thi**: bộ đếm giờ 45 phút, chọn đáp án, nộp bài & xem điểm
- **Chế độ Học**: transcript, đáp án, giải thích accent/phát âm
- **4 Parts**: Part 1 (ảnh), Part 2 (hỏi–đáp), Part 3 & 4 (hội thoại/bài nói)

## Chạy app

```bash
cd Harker2
python3 -m http.server 8080
```

Mở trình duyệt: http://localhost:8080

## Cấu trúc

```
Harker2/
├── index.html          # Giao diện chính
├── css/app.css         # Styles
├── js/app.js           # Logic ứng dụng
├── public/
│   ├── data/           # JSON đề thi (test01.json – test10.json)
│   ├── images/         # Ảnh Part 1
│   └── audio/          # Symlink tới file MP3
├── data/               # Dữ liệu gốc (PDF + MP3)
└── scripts/
    └── parse_data.py   # Script parse PDF → JSON
```

## Reading (RC)

Dữ liệu từ `data/HACKER Vol 2 RC/`:
- `HACKER 2 READING.pdf` — đề thi
- `KEY RC HACKER 2/TEST *.png` — đáp án

```bash
python3 scripts/parse_reading.py
```

Output: `public/data/reading/test01.json` – `test10.json`

## Parse lại dữ liệu Listening

```bash
# Parse PDF + ảnh (không dịch)
python3 scripts/parse_data.py --skip-translate

# Dịch tiếng Việt (có cache, chạy từng test)
python3 scripts/translate.py 1   # test 01
python3 scripts/translate.py     # tất cả tests
```

## Ghi chú

- Bản dịch tiếng Việt được tạo tự động qua Google Translate (có cache tại `public/data/translation_cache.json`)
- Part 1: mỗi trang PDF chứa 2 ảnh, được crop tự động loại bỏ sidebar tiếng Hàn
- Reading section sẽ được thêm sau
