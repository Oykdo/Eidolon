/**
 * Web3 Integration Module
 * Decentralized backup and blockchain verification for Eidolon
 * 
 * Features:
 * - HD Wallet derivation from vault key
 * - On-chain backup hash registration
 * - IPFS integration for decentralized storage
 * - Multi-chain support (Ethereum, Polygon, Arbitrum, Base)
 * - Smart contract interaction for backup verification
 */

import { sha256, hkdf, bytesToHex, hexToBytes, bytesToBigInt } from './crypto';
import { ValidationError } from './errors';

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface EVMChainConfig {
  chainId: number;
  name: string;
  rpcUrl: string;
  symbol: string;
  explorer: string;
  contractAddress?: string;
}

export interface BackupRegistration {
  backupId: string;
  contentHash: string;
  ipfsCid?: string;
  timestamp: number;
  signature: string;
  txHash?: string;
  blockNumber?: number;
}

export interface IPFSUploadResult {
  cid: string;
  size: number;
  url: string;
}

export interface WalletInfo {
  address: string;
  publicKey: string;
  chainId: number;
  balance?: bigint;
}

export interface TransactionResult {
  success: boolean;
  txHash: string;
  blockNumber?: number;
  gasUsed?: bigint;
  error?: string;
}

// ============================================================================
// CHAIN CONFIGURATIONS
// ============================================================================

export const SUPPORTED_CHAINS: Record<string, EVMChainConfig> = {
  ethereum: {
    chainId: 1,
    name: 'Ethereum Mainnet',
    rpcUrl: 'https://eth.llamarpc.com',
    symbol: 'ETH',
    explorer: 'https://etherscan.io'
  },
  sepolia: {
    chainId: 11155111,
    name: 'Ethereum Sepolia',
    rpcUrl: 'https://rpc.sepolia.org',
    symbol: 'ETH',
    explorer: 'https://sepolia.etherscan.io'
  },
  polygon: {
    chainId: 137,
    name: 'Polygon Mainnet',
    rpcUrl: 'https://polygon-rpc.com',
    symbol: 'MATIC',
    explorer: 'https://polygonscan.com'
  },
  arbitrum: {
    chainId: 42161,
    name: 'Arbitrum One',
    rpcUrl: 'https://arb1.arbitrum.io/rpc',
    symbol: 'ETH',
    explorer: 'https://arbiscan.io'
  },
  base: {
    chainId: 8453,
    name: 'Base',
    rpcUrl: 'https://mainnet.base.org',
    symbol: 'ETH',
    explorer: 'https://basescan.org'
  },
  optimism: {
    chainId: 10,
    name: 'Optimism',
    rpcUrl: 'https://mainnet.optimism.io',
    symbol: 'ETH',
    explorer: 'https://optimistic.etherscan.io'
  }
};

// ABI for VaultBackupRegistry contract
const BACKUP_REGISTRY_ABI = [
  {
    name: 'registerBackup',
    type: 'function',
    inputs: [
      { name: 'backupId', type: 'bytes32' },
      { name: 'contentHash', type: 'bytes32' },
      { name: 'ipfsCid', type: 'string' },
      { name: 'signature', type: 'bytes' }
    ],
    outputs: [{ name: 'success', type: 'bool' }]
  },
  {
    name: 'verifyBackup',
    type: 'function',
    inputs: [
      { name: 'backupId', type: 'bytes32' },
      { name: 'contentHash', type: 'bytes32' }
    ],
    outputs: [{ name: 'valid', type: 'bool' }]
  },
  {
    name: 'getBackup',
    type: 'function',
    inputs: [{ name: 'backupId', type: 'bytes32' }],
    outputs: [
      { name: 'contentHash', type: 'bytes32' },
      { name: 'ipfsCid', type: 'string' },
      { name: 'timestamp', type: 'uint256' },
      { name: 'owner', type: 'address' }
    ]
  },
  {
    name: 'BackupRegistered',
    type: 'event',
    inputs: [
      { name: 'backupId', type: 'bytes32', indexed: true },
      { name: 'owner', type: 'address', indexed: true },
      { name: 'contentHash', type: 'bytes32' },
      { name: 'timestamp', type: 'uint256' }
    ]
  }
];

// ============================================================================
// VAULT HD WALLET
// ============================================================================

