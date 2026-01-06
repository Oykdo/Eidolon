package psnx

import (
	"bytes"
	"testing"
)

func TestKeyGenerator(t *testing.T) {
	kg := NewKeyGenerator()

	t.Run("Generate returns 32 bytes", func(t *testing.T) {
		key, err := kg.Generate()
		if err != nil {
			t.Fatalf("Generate failed: %v", err)
		}
		if len(key) != 32 {
			t.Errorf("Expected 32 bytes, got %d", len(key))
		}
	})

	t.Run("FromPassword is deterministic", func(t *testing.T) {
		key1, salt, err := kg.FromPassword("testpassword123", nil)
		if err != nil {
			t.Fatalf("FromPassword failed: %v", err)
		}

		key2, _, err := kg.FromPassword("testpassword123", salt)
		if err != nil {
			t.Fatalf("FromPassword failed: %v", err)
		}

		if !bytes.Equal(key1, key2) {
			t.Error("Keys should be equal with same password and salt")
		}
	})

	t.Run("GenerateKeyPair returns valid structure", func(t *testing.T) {
		kp, err := kg.GenerateKeyPair()
		if err != nil {
			t.Fatalf("GenerateKeyPair failed: %v", err)
		}

		if len(kp.VaultKey) != 32 {
			t.Errorf("VaultKey should be 32 bytes, got %d", len(kp.VaultKey))
		}
		if len(kp.Fingerprint) != 16 {
			t.Errorf("Fingerprint should be 16 chars, got %d", len(kp.Fingerprint))
		}
		if kp.EntropyBits != 256 {
			t.Errorf("EntropyBits should be 256, got %d", kp.EntropyBits)
		}
	})
}

func TestVault(t *testing.T) {
	kg := NewKeyGenerator()
	vaultKey, _ := kg.Generate()
	vault, err := NewVault(vaultKey)
	if err != nil {
		t.Fatalf("NewVault failed: %v", err)
	}

	t.Run("Encrypt/Decrypt roundtrip", func(t *testing.T) {
		plaintext := []byte("Hello, World!")
		encrypted, err := vault.Encrypt(plaintext)
		if err != nil {
			t.Fatalf("Encrypt failed: %v", err)
		}

		decrypted, err := vault.Decrypt(encrypted)
		if err != nil {
			t.Fatalf("Decrypt failed: %v", err)
		}

		if !bytes.Equal(plaintext, decrypted) {
			t.Error("Decrypted data doesn't match original")
		}
	})

	t.Run("EncryptedData has correct structure", func(t *testing.T) {
		encrypted, _ := vault.Encrypt([]byte("test"))
		if len(encrypted.Nonce) != NonceSize {
			t.Errorf("Nonce should be %d bytes, got %d", NonceSize, len(encrypted.Nonce))
		}
		if len(encrypted.Tag) != TagSize {
			t.Errorf("Tag should be %d bytes, got %d", TagSize, len(encrypted.Tag))
		}
	})

	t.Run("GetFingerprint returns 16 chars", func(t *testing.T) {
		fp := vault.GetFingerprint()
		if len(fp) != 16 {
			t.Errorf("Fingerprint should be 16 chars, got %d", len(fp))
		}
	})
}

func TestSecretSharing(t *testing.T) {
	ss, err := NewSecretSharing(3, 5)
	if err != nil {
		t.Fatalf("NewSecretSharing failed: %v", err)
	}

	kg := NewKeyGenerator()
	secret, _ := kg.Generate()

	t.Run("Split creates correct number of shares", func(t *testing.T) {
		shares, err := ss.Split(secret)
		if err != nil {
			t.Fatalf("Split failed: %v", err)
		}
		if len(shares) != 5 {
			t.Errorf("Expected 5 shares, got %d", len(shares))
		}
	})

	t.Run("Reconstruct recovers secret", func(t *testing.T) {
		shares, _ := ss.Split(secret)
		selected := []*Share{shares[0], shares[2], shares[4]}

		recovered, err := ss.Reconstruct(selected)
		if err != nil {
			t.Fatalf("Reconstruct failed: %v", err)
		}

		if !bytes.Equal(secret, recovered) {
			t.Error("Recovered secret doesn't match original")
		}
	})

	t.Run("VerifyShare validates checksum", func(t *testing.T) {
		shares, _ := ss.Split(secret)
		for _, share := range shares {
			if !ss.VerifyShare(share) {
				t.Errorf("Share %d failed verification", share.Index)
			}
		}
	})
}

