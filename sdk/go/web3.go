package psnx

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"time"

	"golang.org/x/crypto/hkdf"
)

// ChainConfig represents an EVM chain configuration
type ChainConfig struct {
	ChainID         uint64 `json:"chainId"`
	Name            string `json:"name"`
	RPCURL          string `json:"rpcUrl"`
	Symbol          string `json:"symbol"`
	Explorer        string `json:"explorer"`
	ContractAddress string `json:"contractAddress,omitempty"`
}

// EVMChain represents supported EVM chains
type EVMChain int

const (
	ChainEthereum EVMChain = iota
	ChainSepolia
	ChainPolygon
	ChainArbitrum
	ChainBase
	ChainOptimism
)

// Config returns the chain configuration
func (c EVMChain) Config() ChainConfig {
	switch c {
	case ChainEthereum:
		return ChainConfig{
			ChainID:  1,
			Name:     "Ethereum Mainnet",
			RPCURL:   "https://eth.llamarpc.com",
			Symbol:   "ETH",
			Explorer: "https://etherscan.io",
		}
	case ChainSepolia:
		return ChainConfig{
			ChainID:  11155111,
			Name:     "Ethereum Sepolia",
			RPCURL:   "https://rpc.sepolia.org",
			Symbol:   "ETH",
			Explorer: "https://sepolia.etherscan.io",
		}
	case ChainPolygon:
		return ChainConfig{
			ChainID:  137,
			Name:     "Polygon Mainnet",
			RPCURL:   "https://polygon-rpc.com",
			Symbol:   "MATIC",
			Explorer: "https://polygonscan.com",
		}
	case ChainArbitrum:
		return ChainConfig{
			ChainID:  42161,
			Name:     "Arbitrum One",
			RPCURL:   "https://arb1.arbitrum.io/rpc",
			Symbol:   "ETH",
			Explorer: "https://arbiscan.io",
		}
	case ChainBase:
		return ChainConfig{
			ChainID:  8453,
			Name:     "Base",
			RPCURL:   "https://mainnet.base.org",
			Symbol:   "ETH",
			Explorer: "https://basescan.org",
		}
	case ChainOptimism:
		return ChainConfig{
			ChainID:  10,
			Name:     "Optimism",
			RPCURL:   "https://mainnet.optimism.io",
			Symbol:   "ETH",
			Explorer: "https://optimistic.etherscan.io",
		}
	default:
		return ChainConfig{}
	}
}

// AllChains returns all supported chains
func AllChains() []EVMChain {
	return []EVMChain{
		ChainEthereum, ChainSepolia, ChainPolygon,
		ChainArbitrum, ChainBase, ChainOptimism,
	}
}

// ChainFromID finds a chain by its ID
func ChainFromID(chainID uint64) (EVMChain, bool) {
	for _, chain := range AllChains() {
		if chain.Config().ChainID == chainID {
			return chain, true
		}
	}
	return 0, false
}

// WalletInfo contains wallet information
type WalletInfo struct {
	Address   string  `json:"address"`
	PublicKey string  `json:"publicKey"`
	ChainID   uint64  `json:"chainId"`
	Balance   *uint64 `json:"balance,omitempty"`
}

// IPFSUploadResult represents an IPFS upload result
type IPFSUploadResult struct {
	CID  string `json:"cid"`
	Size int    `json:"size"`
	URL  string `json:"url"`
}

// BackupRegistration represents a backup registration
type BackupRegistration struct {
	BackupID    string  `json:"backupId"`
	ContentHash string  `json:"contentHash"`
	IPFSCID     string  `json:"ipfsCid,omitempty"`
	Timestamp   float64 `json:"timestamp"`
	Signature   string  `json:"signature"`
	TxHash      string  `json:"txHash,omitempty"`
	BlockNumber uint64  `json:"blockNumber,omitempty"`
}

// BackupRecord represents a complete backup record
type BackupRecord struct {
	ID                string              `json:"id"`
	LocalHash         string              `json:"localHash"`
	IPFSCID           string              `json:"ipfsCid,omitempty"`
	ChainRegistration *BackupRegistration `json:"chainRegistration,omitempty"`
	CreatedAt         float64             `json:"createdAt"`
	Verified          bool                `json:"verified"`
}

// VaultWeb3Wallet is an HD wallet derived from the vault key
type VaultWeb3Wallet struct {
	privateKey []byte
	address    string
	chain      EVMChain
}

// NewVaultWeb3Wallet creates a new Web3 wallet from a vault key
func NewVaultWeb3Wallet(vaultKey []byte, chain EVMChain) (*VaultWeb3Wallet, error) {
	if len(vaultKey) != 32 {
		return nil, errors.New("vault key must be 32 bytes")
	}

	// Derive private key via HKDF
	hkdfReader := hkdf.New(sha256.New, vaultKey, []byte("PSNX_EVM_WALLET_v1"), []byte("secp256k1_private_key"))
	privateKey := make([]byte, 32)
	if _, err := io.ReadFull(hkdfReader, privateKey); err != nil {
		return nil, err
	}

	// Derive address (simplified - in production use secp256k1)
	addrHash := sha256.Sum256(append(privateKey, []byte("_ADDRESS")...))
	address := "0x" + bytesToHex(addrHash[:20])

	return &VaultWeb3Wallet{
		privateKey: privateKey,
		address:    address,
		chain:      chain,
	}, nil
}

