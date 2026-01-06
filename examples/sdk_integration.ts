/**
 * SDK JavaScript - Exemple d'integration complete avec ZKP
 * 
 * Demontre:
 * - Generation de cles
 * - Chiffrement/dechiffrement local
 * - Authentification ZKP
 * - Secret sharing (Shamir)
 */

import {
  KeyGenerator,
  Vault,
  ZKPProver,
  ZKPVerifier,
  SecretSharing,
  PSNXClient
} from '../sdk/javascript/src';

async function main() {
  console.log('='.repeat(60));
  console.log('  DEMO SDK PSNX - Integration JavaScript + ZKP');
  console.log('='.repeat(60));

  // =========================================================================
  // 1. Generation de cle vault
  // =========================================================================
  console.log('\n[1] GENERATION DE CLE VAULT');
  console.log('-'.repeat(40));

  const keyGen = new KeyGenerator();
  const vaultKey = await keyGen.generate();
  console.log(`    Cle generee: ${Buffer.from(vaultKey).toString('hex').slice(0, 32)}...`);

  const keyPair = await keyGen.generateKeyPair();
  console.log(`    Fingerprint: ${keyPair.fingerprint}`);
  console.log(`    Entropie: ${keyPair.entropyBits} bits`);

  // =========================================================================
  // 2. Chiffrement / Dechiffrement
  // =========================================================================
  console.log('\n[2] CHIFFREMENT / DECHIFFREMENT');
  console.log('-'.repeat(40));

  const vault = new Vault(vaultKey);
  const message = new TextEncoder().encode('Donnees sensibles a proteger');
  
  console.log(`    Message original: "${new TextDecoder().decode(message)}"`);
  
  const encrypted = await vault.encrypt(message);
  console.log(`    Chiffre: ${Buffer.from(encrypted.ciphertext).toString('hex').slice(0, 32)}...`);
  console.log(`    Nonce: ${Buffer.from(encrypted.nonce).toString('hex')}`);
  
  const decrypted = await vault.decrypt(encrypted);
  console.log(`    Dechiffre: "${new TextDecoder().decode(decrypted)}"`);
  console.log(`    Verification: ${Buffer.from(message).equals(Buffer.from(decrypted)) ? 'OK' : 'ERREUR'}`);

  // =========================================================================
  // 3. Zero-Knowledge Proof
  // =========================================================================
  console.log('\n[3] AUTHENTIFICATION ZKP (Schnorr)');
  console.log('-'.repeat(40));

  const prover = await ZKPProver.create(vaultKey);
  console.log(`    Cle publique ZKP: ${prover.getPublicKeyHex().slice(0, 32)}...`);
  console.log(`    Fingerprint ZKP: ${await prover.getFingerprint()}`);

  // Simuler un challenge du serveur
  const challenge = `login_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  console.log(`    Challenge: ${challenge}`);

  // Creer la preuve
  const proofResult = await prover.createProof(challenge);
  console.log(`    Preuve creee a: ${new Date(proofResult.proof.timestamp * 1000).toISOString()}`);
  console.log(`    Commitment: ${proofResult.proof.commitment.slice(0, 32)}...`);
  console.log(`    Response: ${proofResult.proof.response.slice(0, 32)}...`);

  // Verifier la preuve
  const verification = await ZKPVerifier.verify(proofResult, challenge);
  console.log(`    Verification: ${verification.valid ? 'VALIDE' : 'INVALIDE'}`);
  console.log(`    Raison: ${verification.reason}`);

  // =========================================================================
  // 4. Secret Sharing (Shamir)
  // =========================================================================
  console.log('\n[4] SECRET SHARING (Shamir 3/5)');
  console.log('-'.repeat(40));

  const threshold = 3;
  const total = 5;
  const sharing = new SecretSharing(threshold, total);
  
  const secret = vaultKey.slice(0, 32);
  console.log(`    Secret: ${Buffer.from(secret).toString('hex').slice(0, 32)}...`);
  
  const shares = await sharing.split(secret);
  console.log(`    ${shares.length} parts creees:`);
  
  for (const share of shares) {
    console.log(`      Part ${share.index}: checksum=${share.checksum}`);
  }

  // Reconstruction avec 3 parts
  console.log(`\n    Reconstruction avec ${threshold} parts...`);
  const selectedShares = [shares[0], shares[2], shares[4]]; // Parts 1, 3, 5
  console.log(`    Parts selectionnees: ${selectedShares.map(s => s.index).join(', ')}`);
  
  const reconstructed = await sharing.reconstruct(selectedShares);
  const reconstructedHex = Buffer.from(reconstructed).toString('hex');
  const originalHex = Buffer.from(secret).toString('hex');
  
  console.log(`    Secret reconstruit: ${reconstructedHex.slice(0, 32)}...`);
  console.log(`    Verification: ${reconstructedHex === originalHex ? 'OK' : 'ERREUR'}`);

  // =========================================================================
  // 5. Derivation de sous-cle
  // =========================================================================
  console.log('\n[5] DERIVATION DE SOUS-CLES');
  console.log('-'.repeat(40));

  const purposes = ['encryption', 'signing', 'sharing', 'backup'];
  
  for (const purpose of purposes) {
    const subkey = await vault.deriveSubkey(purpose);
    console.log(`    ${purpose.padEnd(12)}: ${Buffer.from(subkey).toString('hex').slice(0, 32)}...`);
  }

  // =========================================================================
  // 6. Conversion vers format API
  // =========================================================================
  console.log('\n[6] SERIALISATION POUR API');
  console.log('-'.repeat(40));

  const payload = Vault.toPayload(encrypted);
  console.log(`    Format API:`);
  console.log(`      ciphertext: ${payload.ciphertext.slice(0, 32)}...`);
  console.log(`      nonce: ${payload.nonce}`);
  console.log(`      tag: ${payload.tag}`);

  const restored = Vault.fromPayload(payload);
  const decrypted2 = await vault.decrypt(restored);
  console.log(`    Restaure et dechiffre: "${new TextDecoder().decode(decrypted2)}"`);

  // =========================================================================
  // 7. Cle depuis mot de passe
  // =========================================================================
  console.log('\n[7] CLE DEPUIS MOT DE PASSE');
  console.log('-'.repeat(40));

  const password = 'MonMotDePasse123!';
  const derived = await keyGen.fromPassword(password);
  
  console.log(`    Mot de passe: ${'*'.repeat(password.length)}`);
  console.log(`    Salt: ${Buffer.from(derived.salt).toString('hex')}`);
  console.log(`    Cle derivee: ${Buffer.from(derived.vaultKey).toString('hex').slice(0, 32)}...`);

  // Verification reproductibilite
  const derived2 = await keyGen.fromPassword(password, derived.salt);
  const match = Buffer.from(derived.vaultKey).equals(Buffer.from(derived2.vaultKey));
  console.log(`    Reproductible: ${match ? 'OUI' : 'NON'}`);

  console.log('\n' + '='.repeat(60));
  console.log('  DEMO TERMINEE');
  console.log('='.repeat(60));
}

// Execute
main().catch(console.error);
