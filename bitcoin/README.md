# Bitcoin Wallet (Web)

Ứng dụng ví Bitcoin chạy trên trình duyệt, tương tự Trust Wallet ở mức cơ bản:

- Tạo ví mới (BIP39 mnemonic 12 từ)
- Nhập ví từ cụm từ khôi phục
- Xem số dư và lịch sử giao dịch
- Nhận BTC (địa chỉ + mã QR)
- Gửi BTC (ký và broadcast giao dịch)

## Công nghệ

- **Vite** + vanilla JavaScript
- **bitcoinjs-lib** — địa chỉ SegWit (BIP84), ký giao dịch
- **bip39 / bip32** — HD wallet
- **Blockstream API** — số dư, UTXO, broadcast

## Chạy ứng dụng

### Cách 1: Live Server (Visual Studio Code) — mở trực tiếp `index.html`

1. Trong VS Code: **File → Open Folder** → chọn thư mục `bitcoin` (quan trọng!)
2. Cài extension **Live Server**
3. Chuột phải file `index.html` → **Open with Live Server**

Hoặc nhấn **Go Live** ở góc dưới phải.

App chạy tại `http://127.0.0.1:5506` (cần **internet** để tải thư viện từ CDN).

**Không cần** `npm install` hay `npm run build` khi dùng cách này.

> Nếu mở cả repo cha (`repo`) thay vì folder `bitcoin`, hãy chuột phải `bitcoin/index.html` → Open with Live Server (không mở `index.html` ở thư mục gốc repo).

### Cách 2: Vite (offline, tự reload khi sửa code)

```bash
cd bitcoin
npm install --registry=https://registry.npmjs.org/
npm run dev
```

### Cách 3: Build production (offline, không cần CDN)

```bash
npm run build
```

Sau đó mở `dist/index.html` bằng Live Server.

## Testnet vs Mainnet

Mặc định khuyến nghị **Testnet** khi học:

1. Tạo ví trên Testnet
2. Lấy test BTC miễn phí tại [https://testnet-faucet.com/btc-testnet/](https://testnet-faucet.com/btc-testnet/)
3. Gửi/nhận thử trước khi dùng mainnet

Mainnet có thể bật khi tạo ví — **chỉ dùng số tiền nhỏ** vì ví web chưa đạt mức bảo mật như Trust Wallet / hardware wallet.

## Bảo mật

- Mnemonic lưu trong `localStorage` — phù hợp học tập, **không** phù hợp lưu số tiền lớn
- Không chia sẻ cụm từ khôi phục
- Production cần: mã hóa PIN, WebCrypto, hardware wallet, audit

## Cấu trúc

```
src/
  main.js         # Giao diện
  wallet.js       # Tạo ví, derive key
  api.js          # Blockstream API
  transaction.js  # Build & sign TX
  storage.js      # localStorage
```

## So với Trust Wallet

| Tính năng | App này | Trust Wallet |
|-----------|---------|--------------|
| Tạo / import ví | Có | Có |
| Nhiều coin | Chỉ BTC | Nhiều chain |
| Mobile app | Web | iOS / Android |
| Bảo mật | Cơ bản | Chuyên nghiệp |
| Swap / DApp | Không | Có |

Đây là nền tảng tốt để học; có thể mở rộng thêm đa địa chỉ, RBF, Lightning, v.v.
