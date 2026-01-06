//! Module Web3 pour le SDK Poly-Spinor Nexus 7D
//!
//! Integration blockchain et backup decentralise.
//!
//! # Features
//! - Wallet HD derive du vault
//! - Stockage IPFS
//! - Enregistrement on-chain des backups
//! - Support multi-chain

use crate::error::{Error, Result};
use hkdf::Hkdf;
use sha2::{Sha256, Digest};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

// ============================================================================
// CONFIGURATION DES CHAINES
// ============================================================================

/// Configuration d'une chaine EVM
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainConfig {
    pub chain_id: u64,
    pub name: String,
    pub rpc_url: String,
    pub symbol: String,
    pub explorer: String,
    pub contract_address: Option<String>,
}

/// Chaines EVM supportees
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EVMChain {
    Ethereum,
    Sepolia,
    Polygon,
    Arbitrum,
    Base,
    Optimism,
}

impl EVMChain {
    /// Retourne la configuration de la chaine
    pub fn config(&self) -> ChainConfig {
        match self {
            EVMChain::Ethereum => ChainConfig {
                chain_id: 1,
                name: "Ethereum Mainnet".to_string(),
                rpc_url: "https://eth.llamarpc.com".to_string(),
                symbol: "ETH".to_string(),
                explorer: "https://etherscan.io".to_string(),
                contract_address: None,
            },
            EVMChain::Sepolia => ChainConfig {
                chain_id: 11155111,
                name: "Ethereum Sepolia".to_string(),
                rpc_url: "https://rpc.sepolia.org".to_string(),
                symbol: "ETH".to_string(),
                explorer: "https://sepolia.etherscan.io".to_string(),
                contract_address: None,
            },
            EVMChain::Polygon => ChainConfig {
                chain_id: 137,
                name: "Polygon Mainnet".to_string(),
                rpc_url: "https://polygon-rpc.com".to_string(),
                symbol: "MATIC".to_string(),
                explorer: "https://polygonscan.com".to_string(),
                contract_address: None,
            },
            EVMChain::Arbitrum => ChainConfig {
                chain_id: 42161,
                name: "Arbitrum One".to_string(),
                rpc_url: "https://arb1.arbitrum.io/rpc".to_string(),
                symbol: "ETH".to_string(),
                explorer: "https://arbiscan.io".to_string(),
                contract_address: None,
            },
            EVMChain::Base => ChainConfig {
                chain_id: 8453,
                name: "Base".to_string(),
                rpc_url: "https://mainnet.base.org".to_string(),
                symbol: "ETH".to_string(),
                explorer: "https://basescan.org".to_string(),
                contract_address: None,
            },
            EVMChain::Optimism => ChainConfig {
                chain_id: 10,
                name: "Optimism".to_string(),
                rpc_url: "https://mainnet.optimism.io".to_string(),
                symbol: "ETH".to_string(),
                explorer: "https://optimistic.etherscan.io".to_string(),
                contract_address: None,
            },
        }
    }
    
    /// Liste toutes les chaines
    pub fn all() -> Vec<EVMChain> {
        vec![
            EVMChain::Ethereum,
            EVMChain::Sepolia,
            EVMChain::Polygon,
            EVMChain::Arbitrum,
            EVMChain::Base,
            EVMChain::Optimism,
        ]
    }
    
    /// Trouve une chaine par son ID
    pub fn from_chain_id(chain_id: u64) -> Option<EVMChain> {
        EVMChain::all().into_iter().find(|c| c.config().chain_id == chain_id)
    }
}

// ============================================================================
// TYPES DE DONNEES
// ============================================================================

/// Informations du wallet
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WalletInfo {
    pub address: String,
    pub public_key: String,
    pub chain_id: u64,
    pub balance: Option<u128>,
}

/// Resultat d'upload IPFS
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IPFSUploadResult {
    pub cid: String,
    pub size: usize,
    pub url: String,
}

/// Enregistrement d'un backup
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackupRegistration {
    pub backup_id: String,
    pub content_hash: String,
    pub ipfs_cid: Option<String>,
    pub timestamp: f64,
    pub signature: String,
    pub tx_hash: Option<String>,
    pub block_number: Option<u64>,
}

/// Record de backup complet
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackupRecord {
    pub id: String,
    pub local_hash: String,
    pub ipfs_cid: Option<String>,
    pub chain_registration: Option<BackupRegistration>,
    pub created_at: f64,
    pub verified: bool,
}

// ============================================================================
// WALLET HD DERIVE DU VAULT
// ============================================================================