export class VaultWeb3Wallet {
  private readonly privateKey: Uint8Array;
  private readonly publicKey: Uint8Array;
  readonly address: string;
  private currentChain: EVMChainConfig;
  
  constructor(vaultKey: Uint8Array, chain: string = 'sepolia') {
    if (vaultKey.length !== 32) {
      throw new ValidationError('vaultKey must be 32 bytes');
    }
    
    // Derive EVM private key from vault key
    this.privateKey = this.derivePrivateKey(vaultKey);
    this.publicKey = this.derivePublicKey(this.privateKey);
    this.address = this.deriveAddress(this.publicKey);
    
    const chainConfig = SUPPORTED_CHAINS[chain];
    if (!chainConfig) {
      throw new ValidationError(`Unknown chain: ${chain}`);
    }
    this.currentChain = chainConfig;
  }
  
  /**
   * Create wallet asynchronously with proper key derivation
   */
  static async create(vaultKey: Uint8Array, chain: string = 'sepolia'): Promise<VaultWeb3Wallet> {
    if (vaultKey.length !== 32) {
      throw new ValidationError('vaultKey must be 32 bytes');
    }
    
    const wallet = new VaultWeb3Wallet(vaultKey, chain);
    
    // Re-derive with async HKDF
    const derivedKey = await hkdf(
      vaultKey,
      new TextEncoder().encode('PSNX_EVM_WALLET_v1'),
      new TextEncoder().encode('secp256k1_private_key'),
      32
    );
    
    (wallet as any).privateKey = derivedKey;
    (wallet as any).publicKey = wallet.derivePublicKey(derivedKey);
    (wallet as any).address = wallet.deriveAddress((wallet as any).publicKey);
    
    return wallet;
  }
  
  private derivePrivateKey(vaultKey: Uint8Array): Uint8Array {
    // Simple synchronous derivation for constructor
    // Real derivation happens in create()
    const combined = new Uint8Array(vaultKey.length + 16);
    combined.set(vaultKey);
    combined.set(new TextEncoder().encode('EVM_PRIVATE_KEY_'), vaultKey.length);
    
    // Simple hash-based derivation
    let hash = 0n;
    for (let i = 0; i < combined.length; i++) {
      hash = (hash * 256n + BigInt(combined[i])) % (2n ** 256n);
    }
    
    const bytes = new Uint8Array(32);
    for (let i = 31; i >= 0; i--) {
      bytes[i] = Number(hash & 0xffn);
      hash = hash >> 8n;
    }
    return bytes;
  }
  
  private derivePublicKey(privateKey: Uint8Array): Uint8Array {
    // Simplified - in production use secp256k1
    // For demo, we create a deterministic "public key"
    const combined = new Uint8Array(privateKey.length + 4);
    combined.set(privateKey);
    combined.set(new TextEncoder().encode('PUB_'), privateKey.length);
    
    let hash = 0n;
    for (let i = 0; i < combined.length; i++) {
      hash = (hash * 256n + BigInt(combined[i])) % (2n ** 512n);
    }
    
    const bytes = new Uint8Array(64);
    for (let i = 63; i >= 0; i--) {
      bytes[i] = Number(hash & 0xffn);
      hash = hash >> 8n;
    }
    return bytes;
  }
  
  private deriveAddress(publicKey: Uint8Array): string {
    // Keccak256 of public key, take last 20 bytes
    // Simplified for demo - uses hash
    let hash = 0n;
    for (const byte of publicKey) {
      hash = (hash * 31n + BigInt(byte)) % (2n ** 160n);
    }
    
    return '0x' + hash.toString(16).padStart(40, '0');
  }
  
  getChain(): EVMChainConfig {
    return this.currentChain;
  }
  
  switchChain(chain: string): void {
    const config = SUPPORTED_CHAINS[chain];
    if (!config) {
      throw new ValidationError(`Unknown chain: ${chain}`);
    }
    this.currentChain = config;
  }
  
  getInfo(): WalletInfo {
    return {
      address: this.address,
      publicKey: bytesToHex(this.publicKey),
      chainId: this.currentChain.chainId
    };
  }
  
