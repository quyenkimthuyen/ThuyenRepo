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

## Chủ đề bài luyện

| Chủ đề | Nội dung |
|--------|----------|
| **Đời sống** | Thói quen, gia đình, mua sắm… |
| **Du lịch** | Khách sạn, sân bay, văn hóa, du lịch bền vững… |
| **Công việc** | Văn phòng, phỏng vấn, làm việc từ xa, lãnh đạo… |
| **Học tập** | Học tiếng Anh, giáo dục… |
| **IELTS Speaking** | Part 1/2/3 — giới thiệu, quê hương, công nghệ… |
| **Sức khỏe** | Thói quen lành mạnh, thần kinh học… |
| **Công nghệ** | AI, không gian… |
| **Xã hội** | Môi trường, mạng xã hội, đô thị hóa… |

Lọc theo **Chủ đề** và **Cấp độ** trên màn hình chính.

## Import bài của bạn

Mở **Import bài của tôi** trên màn hình chính.

### Văn bản (mỗi dòng một câu)

1. Nhập tiêu đề, chọn cấp độ / chủ đề
2. Dán các câu tiếng Anh (mỗi dòng một câu)
3. Bấm **Lưu bài**

### File `.txt` hoặc `.json`

- **`.txt`** — mỗi dòng một câu; tiêu đề lấy từ tên file
- **`.json`** — một bài hoặc nhiều bài:

```json
{
  "title": "My practice",
  "level": "b1",
  "topic": "ielts",
  "sentences": [
    "I would like to talk about my hometown.",
    "It is a small city in the north of the country."
  ]
}
```

Nhiều bài:

```json
{
  "lessons": [
    { "title": "Lesson A", "sentences": ["..."] },
    { "title": "Lesson B", "sentences": ["..."] }
  ]
}
```

Bài import nằm trong nhóm **Bài của tôi**, lưu tại `localStorage` trên trình duyệt. Có thể **Mở** / **Xóa** trong danh sách hoặc nút **Xóa bài này** khi đang luyện.

## Tính năng bổ sung

- **Đọc mẫu (TTS):** nút *Đọc mẫu* hoặc tự đọc khi bật *Tự đọc mẫu khi sang câu mới*
- **Khớp số:** mic nghe `20` vẫn khớp từ `twenty` (và ngược lại)
- **Qua câu:** nút *Câu trước* / *Câu sau* để chuyển giữa các câu mà không cần đọc xong

## Công nghệ

- **Web Speech API** (`SpeechRecognition`) — nhận giọng real-time, `continuous` + `interimResults`
- **Web Speech API** (`speechSynthesis`) — đọc mẫu
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
  "level": "a2",
  "topic": "ielts",
  "title": "Morning routine",
  "sentences": [
    "I wake up at six o'clock.",
    "I brush my teeth every morning."
  ]
}
```

Cấp độ: `a1` | `a2` | `b1` | `b2` | `c1`  
Chủ đề: `daily` | `travel` | `work` | `study` | `ielts` | `health` | `tech` | `society`