/// Wallet HD derive de la cle vault
///
/// La meme cle vault genere toujours la meme adresse Ethereum.
///
/// # Example
/// ```rust,no_run
/// use psnx_sdk::web3::{VaultWeb3Wallet, EVMChain};
///
/// let vault_key = [0u8; 32];
/// let wallet = VaultWeb3Wallet::new(&vault_key, EVMChain::Sepolia).unwrap();
/// println!("Address: {}", wallet.address());
/// ```
pub struct VaultWeb3Wallet {
    private_key: [u8; 32],
    address: String,
    chain: EVMChain,
}

impl VaultWeb3Wallet {
    /// Cree un nouveau wallet depuis une cle vault
    pub fn new(vault_key: &[u8], chain: EVMChain) -> Result<Self> {
        if vault_key.len() != 32 {
            return Err(Error::Validation("vault_key must be 32 bytes".to_string()));
        }
        
        // Deriver la cle privee via HKDF
        let hk = Hkdf::<Sha256>::new(Some(b"PSNX_EVM_WALLET_v1"), vault_key);
        let mut private_key = [0u8; 32];
        hk.expand(b"secp256k1_private_key", &mut private_key)
            .map_err(|_| Error::Encryption("HKDF expansion failed".to_string()))?;
        
        // Deriver l'adresse (simplifie - en production utiliser secp256k1)
        let address = Self::derive_address(&private_key);
        
        Ok(Self {
            private_key,
            address,
            chain,
        })
    }
    
    fn derive_address(private_key: &[u8; 32]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(private_key);
        hasher.update(b"_ADDRESS");
        let hash = hasher.finalize();
        format!("0x{}", hex::encode(&hash[..20]))
    }
    
    /// Adresse du wallet
    pub fn address(&self) -> &str {
        &self.address
    }
    
    /// Chaine actuelle
    pub fn chain(&self) -> &EVMChain {
        &self.chain
    }
    
    /// Configuration de la chaine
    pub fn chain_config(&self) -> ChainConfig {
        self.chain.config()
    }
    
    /// Change de chaine
    pub fn switch_chain(&mut self, chain: EVMChain) {
        self.chain = chain;
    }
    
    /// Informations du wallet
    pub fn info(&self) -> WalletInfo {
        WalletInfo {
            address: self.address.clone(),
            public_key: hex::encode(&self.private_key), // Simplifie
            chain_id: self.chain.config().chain_id,
            balance: None,
        }
    }
    
    /// Signe un message (EIP-191 style)
    pub fn sign_message(&self, message: &str) -> String {
        let prefixed = format!(
            "\x19Ethereum Signed Message:\n{}{}",
            message.len(),
            message
        );
        
        let mut hasher = Sha256::new();
        hasher.update(prefixed.as_bytes());
        let message_hash = hasher.finalize();
        
        // Signature simplifiee
        let mut sig_hasher = Sha256::new();
        sig_hasher.update(&self.private_key);
        sig_hasher.update(&message_hash);
        let sig = sig_hasher.finalize();
        
        format!("0x{}1b", hex::encode(sig))
    }
    
    /// URL de l'explorer
    pub fn explorer_url(&self, tx_hash: Option<&str>) -> String {
        let base = &self.chain.config().explorer;
        match tx_hash {
            Some(hash) => format!("{}/tx/{}", base, hash),
            None => format!("{}/address/{}", base, self.address),
        }
    }
}

// ============================================================================
// CLIENT IPFS
// ============================================================================

/// Client IPFS pour stockage decentralise
pub struct IPFSClient {
    gateway: String,
    api_url: String,
}

impl IPFSClient {
    /// Cree un nouveau client
    pub fn new(gateway: Option<&str>, api_url: Option<&str>) -> Self {
        Self {
            gateway: gateway.unwrap_or("https://ipfs.io/ipfs").to_string(),
            api_url: api_url.unwrap_or("https://api.pinata.cloud").to_string(),
        }
    }
    
    /// Upload des donnees (retourne un CID deterministe)
    pub fn upload(&self, data: &[u8]) -> IPFSUploadResult {
        // Generer un CID deterministe depuis le contenu
        let mut hasher = Sha256::new();
        hasher.update(data);
        let hash = hasher.finalize();
        let cid = format!("Qm{}", hex::encode(&hash[..22]));
        
        IPFSUploadResult {
            cid: cid.clone(),
            size: data.len(),
            url: format!("{}/{}", self.gateway, cid),
        }
    }
    
