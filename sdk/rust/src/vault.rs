//! Vault module for local encryption/decryption

use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use hkdf::Hkdf;
use rand::RngCore;
use serde::{Deserialize, Serialize};
use sha2::Sha256;

use crate::{Error, Result};

/// Encrypted data structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedData {
    pub ciphertext: Vec<u8>,
    pub nonce: Vec<u8>,
    pub tag: Vec<u8>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<serde_json::Value>,
}

impl EncryptedData {
    /// Convert to base64 JSON
    pub fn to_json(&self) -> Result<String> {
        Ok(serde_json::to_string(&EncryptedDataB64 {
            ciphertext: base64::encode(&self.ciphertext),
            nonce: base64::encode(&self.nonce),
            tag: base64::encode(&self.tag),
            metadata: self.metadata.clone(),
        })?)
    }
    
    /// Parse from base64 JSON
    pub fn from_json(json: &str) -> Result<Self> {
        let b64: EncryptedDataB64 = serde_json::from_str(json)?;
        Ok(Self {
            ciphertext: base64::decode(&b64.ciphertext)?,
            nonce: base64::decode(&b64.nonce)?,
            tag: base64::decode(&b64.tag)?,
            metadata: b64.metadata,
        })
    }
}

#[derive(Serialize, Deserialize)]
struct EncryptedDataB64 {
    ciphertext: String,
    nonce: String,
    tag: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    metadata: Option<serde_json::Value>,
}

/// Local vault for encryption/decryption
pub struct Vault {
    encryption_key: [u8; 32],
}

impl Vault {
    const KEY_SIZE: usize = 32;
    const NONCE_SIZE: usize = 12;
    const TAG_SIZE: usize = 16;
    
    /// Create a new vault
    pub fn new(vault_key: &[u8]) -> Result<Self> {
        if vault_key.len() != Self::KEY_SIZE {
            return Err(Error::Validation(format!(
                "vault_key must be {} bytes",
                Self::KEY_SIZE
            )));
        }
        
        // Derive encryption key
        let hkdf = Hkdf::<Sha256>::new(Some(b"PSNX_SDK_v1"), vault_key);
        let mut encryption_key = [0u8; 32];
        hkdf.expand(b"encryption", &mut encryption_key)
            .map_err(|e| Error::Key(e.to_string()))?;
        
        Ok(Self { encryption_key })
    }
    
    /// Encrypt data
    pub fn encrypt(&self, plaintext: &[u8]) -> Result<EncryptedData> {
        let cipher = Aes256Gcm::new_from_slice(&self.encryption_key)
            .map_err(|e| Error::Encryption(e.to_string()))?;
        
        // Generate nonce
        let mut nonce_bytes = [0u8; Self::NONCE_SIZE];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);
        
        // Encrypt
        let ciphertext_with_tag = cipher
            .encrypt(nonce, plaintext)
            .map_err(|e| Error::Encryption(e.to_string()))?;
        
        // Split ciphertext and tag
        let (ciphertext, tag) = ciphertext_with_tag.split_at(
            ciphertext_with_tag.len() - Self::TAG_SIZE
        );
        
        Ok(EncryptedData {
            ciphertext: ciphertext.to_vec(),
            nonce: nonce_bytes.to_vec(),
            tag: tag.to_vec(),
            metadata: None,
        })
    }
    
    /// Encrypt with metadata
    pub fn encrypt_with_metadata(
        &self,
        plaintext: &[u8],
        metadata: serde_json::Value,
    ) -> Result<EncryptedData> {
        let mut encrypted = self.encrypt(plaintext)?;
        encrypted.metadata = Some(metadata);
        Ok(encrypted)
    }
    
    /// Decrypt data
    pub fn decrypt(&self, encrypted: &EncryptedData) -> Result<Vec<u8>> {
        let cipher = Aes256Gcm::new_from_slice(&self.encryption_key)
            .map_err(|e| Error::Decryption(e.to_string()))?;
        
        let nonce = Nonce::from_slice(&encrypted.nonce);
        
        // Combine ciphertext and tag
        let mut ciphertext_with_tag = encrypted.ciphertext.clone();
        ciphertext_with_tag.extend_from_slice(&encrypted.tag);
        
        // Decrypt
        cipher
            .decrypt(nonce, ciphertext_with_tag.as_ref())
            .map_err(|e| Error::Decryption(e.to_string()))
    }
    
    /// Get vault fingerprint
    pub fn fingerprint(&self) -> String {
        use sha2::{Digest, Sha256};
        let hash = Sha256::digest(&self.encryption_key);
        hex::encode(&hash[..8])
    }
    
    /// Derive a subkey for specific purpose
    pub fn derive_subkey(&self, purpose: &str) -> Result<[u8; 32]> {
        let hkdf = Hkdf::<Sha256>::new(Some(b"PSNX_SDK_v1"), &self.encryption_key);
        let mut subkey = [0u8; 32];
        hkdf.expand(purpose.as_bytes(), &mut subkey)
            .map_err(|e| Error::Key(e.to_string()))?;
        Ok(subkey)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_encrypt_decrypt() {
        let vault_key = [0u8; 32];
        let vault = Vault::new(&vault_key).unwrap();
        
        let plaintext = b"Hello, World!";
        let encrypted = vault.encrypt(plaintext).unwrap();
        let decrypted = vault.decrypt(&encrypted).unwrap();
        
        assert_eq!(plaintext.to_vec(), decrypted);
    }
}
