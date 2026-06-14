import { Buffer } from 'buffer';
import QRCode from 'qrcode';
import {
  deriveWallet,
  generateMnemonic,
  validateMnemonic,
  formatBtc,
  btcToSatoshis,
  NETWORKS,
} from './wallet.js';
import {
  getAddressInfo,
  getUtxos,
  getTransactions,
  getFeeEstimates,
  broadcastTransaction,
  pickFeeRate,
} from './api.js';
import { buildAndSignTransaction, enrichUtxosWithRawTx } from './transaction.js';
import { saveWallet, loadWallet, clearWallet, hasWallet } from './storage.js';
import './styles.css';

globalThis.Buffer = Buffer;

const app = document.getElementById('app');

let state = {
  view: 'loading',
  mnemonic: null,
  networkId: 'testnet',
  wallet: null,
  balance: 0,
  txs: [],
  error: null,
  loading: false,
  sendForm: { to: '', amount: '', priority: 'hour' },
  showMnemonic: false,
};

function init() {
  const saved = loadWallet();
  if (saved?.mnemonic) {
    state.mnemonic = saved.mnemonic;
    state.networkId = saved.networkId ?? 'testnet';
    state.wallet = deriveWallet(state.mnemonic, state.networkId);
    state.view = 'wallet';
    refreshWalletData();
  } else {
    state.view = 'welcome';
  }
  render();
}

async function refreshWalletData() {
  if (!state.wallet) return;

  state.loading = true;
  state.error = null;
  render();

  try {
    const [info, txs] = await Promise.all([
      getAddressInfo(state.networkId, state.wallet.address),
      getTransactions(state.networkId, state.wallet.address),
    ]);
    state.balance =
      (info.chain_stats?.funded_txo_sum ?? 0) -
      (info.chain_stats?.spent_txo_sum ?? 0) +
      (info.mempool_stats?.funded_txo_sum ?? 0) -
      (info.mempool_stats?.spent_txo_sum ?? 0);
    state.txs = txs ?? [];
  } catch (err) {
    state.error = err.message ?? 'Không tải được dữ liệu ví';
  } finally {
    state.loading = false;
    render();
  }
}

function setView(view) {
  state.view = view;
  state.error = null;
  render();
}

function createWallet() {
  state.mnemonic = generateMnemonic();
  state.view = 'backup';
  render();
}

function confirmBackup() {
  state.wallet = deriveWallet(state.mnemonic, state.networkId);
  saveWallet({ mnemonic: state.mnemonic, networkId: state.networkId });
  state.view = 'wallet';
  refreshWalletData();
}

function importWallet(mnemonic) {
  const cleaned = mnemonic.trim().toLowerCase();
  if (!validateMnemonic(cleaned)) {
    state.error = 'Cụm từ khôi phục không hợp lệ (cần 12 hoặc 24 từ)';
    render();
    return;
  }
  state.mnemonic = cleaned;
  state.wallet = deriveWallet(cleaned, state.networkId);
  saveWallet({ mnemonic: cleaned, networkId: state.networkId });
  state.view = 'wallet';
  refreshWalletData();
}

function lockWallet() {
  clearWallet();
  state = {
    ...state,
    view: 'welcome',
    mnemonic: null,
    wallet: null,
    balance: 0,
    txs: [],
    showMnemonic: false,
  };
  render();
}

async function sendBitcoin(event) {
  event.preventDefault();
  state.error = null;
  state.loading = true;
  render();

  try {
    const amountSats = btcToSatoshis(state.sendForm.amount);
    const utxos = await getUtxos(state.networkId, state.wallet.address);
    const enriched = await enrichUtxosWithRawTx(state.networkId, utxos);
    const feeEstimates = await getFeeEstimates(state.networkId);
    const feeRate = pickFeeRate(feeEstimates, state.sendForm.priority);

    const { hex, txid } = buildAndSignTransaction({
      networkId: state.networkId,
      utxos: enriched,
      toAddress: state.sendForm.to.trim(),
      amountSats,
      changeAddress: state.wallet.address,
      keyPair: state.wallet.keyPair,
      feeRate,
    });

    await broadcastTransaction(state.networkId, hex);
    state.sendForm = { to: '', amount: '', priority: 'hour' };
    state.view = 'wallet';
    state.error = null;
    await refreshWalletData();
    alert(`Gửi thành công!\nTXID: ${txid}`);
  } catch (err) {
    state.error = err.message ?? 'Gửi Bitcoin thất bại';
    state.loading = false;
    render();
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text);
}