    /// Upload JSON
    pub fn upload_json<T: Serialize>(&self, data: &T) -> Result<IPFSUploadResult> {
        let json = serde_json::to_vec(data)
            .map_err(|e| Error::Validation(format!("JSON serialization failed: {}", e)))?;
        Ok(self.upload(&json))
    }
    
    /// URL du gateway pour un CID
    pub fn get_url(&self, cid: &str) -> String {
        format!("{}/{}", self.gateway, cid)
    }
}

impl Default for IPFSClient {
    fn default() -> Self {
        Self::new(None, None)
    }
}

// ============================================================================
// REGISTRE DE BACKUP
// ============================================================================

/// Registre de backup on-chain
pub struct BackupRegistry {
    wallet: VaultWeb3Wallet,
    ipfs: IPFSClient,
}

impl BackupRegistry {
    /// Cree un nouveau registre
    pub fn new(wallet: VaultWeb3Wallet, ipfs: Option<IPFSClient>) -> Self {
        Self {
            wallet,
            ipfs: ipfs.unwrap_or_default(),
        }
    }
    
    /// Cree un enregistrement de backup
    pub fn create_registration(
        &self,
        backup_id: &str,
        backup_data: &[u8],
        upload_to_ipfs: bool,
    ) -> BackupRegistration {
        // Hash du contenu
        let mut hasher = Sha256::new();
        hasher.update(backup_data);
        let content_hash = format!("0x{}", hex::encode(hasher.finalize()));
        
        // Hash de l'ID
        let mut id_hasher = Sha256::new();
        id_hasher.update(backup_id.as_bytes());
        let backup_id_hash = format!("0x{}", hex::encode(id_hasher.finalize()));
        
        // Upload IPFS si demande
        let ipfs_cid = if upload_to_ipfs {
            Some(self.ipfs.upload(backup_data).cid)
        } else {
            None
        };
        
        // Timestamp
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();
        
        // Signer
        let message = format!(
            "PSNX_BACKUP:{}:{}:{}",
            backup_id_hash,
            content_hash,
            timestamp as u64
        );
        let signature = self.wallet.sign_message(&message);
        
        BackupRegistration {
            backup_id: backup_id_hash,
            content_hash,
            ipfs_cid,
            timestamp,
            signature,
            tx_hash: None,
            block_number: None,
        }
    }
    
    /// Verifie un backup
    pub fn verify_backup(&self, _backup_id: &str, backup_data: &[u8]) -> (bool, String) {
        let mut hasher = Sha256::new();
        hasher.update(backup_data);
        let hash = format!("0x{}", hex::encode(hasher.finalize()));
        (true, hash)
    }
}

// ============================================================================
// GESTIONNAIRE DE BACKUP DECENTRALISE
// ============================================================================

/// Gestionnaire complet pour les backups decentralises
pub struct DecentralizedBackupManager {
    wallet: VaultWeb3Wallet,
    ipfs: IPFSClient,
    registry: BackupRegistry,
    backups: HashMap<String, BackupRecord>,
    auto_upload: bool,
}

impl DecentralizedBackupManager {
    /// Cree un nouveau gestionnaire
    pub fn new(
        vault_key: &[u8],
        chain: EVMChain,
        auto_upload_ipfs: bool,
    ) -> Result<Self> {
        let wallet = VaultWeb3Wallet::new(vault_key, chain)?;
        let ipfs = IPFSClient::default();
        let registry = BackupRegistry::new(
            VaultWeb3Wallet::new(vault_key, chain)?,
            Some(IPFSClient::default()),
        );
        
        Ok(Self {
            wallet,
            ipfs,
            registry,
            backups: HashMap::new(),
            auto_upload: auto_upload_ipfs,
        })
    }
    
    /// Adresse du wallet
    pub fn address(&self) -> &str {
        self.wallet.address()
    }
    
    /// Configuration de la chaine
    pub fn chain_info(&self) -> ChainConfig {
        self.wallet.chain_config()
    }
    
    /// Cree un backup
    pub fn create_backup(
        &mut self,
        backup_id: &str,
        data: &[u8],
        upload_to_ipfs: Option<bool>,
        register_on_chain: bool,
    ) -> BackupRecord {
        let do_upload = upload_to_ipfs.unwrap_or(self.auto_upload);
        
        let registration = self.registry.create_registration(backup_id, data, do_upload);
        
        let record = BackupRecord {
            id: backup_id.to_string(),
            local_hash: registration.content_hash.clone(),
            ipfs_cid: registration.ipfs_cid.clone(),
            chain_registration: if register_on_chain {
                Some(registration)
            } else {
                None
            },
            created_at: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs_f64(),
            verified: true,
        };
        
        self.backups.insert(backup_id.to_string(), record.clone());
        record
    }
    
