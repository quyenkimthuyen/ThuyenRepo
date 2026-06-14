import { NETWORKS } from './wallet.js';

async function apiFetch(networkId, path, options = {}) {
  const config = NETWORKS[networkId];
  const response = await fetch(`${config.apiBase}${path}`, options);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API lỗi: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    return response.json();
  }

  return response.text();
}

export async function getAddressInfo(networkId, address) {
  return apiFetch(networkId, `/address/${address}`);
}

export async function getUtxos(networkId, address) {
  return apiFetch(networkId, `/address/${address}/utxo`);
}

export async function getTransactions(networkId, address) {
  return apiFetch(networkId, `/address/${address}/txs`);
}

export async function getFeeEstimates(networkId) {
  return apiFetch(networkId, '/fee-estimates');
}

export async function broadcastTransaction(networkId, rawTxHex) {
  return apiFetch(networkId, '/tx', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: rawTxHex,
  });
}

export function pickFeeRate(feeEstimates, priority = 'hour') {
  const targets = {
    fast: 3,
    hour: 6,
    economy: 12,
  };
  const blocks = targets[priority] ?? 6;
  const rate = feeEstimates[String(blocks)] ?? feeEstimates['6'] ?? 5;
  return Math.max(1, Math.ceil(rate));
}
