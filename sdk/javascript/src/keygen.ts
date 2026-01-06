/**
 * Generation de cles
 */

import { randomBytes, hkdf, sha256, bytesToHex, bytesToBigInt } from './crypto';
import { ValidationError } from './errors';

export interface KeyPair {
  vaultKey: Uint8Array;
  publicKey: bigint;
  fingerprint: string;
  entropyBits: number;
}

// Parametres Schnorr (RFC 5114)
const P = BigInt(
  '0xFFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1' +
  '29024E088A67CC74020BBEA63B139B22514A08798E3404DD' +
  'EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245' +
  'E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED' +
  'EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D' +
  'C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F' +
  '83655D23DCA3AD961C62F356208552BB9ED529077096966D' +
  '670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B' +
  'E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9' +
  'DE2BCBF6955817183995497CEA956AE515D2261898FA0510' +
  '15728E5A8AACAA68FFFFFFFFFFFFFFFF'
);
const Q = (P - 1n) / 2n;
const G = 2n;

function modPow(base: bigint, exp: bigint, mod: bigint): bigint {
  let result = 1n;
  base = base % mod;
  while (exp > 0n) {
    if (exp % 2n === 1n) {
      result = (result * base) % mod;
    }
    exp = exp / 2n;
    base = (base * base) % mod;
  }
  return result;
}

export class KeyGenerator {
  private extraEntropy: Uint8Array;
  
  static readonly KEY_SIZE = 32;
  
  constructor(extraEntropy?: Uint8Array) {
    this.extraEntropy = extraEntropy ?? new Uint8Array(0);
  }
  
  /**
   * Genere une cle vault aleatoire
   */
  async generate(): Promise<Uint8Array> {
    const entropy = new Uint8Array(64 + this.extraEntropy.length);
    entropy.set(randomBytes(64));
    entropy.set(this.extraEntropy, 64);
    
    return hkdf(
      entropy,
      new TextEncoder().encode('PSNX_KEYGEN_v1'),
      new TextEncoder().encode('vault_master_key')
    );
  }
  
  /**
   * Derive une cle depuis un mot de passe (PBKDF2)
   */
  async fromPassword(password: string, salt?: Uint8Array): Promise<{
    vaultKey: Uint8Array;
    salt: Uint8Array;
  }> {
    if (password.length < 8) {
      throw new ValidationError('Password must be at least 8 characters');
    }
    
    const useSalt = salt ?? randomBytes(16);
    
    // Utiliser PBKDF2 via Web Crypto
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(password),
      'PBKDF2',
      false,
      ['deriveBits']
    );
    
    const derived = await crypto.subtle.deriveBits(
      {
        name: 'PBKDF2',
        salt: useSalt,
        iterations: 100000,
        hash: 'SHA-256'
      },
      keyMaterial,
      256
    );
    
    return {
      vaultKey: new Uint8Array(derived),
      salt: useSalt
    };
  }
  
  /**
   * Genere depuis entropie externe
   */
  async fromEntropy(entropy: Uint8Array, minBits: number = 256): Promise<Uint8Array> {
    if (entropy.length * 8 < minBits) {
      throw new ValidationError(`Entropy must be at least ${minBits} bits`);
    }
    
    const combined = new Uint8Array(entropy.length + 32 + this.extraEntropy.length);
    combined.set(entropy);
    combined.set(randomBytes(32), entropy.length);
    combined.set(this.extraEntropy, entropy.length + 32);
    
    return hkdf(
      combined,
      new TextEncoder().encode('PSNX_EXTERNAL_ENTROPY'),
      new TextEncoder().encode('vault_key_from_external')
    );
  }
  
  /**
   * Genere une paire complete
   */
  async generateKeyPair(): Promise<KeyPair> {
    const vaultKey = await this.generate();
    
    // Deriver cle privee ZKP
    const zkpBytes = await sha256(
      new Uint8Array([...new TextEncoder().encode('PSNX_ZKP_PRIVATE_'), ...vaultKey])
    );
    let x = bytesToBigInt(zkpBytes) % Q;
    if (x === 0n) x = 1n;
    
    // Cle publique
    const publicKey = modPow(G, x, P);
    
    // Fingerprint
    const hash = await sha256(vaultKey);
    const fingerprint = bytesToHex(hash).slice(0, 16);
    
    return {
      vaultKey,
      publicKey,
      fingerprint,
      entropyBits: 256
    };
  }
  
  /**
   * Verifie une cle
   */
  static verify(vaultKey: Uint8Array): boolean {
    if (vaultKey.length !== 32) return false;
    return !vaultKey.every(b => b === 0);
  }
}
