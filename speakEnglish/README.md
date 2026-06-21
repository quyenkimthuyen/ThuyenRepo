# PronounceLab Personal

Ứng dụng web **single-user** luyện phát âm tiếng Anh (1000 từ) — chạy hoàn toàn **local**, không cần đăng ký, không gửi audio lên cloud.

## Tính năng

- **Micro live (real-time):** bật micro liên tục, nhận dạng giọng nói theo thời gian thực (Web Speech API), hiển thị text đang đọc ngay khi có âm thanh
- Hiển thị từ + IPA + phoneme boxes
- Phát mẫu (TTS trình duyệt hoặc file audio)
- Ghi âm qua WebAudio API → gửi tới FastAPI local
- Đánh giá từng phoneme: **xanh** (ok), **vàng** (warn), **đỏ** (mis), **xám** (chưa chấm)
- Gợi ý cải thiện bằng tiếng Việt
- Replay từng đoạn phoneme theo timestamp
- Tự chuyển từ tiếp theo khi đạt ngưỡng
- Lưu lịch sử luyện tập trong `localStorage`

## Cấu trúc repository

```
speakEnglish/
├── README.md
├── TEST_PLAN.md
├── frontend/
│   ├── index.html          # Giao diện chính
│   ├── app.js              # Logic frontend (ES6 modules)
│   ├── styles.css          # UI responsive dark theme
│   ├── config.json         # API URL, thresholds
│   └── data/
│       └── words.json      # 20 từ demo (mở rộng tới 1000)
└── backend/
    ├── main.py             # FastAPI entry point
    ├── config.py           # Cấu hình aligner, scorer, thresholds
    ├── requirements.txt
    ├── api/
    │   └── evaluate.py     # POST /api/v1/evaluate
    ├── services/
    │   ├── audio_processor.py   # Resample 16kHz mono (ffmpeg)
    │   ├── aligner.py           # MFA / Gentle / fallback
    │   ├── scorer.py            # GOP / wav2vec2 / fallback
    │   ├── phoneme_utils.py     # IPA, labels, gợi ý tiếng Việt
    │   └── evaluator.py         # Pipeline orchestrator
    ├── scripts/
    │   └── setup_aligner.sh     # Hướng dẫn cài Gentle/MFA
    └── tmp/uploads/             # Audio tạm (tự tạo khi chạy)
```

## Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|------------|---------------------|
| Python | 3.10+ |
| ffmpeg | Bất kỳ bản gần đây |
| Trình duyệt | Chrome / Firefox / Edge (hỗ trợ MediaRecorder) |
| (Tùy chọn) Docker | Cho Gentle aligner |
| (Tùy chọn) Conda | Cho Montreal Forced Aligner |

## Cài đặt — Linux / macOS

### 1. Cài ffmpeg

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 2. Backend Python

```bash
cd speakEnglish/backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Chạy backend

```bash
cd speakEnglish/backend
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Kiểm tra: mở http://127.0.0.1:8000/api/v1/health

### 4. Chạy frontend

**Cách 1 — Live Server (khuyến nghị):**

```bash
# VS Code: "Live Server" extension → Open with Live Server
# Hoặc Python:
cd speakEnglish/frontend
python3 -m http.server 5500
```

Mở http://localhost:5500

**Cách 2 — Mở file trực tiếp:**

Mở `frontend/index.html` trong trình duyệt (một số tính năng fetch có thể bị hạn chế do CORS).

## Cài đặt — Windows

