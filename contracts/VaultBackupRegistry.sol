// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title VaultBackupRegistry
 * @notice On-chain registry for Eidolon vault backups
 * @dev Stores backup hashes and IPFS CIDs for verification
 * 
 * Features:
 * - Register backup hashes with IPFS CID
 * - Verify backup integrity on-chain
 * - Multi-chain deployment support
 * - Owner-based access control
 * - Event emission for indexing
 */

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

contract VaultBackupRegistry is Ownable, ReentrancyGuard {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;
    
    // ========================================================================
    // STRUCTS
    // ========================================================================
    
    struct BackupEntry {
        bytes32 contentHash;      // SHA-256 hash of backup content
        string ipfsCid;           // IPFS Content Identifier
        uint256 timestamp;        // Registration timestamp
        address owner;            // Backup owner address
        bool exists;              // Entry existence flag
        uint256 version;          // Backup version number
    }
    
    struct VaultInfo {
        address owner;
        bytes32 publicKeyHash;    // Hash of vault public key
        uint256 backupCount;
        uint256 registeredAt;
        bool isActive;
    }
    
    // ========================================================================
    // STATE VARIABLES
    // ========================================================================
    
    /// @notice Mapping from backup ID to backup entry
    mapping(bytes32 => BackupEntry) public backups;
    
    /// @notice Mapping from vault public key hash to vault info
    mapping(bytes32 => VaultInfo) public vaults;
    
    /// @notice Mapping from owner to their backup IDs
    mapping(address => bytes32[]) public ownerBackups;
    
    /// @notice Total number of registered backups
    uint256 public totalBackups;
    
    /// @notice Total number of registered vaults
    uint256 public totalVaults;
    
    /// @notice Registration fee (can be 0)
    uint256 public registrationFee;
    
    /// @notice Minimum time between backup updates
    uint256 public updateCooldown = 1 hours;
    
    /// @notice Last update timestamp per backup
    mapping(bytes32 => uint256) public lastUpdateTime;
    
    // ========================================================================
    // EVENTS
    // ========================================================================
    
    event BackupRegistered(
        bytes32 indexed backupId,
        address indexed owner,
        bytes32 contentHash,
        string ipfsCid,
        uint256 timestamp,
        uint256 version
    );
    
    event BackupUpdated(
        bytes32 indexed backupId,
        bytes32 oldHash,
        bytes32 newHash,
        string newIpfsCid,
        uint256 version
    );
    
    event BackupVerified(
        bytes32 indexed backupId,
        address indexed verifier,
        bool isValid
    );
    
    event VaultRegistered(
        bytes32 indexed publicKeyHash,
        address indexed owner,
        uint256 timestamp
    );
    
    event RegistrationFeeUpdated(uint256 oldFee, uint256 newFee);
    
    // ========================================================================
    // ERRORS
    // ========================================================================
    
    error BackupAlreadyExists();
    error BackupNotFound();
    error NotBackupOwner();
    error InvalidSignature();
    error InsufficientFee();
    error UpdateCooldownNotMet();
    error VaultNotRegistered();
    error InvalidContentHash();
    error EmptyIPFSCid();
    
    // ========================================================================
    // CONSTRUCTOR
    // ========================================================================
    
    constructor() Ownable(msg.sender) {
        registrationFee = 0; // Free by default
    }
    
    // ========================================================================
    // VAULT REGISTRATION
    // ========================================================================
    
    /**
     * @notice Register a vault public key
     * @param publicKeyHash Hash of the vault's public key
     */
    function registerVault(bytes32 publicKeyHash) external {
        require(publicKeyHash != bytes32(0), "Invalid public key hash");
        require(!vaults[publicKeyHash].isActive, "Vault already registered");
        
        vaults[publicKeyHash] = VaultInfo({
            owner: msg.sender,
            publicKeyHash: publicKeyHash,
            backupCount: 0,
            registeredAt: block.timestamp,
            isActive: true
        });
        
        totalVaults++;
        
        emit VaultRegistered(publicKeyHash, msg.sender, block.timestamp);
    }
    
    // ========================================================================
    // BACKUP REGISTRATION
    // ========================================================================
    
    /**
     * @notice Register a new backup
     * @param backupId Unique identifier for the backup (hash of backup name)
     * @param contentHash SHA-256 hash of backup content
     * @param ipfsCid IPFS Content Identifier for the backup
     * @param signature Signature proving ownership
     */
    function registerBackup(
        bytes32 backupId,
        bytes32 contentHash,
        string calldata ipfsCid,
        bytes calldata signature
    ) external payable nonReentrant returns (bool) {
        // Validate inputs
        if (contentHash == bytes32(0)) revert InvalidContentHash();
        if (bytes(ipfsCid).length == 0) revert EmptyIPFSCid();
        if (backups[backupId].exists) revert BackupAlreadyExists();
        
        // Check fee
        if (msg.value < registrationFee) revert InsufficientFee();
        
        // Verify signature
        bytes32 messageHash = keccak256(
            abi.encodePacked(
                "PSNX_BACKUP:",
                backupId,
                ":",
                contentHash,
                ":",
                block.timestamp
            )
        );
        bytes32 ethSignedHash = messageHash.toEthSignedMessageHash();
        address signer = ethSignedHash.recover(signature);
        
        if (signer != msg.sender) revert InvalidSignature();
        
        // Store backup
        backups[backupId] = BackupEntry({
            contentHash: contentHash,
            ipfsCid: ipfsCid,
            timestamp: block.timestamp,
            owner: msg.sender,
            exists: true,
            version: 1
        });
        
        ownerBackups[msg.sender].push(backupId);
        totalBackups++;
        lastUpdateTime[backupId] = block.timestamp;
        
        emit BackupRegistered(
            backupId,
            msg.sender,
            contentHash,
            ipfsCid,
            block.timestamp,
            1
        );
        
        return true;
    }
    
    /**
     * @notice Update an existing backup
     * @param backupId Backup identifier
     * @param newContentHash New content hash
     * @param newIpfsCid New IPFS CID
     */
    function updateBackup(
        bytes32 backupId,
        bytes32 newContentHash,
        string calldata newIpfsCid
    ) external nonReentrant {
        BackupEntry storage backup = backups[backupId];
        
        if (!backup.exists) revert BackupNotFound();
        if (backup.owner != msg.sender) revert NotBackupOwner();
        if (block.timestamp < lastUpdateTime[backupId] + updateCooldown) {
            revert UpdateCooldownNotMet();
        }
        if (newContentHash == bytes32(0)) revert InvalidContentHash();
        
        bytes32 oldHash = backup.contentHash;
        
        backup.contentHash = newContentHash;
        backup.ipfsCid = newIpfsCid;
        backup.timestamp = block.timestamp;
        backup.version++;
        
        lastUpdateTime[backupId] = block.timestamp;
        
        emit BackupUpdated(
            backupId,
            oldHash,
            newContentHash,
            newIpfsCid,
            backup.version
        );
    }
    
    // ========================================================================
    // VERIFICATION
    // ========================================================================
    
    /**
     * @notice Verify a backup's content hash
     * @param backupId Backup identifier
     * @param contentHash Hash to verify against
     * @return valid True if hashes match
     */
    function verifyBackup(
        bytes32 backupId,
        bytes32 contentHash
    ) external returns (bool valid) {
        BackupEntry storage backup = backups[backupId];
        
        if (!backup.exists) revert BackupNotFound();
        
        valid = backup.contentHash == contentHash;
        
        emit BackupVerified(backupId, msg.sender, valid);
        
        return valid;
    }
    
    /**
     * @notice Get backup details
     * @param backupId Backup identifier
     * @return contentHash The content hash
     * @return ipfsCid The IPFS CID
     * @return timestamp Registration timestamp
     * @return owner Backup owner
     * @return version Backup version
     */
    function getBackup(bytes32 backupId) external view returns (
        bytes32 contentHash,
        string memory ipfsCid,
        uint256 timestamp,
        address owner,
        uint256 version
    ) {
        BackupEntry storage backup = backups[backupId];
        if (!backup.exists) revert BackupNotFound();
        
        return (
            backup.contentHash,
            backup.ipfsCid,
            backup.timestamp,
            backup.owner,
            backup.version
        );
    }
    
    /**
     * @notice Check if a backup exists
     * @param backupId Backup identifier
     * @return exists True if backup exists
     */
    function backupExists(bytes32 backupId) external view returns (bool) {
        return backups[backupId].exists;
    }
    
    /**
     * @notice Get all backup IDs for an owner
     * @param owner Owner address
     * @return backupIds Array of backup IDs
     */
    function getOwnerBackups(address owner) external view returns (bytes32[] memory) {
        return ownerBackups[owner];
    }
    
    /**
     * @notice Get backup count for an owner
     * @param owner Owner address
     * @return count Number of backups
     */
    function getOwnerBackupCount(address owner) external view returns (uint256) {
        return ownerBackups[owner].length;
    }
    
    // ========================================================================
    // ADMIN FUNCTIONS
    // ========================================================================
    
    /**
     * @notice Update registration fee
     * @param newFee New fee amount in wei
     */
    function setRegistrationFee(uint256 newFee) external onlyOwner {
        uint256 oldFee = registrationFee;
        registrationFee = newFee;
        emit RegistrationFeeUpdated(oldFee, newFee);
    }
    
    /**
     * @notice Update cooldown period
     * @param newCooldown New cooldown in seconds
     */
    function setUpdateCooldown(uint256 newCooldown) external onlyOwner {
        updateCooldown = newCooldown;
    }
    
    /**
     * @notice Withdraw collected fees
     */
    function withdrawFees() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No fees to withdraw");
        payable(owner()).transfer(balance);
    }
    
    // ========================================================================
    // BATCH OPERATIONS
    // ========================================================================
    
    /**
     * @notice Batch verify multiple backups
     * @param backupIds Array of backup IDs
     * @param contentHashes Array of content hashes
     * @return results Array of verification results
     */
    function batchVerify(
        bytes32[] calldata backupIds,
        bytes32[] calldata contentHashes
    ) external view returns (bool[] memory results) {
        require(backupIds.length == contentHashes.length, "Array length mismatch");
        
        results = new bool[](backupIds.length);
        
        for (uint256 i = 0; i < backupIds.length; i++) {
            BackupEntry storage backup = backups[backupIds[i]];
            results[i] = backup.exists && backup.contentHash == contentHashes[i];
        }
        
        return results;
    }
    
    /**
     * @notice Get multiple backups at once
     * @param backupIds Array of backup IDs
     * @return entries Array of backup entries (as tuples)
     */
    function batchGetBackups(bytes32[] calldata backupIds) external view returns (
        bytes32[] memory contentHashes,
        string[] memory ipfsCids,
        uint256[] memory timestamps,
        address[] memory owners
    ) {
        uint256 length = backupIds.length;
        contentHashes = new bytes32[](length);
        ipfsCids = new string[](length);
        timestamps = new uint256[](length);
        owners = new address[](length);
        
        for (uint256 i = 0; i < length; i++) {
            BackupEntry storage backup = backups[backupIds[i]];
            if (backup.exists) {
                contentHashes[i] = backup.contentHash;
                ipfsCids[i] = backup.ipfsCid;
                timestamps[i] = backup.timestamp;
                owners[i] = backup.owner;
            }
        }
        
        return (contentHashes, ipfsCids, timestamps, owners);
    }
}
