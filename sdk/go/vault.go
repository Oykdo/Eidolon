package psnx

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"io"

	"golang.org/x/crypto/hkdf"
)

const (
	// KeySize is the required vault key size in bytes
	KeySize = 32
	// NonceSize is the AES-GCM nonce size
	NonceSize = 12
	// TagSize is the AES-GCM authentication tag size
	TagSize = 16
)

// EncryptedData represents encrypted data with metadata
type EncryptedData struct {
	Ciphertext []byte                 `json:"ciphertext"`
	Nonce      []byte                 `json:"nonce"`
	Tag        []byte                 `json:"tag"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

// ToJSON serializes the encrypted data to JSON
func (e *EncryptedData) ToJSON() ([]byte, error) {
	return json.Marshal(map[string]interface{}{
		"ciphertext": base64.StdEncoding.EncodeToString(e.Ciphertext),
		"nonce":      base64.StdEncoding.EncodeToString(e.Nonce),
		"tag":        base64.StdEncoding.EncodeToString(e.Tag),
		"metadata":   e.Metadata,
	})
}

// EncryptedDataFromJSON deserializes encrypted data from JSON
func EncryptedDataFromJSON(data []byte) (*EncryptedData, error) {
	var raw map[string]interface{}
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, err
	}

	ciphertext, err := base64.StdEncoding.DecodeString(raw["ciphertext"].(string))
	if err != nil {
		return nil, err
	}

	nonce, err := base64.StdEncoding.DecodeString(raw["nonce"].(string))
	if err != nil {
		return nil, err
	}

	tag, err := base64.StdEncoding.DecodeString(raw["tag"].(string))
	if err != nil {
		return nil, err
	}

	metadata, _ := raw["metadata"].(map[string]interface{})

	return &EncryptedData{
		Ciphertext: ciphertext,
		Nonce:      nonce,
		Tag:        tag,
		Metadata:   metadata,
	}, nil
}

// Vault provides encryption and decryption using AES-256-GCM
type Vault struct {
	masterKey     []byte
	encryptionKey []byte
}

// NewVault creates a new Vault with the given vault key
func NewVault(vaultKey []byte) (*Vault, error) {
	if len(vaultKey) != KeySize {
		return nil, errors.New("vault key must be 32 bytes")
	}

	v := &Vault{
		masterKey: make([]byte, KeySize),
	}
	copy(v.masterKey, vaultKey)

	// Derive encryption key using HKDF
	encKey, err := v.deriveKey([]byte("encryption"))
	if err != nil {
		return nil, err
	}
	v.encryptionKey = encKey

	return v, nil
}

func (v *Vault) deriveKey(purpose []byte) ([]byte, error) {
	hkdfReader := hkdf.New(sha256.New, v.masterKey, []byte("PSNX_SDK_v1"), purpose)
	key := make([]byte, KeySize)
	if _, err := io.ReadFull(hkdfReader, key); err != nil {
		return nil, err
	}
	return key, nil
}

// Encrypt encrypts plaintext using AES-256-GCM
func (v *Vault) Encrypt(plaintext []byte) (*EncryptedData, error) {
	return v.EncryptWithMetadata(plaintext, nil)
}

// EncryptWithMetadata encrypts plaintext with optional metadata
func (v *Vault) EncryptWithMetadata(plaintext []byte, metadata map[string]interface{}) (*EncryptedData, error) {
	block, err := aes.NewCipher(v.encryptionKey)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonce := make([]byte, NonceSize)
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, err
	}

	// Encrypt (ciphertext includes the auth tag)
	ciphertextWithTag := gcm.Seal(nil, nonce, plaintext, nil)

	// Separate ciphertext and tag
	ciphertext := ciphertextWithTag[:len(ciphertextWithTag)-TagSize]
	tag := ciphertextWithTag[len(ciphertextWithTag)-TagSize:]

	return &EncryptedData{
		Ciphertext: ciphertext,
		Nonce:      nonce,
		Tag:        tag,
		Metadata:   metadata,
	}, nil
}

// Decrypt decrypts encrypted data
func (v *Vault) Decrypt(encrypted *EncryptedData) ([]byte, error) {
	block, err := aes.NewCipher(v.encryptionKey)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	// Recombine ciphertext and tag
	ciphertextWithTag := append(encrypted.Ciphertext, encrypted.Tag...)

	plaintext, err := gcm.Open(nil, encrypted.Nonce, ciphertextWithTag, nil)
	if err != nil {
		return nil, errors.New("decryption failed: authentication error")
	}

	return plaintext, nil
}

// GetFingerprint returns the vault fingerprint (first 16 hex chars of SHA-256)
func (v *Vault) GetFingerprint() string {
	hash := sha256.Sum256(v.masterKey)
	return bytesToHex(hash[:8])
}

// DeriveSubkey derives a subkey for a specific purpose
func (v *Vault) DeriveSubkey(purpose string) ([]byte, error) {
	return v.deriveKey([]byte(purpose))
}