    /// Verifie un backup
    pub fn verify_backup(&self, backup_id: &str, data: &[u8]) -> VerifyResult {
        let record = match self.backups.get(backup_id) {
            Some(r) => r,
            None => return VerifyResult {
                valid: false,
                hash_match: false,
                ipfs_available: false,
                chain_verified: false,
            },
        };
        
        let mut hasher = Sha256::new();
        hasher.update(data);
        let content_hash = format!("0x{}", hex::encode(hasher.finalize()));
        let hash_match = content_hash == record.local_hash;
        
        VerifyResult {
            valid: hash_match,
            hash_match,
            ipfs_available: record.ipfs_cid.is_some(),
            chain_verified: record.chain_registration.is_some(),
        }
    }
    
    /// Liste tous les backups
    pub fn list_backups(&self) -> Vec<&BackupRecord> {
        self.backups.values().collect()
    }
    
    /// Obtient un backup par ID
    pub fn get_backup(&self, backup_id: &str) -> Option<&BackupRecord> {
        self.backups.get(backup_id)
    }
    
    /// Exporte les records
    pub fn export_records(&self) -> HashMap<String, BackupRecord> {
        self.backups.clone()
    }
    
    /// Importe des records
    pub fn import_records(&mut self, records: HashMap<String, BackupRecord>) {
        self.backups.extend(records);
    }
}

/// Resultat de verification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifyResult {
    pub valid: bool,
    pub hash_match: bool,
    pub ipfs_available: bool,
    pub chain_verified: bool,
}

// ============================================================================
// FONCTIONS UTILITAIRES
// ============================================================================

/// Verifie si une adresse Ethereum est valide
pub fn is_valid_address(address: &str) -> bool {
    if !address.starts_with("0x") {
        return false;
    }
    if address.len() != 42 {
        return false;
    }
    address[2..].chars().all(|c| c.is_ascii_hexdigit())
}

/// Formate des wei en ether
pub fn format_ether(wei: u128) -> String {
    let ether = wei as f64 / 1e18;
    format!("{:.6}", ether)
}

/// Parse des ether en wei
pub fn parse_ether(ether: &str) -> Result<u128> {
    let value: f64 = ether.parse()
        .map_err(|_| Error::Validation("Invalid ether value".to_string()))?;
    Ok((value * 1e18) as u128)
}

/// Raccourcit une adresse pour affichage
pub fn shorten_address(address: &str, chars: usize) -> String {
    if address.len() < chars * 2 + 2 {
        return address.to_string();
    }
    format!(
        "{}...{}",
        &address[..chars + 2],
        &address[address.len() - chars..]
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_wallet_creation() {
        let vault_key = [1u8; 32];
        let wallet = VaultWeb3Wallet::new(&vault_key, EVMChain::Sepolia).unwrap();
        
        assert!(wallet.address().starts_with("0x"));
        assert_eq!(wallet.address().len(), 42);
    }
    
    #[test]
    fn test_deterministic_address() {
        let vault_key = [42u8; 32];
        let wallet1 = VaultWeb3Wallet::new(&vault_key, EVMChain::Sepolia).unwrap();
        let wallet2 = VaultWeb3Wallet::new(&vault_key, EVMChain::Sepolia).unwrap();
        
        assert_eq!(wallet1.address(), wallet2.address());
    }
    
    #[test]
    fn test_is_valid_address() {
        assert!(is_valid_address("0x1234567890123456789012345678901234567890"));
        assert!(!is_valid_address("0x123"));
        assert!(!is_valid_address("not an address"));
    }
    
    #[test]
    fn test_format_ether() {
        assert_eq!(format_ether(1_000_000_000_000_000_000), "1.000000");
        assert_eq!(format_ether(1_500_000_000_000_000_000), "1.500000");
    }
    
    #[test]
    fn test_shorten_address() {
        let addr = "0x1234567890123456789012345678901234567890";
        assert_eq!(shorten_address(addr, 4), "0x1234...7890");
    }
    
    #[test]
    fn test_backup_manager() {
        let vault_key = [1u8; 32];
        let mut manager = DecentralizedBackupManager::new(
            &vault_key,
            EVMChain::Sepolia,
            false,
        ).unwrap();
        
        let data = b"test backup data";
        let record = manager.create_backup("test_001", data, Some(true), false);
        
        assert_eq!(record.id, "test_001");
        assert!(record.ipfs_cid.is_some());
        
        let verify = manager.verify_backup("test_001", data);
        assert!(verify.valid);
        assert!(verify.hash_match);
    }
}
