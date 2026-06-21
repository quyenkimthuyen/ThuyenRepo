# Test Plan — PronounceLab Personal

## Automated tests (chạy trước mỗi release)

```bash
chmod +x scripts/run_tests.sh
./scripts/run_tests.sh
```

Hoặc từng phần:

```bash
# Backend
cd backend && .venv/bin/pytest tests/ -v

# Frontend
cd frontend && node --test tests/*.test.mjs
```

### Phạm vi automated

| Suite | File | Kiểm tra |
|-------|------|----------|
| API | `backend/tests/test_api.py` | health, evaluate OK/lỗi, cleanup |
| Performance | `backend/tests/test_performance.py` | API < 5s, health < 200ms |
| Phoneme utils | `backend/tests/test_phoneme_utils.py` | label, gợi ý, parse IPA |
| Core logic | `frontend/tests/core.test.mjs` | wordsMatch, timing, VAD RMS |
| Data | `frontend/tests/words.data.test.mjs` | schema words.json |

### Ngưỡng hiệu năng (automated)

| Metric | Ngưỡng |
|--------|--------|
| `GET /health` | < 200 ms |
| `POST /evaluate` (1 từ) | < 5000 ms |
| Fast-path text (logic) | ≤ 800 ms |
| Fast-path score (logic) | ≤ 3500 ms |
| Im lặng mặc định | 500 ms |

---

## Manual E2E (micro + trình duyệt)

### Tiền đề

- Backend: `./run_backend.sh`
- Frontend: `cd frontend && python3 -m http.server 5500`
- Chrome/Edge + microphone + `ffmpeg`

---

## TC-01: Chế độ Chỉ text — phản hồi nhanh

| Mục | Chi tiết |
|-----|----------|
| **Steps** | 1. Chọn **Chỉ text** 2. Chạm màn hình → micro xanh 3. Đọc đúng từ hiển thị |
| **Expected** | - Text hiện < 1s - Vàng xử lý < 0.5s sau khi khớp - Qua từ tiếp theo < 1s tổng |
| **Pass** | Tổng thời gian đọc xong → từ mới ≤ **1.5 giây** |

---

## TC-02: Chế độ Chấm điểm — API + phoneme

| Mục | Chi tiết |
|-----|----------|
| **Steps** | 1. Chạy backend 2. Chọn **Chấm điểm** 3. Đọc từ → im lặng 0.5s |
| **Expected** | - Micro vàng "Đang chấm điểm" - Phoneme boxes có màu trong **≤ 5s** - Footer: Backend online |
| **Pass** | Không hiện lỗi đỏ backend |

---

## TC-03: Micro reset sau 3s không âm thanh

| Mục | Chi tiết |
|-----|----------|
| **Steps** | 1. Bật micro 2. Không nói 3+ giây |
| **Expected** | - Micro vẫn xanh "Sẵn sàng thu âm" - Nói lại → vẫn nhận âm thanh |

---

## TC-04: TTS không bị thu nhầm

| Mục | Chi tiết |
|-----|----------|
| **Steps** | 1. Bật micro 2. Chuyển từ (tự phát mẫu) |
| **Expected** | - Trạng thái "Đang phát mẫu" - Không tự qua từ vì tiếng loa |

---

## TC-05: Phát âm sai — gợi ý

| Mục | Chi tiết |
|-----|----------|
| **Input** | Từ `think` — đọc sai vowel |
| **Expected** | Chế độ score: ô đỏ + gợi ý tiếng Việt, không qua từ |

---

## TC-06: Lỗi API

| Mục | Chi tiết |
|-----|----------|
| **Steps** | Tắt backend → chế độ Chấm điểm → đọc từ |
| **Expected** | Message lỗi rõ, micro về xanh sau lỗi |

---

## Checklist acceptance

- [ ] `./scripts/run_tests.sh` — ALL PASSED
- [ ] Chỉ text: đọc đúng → qua từ < 1.5s
- [ ] Chấm điểm: phoneme boxes < 5s
- [ ] Micro xanh/vàng/đỏ đúng trạng thái
- [ ] Reset micro sau 3s im lặng
- [ ] Không thu nhầm TTS