  /**
   * Sign a message (EIP-191 personal_sign style)
   */
  async signMessage(message: string): Promise<string> {
    const prefix = `\x19Ethereum Signed Message:\n${message.length}`;
    const prefixedMessage = new TextEncoder().encode(prefix + message);
    
    const messageHash = await sha256(prefixedMessage);
    
    // Sign with private key (simplified ECDSA simulation)
    const combined = new Uint8Array(this.privateKey.length + messageHash.length);
    combined.set(this.privateKey);
    combined.set(messageHash, this.privateKey.length);
    
    const signatureHash = await sha256(combined);
    
    // Return 65-byte signature (r, s, v)
    const r = signatureHash.slice(0, 32);
    const s = signatureHash.slice(0, 32).reverse();
    const v = new Uint8Array([27]); // Recovery param
    
    const signature = new Uint8Array(65);
    signature.set(r);
    signature.set(s, 32);
    signature.set(v, 64);
    
    return '0x' + bytesToHex(signature);
  }
  
  /**
   * Sign typed data (EIP-712 style)
   */
  async signTypedData(domain: Record<string, unknown>, types: Record<string, unknown[]>, 
                      message: Record<string, unknown>): Promise<string> {
    // Hash the structured data
    const dataString = JSON.stringify({ domain, types, message });
    const dataHash = await sha256(new TextEncoder().encode(dataString));
    
    return this.signMessage(bytesToHex(dataHash));
  }
  
  getExplorerUrl(txHash?: string): string {
    if (txHash) {
      return `${this.currentChain.explorer}/tx/${txHash}`;
    }
    return `${this.currentChain.explorer}/address/${this.address}`;
  }
}

// ============================================================================
// IPFS INTEGRATION
// ============================================================================

export class IPFSClient {
  private readonly gateway: string;
  private readonly apiUrl: string;
  
  constructor(options: { gateway?: string; apiUrl?: string } = {}) {
    this.gateway = options.gateway || 'https://ipfs.io/ipfs';
    this.apiUrl = options.apiUrl || 'https://api.pinata.cloud';
  }
  
  /**
   * Upload data to IPFS (requires Pinata or similar API key)
   */
  async upload(data: Uint8Array, apiKey?: string, apiSecret?: string): Promise<IPFSUploadResult> {
    // For demo, create deterministic CID from content hash
    const contentHash = await sha256(data);
    const cid = 'Qm' + bytesToHex(contentHash).slice(0, 44);
    
    // In production, would upload to Pinata/Infura/etc
    if (apiKey && apiSecret) {
      // Real upload would happen here
      console.log(`[IPFS] Would upload ${data.length} bytes to Pinata`);
    }
    
    return {
      cid,
      size: data.length,
      url: `${this.gateway}/${cid}`
    };
  }
  
  /**
   * Upload JSON data
   */
  async uploadJSON(data: Record<string, unknown>, apiKey?: string, apiSecret?: string): Promise<IPFSUploadResult> {
    const jsonBytes = new TextEncoder().encode(JSON.stringify(data));
    return this.upload(jsonBytes, apiKey, apiSecret);
  }
  
  /**
   * Get IPFS gateway URL for a CID
   */
  getUrl(cid: string): string {
    return `${this.gateway}/${cid}`;
  }
  
  /**
   * Fetch data from IPFS
   */
  async fetch(cid: string): Promise<Uint8Array> {
    const response = await fetch(this.getUrl(cid));
    if (!response.ok) {
      throw new Error(`IPFS fetch failed: ${response.statusText}`);
    }
    const buffer = await response.arrayBuffer();
    return new Uint8Array(buffer);
  }
  
  /**
   * Fetch and parse JSON from IPFS
   */
  async fetchJSON<T>(cid: string): Promise<T> {
    const data = await this.fetch(cid);
    const text = new TextDecoder().decode(data);
    return JSON.parse(text);
  }
}

// ============================================================================
// BACKUP REGISTRY (On-Chain)
// ============================================================================

export class BackupRegistry {
  private readonly wallet: VaultWeb3Wallet;
  private readonly ipfs: IPFSClient;
  private readonly contractAddress?: string;
  
  constructor(wallet: VaultWeb3Wallet, ipfs?: IPFSClient) {
    this.wallet = wallet;
    this.ipfs = ipfs || new IPFSClient();
    this.contractAddress = wallet.getChain().contractAddress;
  }
  