1. Cài [Python 3.10+](https://www.python.org/downloads/) — tick "Add to PATH"
2. Cài [ffmpeg](https://ffmpeg.org/download.html) — thêm vào PATH
3. Mở PowerShell:

```powershell
cd speakEnglish\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

4. Mở terminal khác:

```powershell
cd speakEnglish\frontend
python -m http.server 5500
```

5. Truy cập http://localhost:5500

## Cấu hình

### Biến môi trường (backend)

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `ALIGNMENT_METHOD` | `fallback` | `fallback` \| `gentle` \| `mfa` |
| `SCORING_METHOD` | `fallback` | `fallback` \| `gop` \| `wav2vec2` |
| `THRESHOLD_OK` | `0.75` | Ngưỡng label "ok" |
| `THRESHOLD_WARN` | `0.50` | Ngưỡng label "warn" |
| `OVERALL_PASS_SCORE` | `80` | Điểm tổng tối thiểu để đạt |
| `GENTLE_URL` | `http://localhost:8765` | URL Gentle service |

Ví dụ:

```bash
export ALIGNMENT_METHOD=gentle
export SCORING_METHOD=fallback
uvicorn main:app --port 8000
```

### Frontend (`config.json` / Settings UI)

- `apiBaseUrl`: URL backend
- `thresholds.overallPass`: ngưỡng đạt (%)
- `autoPlaySample`: tự phát mẫu khi mở từ

### Cài Gentle (tùy chọn, chính xác hơn)

```bash
docker run -d --name gentle -p 8765:8765 lowerquality/gentle
export ALIGNMENT_METHOD=gentle
```

Xem thêm: `backend/scripts/setup_aligner.sh gentle`

### Cài MFA (tùy chọn, nâng cao)

```bash
conda create -n mfa -c conda-forge montreal-forced-aligner
conda activate mfa
mfa model download acoustic english_us_arpa
mfa model download dictionary english_us_arpa
export ALIGNMENT_METHOD=mfa
```

Xem thêm: `backend/scripts/setup_aligner.sh mfa`

## API

### `POST /api/v1/evaluate`

**Request** (`multipart/form-data`):

| Field | Type | Mô tả |
|-------|------|-------|
| `file` | audio/webm, wav | Audio ghi âm |
| `target_word` | string | Từ mục tiêu |
| `target_ipa` | string | IPA |
| `target_phonemes` | JSON array | `["s","t","eɪ",...]` |

**Response** (200):

```json
{
  "word": "station",
  "ipa": "/ˈsteɪʃən/",
  "overall_score": 85,
  "passed": true,
  "phonemes": [
    {"ipa":"s","start":0.02,"end":0.08,"score":0.92,"label":"ok","suggestion":""},
    {"ipa":"t","start":0.08,"end":0.12,"score":0.45,"label":"mis","suggestion":"thiếu voicing hoặc vị trí lưỡi sai — thử lại chậm hơn"}
  ],
  "audio_url": "/api/v1/audio/abc123.webm"
}
```

### `GET /api/v1/health`

Trả về trạng thái service và phương thức align/score đang dùng.

### `DELETE /api/v1/audio/cleanup`

Xóa tất cả file audio tạm trong `tmp/uploads/`.

## Thêm từ mới (mở rộng lên 1000)

Chỉnh `frontend/data/words.json`, thêm mục theo schema:

```json
{
  "word": "example",
  "ipa": "/ɪɡˈzæmpəl/",
  "phonemes": ["ɪ", "ɡ", "z", "æ", "m", "p", "ə", "l"],
  "audio_sample_url": ""
}
```

- `phonemes`: danh sách IPA từng âm vị (bắt buộc cho alignment chính xác)
- `audio_sample_url`: URL file mẫu (để trống = dùng TTS trình duyệt)

## Tiêu chí chấm điểm

| Score | Label | Màu UI |
|-------|-------|--------|
| ≥ 0.75 | `ok` | Xanh |
| 0.50 – 0.74 | `warn` | Vàng |
| < 0.50 | `mis` | Đỏ |

**Đạt từ:** tất cả phoneme `ok` **HOẶC** `overall_score ≥ 80` (cấu hình được).

## Quyền riêng tư

- Audio chỉ lưu trong `backend/tmp/uploads/` trên máy local
- Không gửi dữ liệu ra cloud
- Xóa file tạm: `curl -X DELETE http://127.0.0.1:8000/api/v1/audio/cleanup`

## Luồng demo end-to-end

1. Chạy backend + frontend
2. Mở app → chọn từ "hello"
3. Nhấn **Nghe mẫu** (TTS)
4. Nhấn **Ghi âm** → nói "hello" → **Dừng**
5. Trong ≤ 5 giây: phoneme boxes hiện màu + % confidence
6. Click ô phoneme → replay đoạn audio tương ứng
7. Nếu đạt → tự chuyển từ tiếp theo

### Chế độ micro live

1. Nhấn **Bật micro live** (hoặc tự bật nếu bật setting)
2. **Nói từ mục tiêu** — text hiện ra ngay; nếu sai từ sẽ có chú thích đỏ ngay lập tức
3. **Im lặng ~2 giây** sau khi nói → app tự gọi API chấm phoneme
4. **Đúng** → tự chuyển từ tiếp theo; **Sai** → hiện gợi ý từng phoneme, đọc lại cùng từ

## Ghi chú triển khai

- **Chế độ mặc định (`fallback`)**: alignment theo tỷ lệ thời gian + scoring MFCC — chạy ngay không cần cài model nặng, phù hợp demo.
- **Gentle/MFA**: cài thủ công theo `setup_aligner.sh` để tăng độ chính xác alignment.
- **wav2vec2**: bỏ comment trong `requirements.txt`, set `SCORING_METHOD=wav2vec2` (cần ~400MB download model lần đầu).
- **whisper.cpp WASM**: có thể tích hợp riêng cho transcript-only (không dùng cho phoneme scoring trong phiên bản này).

## License

MIT — sử dụng tự do cho mục đích cá nhân.
