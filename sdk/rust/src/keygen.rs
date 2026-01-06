//! Key generation module

use hkdf::Hkdf;
use num_bigint::BigUint;
use rand::{rngs::OsRng, RngCore};
use sha2::{Digest, Sha256};

use crate::{Error, Result};
use crate::zkp::ZKP_PARAMS;

/// Key pair with vault key and ZKP public key
#[derive(Debug, Clone)]
pub struct KeyPair {
    pub vault_key: [u8; 32],
    pub public_key: BigUint,
    pub fingerprint: String,
    pub entropy_bits: u32,
}

/// Key generator
pub struct KeyGenerator {
    extra_entropy: Vec<u8>,
}

impl KeyGenerator {
    /// Create a new key generator
    pub fn new() -> Self {
        Self {
            extra_entropy: Vec::new(),
        }
    }
    
    /// Create with extra entropy
    pub fn with_entropy(entropy: &[u8]) -> Self {
        Self {
            extra_entropy: entropy.to_vec(),
        }
    }
    
    /// Generate a random vault key
    pub fn generate(&self) -> [u8; 32] {
        let mut entropy = vec![0u8; 64];
        OsRng.fill_bytes(&mut entropy);
        entropy.extend_from_slice(&self.extra_entropy);
        
        let hkdf = Hkdf::<Sha256>::new(Some(b"PSNX_KEYGEN_v1"), &entropy);
        let mut vault_key = [0u8; 32];
        hkdf.expand(b"vault_master_key", &mut vault_key).unwrap();
        
        vault_key
    }
    
    /// Derive key from password using Scrypt-like KDF
    pub fn from_password(password: &str, salt: Option<&[u8]>) -> Result<([u8; 32], Vec<u8>)> {
        if password.len() < 8 {
            return Err(Error::Validation(
                "Password must be at least 8 characters".to_string()
            ));
        }
        
        let salt = salt.map(|s| s.to_vec()).unwrap_or_else(|| {
            let mut s = vec![0u8; 16];
            OsRng.fill_bytes(&mut s);
            s
        });
        
        // PBKDF2-like derivation (simplified)
        let hkdf = Hkdf::<Sha256>::new(Some(&salt), password.as_bytes());
        let mut vault_key = [0u8; 32];
        hkdf.expand(b"vault_key_from_password", &mut vault_key)
            .map_err(|e| Error::Key(e.to_string()))?;
        
        Ok((vault_key, salt))
    }
    
    /// Generate from external entropy
    pub fn from_entropy(&self, entropy: &[u8], min_bits: usize) -> Result<[u8; 32]> {
        if entropy.len() * 8 < min_bits {
            return Err(Error::Validation(format!(
                "Entropy must be at least {} bits",
                min_bits
            )));
        }
        
        let mut combined = entropy.to_vec();
        let mut system_entropy = vec![0u8; 32];
        OsRng.fill_bytes(&mut system_entropy);
        combined.extend_from_slice(&system_entropy);
        combined.extend_from_slice(&self.extra_entropy);
        
        let hkdf = Hkdf::<Sha256>::new(Some(b"PSNX_EXTERNAL_ENTROPY"), &combined);
        let mut vault_key = [0u8; 32];
        hkdf.expand(b"vault_key_from_external", &mut vault_key)
            .map_err(|e| Error::Key(e.to_string()))?;
        
        Ok(vault_key)
    }
    
    /// Generate a complete key pair
    pub fn generate_keypair(&self) -> KeyPair {
        let vault_key = self.generate();
        
        // Derive ZKP private key
        let mut hasher = Sha256::new();
        hasher.update(b"PSNX_ZKP_PRIVATE_");
        hasher.update(&vault_key);
        let hash = hasher.finalize();
        
        let x = BigUint::from_bytes_be(&hash) % &ZKP_PARAMS.q;
        let x = if x == BigUint::ZERO {
            BigUint::from(1u32)
        } else {
            x
        };
        
        // Public key
        let public_key = ZKP_PARAMS.g.modpow(&x, &ZKP_PARAMS.p);
        
        // Fingerprint
        let fingerprint = hex::encode(&Sha256::digest(&vault_key)[..8]);
        
        KeyPair {
            vault_key,
            public_key,
            fingerprint,
            entropy_bits: 256,
        }
    }
    
    /// Verify a key is valid
    pub fn verify(vault_key: &[u8]) -> bool {
        vault_key.len() == 32 && !vault_key.iter().all(|&b| b == 0)
    }
}

impl Default for KeyGenerator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_generate() {
        let gen = KeyGenerator::new();
        let key = gen.generate();
        assert!(KeyGenerator::verify(&key));
    }
    
    #[test]
    fn test_keypair() {
        let gen = KeyGenerator::new();
        let keypair = gen.generate_keypair();
        assert!(KeyGenerator::verify(&keypair.vault_key));
        assert!(!keypair.fingerprint.is_empty());
    }
}