func TestZKP(t *testing.T) {
	kg := NewKeyGenerator()
	vaultKey, _ := kg.Generate()

	prover, err := NewZKPProver(vaultKey)
	if err != nil {
		t.Fatalf("NewZKPProver failed: %v", err)
	}

	t.Run("GetPublicKeyHex starts with 0x", func(t *testing.T) {
		pk := prover.GetPublicKeyHex()
		if pk[:2] != "0x" {
			t.Error("Public key should start with 0x")
		}
	})

	t.Run("CreateProof returns valid structure", func(t *testing.T) {
		result, err := prover.CreateProof("test-challenge")
		if err != nil {
			t.Fatalf("CreateProof failed: %v", err)
		}

		if result.Proof.Commitment[:2] != "0x" {
			t.Error("Commitment should start with 0x")
		}
		if result.Challenge != "test-challenge" {
			t.Error("Challenge should match input")
		}
	})

	t.Run("Verifier validates proof", func(t *testing.T) {
		challenge := "verify-test"
		result, _ := prover.CreateProof(challenge)

		verifier := NewZKPVerifier()
		valid, reason := verifier.Verify(result, challenge, 300)

		if !valid {
			t.Errorf("Proof should be valid, got: %s", reason)
		}
	})
}

func TestWeb3Wallet(t *testing.T) {
	kg := NewKeyGenerator()
	vaultKey, _ := kg.Generate()

	wallet, err := NewVaultWeb3Wallet(vaultKey, ChainSepolia)
	if err != nil {
		t.Fatalf("NewVaultWeb3Wallet failed: %v", err)
	}

	t.Run("Address is valid format", func(t *testing.T) {
		addr := wallet.Address()
		if !IsValidAddress(addr) {
			t.Errorf("Invalid address: %s", addr)
		}
	})

	t.Run("Same vaultKey produces same address", func(t *testing.T) {
		wallet2, _ := NewVaultWeb3Wallet(vaultKey, ChainSepolia)
		if wallet.Address() != wallet2.Address() {
			t.Error("Same vault key should produce same address")
		}
	})

	t.Run("SignMessage returns signature", func(t *testing.T) {
		sig := wallet.SignMessage("Hello")
		if sig[:2] != "0x" {
			t.Error("Signature should start with 0x")
		}
	})

	t.Run("ChainConfig returns correct chain", func(t *testing.T) {
		config := wallet.ChainConfig()
		if config.ChainID != 11155111 {
			t.Errorf("Expected Sepolia chain ID 11155111, got %d", config.ChainID)
		}
	})
}

func TestBackupManager(t *testing.T) {
	kg := NewKeyGenerator()
	vaultKey, _ := kg.Generate()

	manager, err := NewDecentralizedBackupManager(vaultKey, ChainSepolia, true)
	if err != nil {
		t.Fatalf("NewDecentralizedBackupManager failed: %v", err)
	}

	t.Run("CreateBackup works", func(t *testing.T) {
		data := []byte("test backup data")
		record := manager.CreateBackup("test_001", data, nil, false)

		if record.ID != "test_001" {
			t.Errorf("Expected ID test_001, got %s", record.ID)
		}
		if record.LocalHash[:2] != "0x" {
			t.Error("LocalHash should start with 0x")
		}
	})

	t.Run("VerifyBackup confirms valid backup", func(t *testing.T) {
		data := []byte("verify test data")
		manager.CreateBackup("verify_001", data, nil, false)

		result := manager.VerifyBackup("verify_001", data)
		if !result.Valid {
			t.Error("Backup should be valid")
		}
		if !result.HashMatch {
			t.Error("Hash should match")
		}
	})

	t.Run("VerifyBackup detects tampering", func(t *testing.T) {
		original := []byte("original data")
		modified := []byte("modified data")
		manager.CreateBackup("tamper_001", original, nil, false)

		result := manager.VerifyBackup("tamper_001", modified)
		if result.Valid {
			t.Error("Modified data should fail verification")
		}
	})

	t.Run("ListBackups returns all backups", func(t *testing.T) {
		backups := manager.ListBackups()
		if len(backups) < 3 {
			t.Errorf("Expected at least 3 backups, got %d", len(backups))
		}
	})
}

func TestUtilities(t *testing.T) {
	t.Run("IsValidAddress", func(t *testing.T) {
		if !IsValidAddress("0x1234567890123456789012345678901234567890") {
			t.Error("Valid address should pass")
		}
		if IsValidAddress("0x123") {
			t.Error("Short address should fail")
		}
		if IsValidAddress("not an address") {
			t.Error("Invalid address should fail")
		}
	})

	t.Run("FormatEther", func(t *testing.T) {
		result := FormatEther(1000000000000000000)
		if result != "1.000000" {
			t.Errorf("Expected 1.000000, got %s", result)
		}
	})

	t.Run("ShortenAddress", func(t *testing.T) {
		addr := "0x1234567890123456789012345678901234567890"
		short := ShortenAddress(addr, 4)
		if short != "0x1234...7890" {
			t.Errorf("Expected 0x1234...7890, got %s", short)
		}
	})
}
