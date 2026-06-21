# Test Plan — PronounceLab Personal

5 test cases end-to-end với expected outputs.

## Tiền đề

- Backend chạy: `uvicorn main:app --host 127.0.0.1 --port 8000`
- Frontend chạy: `python -m http.server 5500` trong `frontend/`
- Microphone hoạt động
- `ffmpeg` đã cài

---

## TC-01: Phát âm đúng (correct pronunciation)

| Mục | Chi tiết |
|-----|----------|
| **Input** | Từ: `hello` — ghi âm phát âm chuẩn "hello" |
| **Steps** | 1. Chọn "hello" 2. Ghi âm 3. Dừng |
| **Expected** | - HTTP 200 từ `/api/v1/evaluate` |
| | - `overall_score` ≥ 70 |
| | - Phần lớn phonemes có `label` = `ok` hoặc `warn` |
| | - `passed` = `true` (nếu đủ ngưỡng) |
| | - UI: ô phoneme xanh/vàng, tự chuyển từ sau ~1.5s |
| | - `localStorage` ghi nhận +1 attempt |

---

## TC-02: Lỗi nguyên âm (vowel error)

| Mục | Chi tiết |
|-----|----------|
| **Input** | Từ: `think` (/θɪŋk/) — cố tình phát âm "thenk" (thay ɪ → e) |
| **Steps** | 1. Chọn "think" 2. Ghi âm phát âm sai nguyên âm 3. Dừng |
| **Expected** | - Phoneme `ɪ` có `label` = `mis` hoặc `warn` |
| | - `suggestion` không rỗng (gợi ý tiếng Việt về vowel) |
| | - `passed` = `false` |
| | - UI: ít nhất 1 ô đỏ/vàng, nút "Thử lại" hiện |
| | - Không tự chuyển từ |

---

## TC-03: Lỗi phụ âm (consonant error)

| Mục | Chi tiết |
|-----|----------|
| **Input** | Từ: `three` (/θriː/) — phát âm "free" (thay θ → f) |
| **Steps** | 1. Chọn "three" 2. Ghi âm 3. Dừng |
| **Expected** | - Phoneme `θ` có `label` = `mis` |
| | - `suggestion` chứa gợi ý về đặt lưỡi giữa răng |
| | - `overall_score` < 80 |
| | - UI: ô `θ` màu đỏ, feedback list hiển thị gợi ý |

---

## TC-04: Nói thừa từ (extra word)

| Mục | Chi tiết |
|-----|----------|
| **Input** | Từ: `water` — nói "the water please" |
| **Steps** | 1. Chọn "water" 2. Ghi âm câu dài 3. Dừng |
| **Expected** | - HTTP 200 (không crash) |
| | - Alignment fallback chia theo tỷ lệ thời gian |
| | - Một số phonemes có score thấp hơn bình thường |
| | - `passed` có thể `false` do timing/energy lệch |
| | - App không crash, hiển thị phoneme boxes |

---

## TC-05: Audio nhiễu (noisy audio)

| Mục | Chi tiết |
|-----|----------|
| **Input** | Từ: `school` — ghi âm trong môi trường ồn hoặc nói rất nhỏ |
| **Steps** | 1. Chọn "school" 2. Ghi âm với tiếng ồn nền 3. Dừng |
| **Expected** | - HTTP 200 |
| | - `overall_score` thấp hơn TC-01 (< 60 thường gặp) |
| | - Nhiều phonemes `warn` hoặc `mis` |
| | - `passed` = `false` |
| | - Spinner biến mất trong ≤ 5s |
| | - Replay segment vẫn hoạt động (click ô phoneme) |

---

## API unit tests (curl)

### Health check

```bash
curl http://127.0.0.1:8000/api/v1/health
# Expected: {"status":"ok","alignment_method":"fallback","scoring_method":"fallback"}
```

### Evaluate với file WAV

```bash
# Tạo file test 1 giây (cần ffmpeg)
ffmpeg -f lavfi -i "sine=frequency=440:duration=1" -ar 16000 test.wav -y

curl -X POST http://127.0.0.1:8000/api/v1/evaluate \
  -F "file=@test.wav" \
  -F "target_word=hello" \
  -F "target_ipa=/həˈloʊ/" \
  -F 'target_phonemes=["h","ə","l","oʊ"]'
# Expected: JSON với 4 phonemes, overall_score 0-100
```

### Error: file quá ngắn

```bash
echo "x" > tiny.webm
curl -X POST http://127.0.0.1:8000/api/v1/evaluate \
  -F "file=@tiny.webm" \
  -F "target_word=hello"
# Expected: HTTP 400, {"detail":{"error":"Audio file too short"}}
```

### Error: thiếu target_word

```bash
curl -X POST http://127.0.0.1:8000/api/v1/evaluate \
  -F "file=@test.wav" \
  -F "target_word="
# Expected: HTTP 400
```

---

## Acceptance criteria checklist

- [ ] Mở index.html → chọn word → play sample → record → stop
- [ ] Trong ≤ 5s hiện phoneme boxes có màu và suggestion
- [ ] Replay segment hoạt động (click ô phoneme)
- [ ] Tất cả chạy local, không gọi cloud API
- [ ] Lịch sử lưu trong localStorage
- [ ] Đạt ngưỡng → tự chuyển từ tiếp theo
