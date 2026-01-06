//! Zero-Knowledge Proofs (Schnorr)

use num_bigint::BigUint;
use rand::{rngs::OsRng, RngCore};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::{Error, Result};

/// ZKP parameters (RFC 5114)
pub struct ZKPParams {
    pub p: BigUint,
    pub q: BigUint,
    pub g: BigUint,
}

lazy_static::lazy_static! {
    pub static ref ZKP_PARAMS: ZKPParams = {
        let p_hex = concat!(
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1",
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD",
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245",
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED",
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D",
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F",
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D",
            "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B",
            "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9",
            "DE2BCBF6955817183995497CEA956AE515D2261898FA0510",
            "15728E5A8AACAA68FFFFFFFFFFFFFFFF"
        );
        let p = BigUint::parse_bytes(p_hex.as_bytes(), 16).unwrap();
        let q = (&p - BigUint::from(1u32)) / BigUint::from(2u32);
        let g = BigUint::from(2u32);
        
        ZKPParams { p, q, g }
    };
}

/// ZKP Proof structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZKPProof {
    pub commitment: String, // R = g^k (hex)
    pub challenge: String,  // c (hex)
    pub response: String,   // s = k + c*x (hex)
    pub public_key: String, // Y = g^x (hex)
    pub message: String,    // hex
    pub timestamp: f64,
}

/// ZKP Prover (client-side)
pub struct ZKPProver {
    x: BigUint,  // Private key
    y: BigUint,  // Public key
}

impl ZKPProver {
    /// Create a new prover from vault key
    pub fn new(vault_key: &[u8]) -> Result<Self> {
        if vault_key.len() != 32 {
            return Err(Error::Validation("vault_key must be 32 bytes".to_string()));
        }
        
        // Derive private key
        let mut hasher = Sha256::new();
        hasher.update(b"PSNX_ZKP_PRIVATE_");
        hasher.update(vault_key);
        let hash = hasher.finalize();
        
        let x = BigUint::from_bytes_be(&hash) % &ZKP_PARAMS.q;
        let x = if x == BigUint::ZERO {
            BigUint::from(1u32)
        } else {
            x
        };
        
        // Public key
        let y = ZKP_PARAMS.g.modpow(&x, &ZKP_PARAMS.p);
        
        Ok(Self { x, y })
    }
    
    /// Get public key
    pub fn public_key(&self) -> &BigUint {
        &self.y
    }
    
    /// Get public key as hex
    pub fn public_key_hex(&self) -> String {
        format!("0x{}", hex::encode(self.y.to_bytes_be()))
    }
    
    /// Get fingerprint
    pub fn fingerprint(&self) -> String {
        let hash = Sha256::digest(&self.y.to_bytes_be());
        hex::encode(&hash[..8])
    }
    
    /// Create a ZKP proof for a challenge
    pub fn create_proof(&self, challenge: &str) -> Result<serde_json::Value> {
        let message = challenge.as_bytes();
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();
        
        // Commitment: R = g^k
        let mut k_bytes = vec![0u8; 32];
        OsRng.fill_bytes(&mut k_bytes);
        let k = BigUint::from_bytes_be(&k_bytes) % &ZKP_PARAMS.q;
        let k = if k == BigUint::ZERO { BigUint::from(1u32) } else { k };
        let r = ZKP_PARAMS.g.modpow(&k, &ZKP_PARAMS.p);
        
        // Challenge: c = H(R || Y || m)
        let mut hasher = Sha256::new();
        hasher.update(&r.to_bytes_be());
        hasher.update(&self.y.to_bytes_be());
        hasher.update(message);
        let c_hash = hasher.finalize();
        let c = BigUint::from_bytes_be(&c_hash) % &ZKP_PARAMS.q;
        
        // Response: s = k + c*x mod Q
        let s = (&k + &c * &self.x) % &ZKP_PARAMS.q;
        
        let proof = ZKPProof {
            commitment: format!("0x{}", hex::encode(r.to_bytes_be())),
            challenge: format!("0x{}", hex::encode(c.to_bytes_be())),
            response: format!("0x{}", hex::encode(s.to_bytes_be())),
            public_key: self.public_key_hex(),
            message: hex::encode(message),
            timestamp,
        };
        
        Ok(serde_json::json!({
            "proof": proof,
            "challenge": challenge,
            "key_fingerprint": self.fingerprint(),
            "timestamp": timestamp
        }))
    }
}

