# Reading Aloud — Luyện đọc tiếng Anh (thuần frontend)

App luyện **speaking** bằng cách **đọc to** đoạn văn tiếng Anh. Micro nhận diện giọng nói real-time, **tích lũy dần** các từ đọc đúng trong câu hiện tại; khi đủ từ thì pass sang câu tiếp theo.

## Mục tiêu

- Người dùng đọc to từng câu tiếng Anh.
- App so khớp text từ microphone với từ trong câu (không chấm phát âm chi tiết).
- Từ đọc đúng → đổi màu. Câu hoàn thành → đổi màu → tự chuyển câu kế.

## Luồng sử dụng

```
Bật mic → hiện câu 1 (các từ chưa khớp)
     ↓
Đọc to → nhận từ real-time → từ khớp được tích lũy → đổi màu
     ↓
Đủ tất cả từ trong câu → câu hoàn thành → sang câu 2
     ↓
Hết bài → thông báo hoàn thành
```

## Khớp từ — tích lũy dần

| Quy tắc | Mô tả |
|--------|--------|
| Chỉ khớp câu hiện tại | So với các từ **chưa khớp** của câu đang luyện |
| Tích lũy dần | Mỗi từ đúng được cộng dồn; không cần đọc đúng thứ tự |
| Mỗi ô từ khớp một lần | Từ đã xanh không khớp lại |
| Linh hoạt với ASR | Từ thừa/sai bỏ qua; lặp từ không ảnh hưởng nếu ô đó đã khớp |
| Chuẩn hóa | lower case, bỏ dấu câu đầu/cuối trước khi so |

## Công nghệ

- **Web Speech API** (`SpeechRecognition`) — nhận giọng real-time, `continuous` + `interimResults`
- **Vanilla HTML/CSS/JS** — không framework, không backend
- **localStorage** — lưu tiến độ bài đang làm

## Yêu cầu trình duyệt

- Chrome hoặc Edge (khuyến nghị)
- Quyền microphone
- Kết nối internet (Chrome gửi audio cho dịch vụ nhận dạng)

## Chạy app

Mở qua HTTP (microphone thường không hoạt động với `file://`):

```bash
cd Reading
python3 -m http.server 8080
```

Truy cập: http://localhost:8080

## Cấu trúc

```
Reading/
├── index.html      # Giao diện
├── css/style.css   # Style
├── js/
│   ├── app.js      # UI + speech + state
│   ├── matcher.js  # Logic khớp từ
│   └── lessons.js  # Dữ liệu bài mẫu
└── README.md       # Tài liệu này
```

## Định dạng bài (mở rộng)

```json
{
  "id": "lesson-01",
  "title": "Morning routine",
  "sentences": [
    "I wake up at six o'clock.",
    "I brush my teeth every morning."
  ]
}
```
