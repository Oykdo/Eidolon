/**
 * Poly-Spinor Nexus 7D - JavaScript/TypeScript SDK
 * 
 * @example
 * ```typescript
 * import { PSNXClient, Vault, KeyGenerator } from '@psnx/sdk';
 * 
 * const keyGen = new KeyGenerator();
 * const vaultKey = keyGen.generate();
 * 
 * const vault = new Vault(vaultKey);
 * const encrypted = await vault.encrypt(new TextEncoder().encode('secret'));
 * const decrypted = await vault.decrypt(encrypted);
 * 
 * const client = new PSNXClient('https://api.example.com', vaultKey);
 * await client.login('user_id');
 * ```
 */

export { Vault } from './vault';
export type { EncryptedData } from './vault';
export { KeyGenerator } from './keygen';
export type { KeyPair } from './keygen';
export { SecretSharing } from './sharing';
export type { Share } from './sharing';
export { ZKPProver, ZKPVerifier } from './zkp';
export type { ZKPProof } from './zkp';
export { PSNXClient } from './client';
export type { Session } from './client';

// Web3 & Blockchain
export {
  VaultWeb3Wallet,
  IPFSClient,
  BackupRegistry,
  DecentralizedBackupManager,
  SUPPORTED_CHAINS,
  isValidAddress,
  formatEther,
  parseEther,
  shortenAddress,
  getChainById,
  getChainByName
} from './web3';
export type {
  EVMChainConfig,
  BackupRegistration,
  IPFSUploadResult,
  WalletInfo,
  TransactionResult,
  DecentralizedBackupConfig,
  BackupRecord
} from './web3';

export * from './errors';
export * from './types';