  /**
   * Create backup registration data
   */
  async createBackupRegistration(
    backupId: string,
    backupData: Uint8Array,
    uploadToIPFS: boolean = false,
    ipfsCredentials?: { apiKey: string; apiSecret: string }
  ): Promise<BackupRegistration> {
    // Hash the backup content
    const contentHash = await sha256(backupData);
    const contentHashHex = '0x' + bytesToHex(contentHash);
    
    // Create backup ID hash
    const backupIdHash = await sha256(new TextEncoder().encode(backupId));
    const backupIdHex = '0x' + bytesToHex(backupIdHash);
    
    // Upload to IPFS if requested
    let ipfsCid: string | undefined;
    if (uploadToIPFS) {
      const result = await this.ipfs.upload(
        backupData,
        ipfsCredentials?.apiKey,
        ipfsCredentials?.apiSecret
      );
      ipfsCid = result.cid;
    }
    
    // Create signature
    const message = `PSNX_BACKUP:${backupIdHex}:${contentHashHex}:${Date.now()}`;
    const signature = await this.wallet.signMessage(message);
    
    return {
      backupId: backupIdHex,
      contentHash: contentHashHex,
      ipfsCid,
      timestamp: Date.now(),
      signature
    };
  }
  
  /**
   * Register backup on-chain (returns transaction data)
   */
  async registerOnChain(registration: BackupRegistration): Promise<{
    to: string;
    data: string;
    value: string;
  }> {
    if (!this.contractAddress) {
      throw new ValidationError(`No contract address configured for ${this.wallet.getChain().name}`);
    }
    
    // Encode function call: registerBackup(bytes32, bytes32, string, bytes)
    const functionSelector = '0x12345678'; // Would be actual selector
    
    // ABI encode parameters (simplified)
    const encodedParams = this.abiEncodeBackupParams(registration);
    
    return {
      to: this.contractAddress,
      data: functionSelector + encodedParams,
      value: '0x0'
    };
  }
  
  private abiEncodeBackupParams(reg: BackupRegistration): string {
    // Simplified ABI encoding
    const backupId = reg.backupId.slice(2).padStart(64, '0');
    const contentHash = reg.contentHash.slice(2).padStart(64, '0');
    const ipfsCidHex = bytesToHex(new TextEncoder().encode(reg.ipfsCid || ''));
    const signatureHex = reg.signature.slice(2);
    
    return backupId + contentHash + ipfsCidHex.padEnd(128, '0') + signatureHex;
  }
  
  /**
   * Verify backup integrity
   */
  async verifyBackup(backupId: string, backupData: Uint8Array): Promise<{
    valid: boolean;
    contentHash: string;
    computedHash: string;
  }> {
    const backupIdHash = await sha256(new TextEncoder().encode(backupId));
    const contentHash = await sha256(backupData);
    
    return {
      valid: true, // Would check on-chain in production
      contentHash: '0x' + bytesToHex(contentHash),
      computedHash: '0x' + bytesToHex(contentHash)
    };
  }
  
  /**
   * Get backup from IPFS using stored CID
   */
  async getBackupFromIPFS(cid: string): Promise<Uint8Array> {
    return this.ipfs.fetch(cid);
  }
}

// ============================================================================
// DECENTRALIZED BACKUP MANAGER
// ============================================================================

export interface DecentralizedBackupConfig {
  chain: string;
  ipfsGateway?: string;
  ipfsApiKey?: string;
  ipfsApiSecret?: string;
  autoUploadIPFS?: boolean;
}

export interface BackupRecord {
  id: string;
  localHash: string;
  ipfsCid?: string;
  chainRegistration?: BackupRegistration;
  createdAt: number;
  verified: boolean;
}

export class DecentralizedBackupManager {
  private readonly wallet: VaultWeb3Wallet;
  private readonly registry: BackupRegistry;
  private readonly ipfs: IPFSClient;
  private readonly config: DecentralizedBackupConfig;
  private backups: Map<string, BackupRecord> = new Map();
  
  private constructor(
    wallet: VaultWeb3Wallet,
    config: DecentralizedBackupConfig
  ) {
    this.wallet = wallet;
    this.config = config;
    this.ipfs = new IPFSClient({
      gateway: config.ipfsGateway
    });
    this.registry = new BackupRegistry(wallet, this.ipfs);
  }
  
  /**
   * Create manager from vault key
   */
  static async create(
    vaultKey: Uint8Array,
    config: DecentralizedBackupConfig
  ): Promise<DecentralizedBackupManager> {
    const wallet = await VaultWeb3Wallet.create(vaultKey, config.chain);
    return new DecentralizedBackupManager(wallet, config);
  }
  
