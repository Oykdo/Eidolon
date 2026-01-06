/**
 * Zero-Knowledge Proofs (Schnorr)
 */

import { 
  randomBytes, sha256, bytesToHex, bytesToBigInt, bigIntToBytes 
} from './crypto';
import { ValidationError, AuthenticationError } from './errors';

// Parametres du groupe (RFC 5114)
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
  base = ((base % mod) + mod) % mod;
  while (exp > 0n) {
    if (exp % 2n === 1n) {
      result = (result * base) % mod;
    }
    exp = exp / 2n;
    base = (base * base) % mod;
  }
  return result;
}

export interface ZKPProof {
  commitment: string;  // R = g^k (hex)
  challenge: string;   // c (hex)
  response: string;    // s = k + c*x (hex)
  publicKey: string;   // Y = g^x (hex)
  message: string;     // hex
  timestamp: number;
}

export class ZKPProver {
  private readonly x: bigint;  // Cle privee
  private readonly Y: bigint;  // Cle publique
  
  constructor(vaultKey: Uint8Array) {
    if (vaultKey.length !== 32) {
      throw new ValidationError('vaultKey must be 32 bytes');
    }
    
    // Deriver cle privee
    const prefix = new TextEncoder().encode('PSNX_ZKP_PRIVATE_');
    const combined = new Uint8Array(prefix.length + vaultKey.length);
    combined.set(prefix);
    combined.set(vaultKey, prefix.length);
    
    // Note: synchrone sha256 via crypto.subtle pas dispo
    // On utilise une derivation simple pour l'instant
    let hash = 0n;
    for (let i = 0; i < combined.length; i++) {
      hash = (hash * 256n + BigInt(combined[i])) % Q;
    }
    
    this.x = hash === 0n ? 1n : hash;
    this.Y = modPow(G, this.x, P);
  }
  
  /**
   * Initialise avec hash async
   */
  static async create(vaultKey: Uint8Array): Promise<ZKPProver> {
    if (vaultKey.length !== 32) {
      throw new ValidationError('vaultKey must be 32 bytes');
    }
    
    const prefix = new TextEncoder().encode('PSNX_ZKP_PRIVATE_');
    const combined = new Uint8Array(prefix.length + vaultKey.length);
    combined.set(prefix);
    combined.set(vaultKey, prefix.length);
    
    const hash = await sha256(combined);
    let x = bytesToBigInt(hash) % Q;
    if (x === 0n) x = 1n;
    
    const prover = new ZKPProver(vaultKey);
    (prover as any).x = x;
    (prover as any).Y = modPow(G, x, P);
    
    return prover;
  }
  
  getPublicKey(): bigint {
    return this.Y;
  }
  
  getPublicKeyHex(): string {
    return '0x' + this.Y.toString(16);
  }
  
  async getFingerprint(): Promise<string> {
    const yBytes = bigIntToBytes(this.Y, 256);
    const hash = await sha256(yBytes);
    return bytesToHex(hash).slice(0, 16);
  }
  
  /**
   * Cree une preuve ZKP
   */
  async createProof(challenge: string): Promise<{
    proof: ZKPProof;
    challenge: string;
    keyFingerprint: string;
    timestamp: number;
  }> {
    const message = new TextEncoder().encode(challenge);
    const timestamp = Date.now() / 1000;
    
    // Commitment: R = g^k
    const kBytes = randomBytes(32);
    const k = (bytesToBigInt(kBytes) % (Q - 1n)) + 1n;
    const R = modPow(G, k, P);
    
    // Challenge: c = H(R || Y || m)
    const rBytes = bigIntToBytes(R, 256);
    const yBytes = bigIntToBytes(this.Y, 256);
    const data = new Uint8Array(rBytes.length + yBytes.length + message.length);
    data.set(rBytes);
    data.set(yBytes, rBytes.length);
    data.set(message, rBytes.length + yBytes.length);
    
    const cHash = await sha256(data);
    const c = bytesToBigInt(cHash) % Q;
    
    // Response: s = k + c*x mod Q
    let s = (k + c * this.x) % Q;
    if (s < 0n) s += Q;
    
    const proof: ZKPProof = {
      commitment: '0x' + R.toString(16),
      challenge: '0x' + c.toString(16),
      response: '0x' + s.toString(16),
      publicKey: '0x' + this.Y.toString(16),
      message: bytesToHex(message),
      timestamp
    };
    
    return {
      proof,
      challenge,
      keyFingerprint: await this.getFingerprint(),
      timestamp
    };
  }
}

export class ZKPVerifier {
  /**
   * Verifie une preuve ZKP
   */
  static async verify(
    authData: { proof: ZKPProof; challenge: string },
    expectedChallenge: string,
    maxAgeSeconds: number = 300
  ): Promise<{ valid: boolean; reason: string }> {
    try {
      const { proof } = authData;
      
      // Verifier challenge
      if (authData.challenge !== expectedChallenge) {
        return { valid: false, reason: 'Challenge mismatch' };
      }
      
      // Verifier age
      const age = Date.now() / 1000 - proof.timestamp;
      if (age > maxAgeSeconds) {
        return { valid: false, reason: `Proof expired (age: ${age.toFixed(1)}s)` };
      }
      if (age < -60) {
        return { valid: false, reason: 'Proof from future' };
      }
      
      // Parser les valeurs
      const R = BigInt(proof.commitment);
      const c = BigInt(proof.challenge);
      const s = BigInt(proof.response);
      const Y = BigInt(proof.publicKey);
      const message = new Uint8Array(
        proof.message.match(/.{2}/g)!.map(b => parseInt(b, 16))
      );
      
      // Verifier le challenge hash
      const rBytes = bigIntToBytes(R, 256);
      const yBytes = bigIntToBytes(Y, 256);
      const data = new Uint8Array(rBytes.length + yBytes.length + message.length);
      data.set(rBytes);
      data.set(yBytes, rBytes.length);
      data.set(message, rBytes.length + yBytes.length);
      
      const expectedC = bytesToBigInt(await sha256(data)) % Q;
      if (expectedC !== c) {
        return { valid: false, reason: 'Invalid challenge hash' };
      }
      
      // Verifier: g^s == R * Y^c mod p
      const lhs = modPow(G, s, P);
      const rhs = (R * modPow(Y, c, P)) % P;
      
      if (lhs !== rhs) {
        return { valid: false, reason: 'Cryptographic verification failed' };
      }
      
      return { valid: true, reason: 'OK' };
      
    } catch (e) {
      return { valid: false, reason: `Verification error: ${e}` };
    }
  }
  
  /**
   * Verifie une cle publique
   */
  static async verifyPublicKey(publicKey: bigint): Promise<boolean> {
    if (publicKey < 2n || publicKey >= P - 1n) {
      return false;
    }
    
    // Doit etre dans le sous-groupe
    return modPow(publicKey, Q, P) === 1n;
  }
}
