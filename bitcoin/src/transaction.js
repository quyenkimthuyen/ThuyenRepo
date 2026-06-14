import { Buffer } from 'buffer';
import * as bitcoin from 'bitcoinjs-lib';
import { NETWORKS } from './wallet.js';

const DUST_LIMIT = 546;

export function buildAndSignTransaction({
  networkId,
  utxos,
  toAddress,
  amountSats,
  changeAddress,
  keyPair,
  feeRate,
}) {
  const config = NETWORKS[networkId];
  const psbt = new bitcoin.Psbt({ network: config.network });

  let inputSum = 0;
  for (const utxo of utxos) {
    const txHex = utxo.txHex;
    if (!txHex) {
      throw new Error('Thiếu dữ liệu UTXO để ký giao dịch');
    }

    psbt.addInput({
      hash: utxo.txid,
      index: utxo.vout,
      nonWitnessUtxo: Buffer.from(txHex, 'hex'),
    });
    inputSum += utxo.value;
  }

  psbt.addOutput({
    address: toAddress,
    value: amountSats,
  });

  const estimatedVsize = estimateVsize(utxos.length, 2);
  let fee = Math.ceil(estimatedVsize * feeRate);

  let change = inputSum - amountSats - fee;
  if (change < 0) {
    throw new Error('Số dư không đủ để gửi (kể cả phí)');
  }

  if (change >= DUST_LIMIT) {
    psbt.addOutput({
      address: changeAddress,
      value: change,
    });
  } else {
    fee = inputSum - amountSats;
    change = 0;
  }

  if (fee <= 0 || inputSum < amountSats + fee) {
    throw new Error('Số dư không đủ để trả phí mạng');
  }

  for (let i = 0; i < utxos.length; i += 1) {
    psbt.signInput(i, keyPair);
  }

  psbt.finalizeAllInputs();
  const tx = psbt.extractTransaction();

  return {
    hex: tx.toHex(),
    txid: tx.getId(),
    fee,
    change,
  };
}

function estimateVsize(inputCount, outputCount) {
  return 10 + inputCount * 68 + outputCount * 31;
}

export async function enrichUtxosWithRawTx(networkId, utxos) {
  const config = NETWORKS[networkId];
  const enriched = [];

  for (const utxo of utxos) {
    const response = await fetch(`${config.apiBase}/tx/${utxo.txid}/hex`);
    if (!response.ok) {
      throw new Error(`Không tải được tx ${utxo.txid}`);
    }
    const txHex = await response.text();
    enriched.push({ ...utxo, txHex: txHex.trim() });
  }

  return enriched;
}