function renderWelcome() {
  return `
    <div class="screen welcome">
      <div class="logo">₿</div>
      <h1>Bitcoin Wallet</h1>
      <p class="subtitle">Ví Bitcoin trên trình duyệt — tạo ví, nhận và gửi BTC</p>
      <div class="card">
        <label class="field">
          <span>Mạng Bitcoin</span>
          <select id="network-select">
            ${Object.values(NETWORKS)
              .map(
                (n) =>
                  `<option value="${n.id}" ${state.networkId === n.id ? 'selected' : ''}>${n.label}</option>`
              )
              .join('')}
          </select>
        </label>
        <p class="hint">Khuyến nghị dùng <strong>Testnet</strong> khi học và thử nghiệm.</p>
      </div>
      <button class="btn primary" id="btn-create">Tạo ví mới</button>
      <button class="btn secondary" id="btn-import-show">Nhập ví có sẵn</button>
    </div>
  `;
}

function renderImport() {
  return `
    <div class="screen">
      <button class="btn text" id="btn-back-welcome">← Quay lại</button>
      <h2>Nhập ví</h2>
      <p class="subtitle">Nhập 12 hoặc 24 từ khôi phục (mnemonic)</p>
      ${state.error ? `<div class="alert error">${state.error}</div>` : ''}
      <form id="import-form" class="card">
        <label class="field">
          <span>Cụm từ khôi phục</span>
          <textarea id="import-mnemonic" rows="3" placeholder="word1 word2 word3 ..." required></textarea>
        </label>
        <button type="submit" class="btn primary">Khôi phục ví</button>
      </form>
    </div>
  `;
}

function renderBackup() {
  const words = state.mnemonic.split(' ');
  return `
    <div class="screen">
      <h2>Sao lưu cụm từ khôi phục</h2>
      <div class="alert warning">
        Ghi lại 12 từ này theo đúng thứ tự. Ai có cụm từ sẽ kiểm soát ví của bạn.
        Không chia sẻ với bất kỳ ai.
      </div>
      <div class="mnemonic-grid">
        ${words.map((w, i) => `<div class="mnemonic-word"><span>${i + 1}</span>${w}</div>`).join('')}
      </div>
      <button class="btn secondary" id="btn-copy-mnemonic">Sao chép</button>
      <button class="btn primary" id="btn-confirm-backup">Tôi đã lưu — Tiếp tục</button>
    </div>
  `;
}

function renderWallet() {
  const config = NETWORKS[state.networkId];
  const tab = state.view;

  return `
    <div class="wallet-layout">
      <header class="wallet-header">
        <div>
          <p class="network-badge">${config.label}</p>
          <h1 class="balance">${formatBtc(state.balance, config.coin)}</h1>
          <p class="address" title="${state.wallet.address}">${truncate(state.wallet.address)}</p>
        </div>
        <button class="btn icon" id="btn-refresh" title="Làm mới">↻</button>
      </header>

      ${state.error ? `<div class="alert error">${state.error}</div>` : ''}
      ${state.loading ? '<div class="loading-bar"></div>' : ''}

      <nav class="tabs">
        <button class="tab ${tab === 'wallet' ? 'active' : ''}" data-tab="wallet">Tổng quan</button>
        <button class="tab ${tab === 'receive' ? 'active' : ''}" data-tab="receive">Nhận</button>
        <button class="tab ${tab === 'send' ? 'active' : ''}" data-tab="send">Gửi</button>
        <button class="tab ${tab === 'settings' ? 'active' : ''}" data-tab="settings">Cài đặt</button>
      </nav>

      <main class="wallet-content">
        ${tab === 'wallet' ? renderOverview(config) : ''}
        ${tab === 'receive' ? renderReceive(config) : ''}
        ${tab === 'send' ? renderSend(config) : ''}
        ${tab === 'settings' ? renderSettings() : ''}
      </main>
    </div>
  `;
}

