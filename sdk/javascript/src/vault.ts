/**
 * Module Vault pour chiffrement local
 */

import {
  hkdf, aesGcmEncrypt, aesGcmDecrypt,
  bytesToBase64, base64ToBytes, sha256, bytesToHex
} from './crypto';
import { EncryptionError, DecryptionError, ValidationError } from './errors';
import type { EncryptedPayload } from './types';

export interface EncryptedData {
  ciphertext: Uint8Array;
  nonce: Uint8Array;
  tag: Uint8Array;
  metadata?: Record<string, unknown>;
}

export class Vault {
  private readonly masterKey: Uint8Array;
  private encryptionKey: Uint8Array | null = null;
  
  static readonly KEY_SIZE = 32;
  static readonly NONCE_SIZE = 12;
  static readonly TAG_SIZE = 16;
  
  constructor(vaultKey: Uint8Array) {
    if (vaultKey.length !== Vault.KEY_SIZE) {
      throw new ValidationError(`vaultKey must be ${Vault.KEY_SIZE} bytes`);
    }
    this.masterKey = vaultKey;
  }
  
  /**
   * Initialise les cles derivees
   */
  private async init(): Promise<void> {
    if (!this.encryptionKey) {
      this.encryptionKey = await hkdf(
        this.masterKey,
        new TextEncoder().encode('PSNX_SDK_v1'),
        new TextEncoder().encode('encryption')
      );
    }
  }
  
  /**
   * Chiffre des donnees
   */
  async encrypt(
    plaintext: Uint8Array,
    metadata?: Record<string, unknown>
  ): Promise<EncryptedData> {
    await this.init();
    
    try {
      const { ciphertext, nonce, tag } = await aesGcmEncrypt(
        this.encryptionKey!,
        plaintext
      );
      
      return { ciphertext, nonce, tag, metadata };
    } catch (e) {
      throw new EncryptionError(`Encryption failed: ${e}`);
    }
  }
  
  /**
   * Dechiffre des donnees
   */
  async decrypt(encrypted: EncryptedData): Promise<Uint8Array> {
    await this.init();
    
    try {
      return await aesGcmDecrypt(
        this.encryptionKey!,
        encrypted.ciphertext,
        encrypted.nonce,
        encrypted.tag
      );
    } catch (e) {
      throw new DecryptionError(`Decryption failed: ${e}`);
    }
  }
  
  /**
   * Convertit en format API
   */
  static toPayload(data: EncryptedData): EncryptedPayload {
    return {
      ciphertext: bytesToBase64(data.ciphertext),
      nonce: bytesToBase64(data.nonce),
      tag: bytesToBase64(data.tag),
      metadata: data.metadata
    };
  }
  
  /**
   * Parse depuis format API
   */
  static fromPayload(payload: EncryptedPayload): EncryptedData {
    return {
      ciphertext: base64ToBytes(payload.ciphertext),
      nonce: base64ToBytes(payload.nonce),
      tag: base64ToBytes(payload.tag),
      metadata: payload.metadata
    };
  }
  
  /**
   * Empreinte du vault
   */
  async getFingerprint(): Promise<string> {
    const hash = await sha256(this.masterKey);
    return bytesToHex(hash).slice(0, 16);
  }
  
  /**
   * Derive une sous-cle
   */
  async deriveSubkey(purpose: string): Promise<Uint8Array> {
    return hkdf(
      this.masterKey,
      new TextEncoder().encode('PSNX_SDK_v1'),
      new TextEncoder().encode(purpose)
    );
  }
}