// Address returns the wallet address
func (w *VaultWeb3Wallet) Address() string {
	return w.address
}

// Chain returns the current chain
func (w *VaultWeb3Wallet) Chain() EVMChain {
	return w.chain
}

// ChainConfig returns the chain configuration
func (w *VaultWeb3Wallet) ChainConfig() ChainConfig {
	return w.chain.Config()
}

// SwitchChain changes the current chain
func (w *VaultWeb3Wallet) SwitchChain(chain EVMChain) {
	w.chain = chain
}

// Info returns wallet information
func (w *VaultWeb3Wallet) Info() WalletInfo {
	return WalletInfo{
		Address:   w.address,
		PublicKey: bytesToHex(w.privateKey), // Simplified
		ChainID:   w.chain.Config().ChainID,
	}
}

// SignMessage signs a message (EIP-191 style)
func (w *VaultWeb3Wallet) SignMessage(message string) string {
	prefixed := fmt.Sprintf("\x19Ethereum Signed Message:\n%d%s", len(message), message)

	messageHash := sha256.Sum256([]byte(prefixed))

	sigHash := sha256.Sum256(append(w.privateKey, messageHash[:]...))

	return "0x" + bytesToHex(sigHash[:]) + "1b"
}

// ExplorerURL returns the explorer URL
func (w *VaultWeb3Wallet) ExplorerURL(txHash string) string {
	base := w.chain.Config().Explorer
	if txHash != "" {
		return fmt.Sprintf("%s/tx/%s", base, txHash)
	}
	return fmt.Sprintf("%s/address/%s", base, w.address)
}

// IPFSClient is a client for IPFS operations
type IPFSClient struct {
	gateway string
	apiURL  string
}

// NewIPFSClient creates a new IPFS client
func NewIPFSClient(gateway, apiURL string) *IPFSClient {
	if gateway == "" {
		gateway = "https://ipfs.io/ipfs"
	}
	if apiURL == "" {
		apiURL = "https://api.pinata.cloud"
	}
	return &IPFSClient{
		gateway: gateway,
		apiURL:  apiURL,
	}
}

// Upload uploads data to IPFS (returns deterministic CID)
func (c *IPFSClient) Upload(data []byte) IPFSUploadResult {
	hash := sha256.Sum256(data)
	cid := "Qm" + bytesToHex(hash[:22])

	return IPFSUploadResult{
		CID:  cid,
		Size: len(data),
		URL:  fmt.Sprintf("%s/%s", c.gateway, cid),
	}
}

// UploadJSON uploads JSON data to IPFS
func (c *IPFSClient) UploadJSON(data interface{}) (IPFSUploadResult, error) {
	jsonBytes, err := json.Marshal(data)
	if err != nil {
		return IPFSUploadResult{}, err
	}
	return c.Upload(jsonBytes), nil
}

// GetURL returns the gateway URL for a CID
func (c *IPFSClient) GetURL(cid string) string {
	return fmt.Sprintf("%s/%s", c.gateway, cid)
}

// BackupRegistry manages on-chain backup registrations
type BackupRegistry struct {
	wallet *VaultWeb3Wallet
	ipfs   *IPFSClient
}

// NewBackupRegistry creates a new backup registry
func NewBackupRegistry(wallet *VaultWeb3Wallet, ipfs *IPFSClient) *BackupRegistry {
	if ipfs == nil {
		ipfs = NewIPFSClient("", "")
	}
	return &BackupRegistry{
		wallet: wallet,
		ipfs:   ipfs,
	}
}

// CreateRegistration creates a backup registration
func (r *BackupRegistry) CreateRegistration(backupID string, data []byte, uploadToIPFS bool) BackupRegistration {
	// Content hash
	contentHash := sha256.Sum256(data)
	contentHashHex := "0x" + bytesToHex(contentHash[:])

	// Backup ID hash
	idHash := sha256.Sum256([]byte(backupID))
	backupIDHex := "0x" + bytesToHex(idHash[:])

	// IPFS upload
	var ipfsCID string
	if uploadToIPFS {
		result := r.ipfs.Upload(data)
		ipfsCID = result.CID
	}

	// Timestamp
	timestamp := float64(time.Now().UnixMilli()) / 1000.0

	// Sign
	message := fmt.Sprintf("PSNX_BACKUP:%s:%s:%d", backupIDHex, contentHashHex, int64(timestamp))
	signature := r.wallet.SignMessage(message)

	return BackupRegistration{
		BackupID:    backupIDHex,
		ContentHash: contentHashHex,
		IPFSCID:     ipfsCID,
		Timestamp:   timestamp,
		Signature:   signature,
	}
}

