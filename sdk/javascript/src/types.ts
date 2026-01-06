/**
 * Types communs pour le SDK
 */

export interface EncryptedPayload {
  ciphertext: string; // Base64
  nonce: string;      // Base64
  tag: string;        // Base64
  metadata?: Record<string, unknown>;
}

export interface ShareData {
  index: number;
  data: string;       // Base64
  threshold: number;
  total: number;
  checksum: string;
}

export interface AuthChallenge {
  challenge: string;
  expires_in: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface VaultInfo {
  user_id: string;
  vault_initialized: boolean;
  security_score?: string;
  features?: Record<string, unknown>;
}

export interface HealthStatus {
  status: string;
  version: string;
  timestamp: string;
}
