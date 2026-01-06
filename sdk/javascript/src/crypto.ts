/**
 * Utilitaires cryptographiques
 * Utilise Web Crypto API (browser) ou Node.js crypto
 */

// Detecter l'environnement
const isNode = typeof process !== 'undefined' && 
               process.versions?.node !== undefined;

// Interface crypto unifiee
interface CryptoInterface {
  getRandomValues(array: Uint8Array): Uint8Array;
  subtle: SubtleCrypto;
}

let cryptoImpl: CryptoInterface;

if (isNode) {
  // Node.js
  const nodeCrypto = require('crypto');
  cryptoImpl = nodeCrypto.webcrypto as CryptoInterface;
} else {
  // Browser
  cryptoImpl = globalThis.crypto as CryptoInterface;
}

export const crypto = cryptoImpl;

/**
 * Genere des bytes aleatoires
 */
export function randomBytes(length: number): Uint8Array {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return bytes;
}

/**
 * SHA-256
 */
export async function sha256(data: Uint8Array): Promise<Uint8Array> {
  const hash = await crypto.subtle.digest('SHA-256', data);
  return new Uint8Array(hash);
}

/**
 * HKDF - Key Derivation
 */
export async function hkdf(
  secret: Uint8Array,
  salt: Uint8Array,
  info: Uint8Array,
  length: number = 32
): Promise<Uint8Array> {
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    secret,
    'HKDF',
    false,
    ['deriveBits']
  );
  
  const derived = await crypto.subtle.deriveBits(
    {
      name: 'HKDF',
      hash: 'SHA-256',
      salt,
      info
    },
    keyMaterial,
    length * 8
  );
  
  return new Uint8Array(derived);
}

/**
 * AES-GCM Encrypt
 */
export async function aesGcmEncrypt(
  key: Uint8Array,
  plaintext: Uint8Array,
  additionalData?: Uint8Array
): Promise<{ ciphertext: Uint8Array; nonce: Uint8Array; tag: Uint8Array }> {
  const nonce = randomBytes(12);
  
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    key,
    'AES-GCM',
    false,
    ['encrypt']
  );
  
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData,
      tagLength: 128
    },
    cryptoKey,
    plaintext
  );
  
  const encryptedBytes = new Uint8Array(encrypted);
  const ciphertext = encryptedBytes.slice(0, -16);
  const tag = encryptedBytes.slice(-16);
  
  return { ciphertext, nonce, tag };
}

/**
 * AES-GCM Decrypt
 */
export async function aesGcmDecrypt(
  key: Uint8Array,
  ciphertext: Uint8Array,
  nonce: Uint8Array,
  tag: Uint8Array,
  additionalData?: Uint8Array
): Promise<Uint8Array> {
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    key,
    'AES-GCM',
    false,
    ['decrypt']
  );
  
  // Combiner ciphertext et tag
  const combined = new Uint8Array(ciphertext.length + tag.length);
  combined.set(ciphertext);
  combined.set(tag, ciphertext.length);
  
  const decrypted = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData,
      tagLength: 128
    },
    cryptoKey,
    combined
  );
  
  return new Uint8Array(decrypted);
}

/**
 * Conversion bytes <-> hex
 */
export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

export function hexToBytes(hex: string): Uint8Array {
  if (hex.startsWith('0x')) hex = hex.slice(2);
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}

/**
 * Conversion bytes <-> base64
 */
export function bytesToBase64(bytes: Uint8Array): string {
  if (isNode) {
    return Buffer.from(bytes).toString('base64');
  }
  return btoa(String.fromCharCode(...bytes));
}

export function base64ToBytes(base64: string): Uint8Array {
  if (isNode) {
    return new Uint8Array(Buffer.from(base64, 'base64'));
  }
  return new Uint8Array(atob(base64).split('').map(c => c.charCodeAt(0)));
}

/**
 * BigInt depuis bytes
 */
export function bytesToBigInt(bytes: Uint8Array): bigint {
  let result = 0n;
  for (const byte of bytes) {
    result = (result << 8n) | BigInt(byte);
  }
  return result;
}

export function bigIntToBytes(n: bigint, length?: number): Uint8Array {
  const hex = n.toString(16).padStart((length ?? Math.ceil(n.toString(16).length / 2)) * 2, '0');
  return hexToBytes(hex);
}
