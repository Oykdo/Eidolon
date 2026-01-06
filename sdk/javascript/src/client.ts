/**
 * Client API pour le SDK
 */

import { Vault, EncryptedData } from './vault';
import { ZKPProver } from './zkp';
import { SecretSharing, Share } from './sharing';
import { NetworkError, AuthenticationError } from './errors';
import { bytesToBase64, base64ToBytes } from './crypto';
import type { AuthTokens, VaultInfo, HealthStatus, EncryptedPayload, ShareData } from './types';

export interface Session {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  userId: string;
}

export class PSNXClient {
  private readonly baseUrl: string;
  private readonly vault: Vault;
  private readonly zkp: ZKPProver;
  private session: Session | null = null;
  
  constructor(baseUrl: string, vaultKey: Uint8Array) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.vault = new Vault(vaultKey);
    this.zkp = new ZKPProver(vaultKey);
  }
  
  /**
   * Factory async pour initialisation complete
   */
  static async create(baseUrl: string, vaultKey: Uint8Array): Promise<PSNXClient> {
    const client = new PSNXClient(baseUrl, vaultKey);
    (client as any).zkp = await ZKPProver.create(vaultKey);
    return client;
  }
  
  get isAuthenticated(): boolean {
    return this.session !== null;
  }
  
  get publicKey(): string {
    return this.zkp.getPublicKeyHex();
  }
  
  async getFingerprint(): Promise<string> {
    return this.vault.getFingerprint();
  }
  
  // ===========================================================================
  // HTTP
  // ===========================================================================
  
  private async request<T>(
    method: string,
    endpoint: string,
    body?: unknown,
    auth: boolean = true
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    if (auth && this.session) {
      headers['Authorization'] = `Bearer ${this.session.accessToken}`;
    }
    
    const options: RequestInit = {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    };
    
    try {
      const response = await fetch(url, options);
      
      if (response.status === 401) {
        throw new AuthenticationError('Authentication required or token expired');
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText })) as { detail?: string };
        throw new NetworkError(errorData.detail || 'Request failed', response.status);
      }
      
      return response.json() as Promise<T>;
    } catch (e) {
      if (e instanceof NetworkError || e instanceof AuthenticationError) {
        throw e;
      }
      throw new NetworkError(`Request failed: ${String(e)}`);
    }
  }
  
  // ===========================================================================
  // Authentication
  // ===========================================================================
  
  /**
   * Login avec ZKP
   */
  async login(userId: string): Promise<Session> {
    // 1. Demander challenge
    const challengeResp = await this.request<{ challenge: string }>(
      'POST', '/auth/challenge',
      { public_key: this.publicKey },
      false
    );
    
    // 2. Creer preuve ZKP
    const proof = await this.zkp.createProof(challengeResp.challenge);
    
    // 3. Login
    const tokens = await this.request<AuthTokens>(
      'POST', '/auth/login',
      {
        public_key: this.publicKey,
        proof,
        user_id: userId
      },
      false
    );
    
    this.session = {
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      expiresIn: tokens.expires_in,
      userId
    };
    
    return this.session;
  }
  
  /**
   * Rafraichit le token
   */
  async refresh(): Promise<Session> {
    if (!this.session) {
      throw new AuthenticationError('Not authenticated');
    }
    
    const tokens = await this.request<AuthTokens>(
      'POST', '/auth/refresh',
      { refresh_token: this.session.refreshToken },
      false
    );
    
    this.session.accessToken = tokens.access_token;
    this.session.expiresIn = tokens.expires_in;
    
    return this.session;
  }
  
  /**
   * Logout
   */
  async logout(): Promise<void> {
    if (this.session) {
      try {
        await this.request('POST', '/auth/logout');
      } catch {
        // Ignore errors
      }
      this.session = null;
    }
  }
  
  // ===========================================================================
  // Vault Operations
  // ===========================================================================
  
  /**
   * Info vault
   */
  async vaultInfo(): Promise<VaultInfo> {
    return this.request('GET', '/vault/info');
  }
  
  /**
   * Chiffre via API
   */
  async encrypt(data: Uint8Array, metadata?: Record<string, unknown>): Promise<EncryptedPayload> {
    return this.request('POST', '/vault/encrypt', {
      data: bytesToBase64(data),
      metadata
    });
  }
  
  /**
   * Dechiffre via API
   */
  async decrypt(encrypted: EncryptedPayload): Promise<Uint8Array> {
    const resp = await this.request<{ data: string }>('POST', '/vault/decrypt', encrypted);
    return base64ToBytes(resp.data);
  }
  
  /**
   * Chiffrement local (plus secure)
   */
  async encryptLocal(data: Uint8Array): Promise<EncryptedData> {
    return this.vault.encrypt(data);
  }
  
  /**
   * Dechiffrement local
   */
  async decryptLocal(encrypted: EncryptedData): Promise<Uint8Array> {
    return this.vault.decrypt(encrypted);
  }
  
  // ===========================================================================
  // Secret Sharing
  // ===========================================================================
  
  /**
   * Cree des parts via API
   */
  async createShares(
    threshold: number = 3,
    total: number = 5,
    guardianNames?: string[]
  ): Promise<{ shares: ShareData[]; threshold: number; total: number }> {
    return this.request('POST', '/vault/shares', {
      threshold,
      total,
      guardian_names: guardianNames
    });
  }
  
  /**
   * Cree des parts localement
   */
  async createSharesLocal(threshold: number = 3, total: number = 5): Promise<Share[]> {
    const shareKey = await this.vault.deriveSubkey('sharing');
    const ss = new SecretSharing(threshold, total);
    return ss.split(shareKey);
  }
  
  // ===========================================================================
  // Health
  // ===========================================================================
  
  async health(): Promise<HealthStatus> {
    return this.request('GET', '/health', undefined, false);
  }
  
  async ping(): Promise<boolean> {
    try {
      await this.health();
      return true;
    } catch {
      return false;
    }
  }
}