function renderOverview(config) {
  if (!state.txs.length) {
    return `<div class="empty">Chưa có giao dịch nào</div>`;
  }

  return `
    <h3>Lịch sử giao dịch</h3>
    <ul class="tx-list">
      ${state.txs
        .map((tx) => {
          const received = tx.vout.some((o) => o.scriptpubkey_address === state.wallet.address);
          const sent = tx.vin.some(
            (i) => i.prevout?.scriptpubkey_address === state.wallet.address
          );
          const type = received && !sent ? 'Nhận' : sent ? 'Gửi' : 'Khác';
          const value = tx.vout
            .filter((o) => o.scriptpubkey_address === state.wallet.address)
            .reduce((s, o) => s + o.value, 0);
          const date = new Date(tx.status.block_time * 1000).toLocaleString('vi-VN');
          return `
            <li class="tx-item">
              <div>
                <strong>${type}</strong>
                <span class="tx-date">${tx.status.confirmed ? date : 'Đang chờ'}</span>
              </div>
              <div>
                <span class="${received ? 'positive' : 'negative'}">
                  ${received ? '+' : '-'}${formatBtc(value, config.coin)}
                </span>
                <a href="${config.explorerTx(tx.txid)}" target="_blank" rel="noopener">Xem</a>
              </div>
            </li>
          `;
        })
        .join('')}
    </ul>
  `;
}

function renderReceive(config) {
  return `
    <div class="receive-panel">
      <h3>Nhận Bitcoin</h3>
      <p>Gửi ${config.coin} đến địa chỉ sau:</p>
      <div class="qr-wrap"><canvas id="qr-canvas"></canvas></div>
      <div class="address-box">
        <code id="receive-address">${state.wallet.address}</code>
        <button class="btn secondary" id="btn-copy-address">Sao chép</button>
      </div>
      <a class="btn text" href="${config.explorerAddr(state.wallet.address)}" target="_blank" rel="noopener">
        Xem trên Blockstream →
      </a>
    </div>
  `;
}

function renderSend(config) {
  return `
    <form id="send-form" class="card send-form">
      <h3>Gửi Bitcoin</h3>
      <p class="hint">Số dư khả dụng: <strong>${formatBtc(state.balance, config.coin)}</strong></p>
      ${state.error ? `<div class="alert error">${state.error}</div>` : ''}
      <label class="field">
        <span>Địa chỉ người nhận</span>
        <input type="text" id="send-to" value="${state.sendForm.to}" placeholder="bc1... hoặc tb1..." required />
      </label>
      <label class="field">
        <span>Số lượng (${config.coin})</span>
        <input type="number" id="send-amount" step="0.00000001" min="0" value="${state.sendForm.amount}" required />
      </label>
      <label class="field">
        <span>Tốc độ phí</span>
        <select id="send-priority">
          <option value="fast" ${state.sendForm.priority === 'fast' ? 'selected' : ''}>Nhanh (~3 block)</option>
          <option value="hour" ${state.sendForm.priority === 'hour' ? 'selected' : ''}>Trung bình (~1 giờ)</option>
          <option value="economy" ${state.sendForm.priority === 'economy' ? 'selected' : ''}>Tiết kiệm</option>
        </select>
      </label>
      <button type="submit" class="btn primary" ${state.loading ? 'disabled' : ''}>
        ${state.loading ? 'Đang gửi...' : 'Gửi Bitcoin'}
      </button>
    </form>
  `;
}

