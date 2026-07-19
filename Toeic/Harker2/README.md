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

## Parse lại dữ liệu

Khi cập nhật PDF:

```bash
python3 scripts/parse_data.py
```

## Ghi chú

- Bản dịch tiếng Việt sẽ được bổ sung trong phiên bản tiếp theo
- Một số ảnh Part 1 có thể chưa đầy đủ (đang cập nhật từ PDF)
- Reading section sẽ được thêm sau
