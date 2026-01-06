package psnx

import (
	"crypto/rand"
	"crypto/sha256"
	"errors"
	"io"
	"math/big"

	"golang.org/x/crypto/hkdf"
	"golang.org/x/crypto/pbkdf2"
)

// KeyPair represents a vault key pair with public key
type KeyPair struct {
	VaultKey    []byte
	PublicKey   *big.Int
	Fingerprint string
	EntropyBits int
}

// KeyGenerator generates cryptographic keys for the vault
type KeyGenerator struct {
	extraEntropy []byte
}

// NewKeyGenerator creates a new key generator
func NewKeyGenerator() *KeyGenerator {
	return &KeyGenerator{}
}

// NewKeyGeneratorWithEntropy creates a key generator with extra entropy
func NewKeyGeneratorWithEntropy(entropy []byte) *KeyGenerator {
	return &KeyGenerator{
		extraEntropy: entropy,
	}
}

// Generate creates a new random vault key
func (kg *KeyGenerator) Generate() ([]byte, error) {
	entropy := make([]byte, 64+len(kg.extraEntropy))
	if _, err := io.ReadFull(rand.Reader, entropy[:64]); err != nil {
		return nil, err
	}
	copy(entropy[64:], kg.extraEntropy)

	// Derive key using HKDF
	hkdfReader := hkdf.New(sha256.New, entropy, []byte("PSNX_KEYGEN_v1"), []byte("vault_master_key"))
	key := make([]byte, KeySize)
	if _, err := io.ReadFull(hkdfReader, key); err != nil {
		return nil, err
	}

	return key, nil
}

// FromPassword derives a vault key from a password
func (kg *KeyGenerator) FromPassword(password string, salt []byte) (vaultKey []byte, usedSalt []byte, err error) {
	if len(password) < 8 {
		return nil, nil, errors.New("password must be at least 8 characters")
	}

	if salt == nil {
		salt = make([]byte, 16)
		if _, err := io.ReadFull(rand.Reader, salt); err != nil {
			return nil, nil, err
		}
	}

	// PBKDF2 with 100,000 iterations
	key := pbkdf2.Key([]byte(password), salt, 100000, KeySize, sha256.New)

	return key, salt, nil
}

// FromEntropy derives a vault key from external entropy
func (kg *KeyGenerator) FromEntropy(entropy []byte, minBits int) ([]byte, error) {
	if len(entropy)*8 < minBits {
		return nil, errors.New("entropy must be at least the minimum bits")
	}

	combined := make([]byte, len(entropy)+32+len(kg.extraEntropy))
	copy(combined, entropy)

	randomPart := make([]byte, 32)
	if _, err := io.ReadFull(rand.Reader, randomPart); err != nil {
		return nil, err
	}
	copy(combined[len(entropy):], randomPart)
	copy(combined[len(entropy)+32:], kg.extraEntropy)

	// Derive key using HKDF
	hkdfReader := hkdf.New(sha256.New, combined, []byte("PSNX_EXTERNAL_ENTROPY"), []byte("vault_key_from_external"))
	key := make([]byte, KeySize)
	if _, err := io.ReadFull(hkdfReader, key); err != nil {
		return nil, err
	}

	return key, nil
}

// GenerateKeyPair generates a complete key pair
func (kg *KeyGenerator) GenerateKeyPair() (*KeyPair, error) {
	vaultKey, err := kg.Generate()
	if err != nil {
		return nil, err
	}

	// Derive ZKP private key
	combined := append([]byte("PSNX_ZKP_PRIVATE_"), vaultKey...)
	hash := sha256.Sum256(combined)

	// Public key calculation (simplified)
	x := new(big.Int).SetBytes(hash[:])
	x.Mod(x, Q)
	if x.Sign() == 0 {
		x.SetInt64(1)
	}

	publicKey := new(big.Int).Exp(G, x, P)

	// Fingerprint
	fpHash := sha256.Sum256(vaultKey)
	fingerprint := bytesToHex(fpHash[:8])

	return &KeyPair{
		VaultKey:    vaultKey,
		PublicKey:   publicKey,
		Fingerprint: fingerprint,
		EntropyBits: 256,
	}, nil
}

// Verify checks if a vault key is valid
func Verify(vaultKey []byte) bool {
	if len(vaultKey) != 32 {
		return false
	}
	// Check it's not all zeros
	for _, b := range vaultKey {
		if b != 0 {
			return true
		}
	}
	return false
}
