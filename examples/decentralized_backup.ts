/**
 * Exemple: Système de Backup Décentralisé
 * Poly-Spinor Nexus 7D
 * 
 * Démontre:
 * - Création d'un backup chiffré du vault
 * - Upload vers IPFS (décentralisé)
 * - Enregistrement du hash on-chain
 * - Vérification d'intégrité
 * - Restauration depuis IPFS
 */

import {
  KeyGenerator,
  Vault,
  SecretSharing,
  VaultWeb3Wallet,
  DecentralizedBackupManager,
  SUPPORTED_CHAINS,
  shortenAddress,
  formatEther
} from '../sdk/javascript/src';

async function main() {
  console.log('='.repeat(70));
  console.log('  SYSTEME DE BACKUP DECENTRALISE - POLY-SPINOR NEXUS 7D');
  console.log('='.repeat(70));

  // =========================================================================
  // 1. INITIALISATION
  // =========================================================================
  console.log('\n[1] INITIALISATION DU VAULT');
  console.log('-'.repeat(50));

  const keyGen = new KeyGenerator();
  const vaultKey = await keyGen.generate();
  const vault = new Vault(vaultKey);

  console.log(`    Cle vault generee: ${Buffer.from(vaultKey).toString('hex').slice(0, 32)}...`);
  console.log(`    Fingerprint: ${await vault.getFingerprint()}`);

  // =========================================================================
  // 2. WALLET WEB3
  // =========================================================================
  console.log('\n[2] DERIVATION DU WALLET WEB3');
  console.log('-'.repeat(50));

  // Créer un wallet sur Sepolia (testnet)
  const backupManager = await DecentralizedBackupManager.create(vaultKey, {
    chain: 'sepolia',
    autoUploadIPFS: true,
    ipfsGateway: 'https://ipfs.io/ipfs'
  });

  const walletAddress = backupManager.getWalletAddress();
  const chainInfo = backupManager.getChainInfo();

  console.log(`    Adresse wallet: ${walletAddress}`);
  console.log(`    Adresse courte: ${shortenAddress(walletAddress)}`);
  console.log(`    Reseau: ${chainInfo.name} (Chain ID: ${chainInfo.chainId})`);
  console.log(`    Symbole: ${chainInfo.symbol}`);
  console.log(`    Explorer: ${chainInfo.explorer}/address/${walletAddress}`);

  // =========================================================================
  // 3. DONNEES A SAUVEGARDER
  // =========================================================================
  console.log('\n[3] PREPARATION DES DONNEES');
  console.log('-'.repeat(50));

  // Données sensibles à sauvegarder
  const sensitiveData = {
    vault_version: '7.0',
    created_at: new Date().toISOString(),
    secrets: [
      { name: 'API Key Production', value: 'sk_live_xxxxxxxxxxxxx' },
      { name: 'Database Password', value: 'super_secret_db_pass' },
      { name: 'Private Key', value: '0x1234567890abcdef...' }
    ],
    metadata: {
      owner: 'user@example.com',
      backup_schedule: 'daily'
    }
  };

  const plaintext = new TextEncoder().encode(JSON.stringify(sensitiveData, null, 2));
  console.log(`    Taille des donnees: ${plaintext.length} bytes`);
  console.log(`    Nombre de secrets: ${sensitiveData.secrets.length}`);

  // Chiffrer avec le vault
  const encrypted = await vault.encrypt(plaintext, { type: 'full_backup' });
  const payload = Vault.toPayload(encrypted);
  const backupBytes = new TextEncoder().encode(JSON.stringify(payload));

  console.log(`    Donnees chiffrees: ${backupBytes.length} bytes`);
  console.log(`    Nonce: ${payload.nonce}`);

  // =========================================================================
  // 4. CREATION DU BACKUP DECENTRALISE
  // =========================================================================
  console.log('\n[4] BACKUP DECENTRALISE (IPFS + On-Chain)');
  console.log('-'.repeat(50));

  const backupId = `vault_backup_${Date.now()}`;
  
  const backup = await backupManager.createBackup(
    backupId,
    backupBytes,
    { uploadToIPFS: true, registerOnChain: true }
  );

  console.log(`    Backup ID: ${backup.id}`);
  console.log(`    Content Hash: ${backup.localHash.slice(0, 32)}...`);
  console.log(`    IPFS CID: ${backup.ipfsCid || 'Non uploade'}`);
  console.log(`    Timestamp: ${new Date(backup.createdAt).toISOString()}`);
  console.log(`    Verifie: ${backup.verified ? 'Oui' : 'Non'}`);

  if (backup.chainRegistration) {
    console.log(`\n    [On-Chain Registration]`);
    console.log(`    Backup ID (hash): ${backup.chainRegistration.backupId.slice(0, 32)}...`);
    console.log(`    Signature: ${backup.chainRegistration.signature.slice(0, 32)}...`);
  }

  // =========================================================================
  // 5. SECRET SHARING (Backup des parts)
  // =========================================================================
  console.log('\n[5] SECRET SHARING (Sauvegarde Distribuee)');
  console.log('-'.repeat(50));

  const sharing = new SecretSharing(3, 5);
  const shares = await sharing.split(vaultKey);

  console.log(`    Schema: 3-of-5 (${shares.length} parts creees)`);
  console.log(`    Parts:`);

  // Créer un backup pour chaque part
  const shareBackups = [];
  for (const share of shares) {
    const shareData = SecretSharing.toData(share);
    const shareBytes = new TextEncoder().encode(JSON.stringify(shareData));
    
    const shareBackup = await backupManager.createBackup(
      `share_${share.index}_${Date.now()}`,
      shareBytes,
      { uploadToIPFS: true }
    );
    
    shareBackups.push(shareBackup);
    console.log(`      Part ${share.index}: checksum=${share.checksum}, IPFS=${shareBackup.ipfsCid?.slice(0, 20)}...`);
  }

  // =========================================================================
  // 6. VERIFICATION D'INTEGRITE
  // =========================================================================
  console.log('\n[6] VERIFICATION D\'INTEGRITE');
  console.log('-'.repeat(50));

  const verificationResult = await backupManager.verifyBackup(backupId, backupBytes);
  console.log(`    Backup valide: ${verificationResult.valid ? 'OUI' : 'NON'}`);
  console.log(`    Hash match: ${verificationResult.details.hashMatch ? 'OUI' : 'NON'}`);
  console.log(`    IPFS disponible: ${verificationResult.details.ipfsAvailable ? 'OUI' : 'NON'}`);
  console.log(`    Enregistre on-chain: ${verificationResult.details.chainVerified ? 'OUI' : 'NON'}`);

  // Test avec données modifiées
  const tamperedData = new TextEncoder().encode('Modified data');
  const tamperResult = await backupManager.verifyBackup(backupId, tamperedData);
  console.log(`\n    [Test de detection de modification]`);
  console.log(`    Donnees modifiees detectees: ${!tamperResult.valid ? 'OUI' : 'NON'}`);

  // =========================================================================
  // 7. LISTE DES BACKUPS
  // =========================================================================
  console.log('\n[7] LISTE DES BACKUPS');
  console.log('-'.repeat(50));

  const allBackups = backupManager.listBackups();
  console.log(`    Total: ${allBackups.length} backups\n`);

  for (const b of allBackups.slice(0, 5)) {
    console.log(`    - ${b.id.slice(0, 30)}...`);
    console.log(`      Hash: ${b.localHash.slice(0, 24)}...`);
    console.log(`      IPFS: ${b.ipfsCid ? b.ipfsCid.slice(0, 20) + '...' : 'N/A'}`);
    console.log(`      Date: ${new Date(b.createdAt).toLocaleString()}`);
  }

  // =========================================================================
  // 8. EXPORT DES RECORDS
  // =========================================================================
  console.log('\n[8] EXPORT DES RECORDS');
  console.log('-'.repeat(50));

  const exportedRecords = backupManager.exportRecords();
  const exportJson = JSON.stringify(exportedRecords, null, 2);
  
  console.log(`    Records exportes: ${Object.keys(exportedRecords).length}`);
  console.log(`    Taille JSON: ${exportJson.length} bytes`);

  // =========================================================================
  // 9. SIMULATION DE RESTAURATION
  // =========================================================================
  console.log('\n[9] SIMULATION DE RESTAURATION');
  console.log('-'.repeat(50));

  // Créer un nouveau manager (simule une nouvelle installation)
  const newManager = await DecentralizedBackupManager.create(vaultKey, {
    chain: 'sepolia'
  });

  // Importer les records
  newManager.importRecords(exportedRecords);
  console.log(`    Records importes: ${newManager.listBackups().length}`);

  // Récupérer un backup
  const recoveredBackup = newManager.getBackup(backupId);
  if (recoveredBackup) {
    console.log(`    Backup trouve: ${recoveredBackup.id}`);
    console.log(`    Hash original: ${recoveredBackup.localHash.slice(0, 32)}...`);
    
    // Vérifier l'intégrité
    const recoveryVerify = await newManager.verifyBackup(backupId, backupBytes);
    console.log(`    Integrite verifiee: ${recoveryVerify.valid ? 'OUI' : 'NON'}`);
    
    // Déchiffrer
    const decryptedPayload = JSON.parse(new TextDecoder().decode(backupBytes));
    const restored = Vault.fromPayload(decryptedPayload);
    const decrypted = await vault.decrypt(restored);
    const restoredData = JSON.parse(new TextDecoder().decode(decrypted));
    
    console.log(`\n    [Donnees restaurees]`);
    console.log(`    Version vault: ${restoredData.vault_version}`);
    console.log(`    Secrets recuperes: ${restoredData.secrets.length}`);
    console.log(`    Propriétaire: ${restoredData.metadata.owner}`);
  }

  // =========================================================================
  // 10. CHAINES SUPPORTEES
  // =========================================================================
  console.log('\n[10] CHAINES EVM SUPPORTEES');
  console.log('-'.repeat(50));

  for (const [name, config] of Object.entries(SUPPORTED_CHAINS)) {
    console.log(`    ${name.padEnd(12)} | Chain ID: ${config.chainId.toString().padEnd(8)} | ${config.symbol}`);
  }

  // =========================================================================
  // RESUME
  // =========================================================================
  console.log('\n' + '='.repeat(70));
  console.log('  RESUME DU SYSTEME DE BACKUP DECENTRALISE');
  console.log('='.repeat(70));
  console.log(`
  Le systeme de backup decentralise Poly-Spinor Nexus 7D offre:

  [1] CHIFFREMENT LOCAL
      - AES-256-GCM pour les donnees
      - Derivation de cles HKDF
      - Metadonnees chiffrees

  [2] STOCKAGE DECENTRALISE (IPFS)
      - Donnees distribuees sur le reseau IPFS
      - Content-addressed (immuable)
      - Accessible depuis n'importe quel gateway

  [3] VERIFICATION ON-CHAIN
      - Hash du backup enregistre sur Ethereum/L2
      - Preuve d'existence horodatee
      - Verification cryptographique

  [4] SECRET SHARING
      - Parts Shamir pour recuperation
      - Chaque part sauvegardee independamment
      - Threshold pour reconstruction

  [5] MULTI-CHAIN
      - Ethereum, Polygon, Arbitrum, Base, Optimism
      - Meme cle vault = meme adresse sur toutes les chaines
      - Choix du reseau selon couts/vitesse

  Adresse de reception pour les frais de gas:
  ${walletAddress}
  `);
  console.log('='.repeat(70));
}

main().catch(console.error);