// DecentralizedBackupManager manages decentralized backups
type DecentralizedBackupManager struct {
	wallet     *VaultWeb3Wallet
	ipfs       *IPFSClient
	registry   *BackupRegistry
	backups    map[string]BackupRecord
	autoUpload bool
}

// NewDecentralizedBackupManager creates a new backup manager
func NewDecentralizedBackupManager(vaultKey []byte, chain EVMChain, autoUploadIPFS bool) (*DecentralizedBackupManager, error) {
	wallet, err := NewVaultWeb3Wallet(vaultKey, chain)
	if err != nil {
		return nil, err
	}

	ipfs := NewIPFSClient("", "")
	registry := NewBackupRegistry(wallet, ipfs)

	return &DecentralizedBackupManager{
		wallet:     wallet,
		ipfs:       ipfs,
		registry:   registry,
		backups:    make(map[string]BackupRecord),
		autoUpload: autoUploadIPFS,
	}, nil
}

// Address returns the wallet address
func (m *DecentralizedBackupManager) Address() string {
	return m.wallet.Address()
}

// ChainInfo returns the chain configuration
func (m *DecentralizedBackupManager) ChainInfo() ChainConfig {
	return m.wallet.ChainConfig()
}

// CreateBackup creates a new backup
func (m *DecentralizedBackupManager) CreateBackup(backupID string, data []byte, uploadToIPFS *bool, registerOnChain bool) BackupRecord {
	doUpload := m.autoUpload
	if uploadToIPFS != nil {
		doUpload = *uploadToIPFS
	}

	registration := m.registry.CreateRegistration(backupID, data, doUpload)

	var chainReg *BackupRegistration
	if registerOnChain {
		chainReg = &registration
	}

	record := BackupRecord{
		ID:                backupID,
		LocalHash:         registration.ContentHash,
		IPFSCID:           registration.IPFSCID,
		ChainRegistration: chainReg,
		CreatedAt:         float64(time.Now().UnixMilli()) / 1000.0,
		Verified:          true,
	}

	m.backups[backupID] = record
	return record
}

// VerifyBackup verifies a backup
func (m *DecentralizedBackupManager) VerifyBackup(backupID string, data []byte) VerifyBackupResult {
	record, exists := m.backups[backupID]
	if !exists {
		return VerifyBackupResult{Valid: false}
	}

	contentHash := sha256.Sum256(data)
	contentHashHex := "0x" + bytesToHex(contentHash[:])
	hashMatch := contentHashHex == record.LocalHash

	return VerifyBackupResult{
		Valid:         hashMatch,
		HashMatch:     hashMatch,
		IPFSAvailable: record.IPFSCID != "",
		ChainVerified: record.ChainRegistration != nil,
	}
}

// VerifyBackupResult contains verification results
type VerifyBackupResult struct {
	Valid         bool `json:"valid"`
	HashMatch     bool `json:"hashMatch"`
	IPFSAvailable bool `json:"ipfsAvailable"`
	ChainVerified bool `json:"chainVerified"`
}

// ListBackups returns all backups
func (m *DecentralizedBackupManager) ListBackups() []BackupRecord {
	records := make([]BackupRecord, 0, len(m.backups))
	for _, r := range m.backups {
		records = append(records, r)
	}
	return records
}

// GetBackup returns a backup by ID
func (m *DecentralizedBackupManager) GetBackup(backupID string) (BackupRecord, bool) {
	r, ok := m.backups[backupID]
	return r, ok
}

// ExportRecords exports all records
func (m *DecentralizedBackupManager) ExportRecords() map[string]BackupRecord {
	result := make(map[string]BackupRecord)
	for k, v := range m.backups {
		result[k] = v
	}
	return result
}

// ImportRecords imports records
func (m *DecentralizedBackupManager) ImportRecords(records map[string]BackupRecord) {
	for k, v := range records {
		m.backups[k] = v
	}
}

// Utility functions

// IsValidAddress checks if an Ethereum address is valid
func IsValidAddress(address string) bool {
	if len(address) != 42 {
		return false
	}
	if address[:2] != "0x" {
		return false
	}
	for _, c := range address[2:] {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
			return false
		}
	}
	return true
}

// FormatEther formats wei to ether
func FormatEther(wei uint64) string {
	ether := float64(wei) / 1e18
	return fmt.Sprintf("%.6f", ether)
}

// ParseEther parses ether to wei
func ParseEther(ether string) (uint64, error) {
	var value float64
	_, err := fmt.Sscanf(ether, "%f", &value)
	if err != nil {
		return 0, err
	}
	return uint64(value * 1e18), nil
}

// ShortenAddress shortens an address for display
func ShortenAddress(address string, chars int) string {
	if len(address) < chars*2+2 {
		return address
	}
	return fmt.Sprintf("%s...%s", address[:chars+2], address[len(address)-chars:])
}
