/**
 * Shamir Secret Sharing
 */

import { randomBytes, sha256, bytesToHex, bytesToBase64, base64ToBytes, bytesToBigInt, bigIntToBytes } from './crypto';
import { ShareError, ValidationError } from './errors';
import type { ShareData } from './types';

export interface Share {
  index: number;
  data: Uint8Array;
  threshold: number;
  total: number;
  checksum: string;
}

// Prime pour GF(p)
const PRIME = 2n ** 256n - 189n;

export class SecretSharing {
  private readonly k: number; // threshold
  private readonly n: number; // total
  
  constructor(threshold: number = 3, total: number = 5) {
    if (threshold < 2) {
      throw new ValidationError('Threshold must be >= 2');
    }
    if (total < threshold) {
      throw new ValidationError('Total must be >= threshold');
    }
    if (total > 255) {
      throw new ValidationError('Maximum 255 shares');
    }
    
    this.k = threshold;
    this.n = total;
  }
  
  /**
   * Divise le secret en N parts
   */
  async split(secret: Uint8Array): Promise<Share[]> {
    if (secret.length > 32) {
      throw new ValidationError('Secret too large (max 32 bytes)');
    }
    
    // Convertir en bigint
    const secretInt = bytesToBigInt(secret);
    
    // Coefficients du polynome
    const coefficients: bigint[] = [secretInt];
    for (let i = 1; i < this.k; i++) {
      const rand = bytesToBigInt(randomBytes(32));
      coefficients.push((rand % (PRIME - 1n)) + 1n);
    }
    
    // Evaluer en N points
    const shares: Share[] = [];
    for (let x = 1; x <= this.n; x++) {
      const y = this.evaluate(coefficients, BigInt(x));
      const yBytes = bigIntToBytes(y, 32);
      
      // Checksum
      const indexBytes = new Uint8Array(4);
      new DataView(indexBytes.buffer).setUint32(0, x, false);
      const toHash = new Uint8Array(yBytes.length + 4);
      toHash.set(yBytes);
      toHash.set(indexBytes, yBytes.length);
      const hash = await sha256(toHash);
      const checksum = bytesToHex(hash).slice(0, 8);
      
      shares.push({
        index: x,
        data: yBytes,
        threshold: this.k,
        total: this.n,
        checksum
      });
    }
    
    return shares;
  }
  
  /**
   * Reconstruit le secret depuis K parts
   */
  async reconstruct(shares: Share[]): Promise<Uint8Array> {
    if (shares.length < this.k) {
      throw new ShareError(`Need ${this.k} shares, got ${shares.length}`);
    }
    
    // Verifier checksums
    for (const share of shares) {
      const valid = await this.verifyShare(share);
      if (!valid) {
        throw new ShareError(`Share ${share.index} corrupted`);
      }
    }
    
    // Utiliser K parts
    const useShares = shares.slice(0, this.k);
    
    // Verifier unicite
    const indices = new Set(useShares.map(s => s.index));
    if (indices.size !== useShares.length) {
      throw new ShareError('Duplicate shares');
    }
    
    // Points (x, y)
    const points: [bigint, bigint][] = useShares.map(s => [
      BigInt(s.index),
      bytesToBigInt(s.data)
    ]);
    
    // Interpolation de Lagrange
    const secretInt = this.lagrange(points, 0n);
    
    // Convertir en bytes
    const bytes = bigIntToBytes(secretInt, 32);
    
    // Retirer les zeros au debut
    let start = 0;
    while (start < bytes.length - 1 && bytes[start] === 0) start++;
    
    return bytes.slice(start);
  }
  
  /**
   * Evalue le polynome en x
   */
  private evaluate(coefficients: bigint[], x: bigint): bigint {
    let result = 0n;
    let xPower = 1n;
    
    for (const coeff of coefficients) {
      result = (result + coeff * xPower) % PRIME;
      xPower = (xPower * x) % PRIME;
    }
    
    return result;
  }
  
  /**
   * Interpolation de Lagrange
   */
  private lagrange(points: [bigint, bigint][], x: bigint): bigint {
    let result = 0n;
    
    for (let i = 0; i < points.length; i++) {
      const [xi, yi] = points[i];
      let num = 1n;
      let den = 1n;
      
      for (let j = 0; j < points.length; j++) {
        if (i !== j) {
          const [xj] = points[j];
          num = (num * (x - xj)) % PRIME;
          den = (den * (xi - xj)) % PRIME;
        }
      }
      
      // Inverse modulaire
      const denInv = this.modInverse(den, PRIME);
      const coeff = (num * denInv) % PRIME;
      result = (result + yi * coeff) % PRIME;
    }
    
    // Gerer les negatifs
    if (result < 0n) result += PRIME;
    
    return result;
  }
  
  /**
   * Inverse modulaire (extended Euclidean)
   */
  private modInverse(a: bigint, m: bigint): bigint {
    if (a < 0n) a = ((a % m) + m) % m;
    
    let [old_r, r] = [a, m];
    let [old_s, s] = [1n, 0n];
    
    while (r !== 0n) {
      const q = old_r / r;
      [old_r, r] = [r, old_r - q * r];
      [old_s, s] = [s, old_s - q * s];
    }
    
    if (old_s < 0n) old_s += m;
    return old_s;
  }
  
  /**
   * Verifie le checksum d'une part
   */
  async verifyShare(share: Share): Promise<boolean> {
    const indexBytes = new Uint8Array(4);
    new DataView(indexBytes.buffer).setUint32(0, share.index, false);
    
    const toHash = new Uint8Array(share.data.length + 4);
    toHash.set(share.data);
    toHash.set(indexBytes, share.data.length);
    
    const hash = await sha256(toHash);
    const expected = bytesToHex(hash).slice(0, 8);
    
    return share.checksum === expected;
  }
  
  /**
   * Convertit une part en format transferable
   */
  static toData(share: Share): ShareData {
    return {
      index: share.index,
      data: bytesToBase64(share.data),
      threshold: share.threshold,
      total: share.total,
      checksum: share.checksum
    };
  }
  
  /**
   * Parse depuis format transferable
   */
  static fromData(data: ShareData): Share {
    return {
      index: data.index,
      data: base64ToBytes(data.data),
      threshold: data.threshold,
      total: data.total,
      checksum: data.checksum
    };
  }
}