function renderSettings() {
  return `
    <div class="card settings">
      <h3>Cài đặt</h3>
      <button class="btn secondary" id="btn-show-mnemonic">
        ${state.showMnemonic ? 'Ẩn' : 'Hiện'} cụm từ khôi phục
      </button>
      ${
        state.showMnemonic
          ? `<div class="mnemonic-grid small">${state.mnemonic
              .split(' ')
              .map((w, i) => `<div class="mnemonic-word"><span>${i + 1}</span>${w}</div>`)
              .join('')}</div>`
          : ''
      }
      <div class="alert warning">
        Ví lưu mnemonic trong localStorage của trình duyệt. Chỉ dùng cho học tập / testnet.
        Để dùng mainnet thật, cần bảo mật chuyên nghiệp hơn (hardware wallet, mã hóa mạnh).
      </div>
      <button class="btn danger" id="btn-lock">Khóa ví (xóa khỏi thiết bị)</button>
    </div>
  `;
}

function truncate(str, len = 16) {
  if (str.length <= len * 2) return str;
  return `${str.slice(0, len)}...${str.slice(-len)}`;
}

function render() {
  let html = '';
  switch (state.view) {
    case 'welcome':
      html = renderWelcome();
      break;
    case 'import':
      html = renderImport();
      break;
    case 'backup':
      html = renderBackup();
      break;
    case 'wallet':
    case 'receive':
    case 'send':
    case 'settings':
      html = renderWallet();
      break;
    default:
      html = '<div class="screen">Đang tải...</div>';
  }

  app.innerHTML = html;
  bindEvents();
}

function bindEvents() {
  document.getElementById('btn-create')?.addEventListener('click', createWallet);
  document.getElementById('btn-import-show')?.addEventListener('click', () => setView('import'));
  document.getElementById('btn-back-welcome')?.addEventListener('click', () => setView('welcome'));
  document.getElementById('network-select')?.addEventListener('change', (e) => {
    state.networkId = e.target.value;
  });
  document.getElementById('import-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const mnemonic = document.getElementById('import-mnemonic').value;
    importWallet(mnemonic);
  });
  document.getElementById('btn-confirm-backup')?.addEventListener('click', confirmBackup);
  document.getElementById('btn-copy-mnemonic')?.addEventListener('click', () => {
    copyText(state.mnemonic);
    alert('Đã sao chép cụm từ khôi phục');
  });
  document.getElementById('btn-refresh')?.addEventListener('click', refreshWalletData);
  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => setView(btn.dataset.tab));
  });
  document.getElementById('btn-copy-address')?.addEventListener('click', () => {
    copyText(state.wallet.address);
    alert('Đã sao chép địa chỉ');
  });
  document.getElementById('send-form')?.addEventListener('submit', sendBitcoin);
  document.getElementById('send-to')?.addEventListener('input', (e) => {
    state.sendForm.to = e.target.value;
  });
  document.getElementById('send-amount')?.addEventListener('input', (e) => {
    state.sendForm.amount = e.target.value;
  });
  document.getElementById('send-priority')?.addEventListener('change', (e) => {
    state.sendForm.priority = e.target.value;
  });
  document.getElementById('btn-show-mnemonic')?.addEventListener('click', () => {
    state.showMnemonic = !state.showMnemonic;
    render();
  });
  document.getElementById('btn-lock')?.addEventListener('click', () => {
    if (confirm('Xóa ví khỏi trình duyệt? Bạn cần cụm từ khôi phục để vào lại.')) {
      lockWallet();
    }
  });

  if (state.view === 'receive' && state.wallet) {
    const canvas = document.getElementById('qr-canvas');
    if (canvas) {
      QRCode.toCanvas(canvas, `bitcoin:${state.wallet.address}`, {
        width: 220,
        margin: 2,
        color: { dark: '#f7931a', light: '#141821' },
      });
    }
  }
}

init();
