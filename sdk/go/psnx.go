// Package psnx provides the official Go SDK for Poly-Spinor Nexus 7D.
//
// This SDK enables interaction with the Poly-Spinor Nexus 7D API,
// providing cryptographic operations, vault management, and blockchain integration.
//
// Example usage:
//
//	import "github.com/poly-spinor/psnx-sdk-go"
//
//	// Generate a vault key
//	keyGen := psnx.NewKeyGenerator()
//	vaultKey, _ := keyGen.Generate()
//
//	// Create a vault for encryption
//	vault, _ := psnx.NewVault(vaultKey)
//	encrypted, _ := vault.Encrypt([]byte("secret data"))
//	decrypted, _ := vault.Decrypt(encrypted)
//
//	// Web3 wallet derived from vault key
//	wallet, _ := psnx.NewVaultWeb3Wallet(vaultKey, psnx.ChainSepolia)
//	fmt.Println("Address:", wallet.Address())
package psnx

// Version of the SDK
const Version = "1.0.0"
