# Cursor AI Proxy — Quick start

Proxy local cho app **Nhìn lại suy nghĩ**. App browser gọi `http://localhost:3001`; proxy gọi Cursor qua `@cursor/sdk`.

## Chạy nhanh

```bash
cd server
npm install --registry https://registry.npmjs.org
export CURSOR_API_KEY="cursor_YOUR_KEY_HERE"
npm start
```

## Biến môi trường

| Biến | Mặc định | Mô tả |
|------|----------|--------|
| `CURSOR_API_KEY` | *(bắt buộc)* | Key từ [Cursor Dashboard → Integrations](https://cursor.com/dashboard/integrations) |
| `AI_SERVER_PORT` | `3001` | Port proxy |
| `CURSOR_MODEL` | `composer-2.5` | Model Cursor |

## Kiểm tra

```bash
curl http://localhost:3001/api/health
```

`hasKey: true` → sẵn sàng cho app.

## Scripts

| Lệnh | Việc làm |
|------|----------|
| `npm start` | Chạy server |
| `npm run dev` | Chạy với `--watch` (tự reload khi sửa file) |

Hướng dẫn đầy đủ: [../README.md](../README.md)
