import { Buffer } from 'buffer';
import * as bitcoin from 'bitcoinjs-lib';
import * as bip39 from 'bip39';
import BIP32Factory from 'bip32';
import * as ecc from '@bitcoinerlab/secp256k1';
import ECPairFactory from 'ecpair';

const bip32 = BIP32Factory(ecc);
const ECPair = ECPairFactory(ecc);

bitcoin.initEccLib(ecc);

export const NETWORKS = {
  mainnet: {
    id: 'mainnet',
    label: 'Bitcoin Mainnet',
    network: bitcoin.networks.bitcoin,
    apiBase: 'https://blockstream.info/api',
    explorerTx: (txid) => `https://blockstream.info/tx/${txid}`,
    explorerAddr: (addr) => `https://blockstream.info/address/${addr}`,
    coin: 'BTC',
  },
  testnet: {
    id: 'testnet',
    label: 'Bitcoin Testnet',
    network: bitcoin.networks.testnet,
    apiBase: 'https://blockstream.info/testnet/api',
    explorerTx: (txid) => `https://blockstream.info/testnet/tx/${txid}`,
    explorerAddr: (addr) => `https://blockstream.info/testnet/address/${addr}`,
    coin: 'tBTC',
  },
};

const DERIVATION_PATHS = {
  mainnet: "m/84'/0'/0'/0/0",
  testnet: "m/84'/1'/0'/0/0",
};

export function generateMnemonic(strength = 128) {
  return bip39.generateMnemonic(strength);
}

export function validateMnemonic(mnemonic) {
  return bip39.validateMnemonic(mnemonic.trim().toLowerCase());
}

export function deriveWallet(mnemonic, networkId = 'testnet') {
  const config = NETWORKS[networkId] ?? NETWORKS.testnet;
  const derivationPath = DERIVATION_PATHS[networkId] ?? DERIVATION_PATHS.testnet;
  const seed = bip39.mnemonicToSeedSync(mnemonic.trim().toLowerCase());
  const root = bip32.fromSeed(seed, config.network);
  const child = root.derivePath(derivationPath);

  const { address } = bitcoin.payments.p2wpkh({
    pubkey: child.publicKey,
    network: config.network,
  });

  if (!address) {
    throw new Error('Không tạo được địa chỉ ví');
  }

  const keyPair = ECPair.fromPrivateKey(child.privateKey, {
    network: config.network,
  });

  return {
    networkId,
    address,
    publicKey: child.publicKey.toString('hex'),
    keyPair,
    derivationPath,
  };
}

export function satoshisToBtc(sats) {
  return (sats / 1e8).toFixed(8);
}

export function btcToSatoshis(btc) {
  const value = Number(btc);
  if (!Number.isFinite(value) || value < 0) {
    throw new Error('Số tiền không hợp lệ');
  }
  return Math.round(value * 1e8);
}

export function formatBtc(sats, coin = 'BTC') {
  const amount = satoshisToBtc(sats);
  return `${amount} ${coin}`;
}

export { bitcoin, Buffer, ECPair };
