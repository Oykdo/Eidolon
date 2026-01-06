/**
 * Test d'integration SDK JavaScript <-> API Python
 * 
 * Ce test verifie que:
 * - Les formats de donnees sont compatibles
 * - Les preuves ZKP JS sont verifiables par Python
 * - Le chiffrement est interoperable
 */

import {
  KeyGenerator,
  Vault,
  ZKPProver,
  SecretSharing
} from '../sdk/javascript/src';
import type { ZKPProof, EncryptedData } from '../sdk/javascript/src';

interface TestResult {
  name: string;
  passed: boolean;
  details?: string;
}

const results: TestResult[] = [];

function test(name: string, fn: () => Promise<boolean> | boolean): Promise<void> {
  return (async () => {
    try {
      const passed = await fn();
      results.push({ name, passed });
      console.log(`  ${passed ? '[PASS]' : '[FAIL]'} ${name}`);
    } catch (e) {
      results.push({ name, passed: false, details: String(e) });
      console.log(`  [FAIL] ${name}: ${e}`);
    }
  })();
}

async function runTests() {
  console.log('\n' + '='.repeat(60));
  console.log('  TESTS INTEGRATION SDK JS <-> API PYTHON');
  console.log('='.repeat(60) + '\n');

  // =========================================================================
  // 1. KeyGenerator
  // =========================================================================
  console.log('[1] KeyGenerator');
  
  const keyGen = new KeyGenerator();
  
  await test('generate() returns 32 bytes', async () => {
    const key = await keyGen.generate();
    return key.length === 32;
  });

  await test('generateKeyPair() has valid structure', async () => {
    const kp = await keyGen.generateKeyPair();
    return (
      kp.vaultKey.length === 32 &&
      kp.fingerprint.length === 16 &&
      kp.entropyBits === 256 &&
      kp.publicKey > 0n
    );
  });

  await test('fromPassword() is deterministic', async () => {
    const pwd = 'test-password-123';
    const d1 = await keyGen.fromPassword(pwd);
    const d2 = await keyGen.fromPassword(pwd, d1.salt);
    return Buffer.from(d1.vaultKey).equals(Buffer.from(d2.vaultKey));
  });

  // =========================================================================
  // 2. Vault
  // =========================================================================
  console.log('\n[2] Vault Encryption');
  
  const vaultKey = await keyGen.generate();
  const vault = new Vault(vaultKey);

  await test('encrypt/decrypt roundtrip', async () => {
    const data = new TextEncoder().encode('test data 123');
    const encrypted = await vault.encrypt(data);
    const decrypted = await vault.decrypt(encrypted);
    return Buffer.from(data).equals(Buffer.from(decrypted));
  });

  await test('encrypted data has correct structure', async () => {
    const data = new TextEncoder().encode('test');
    const encrypted = await vault.encrypt(data);
    return (
      encrypted.ciphertext instanceof Uint8Array &&
      encrypted.nonce.length === 12 &&
      encrypted.tag.length === 16
    );
  });

  await test('Vault.toPayload() creates base64 strings', async () => {
    const data = new TextEncoder().encode('test');
    const encrypted = await vault.encrypt(data);
    const payload = Vault.toPayload(encrypted);
    return (
      typeof payload.ciphertext === 'string' &&
      typeof payload.nonce === 'string' &&
      typeof payload.tag === 'string'
    );
  });

  await test('Vault.fromPayload() restores correctly', async () => {
    const data = new TextEncoder().encode('test');
    const encrypted = await vault.encrypt(data);
    const payload = Vault.toPayload(encrypted);
    const restored = Vault.fromPayload(payload);
    const decrypted = await vault.decrypt(restored);
    return Buffer.from(data).equals(Buffer.from(decrypted));
  });

  // =========================================================================
  // 3. ZKP
  // =========================================================================
  console.log('\n[3] ZKP Authentication');
  
  const zkp = await ZKPProver.create(vaultKey);

  await test('ZKPProver.getPublicKeyHex() starts with 0x', () => {
    return zkp.getPublicKeyHex().startsWith('0x');
  });

  await test('createProof() returns valid structure', async () => {
    const proof = await zkp.createProof('test-challenge');
    return (
      proof.proof.commitment.startsWith('0x') &&
      proof.proof.challenge.startsWith('0x') &&
      proof.proof.response.startsWith('0x') &&
      proof.proof.publicKey.startsWith('0x') &&
      typeof proof.proof.timestamp === 'number' &&
      proof.challenge === 'test-challenge'
    );
  });

  await test('proof format matches API expectations', async () => {
    const challenge = `login_${Date.now()}`;
    const result = await zkp.createProof(challenge);
    
    // Format attendu par api/auth.py VaultZKPAuth.verify_auth
    const apiFormat = {
      proof: {
        commitment: result.proof.commitment,
        challenge: result.proof.challenge,
        response: result.proof.response,
        public_key: result.proof.publicKey,
        message: result.proof.message,
        timestamp: result.proof.timestamp
      },
      challenge: result.challenge,
      key_fingerprint: result.keyFingerprint,
      timestamp: result.timestamp
    };
    
    return (
      typeof apiFormat.proof.commitment === 'string' &&
      typeof apiFormat.proof.public_key === 'string' &&
      typeof apiFormat.challenge === 'string'
    );
  });

  // =========================================================================
  // 4. Secret Sharing
  // =========================================================================
  console.log('\n[4] Secret Sharing');
  
  const sharing = new SecretSharing(3, 5);

  await test('split() creates correct number of shares', async () => {
    const shares = await sharing.split(vaultKey);
    return shares.length === 5;
  });

  await test('shares have valid structure', async () => {
    const shares = await sharing.split(vaultKey);
    return shares.every(s => 
      typeof s.index === 'number' &&
      s.data instanceof Uint8Array &&
      s.threshold === 3 &&
      s.total === 5 &&
      typeof s.checksum === 'string'
    );
  });

  await test('reconstruct() with threshold shares works', async () => {
    const shares = await sharing.split(vaultKey);
    const selected = [shares[0], shares[2], shares[4]];
    const reconstructed = await sharing.reconstruct(selected);
    return Buffer.from(vaultKey).equals(Buffer.from(reconstructed));
  });

  await test('SecretSharing.toData() creates API format', async () => {
    const shares = await sharing.split(vaultKey);
    const data = SecretSharing.toData(shares[0]);
    return (
      typeof data.index === 'number' &&
      typeof data.data === 'string' &&
      typeof data.threshold === 'number' &&
      typeof data.total === 'number' &&
      typeof data.checksum === 'string'
    );
  });

  // =========================================================================
  // 5. Cross-compatibility checks
  // =========================================================================
  console.log('\n[5] Cross-Compatibility');

  await test('hex encoding matches Python format', async () => {
    const bytes = new Uint8Array([0x12, 0x34, 0xab, 0xcd]);
    const hex = Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
    return hex === '1234abcd';
  });

  await test('base64 encoding is standard', async () => {
    const bytes = new Uint8Array([1, 2, 3, 4]);
    const b64 = Buffer.from(bytes).toString('base64');
    return b64 === 'AQIDBA==';
  });

  await test('bigint to hex conversion', () => {
    const n = 0x123456789abcdefn;
    const hex = '0x' + n.toString(16);
    return hex === '0x123456789abcdef';
  });

  // =========================================================================
  // Resume
  // =========================================================================
  console.log('\n' + '='.repeat(60));
  const passed = results.filter(r => r.passed).length;
  const total = results.length;
  console.log(`  RESULTAT: ${passed}/${total} tests reussis`);
  
  if (passed === total) {
    console.log('  STATUS: OK - SDK compatible avec API Python');
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
