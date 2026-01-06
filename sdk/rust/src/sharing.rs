//! Shamir Secret Sharing

use num_bigint::BigUint;
use num_traits::{One, Zero};
use rand::{rngs::OsRng, RngCore};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::{Error, Result};

/// Prime for GF(p)
fn prime() -> BigUint {
    BigUint::from(2u32).pow(256) - BigUint::from(189u32)
}

/// A share of the secret
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Share {
    pub index: u8,
    pub data: Vec<u8>,
    pub threshold: u8,
    pub total: u8,
    pub checksum: String,
}

impl Share {
    /// Verify the checksum
    pub fn verify(&self) -> bool {
        let mut hasher = Sha256::new();
        hasher.update(&self.data);
        hasher.update(&[self.index]);
        let hash = hasher.finalize();
        let expected = hex::encode(&hash[..4]);
        self.checksum == expected
    }
    
    /// To base64 JSON
    pub fn to_json(&self) -> Result<String> {
        Ok(serde_json::to_string(&ShareB64 {
            index: self.index,
            data: base64::encode(&self.data),
            threshold: self.threshold,
            total: self.total,
            checksum: self.checksum.clone(),
        })?)
    }
    
    /// From base64 JSON
    pub fn from_json(json: &str) -> Result<Self> {
        let b64: ShareB64 = serde_json::from_str(json)?;
        Ok(Self {
            index: b64.index,
            data: base64::decode(&b64.data)?,
            threshold: b64.threshold,
            total: b64.total,
            checksum: b64.checksum,
        })
    }
}

#[derive(Serialize, Deserialize)]
struct ShareB64 {
    index: u8,
    data: String,
    threshold: u8,
    total: u8,
    checksum: String,
}

/// Shamir Secret Sharing scheme
pub struct SecretSharing {
    k: u8, // threshold
    n: u8, // total
}

impl SecretSharing {
    /// Create a new sharing scheme
    pub fn new(threshold: u8, total: u8) -> Result<Self> {
        if threshold < 2 {
            return Err(Error::Validation("Threshold must be >= 2".to_string()));
        }
        if total < threshold {
            return Err(Error::Validation("Total must be >= threshold".to_string()));
        }
        
        Ok(Self { k: threshold, n: total })
    }
    
    /// Split secret into N shares
    pub fn split(&self, secret: &[u8]) -> Result<Vec<Share>> {
        if secret.len() > 32 {
            return Err(Error::Validation("Secret too large (max 32 bytes)".to_string()));
        }
        
        let p = prime();
        let secret_int = BigUint::from_bytes_be(secret);
        
        // Generate polynomial coefficients
        let mut coefficients = vec![secret_int];
        for _ in 1..self.k {
            let mut rand_bytes = vec![0u8; 32];
            OsRng.fill_bytes(&mut rand_bytes);
            let coeff = BigUint::from_bytes_be(&rand_bytes) % &p;
            coefficients.push(if coeff.is_zero() { BigUint::one() } else { coeff });
        }
        
        // Evaluate at N points
        let mut shares = Vec::with_capacity(self.n as usize);
        for x in 1..=self.n {
            let x_big = BigUint::from(x);
            let y = self.evaluate(&coefficients, &x_big, &p);
            
            // Pad to 32 bytes
            let mut y_bytes = y.to_bytes_be();
            while y_bytes.len() < 32 {
                y_bytes.insert(0, 0);
            }
            
            // Checksum
            let mut hasher = Sha256::new();
            hasher.update(&y_bytes);
            hasher.update(&[x]);
            let hash = hasher.finalize();
            let checksum = hex::encode(&hash[..4]);
            
            shares.push(Share {
                index: x,
                data: y_bytes,
                threshold: self.k,
                total: self.n,
                checksum,
            });
        }
        
        Ok(shares)
    }
    
    /// Reconstruct secret from K shares
    pub fn reconstruct(&self, shares: &[Share]) -> Result<Vec<u8>> {
        if shares.len() < self.k as usize {
            return Err(Error::Share(format!(
                "Need {} shares, got {}",
                self.k,
                shares.len()
            )));
        }
        
        // Verify checksums
        for share in shares {
            if !share.verify() {
                return Err(Error::Share(format!("Share {} corrupted", share.index)));
            }
        }
        
        let p = prime();
        
        // Use first K shares
        let use_shares: Vec<_> = shares.iter().take(self.k as usize).collect();
        
        // Check uniqueness
        let mut indices: Vec<_> = use_shares.iter().map(|s| s.index).collect();
        indices.sort();
        indices.dedup();
        if indices.len() != self.k as usize {
            return Err(Error::Share("Duplicate shares".to_string()));
        }
        
        // Points (x, y)
        let points: Vec<_> = use_shares
            .iter()
            .map(|s| (BigUint::from(s.index), BigUint::from_bytes_be(&s.data)))
            .collect();
        
        // Lagrange interpolation
        let secret_int = self.lagrange(&points, &BigUint::zero(), &p);
        
        // Convert to bytes
        let mut bytes = secret_int.to_bytes_be();
        
        // Remove leading zeros but keep at least one byte
        while bytes.len() > 1 && bytes[0] == 0 {
            bytes.remove(0);
        }
        
        Ok(bytes)
    }
    
    fn evaluate(&self, coefficients: &[BigUint], x: &BigUint, p: &BigUint) -> BigUint {
        let mut result = BigUint::zero();
        let mut x_power = BigUint::one();
        
        for coeff in coefficients {
            result = (&result + coeff * &x_power) % p;
            x_power = (&x_power * x) % p;
        }
        
        result
    }
    
    fn lagrange(&self, points: &[(BigUint, BigUint)], x: &BigUint, p: &BigUint) -> BigUint {
        let mut result = BigUint::zero();
        
        for (i, (xi, yi)) in points.iter().enumerate() {
            let mut num = BigUint::one();
            let mut den = BigUint::one();
            
            for (j, (xj, _)) in points.iter().enumerate() {
                if i != j {
                    // num = num * (x - xj)
                    let diff = if x >= xj {
                        x - xj
                    } else {
                        p - (xj - x) % p
                    };
                    num = (&num * &diff) % p;
                    
                    // den = den * (xi - xj)
                    let diff = if xi >= xj {
                        xi - xj
                    } else {
                        p - (xj - xi) % p
                    };
                    den = (&den * &diff) % p;
                }
            }
            
            // Modular inverse
            let den_inv = self.mod_inverse(&den, p);
            let coeff = (&num * &den_inv) % p;
            result = (&result + yi * &coeff) % p;
        }
        
        result
    }
    
    fn mod_inverse(&self, a: &BigUint, m: &BigUint) -> BigUint {
        // Extended Euclidean algorithm using Fermat's little theorem
        // a^(-1) = a^(p-2) mod p for prime p
        let exp = m - BigUint::from(2u32);
        a.modpow(&exp, m)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_split_reconstruct() {
        let ss = SecretSharing::new(3, 5).unwrap();
        let secret = b"my secret key!!!"; // 16 bytes
        
        let shares = ss.split(secret).unwrap();
        assert_eq!(shares.len(), 5);
        
        // Reconstruct with 3 shares
        let recovered = ss.reconstruct(&shares[0..3]).unwrap();
        assert_eq!(secret.to_vec(), recovered);
    }
}
