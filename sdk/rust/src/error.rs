//! Error types for the SDK

use thiserror::Error;

/// SDK Error type
#[derive(Error, Debug)]
pub enum Error {
    #[error("Encryption error: {0}")]
    Encryption(String),
    
    #[error("Decryption error: {0}")]
    Decryption(String),
    
    #[error("Authentication error: {0}")]
    Authentication(String),
    
    #[error("Validation error: {0}")]
    Validation(String),
    
    #[error("Share error: {0}")]
    Share(String),
    
    #[error("Key error: {0}")]
    Key(String),
    
    #[error("ZKP error: {0}")]
    ZKP(String),
    
    #[cfg(feature = "client")]
    #[error("Network error: {0}")]
    Network(String),
    
    #[cfg(feature = "client")]
    #[error("HTTP error: {status} - {message}")]
    Http { status: u16, message: String },
    
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    
    #[error("Base64 decode error: {0}")]
    Base64(#[from] base64::DecodeError),
}

/// Result type alias
pub type Result<T> = std::result::Result<T, Error>;
