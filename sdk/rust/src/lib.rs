//! # Poly-Spinor Nexus 7D SDK
//!
//! SDK officiel pour interagir avec l'API Poly-Spinor Nexus 7D.
//!
//! ## Example
//!
//! ```rust,no_run
//! use psnx_sdk::{KeyGenerator, Vault, SecretSharing};
//!
//! // Generer une cle
//! let key_gen = KeyGenerator::new();
//! let vault_key = key_gen.generate();
//!
//! // Creer un vault
//! let vault = Vault::new(&vault_key).unwrap();
//! let encrypted = vault.encrypt(b"secret data").unwrap();
//! let decrypted = vault.decrypt(&encrypted).unwrap();
//!
//! // Partage de secret
//! let ss = SecretSharing::new(3, 5).unwrap();
//! let shares = ss.split(&vault_key).unwrap();
//! let recovered = ss.reconstruct(&shares[0..3]).unwrap();
//! ```

mod error;
mod vault;
mod keygen;
mod sharing;
mod zkp;
pub mod web3;
#[cfg(feature = "client")]
mod client;

pub use error::{Error, Result};
pub use vault::{Vault, EncryptedData};
pub use keygen::{KeyGenerator, KeyPair};
pub use sharing::{SecretSharing, Share};
pub use zkp::{ZKPProver, ZKPVerifier, ZKPProof};
pub use web3::{
    VaultWeb3Wallet, IPFSClient, BackupRegistry, DecentralizedBackupManager,
    EVMChain, ChainConfig, BackupRecord, BackupRegistration, VerifyResult,
    is_valid_address, format_ether, parse_ether, shorten_address,
};
#[cfg(feature = "client")]
pub use client::{PSNXClient, Session};

/// Version du SDK
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