/// ZKP Verifier (server-side)
pub struct ZKPVerifier;

impl ZKPVerifier {
    /// Verify a ZKP proof
    pub fn verify(
        auth_data: &serde_json::Value,
        expected_challenge: &str,
        max_age_seconds: f64,
    ) -> Result<(bool, String)> {
        let proof: ZKPProof = serde_json::from_value(
            auth_data["proof"].clone()
        ).map_err(|e| Error::ZKP(e.to_string()))?;
        
        // Check challenge
        if auth_data["challenge"].as_str() != Some(expected_challenge) {
            return Ok((false, "Challenge mismatch".to_string()));
        }
        
        // Check age
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();
        let age = now - proof.timestamp;
        
        if age > max_age_seconds {
            return Ok((false, format!("Proof expired (age: {:.1}s)", age)));
        }
        if age < -60.0 {
            return Ok((false, "Proof from future".to_string()));
        }
        
        // Parse values
        let r = BigUint::parse_bytes(
            proof.commitment.trim_start_matches("0x").as_bytes(), 16
        ).ok_or_else(|| Error::ZKP("Invalid commitment".to_string()))?;
        
        let c = BigUint::parse_bytes(
            proof.challenge.trim_start_matches("0x").as_bytes(), 16
        ).ok_or_else(|| Error::ZKP("Invalid challenge".to_string()))?;
        
        let s = BigUint::parse_bytes(
            proof.response.trim_start_matches("0x").as_bytes(), 16
        ).ok_or_else(|| Error::ZKP("Invalid response".to_string()))?;
        
        let y = BigUint::parse_bytes(
            proof.public_key.trim_start_matches("0x").as_bytes(), 16
        ).ok_or_else(|| Error::ZKP("Invalid public key".to_string()))?;
        
        let message = hex::decode(&proof.message)
            .map_err(|e| Error::ZKP(e.to_string()))?;
        
        // Verify challenge hash
        let mut hasher = Sha256::new();
        hasher.update(&r.to_bytes_be());
        hasher.update(&y.to_bytes_be());
        hasher.update(&message);
        let expected_c = BigUint::from_bytes_be(&hasher.finalize()) % &ZKP_PARAMS.q;
        
        if expected_c != c {
            return Ok((false, "Invalid challenge hash".to_string()));
        }
        
        // Verify: g^s == R * Y^c mod p
        let lhs = ZKP_PARAMS.g.modpow(&s, &ZKP_PARAMS.p);
        let rhs = (&r * y.modpow(&c, &ZKP_PARAMS.p)) % &ZKP_PARAMS.p;
        
        if lhs != rhs {
            return Ok((false, "Cryptographic verification failed".to_string()));
        }
        
        Ok((true, "OK".to_string()))
    }
    
    /// Verify public key is valid
    pub fn verify_public_key(public_key: &BigUint) -> bool {
        if public_key < &BigUint::from(2u32) || public_key >= &(&ZKP_PARAMS.p - BigUint::from(1u32)) {
            return false;
        }
        
        // Check subgroup membership
        public_key.modpow(&ZKP_PARAMS.q, &ZKP_PARAMS.p) == BigUint::from(1u32)
    }
}

// Add lazy_static dependency
#[macro_use]
extern crate lazy_static;

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_zkp() {
        let vault_key = [0u8; 32];
        let prover = ZKPProver::new(&vault_key).unwrap();
        
        let challenge = "test_challenge_123";
        let proof = prover.create_proof(challenge).unwrap();
        
        let (valid, reason) = ZKPVerifier::verify(&proof, challenge, 300.0).unwrap();
        assert!(valid, "ZKP failed: {}", reason);
    }
}
