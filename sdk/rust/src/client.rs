//! HTTP Client for API

use serde::{Deserialize, Serialize};

use crate::{Error, Result, Vault, ZKPProver, SecretSharing, Share, EncryptedData};

/// Session data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub access_token: String,
    pub refresh_token: String,
    pub expires_in: u64,
    pub user_id: String,
}

#[derive(Debug, Deserialize)]
struct ChallengeResponse {
    challenge: String,
}

#[derive(Debug, Deserialize)]
struct TokenResponse {
    access_token: String,
    refresh_token: String,
    expires_in: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VaultInfo {
    pub user_id: String,
    pub vault_initialized: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub security_score: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthStatus {
    pub status: String,
    pub version: String,
    pub timestamp: String,
}

/// API Client
pub struct PSNXClient {
    base_url: String,
    vault: Vault,
    zkp: ZKPProver,
    session: Option<Session>,
    client: reqwest::Client,
}

impl PSNXClient {
    /// Create a new client
    pub fn new(base_url: &str, vault_key: &[u8]) -> Result<Self> {
        Ok(Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            vault: Vault::new(vault_key)?,
            zkp: ZKPProver::new(vault_key)?,
            session: None,
            client: reqwest::Client::new(),
        })
    }
    
    /// Check if authenticated
    pub fn is_authenticated(&self) -> bool {
        self.session.is_some()
    }
    
    /// Get public key
    pub fn public_key(&self) -> String {
        self.zkp.public_key_hex()
    }
    
    /// Get fingerprint
    pub fn fingerprint(&self) -> String {
        self.vault.fingerprint()
    }
    
    // =========================================================================
    // Authentication
    // =========================================================================
    
    /// Login with ZKP
    pub async fn login(&mut self, user_id: &str) -> Result<Session> {
        // 1. Request challenge
        let challenge_resp: ChallengeResponse = self.client
            .post(format!("{}/auth/challenge", self.base_url))
            .json(&serde_json::json!({
                "public_key": self.public_key()
            }))
            .send()
            .await
            .map_err(|e| Error::Network(e.to_string()))?
            .json()
            .await
            .map_err(|e| Error::Network(e.to_string()))?;
        
        // 2. Create ZKP proof
        let proof = self.zkp.create_proof(&challenge_resp.challenge)?;
        
        // 3. Login
        let token_resp: TokenResponse = self.client
            .post(format!("{}/auth/login", self.base_url))
            .json(&serde_json::json!({
                "public_key": self.public_key(),
                "proof": proof,
                "user_id": user_id
            }))
            .send()
            .await
            .map_err(|e| Error::Network(e.to_string()))?
            .json()
            .await
            .map_err(|e| Error::Network(e.to_string()))?;
        
        let session = Session {
            access_token: token_resp.access_token,
            refresh_token: token_resp.refresh_token,
            expires_in: token_resp.expires_in,
            user_id: user_id.to_string(),
        };
        
        self.session = Some(session.clone());
        Ok(session)
    }
    
    /// Refresh token
    pub async fn refresh(&mut self) -> Result<Session> {
        let session = self.session.as_ref()
            .ok_or_else(|| Error::Authentication("Not authenticated".to_string()))?;
        
        let token_resp: TokenResponse = self.client
            .post(format!("{}/auth/refresh", self.base_url))
            .json(&serde_json::json!({
                "refresh_token": session.refresh_token
            }))
            .send()
            .await
            .map_err(|e| Error::Network(e.to_string()))?
            .json()
            .await
            .map_err(|e| Error::Network(e.to_string()))?;
        
        if let Some(ref mut s) = self.session {
            s.access_token = token_resp.access_token;
            s.expires_in = token_resp.expires_in;
        }
        
        Ok(self.session.clone().unwrap())
    }
    
    /// Logout
    pub async fn logout(&mut self) -> Result<()> {
        if let Some(ref session) = self.session {
            let _ = self.client
                .post(format!("{}/auth/logout", self.base_url))
                .bearer_auth(&session.access_token)
                .send()
                .await;
        }
        self.session = None;
        Ok(())
    }
    
    // =========================================================================
    // Vault Operations
    // =========================================================================
    
    /// Get vault info
    pub async fn vault_info(&self) -> Result<VaultInfo> {
        let session = self.session.as_ref()
            .ok_or_else(|| Error::Authentication("Not authenticated".to_string()))?;
        
        self.client
            .get(format!("{}/vault/info", self.base_url))
            .bearer_auth(&session.access_token)
            .send()
            .await
            .map_err(|e| Error::Network(e.to_string()))?
            .json()
            .await
            .map_err(|e| Error::Network(e.to_string()))
    }
    
    /// Encrypt locally
    pub fn encrypt_local(&self, data: &[u8]) -> Result<EncryptedData> {
        self.vault.encrypt(data)
    }
    
    /// Decrypt locally
    pub fn decrypt_local(&self, encrypted: &EncryptedData) -> Result<Vec<u8>> {
        self.vault.decrypt(encrypted)
    }
    
    // =========================================================================
    // Secret Sharing
    // =========================================================================
    
    /// Create shares locally
    pub fn create_shares_local(&self, threshold: u8, total: u8) -> Result<Vec<Share>> {
        let share_key = self.vault.derive_subkey("sharing")?;
        let ss = SecretSharing::new(threshold, total)?;
        ss.split(&share_key)
    }
    
    // =========================================================================
    // Health
    // =========================================================================
    
    /// Health check
    pub async fn health(&self) -> Result<HealthStatus> {
        self.client
            .get(format!("{}/health", self.base_url))
            .send()
            .await
            .map_err(|e| Error::Network(e.to_string()))?
            .json()
            .await
            .map_err(|e| Error::Network(e.to_string()))
    }
    
    /// Ping
    pub async fn ping(&self) -> bool {
        self.health().await.is_ok()
    }
}
