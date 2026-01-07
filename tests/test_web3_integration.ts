/**
 * Tests d'integration Web3 & Blockchain
 * Eidolon SDK
 */

import {
  KeyGenerator,
  Vault,
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
} from '../sdk/javascript/src';

interface TestResult {
  name: string;
  passed: boolean;
  details?: string;
}

const results: TestResult[] = [];

async function test(name: string, fn: () => Promise<boolean> | boolean): Promise<void> {
  try {
    const passed = await fn();
    results.push({ name, passed });
    console.log(`  ${passed ? '[PASS]' : '[FAIL]'} ${name}`);
  } catch (e) {
    results.push({ name, passed: false, details: String(e) });
    console.log(`  [FAIL] ${name}: ${e}`);
  }
}

async function runTests() {
  console.log('\n' + '='.repeat(60));
  console.log('  TESTS WEB3 & BLOCKCHAIN INTEGRATION');
  console.log('='.repeat(60) + '\n');

  // Generate vault key for tests
  const keyGen = new KeyGenerator();
  const vaultKey = await keyGen.generate();

  // =========================================================================
  // 1. Chain Configuration
  // =========================================================================
  console.log('[1] Chain Configuration');

  await test('SUPPORTED_CHAINS has expected networks', () => {
    const expected = ['ethereum', 'sepolia', 'polygon', 'arbitrum', 'base', 'optimism'];
    return expected.every(chain => chain in SUPPORTED_CHAINS);
  });

  await test('getChainById returns correct chain', () => {
    const chain = getChainById(1);
    return chain?.name === 'Ethereum Mainnet' && chain?.symbol === 'ETH';
  });

  await test('getChainByName returns correct chain', () => {
    const chain = getChainByName('polygon');
    return chain?.chainId === 137 && chain?.symbol === 'MATIC';
  });

  await test('Chain configs have required fields', () => {
    return Object.values(SUPPORTED_CHAINS).every(chain =>
      chain.chainId > 0 &&
      chain.name.length > 0 &&
      chain.rpcUrl.startsWith('https://') &&
      chain.symbol.length > 0 &&
      chain.explorer.startsWith('https://')
    );
  });

  // =========================================================================
  // 2. VaultWeb3Wallet
  // =========================================================================
  console.log('\n[2] VaultWeb3Wallet');

  let wallet: VaultWeb3Wallet;

  await test('VaultWeb3Wallet.create() succeeds', async () => {
    wallet = await VaultWeb3Wallet.create(vaultKey, 'sepolia');
    return wallet !== null;
  });

  await test('wallet address is valid Ethereum address', () => {
    return isValidAddress(wallet.address);
  });

  await test('wallet address starts with 0x and is 42 chars', () => {
    return wallet.address.startsWith('0x') && wallet.address.length === 42;
  });

  await test('getInfo() returns correct structure', () => {
    const info = wallet.getInfo();
    return (
      typeof info.address === 'string' &&
      typeof info.publicKey === 'string' &&
      typeof info.chainId === 'number' &&
      info.chainId === 11155111 // Sepolia
    );
  });

  await test('switchChain() works correctly', () => {
    wallet.switchChain('polygon');
    const chain = wallet.getChain();
    wallet.switchChain('sepolia'); // Reset
    return chain.chainId === 137;
  });

  await test('signMessage() returns valid signature', async () => {
    const signature = await wallet.signMessage('Test message');
    return (
      signature.startsWith('0x') &&
      signature.length === 132 // 0x + 65 bytes * 2
    );
  });

  await test('same vaultKey produces same address', async () => {
    const wallet2 = await VaultWeb3Wallet.create(vaultKey, 'sepolia');
    return wallet.address === wallet2.address;
  });

  await test('different vaultKey produces different address', async () => {
    const differentKey = await keyGen.generate();
    const wallet2 = await VaultWeb3Wallet.create(differentKey, 'sepolia');
    return wallet.address !== wallet2.address;
  });

  await test('getExplorerUrl() returns correct URL', () => {
    const url = wallet.getExplorerUrl();
    return url.includes('sepolia.etherscan.io') && url.includes(wallet.address);
  });

  // =========================================================================
  // 3. IPFSClient
  // =========================================================================
  console.log('\n[3] IPFSClient');

  const ipfs = new IPFSClient();

  await test('IPFSClient upload returns CID', async () => {
    const data = new TextEncoder().encode('Test backup data');
    const result = await ipfs.upload(data);
    return result.cid.startsWith('Qm') && result.size === data.length;
  });

  await test('IPFSClient uploadJSON works', async () => {
    const data = { test: 'value', number: 123 };
    const result = await ipfs.uploadJSON(data);
    return result.cid.startsWith('Qm');
  });

  await test('getUrl returns gateway URL', () => {
    const url = ipfs.getUrl('QmTest123');
    return url.includes('ipfs.io/ipfs/QmTest123');
  });

  await test('same content produces same CID', async () => {
    const data = new TextEncoder().encode('Deterministic content');
    const result1 = await ipfs.upload(data);
    const result2 = await ipfs.upload(data);
    return result1.cid === result2.cid;
  });

  // =========================================================================
  // 4. BackupRegistry
  // =========================================================================
  console.log('\n[4] BackupRegistry');

  const registry = new BackupRegistry(wallet, ipfs);

  await test('createBackupRegistration() returns valid structure', async () => {
    const backupData = new TextEncoder().encode('Encrypted vault backup data');
    const reg = await registry.createBackupRegistration('backup_001', backupData);
    
    return (
      reg.backupId.startsWith('0x') &&
      reg.contentHash.startsWith('0x') &&
      reg.signature.startsWith('0x') &&
      typeof reg.timestamp === 'number'
    );
  });

  await test('createBackupRegistration with IPFS upload', async () => {
    const backupData = new TextEncoder().encode('Backup with IPFS');
    const reg = await registry.createBackupRegistration('backup_002', backupData, true);
    
    return reg.ipfsCid !== undefined && reg.ipfsCid.startsWith('Qm');
  });

  await test('verifyBackup() returns correct result', async () => {
    const backupData = new TextEncoder().encode('Verification test');
    const result = await registry.verifyBackup('backup_003', backupData);
    
    return result.valid && result.contentHash === result.computedHash;
  });

  // =========================================================================
  // 5. DecentralizedBackupManager
  // =========================================================================
  console.log('\n[5] DecentralizedBackupManager');

  let manager: DecentralizedBackupManager;

  await test('DecentralizedBackupManager.create() succeeds', async () => {
    manager = await DecentralizedBackupManager.create(vaultKey, {
      chain: 'sepolia',
      autoUploadIPFS: false
    });
    return manager !== null;
  });

  await test('getWalletAddress() returns valid address', () => {
    return isValidAddress(manager.getWalletAddress());
  });

  await test('getChainInfo() returns Sepolia config', () => {
    const info = manager.getChainInfo();
    return info.chainId === 11155111 && info.name === 'Ethereum Sepolia';
  });

  await test('createBackup() works correctly', async () => {
    const vault = new Vault(vaultKey);
    const testData = new TextEncoder().encode('Secret vault data');
    const encrypted = await vault.encrypt(testData);
    
    const record = await manager.createBackup(
      'vault_backup_2024_01',
      encrypted.ciphertext
    );
    
    return (
      record.id === 'vault_backup_2024_01' &&
      record.localHash.startsWith('0x') &&
      record.verified === true
    );
  });

  await test('createBackup with IPFS upload', async () => {
    const testData = new TextEncoder().encode('IPFS backup test');
    
    const record = await manager.createBackup(
      'ipfs_backup_001',
      testData,
      { uploadToIPFS: true }
    );
    
    return record.ipfsCid !== undefined && record.ipfsCid.startsWith('Qm');
  });

  await test('verifyBackup() confirms valid backup', async () => {
    const testData = new TextEncoder().encode('Verify me');
    await manager.createBackup('verify_test', testData);
    
    const result = await manager.verifyBackup('verify_test', testData);
    return result.valid && result.details.hashMatch;
  });

  await test('verifyBackup() detects invalid data', async () => {
    const originalData = new TextEncoder().encode('Original');
    const modifiedData = new TextEncoder().encode('Modified');
    await manager.createBackup('tamper_test', originalData);
    
    const result = await manager.verifyBackup('tamper_test', modifiedData);
    return !result.valid && !result.details.hashMatch;
  });

  await test('listBackups() returns all backups', () => {
    const backups = manager.listBackups();
    return backups.length >= 3; // Created in previous tests
  });

  await test('getBackup() returns specific backup', () => {
    const backup = manager.getBackup('verify_test');
    return backup !== undefined && backup.id === 'verify_test';
  });

  await test('exportRecords() and importRecords() work', async () => {
    const exported = manager.exportRecords();
    
    const newManager = await DecentralizedBackupManager.create(vaultKey, {
      chain: 'sepolia'
    });
    newManager.importRecords(exported);
    
    return newManager.listBackups().length === manager.listBackups().length;
  });

  // =========================================================================
  // 6. Utility Functions
  // =========================================================================
  console.log('\n[6] Utility Functions');

  await test('isValidAddress() validates correctly', () => {
    return (
      isValidAddress('0x1234567890123456789012345678901234567890') &&
      !isValidAddress('0x123') &&
      !isValidAddress('not an address') &&
      !isValidAddress('1234567890123456789012345678901234567890')
    );
  });

  await test('formatEther() formats correctly', () => {
    const result = formatEther(1000000000000000000n);
    return result === '1.000000';
  });

  await test('parseEther() parses correctly', () => {
    const result = parseEther('1.5');
    return result === 1500000000000000000n;
  });

  await test('shortenAddress() formats correctly', () => {
    const short = shortenAddress('0x1234567890123456789012345678901234567890');
    return short === '0x1234...7890';
  });

  await test('shortenAddress() with custom length', () => {
    const short = shortenAddress('0x1234567890123456789012345678901234567890', 6);
    return short === '0x123456...567890';
  });

  // =========================================================================
  // 7. Integration with Vault
  // =========================================================================
  console.log('\n[7] Integration with Vault');

  await test('Full backup workflow: encrypt -> backup -> verify', async () => {
    // Create vault and encrypt data
    const vault = new Vault(vaultKey);
    const secretData = new TextEncoder().encode('Super secret information');
    const encrypted = await vault.encrypt(secretData);
    
    // Create backup
    const backupPayload = Vault.toPayload(encrypted);
    const backupBytes = new TextEncoder().encode(JSON.stringify(backupPayload));
    
    const backup = await manager.createBackup('full_workflow_test', backupBytes);
    
    // Verify backup
    const verification = await manager.verifyBackup('full_workflow_test', backupBytes);
    
    // Decrypt and verify content
    const restored = Vault.fromPayload(backupPayload);
    const decrypted = await vault.decrypt(restored);
    const decryptedText = new TextDecoder().decode(decrypted);
    
    return (
      verification.valid &&
      decryptedText === 'Super secret information'
    );
  });

  await test('Wallet derived from same key as Vault', async () => {
    // Both should derive consistently from same vault key
    const vault = new Vault(vaultKey);
    const walletFromKey = await VaultWeb3Wallet.create(vaultKey, 'sepolia');
    
    const vaultFingerprint = await vault.getFingerprint();
    
    // Both use same source key
    return (
      walletFromKey.address === manager.getWalletAddress() &&
      vaultFingerprint.length === 16
    );
  });

  // =========================================================================
  // Summary
  // =========================================================================
  console.log('\n' + '='.repeat(60));
  const passed = results.filter(r => r.passed).length;
  const total = results.length;
  console.log(`  RESULTAT: ${passed}/${total} tests reussis`);

  if (passed === total) {
    console.log('  STATUS: OK - Web3 integration operationnelle');
  } else {
    console.log('  STATUS: ERREUR - Certains tests ont echoue');
    results.filter(r => !r.passed).forEach(r => {
      console.log(`    - ${r.name}${r.details ? ': ' + r.details : ''}`);
    });
  }
  console.log('='.repeat(60) + '\n');

  process.exit(passed === total ? 0 : 1);
}

runTests().catch(console.error);