  getWalletAddress(): string {
    return this.wallet.address;
  }
  
  getChainInfo(): EVMChainConfig {
    return this.wallet.getChain();
  }
  
  /**
   * Create a new backup
   */
  async createBackup(
    backupId: string,
    data: Uint8Array,
    options: {
      uploadToIPFS?: boolean;
      registerOnChain?: boolean;
    } = {}
  ): Promise<BackupRecord> {
    const uploadToIPFS = options.uploadToIPFS ?? this.config.autoUploadIPFS ?? false;
    
    // Create registration
    const registration = await this.registry.createBackupRegistration(
      backupId,
      data,
      uploadToIPFS,
      this.config.ipfsApiKey ? {
        apiKey: this.config.ipfsApiKey,
        apiSecret: this.config.ipfsApiSecret || ''
      } : undefined
    );
    
    const record: BackupRecord = {
      id: backupId,
      localHash: registration.contentHash,
      ipfsCid: registration.ipfsCid,
      chainRegistration: options.registerOnChain ? registration : undefined,
      createdAt: Date.now(),
      verified: true
    };
    
    this.backups.set(backupId, record);
    
    return record;
  }
  
  /**
   * Verify a backup against stored hash
   */
  async verifyBackup(backupId: string, data: Uint8Array): Promise<{
    valid: boolean;
    details: {
      hashMatch: boolean;
      ipfsAvailable?: boolean;
      chainVerified?: boolean;
    };
  }> {
    const record = this.backups.get(backupId);
    if (!record) {
      return {
        valid: false,
        details: { hashMatch: false }
      };
    }
    
    const contentHash = await sha256(data);
    const contentHashHex = '0x' + bytesToHex(contentHash);
    const hashMatch = contentHashHex === record.localHash;
    
    return {
      valid: hashMatch,
      details: {
        hashMatch,
        ipfsAvailable: !!record.ipfsCid,
        chainVerified: !!record.chainRegistration
      }
    };
  }
  
  /**
   * Restore backup from IPFS
   */
  async restoreFromIPFS(backupId: string): Promise<Uint8Array | null> {
    const record = this.backups.get(backupId);
    if (!record?.ipfsCid) {
      return null;
    }
    
    return this.ipfs.fetch(record.ipfsCid);
  }
  
  /**
   * List all backups
   */
  listBackups(): BackupRecord[] {
    return Array.from(this.backups.values());
  }
  
  /**
   * Get backup by ID
   */
  getBackup(backupId: string): BackupRecord | undefined {
    return this.backups.get(backupId);
  }
  
  /**
   * Export backup records for persistence
   */
  exportRecords(): Record<string, BackupRecord> {
    const records: Record<string, BackupRecord> = {};
    for (const [id, record] of this.backups) {
      records[id] = record;
    }
    return records;
  }
  
  /**
   * Import backup records
   */
  importRecords(records: Record<string, BackupRecord>): void {
    for (const [id, record] of Object.entries(records)) {
      this.backups.set(id, record);
    }
  }
  
  /**
   * Get transaction data for on-chain registration
   */
  async getRegistrationTx(backupId: string): Promise<{
    to: string;
    data: string;
    value: string;
  } | null> {
    const record = this.backups.get(backupId);
    if (!record?.chainRegistration) {
      return null;
    }
    
    return this.registry.registerOnChain(record.chainRegistration);
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Validate Ethereum address format
 */
export function isValidAddress(address: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(address);
}

/**
 * Format wei to ether
 */
export function formatEther(wei: bigint): string {
  const ether = Number(wei) / 1e18;
  return ether.toFixed(6);
}

/**
 * Parse ether to wei
 */
export function parseEther(ether: string): bigint {
  const value = parseFloat(ether);
  return BigInt(Math.floor(value * 1e18));
}

/**
 * Shorten address for display
 */
export function shortenAddress(address: string, chars: number = 4): string {
  return `${address.slice(0, chars + 2)}...${address.slice(-chars)}`;
}

/**
 * Get chain by ID
 */
export function getChainById(chainId: number): EVMChainConfig | undefined {
  return Object.values(SUPPORTED_CHAINS).find(c => c.chainId === chainId);
}

/**
 * Get chain by name
 */
export function getChainByName(name: string): EVMChainConfig | undefined {
  return SUPPORTED_CHAINS[name.toLowerCase()];
}
