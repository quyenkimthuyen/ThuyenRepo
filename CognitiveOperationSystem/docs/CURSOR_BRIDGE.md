# Cursor Bridge — Mode AI trực tiếp

Mode **Suy ngẫm với Cursor** chat trong app qua Cursor SDK. Trình duyệt chỉ gọi `localhost`; API key nằm trên server Node cục bộ.

---

## Các mode khác có cần server không?

**Không.** Nếu bạn **không** chạy `server/cursor-bridge`, app vẫn dùng bình thường:

| Mode | Cần bridge? | Ghi chú |
|------|-------------|---------|
| **Suy ngẫm trong app** | Không | Rule engine, offline |
| **Suy ngẫm với ChatGPT** | Không | Copy prompt / dán JSON thủ công |
| **Suy ngẫm với Cursor** | **Có** | Chỉ khi bấm card này |
| Bản đồ, Khám phá, Timeline, Thử nghiệm | Không | Không gọi bridge |

Bridge **không chạy nền** khi mở app. Chỉ khi bấm **Suy ngẫm với Cursor** app mới `fetch` tới `http://127.0.0.1:3847/health`. Nếu server tắt → hộp thoại hướng dẫn; các mode khác không bị ảnh hưởng.

---

## Yêu cầu (chỉ mode Cursor)

- Node.js 20+
- [Cursor API key](https://cursor.com/docs) — biến môi trường `CURSOR_API_KEY`
- App mở qua **http://localhost** (Live Server, `npx serve`, v.v.) — tránh `file://` vì CORS

---

## API key (`server/key.txt`)

Bridge đọc key theo thứ tự:

1. Biến môi trường `CURSOR_API_KEY`
2. File `CURSOR_KEY_FILE` (nếu set)
3. `server/key.txt` (cùng thư mục bridge)
4. `/home/toc/thuyen/repo/CognitiveOperationSystem/server/key.txt` (fallback)

Ví dụ:

```bash
# Tạo symlink nếu key nằm ở repo khác
ln -sf /home/toc/thuyen/repo/CognitiveOperationSystem/server/key.txt server/key.txt
```

**Không commit** file key — thêm vào `.gitignore`.

---

## Test

### Mock (không cần bridge, chạy mọi lúc)

```bash
node scripts/run-cursor-direct-tests.js
```

3 kịch bản: regression niềm tin giả, hallucination quarantine, JSON thưa.

### Live (bridge + API key thật)

```bash
node scripts/run-cursor-direct-tests.js --live
```

Script tự start bridge nếu chưa chạy, đọc key từ `server/key.txt` hoặc đường dẫn repo ở trên.

### Trong app

Màn **Thử nghiệm** → mục **Cursor trực tiếp** → Chạy test (mock).

---

## Cài đặt bridge (một lần)

```bash
cd server
npm install --registry https://registry.npmjs.org
```

Nếu registry mặc định đã trỏ npmjs, có thể bỏ `--registry`.

---

## Chạy mode Cursor — từng bước

### Bước 1 — Mở app (terminal hoặc VS Code)

Ví dụ Live Server trên `http://127.0.0.1:5500` (port tùy cấu hình).

App chạy được ngay; chưa cần bridge nếu chỉ dùng mode trong app / ChatGPT.

### Bước 2 — Chạy Cursor bridge (terminal riêng)

```bash
cd server
export CURSOR_API_KEY="your_cursor_api_key_here"
npm start
```

Khi thành công, terminal in:

```text
Cursor bridge listening on http://127.0.0.1:3847
```

Kiểm tra nhanh (terminal khác):

```bash
curl http://127.0.0.1:3847/health
```

Kỳ vọng: `"ok": true`, `"hasApiKey": true`, `"sdkReady": true`.

### Bước 3 — Trong app

1. Trang chủ → viết suy nghĩ ban đầu.
2. Bấm **Suy ngẫm với Cursor**.
3. Chat từng lượt (EEIBVIA do Cursor dẫn).
4. Bấm **Hoàn tất & lưu vào bản đồ** → JSON import vào bản đồ (cùng pipeline evidence như ChatGPT gián tiếp).

### Bước 4 — Dừng bridge

Trong terminal đang chạy bridge: `Ctrl+C`. App và các mode khác vẫn dùng được.

---

## Biến môi trường (tuỳ chọn)

```bash
export CURSOR_API_KEY="..."          # bắt buộc khi chat
export CURSOR_BRIDGE_PORT=3847       # mặc định 3847
export CURSOR_BRIDGE_HOST=127.0.0.1  # mặc định chỉ localhost
export CURSOR_MODEL=composer-2.5     # model Cursor agent
```

---

## Cấu hình URL trong app

Mặc định: `http://127.0.0.1:3847` (lưu LocalStorage, key `settings.cursorBridgeUrl`).

Đổi URL khi bridge không kết nối: hộp thoại **Cần chạy Cursor bridge** → sửa URL → **Thử lại**.

API key **không** lưu trong trình duyệt.

---

## Luồng kỹ thuật (tóm tắt)

```text
Trình duyệt (cursor-direct.js)
    → POST http://127.0.0.1:3847/api/session/...
        → cursor-bridge.mjs + @cursor/sdk + CURSOR_API_KEY
            → Cursor agent (local)
```

---

## API bridge (tham khảo)

| Endpoint | Mô tả |
|----------|--------|
| `GET /health` | SDK + API key |
| `POST /api/session/start` | `{ reflectionPrompt }` → `{ sessionKey, reply }` |
| `POST /api/session/:key/message` | `{ content }` → `{ reply }` |
| `POST /api/session/:key/export` | `{ exportPrompt }` → `{ raw }` |
| `DELETE /api/session/:key` | Đóng agent |

---

## Khắc phục sự cố

| Triệu chứng | Cách xử lý |
|-------------|------------|
| Chỉ mode Cursor lỗi, mode khác OK | Đúng thiết kế — chạy bridge bước 2 |
| "Bridge không kết nối" | `cd server && npm start` |
| `CURSOR_API_KEY is not set` | `export CURSOR_API_KEY=...` trước `npm start` |
| `SDK not installed` | `cd server && npm install` |
| CORS / fetch failed | Mở app qua `http://localhost`, không `file://` |
| `npm install` lỗi 404 `@cursor/sdk` | `npm install --registry https://registry.npmjs.org` |
| Live test fail / `cursor_run_error` | Key hết hạn hoặc Cursor agent lỗi — kiểm tra key trên cursor.com |

---

## Bảo mật

- Bridge bind `127.0.0.1` — không expose LAN trừ khi đổi `CURSOR_BRIDGE_HOST`.
- Không đưa `CURSOR_API_KEY` vào frontend hay LocalStorage.

================
$env:CURSOR_API_KEY = Get-Content api.txt; node cursor-bridge.mjs
