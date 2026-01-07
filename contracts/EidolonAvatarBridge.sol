// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title IEidolonAvatarNFT
 * @notice Interface for the Avatar NFT contract
 */
interface IEidolonAvatarNFT {
    struct AvatarInfo {
        bytes32 vaultId;
        uint256 vaultNumber;
        bool isGenesis;
        uint256 mintedAt;
        string rarityTier;
    }
    
    function ownerOf(uint256 tokenId) external view returns (address);
    function getAvatarInfo(uint256 tokenId) external view returns (AvatarInfo memory);
    function tokenURI(uint256 tokenId) external view returns (string memory);
    function isLocked(uint256 tokenId) external view returns (bool);
    
    function lockForBridge(uint256 tokenId, uint256 destChainId) external;
    function unlockFromBridge(uint256 tokenId) external;
    function burnForBridge(uint256 tokenId, uint256 destChainId) external;
    function mintFromBridge(
        address to,
        bytes32 vaultId,
        uint256 vaultNumber,
        string memory tokenURI_,
        string memory rarityTier,
        bool wasGenesis
    ) external returns (uint256);
}

/**
 * @title EidolonAvatarBridge
 * @notice Cross-chain bridge for Eidolon Avatar NFTs
 * @dev Supports ETH <-> BSC bridging
 * 
 * Bridge flow:
 * 1. User locks avatar on source chain
 * 2. Relayer detects lock event
 * 3. User confirms on destination chain
 * 4. Avatar is burned on source, minted on destination
 * 
 * Security:
 * - Only one avatar can exist at a time (no duplicates)
 * - Relayer network validates transfers
 * - Timelock for cancellation
 */
contract EidolonAvatarBridge is Ownable, ReentrancyGuard, Pausable {
    
    // =========================================================================
    // STATE
    // =========================================================================
    
    // NFT contract
    IEidolonAvatarNFT public avatarNFT;
    
    // Supported destination chains
    mapping(uint256 => bool) public supportedChains;
    mapping(uint256 => address) public destBridgeAddress; // chainId => bridge address
    
    // Relayers (validators)
    mapping(address => bool) public relayers;
    uint256 public requiredSignatures = 1;
    
    // Bridge transfers
    struct BridgeTransfer {
        uint256 tokenId;
        address sender;
        address recipient;
        bytes32 vaultId;
        uint256 vaultNumber;
        string tokenURI;
        string rarityTier;
        bool isGenesis;
        uint256 destChainId;
        uint256 initiatedAt;
        uint256 completedAt;
        bool burned;
        bool completed;
        bool cancelled;
    }
    
    // Pending outgoing transfers (this chain -> other chain)
    mapping(bytes32 => BridgeTransfer) public outgoingTransfers;
    mapping(uint256 => bytes32) public tokenToTransfer; // tokenId => transferId
    
    // Processed incoming transfers (other chain -> this chain)
    mapping(bytes32 => bool) public processedTransfers;
    
    // Fees
    uint256 public bridgeFee = 0.001 ether;
    
    // Timelock
    uint256 public lockPeriod = 5 minutes;
    uint256 public cancelPeriod = 1 hours;
    
    // Nonce for transfer IDs
    uint256 private _nonce;
    
    // =========================================================================
    // EVENTS
    // =========================================================================
    
    event BridgeInitiated(
        bytes32 indexed transferId,
        uint256 indexed tokenId,
        address indexed sender,
        uint256 destChainId,
        bytes32 vaultId
    );
    
    event BridgeBurned(
        bytes32 indexed transferId,
        uint256 indexed tokenId,
        uint256 destChainId
    );
    
    event BridgeCompleted(
        bytes32 indexed transferId,
        uint256 indexed newTokenId,
        address indexed recipient,
        uint256 sourceChainId
    );
    
    event BridgeCancelled(
        bytes32 indexed transferId,
        uint256 indexed tokenId
    );
    
    event RelayerUpdated(address indexed relayer, bool status);
    event ChainUpdated(uint256 indexed chainId, bool supported, address bridge);
    
    // =========================================================================
    // MODIFIERS
    // =========================================================================
    
    modifier onlyRelayer() {
        require(relayers[msg.sender], "Not a relayer");
        _;
    }
    
    // =========================================================================
    // CONSTRUCTOR
    // =========================================================================
    
    constructor(address avatarNFT_) {
        avatarNFT = IEidolonAvatarNFT(avatarNFT_);
        relayers[msg.sender] = true;
    }
    
    // =========================================================================
    // BRIDGE: OUTGOING (Lock & Burn)
    // =========================================================================
    
    /**
     * @notice Initiate bridge transfer to another chain
     * @param tokenId Token to bridge
     * @param destChainId Destination chain ID
     * @param recipient Address on destination chain
     */
    function initiateBridge(
        uint256 tokenId,
        uint256 destChainId,
        address recipient
    ) external payable nonReentrant whenNotPaused returns (bytes32) {
        require(msg.value >= bridgeFee, "Insufficient bridge fee");
        require(supportedChains[destChainId], "Destination chain not supported");
        require(avatarNFT.ownerOf(tokenId) == msg.sender, "Not token owner");
        require(!avatarNFT.isLocked(tokenId), "Token already locked");
        
        // Lock the token
        avatarNFT.lockForBridge(tokenId, destChainId);
        
        // Get avatar info
        IEidolonAvatarNFT.AvatarInfo memory info = avatarNFT.getAvatarInfo(tokenId);
        string memory uri = avatarNFT.tokenURI(tokenId);
        
        // Create transfer ID
        bytes32 transferId = keccak256(abi.encodePacked(
            block.chainid,
            tokenId,
            msg.sender,
            destChainId,
            block.timestamp,
            _nonce++
        ));
        
        // Store transfer
        outgoingTransfers[transferId] = BridgeTransfer({
            tokenId: tokenId,
            sender: msg.sender,
            recipient: recipient,
            vaultId: info.vaultId,
            vaultNumber: info.vaultNumber,
            tokenURI: uri,
            rarityTier: info.rarityTier,
            isGenesis: info.isGenesis,
            destChainId: destChainId,
            initiatedAt: block.timestamp,
            completedAt: 0,
            burned: false,
            completed: false,
            cancelled: false
        });
        
        tokenToTransfer[tokenId] = transferId;
        
        emit BridgeInitiated(transferId, tokenId, msg.sender, destChainId, info.vaultId);
        
        return transferId;
    }
    
    /**
     * @notice Burn token after lock period (called by relayer)
     * @param transferId Transfer to complete
     */
    function burnForBridge(bytes32 transferId) external onlyRelayer nonReentrant {
        BridgeTransfer storage transfer = outgoingTransfers[transferId];
        
        require(transfer.tokenId != 0, "Transfer not found");
        require(!transfer.burned, "Already burned");
        require(!transfer.cancelled, "Transfer cancelled");
        require(block.timestamp >= transfer.initiatedAt + lockPeriod, "Lock period not passed");
        
        // Burn the token
        avatarNFT.burnForBridge(transfer.tokenId, transfer.destChainId);
        
        transfer.burned = true;
        
        emit BridgeBurned(transferId, transfer.tokenId, transfer.destChainId);
    }
    
    /**
     * @notice Cancel bridge transfer (before burn)
     * @param transferId Transfer to cancel
     */
    function cancelBridge(bytes32 transferId) external nonReentrant {
        BridgeTransfer storage transfer = outgoingTransfers[transferId];
        
        require(transfer.tokenId != 0, "Transfer not found");
        require(transfer.sender == msg.sender, "Not transfer initiator");
        require(!transfer.burned, "Already burned, cannot cancel");
        require(!transfer.cancelled, "Already cancelled");
        require(block.timestamp <= transfer.initiatedAt + cancelPeriod, "Cancel period expired");
        
        // Unlock the token
        avatarNFT.unlockFromBridge(transfer.tokenId);
        
        transfer.cancelled = true;
        delete tokenToTransfer[transfer.tokenId];
        
        emit BridgeCancelled(transferId, transfer.tokenId);
    }
    
    // =========================================================================
    // BRIDGE: INCOMING (Mint from other chain)
    // =========================================================================
    
    /**
     * @notice Complete bridge by minting on this chain
     * @param sourceTransferId Transfer ID from source chain
     * @param sourceChainId Source chain ID
     * @param recipient Recipient address
     * @param vaultId Vault ID
     * @param vaultNumber Vault number
     * @param tokenURI_ Token metadata URI
     * @param rarityTier Rarity tier
     * @param isGenesis Was genesis avatar
     */
    function completeBridge(
        bytes32 sourceTransferId,
        uint256 sourceChainId,
        address recipient,
        bytes32 vaultId,
        uint256 vaultNumber,
        string memory tokenURI_,
        string memory rarityTier,
        bool isGenesis
    ) external onlyRelayer nonReentrant whenNotPaused returns (uint256) {
        // Compute unique transfer ID for this chain
        bytes32 localTransferId = keccak256(abi.encodePacked(
            sourceTransferId,
            sourceChainId,
            block.chainid
        ));
        
        require(!processedTransfers[localTransferId], "Transfer already processed");
        
        // Mint the avatar
        uint256 newTokenId = avatarNFT.mintFromBridge(
            recipient,
            vaultId,
            vaultNumber,
            tokenURI_,
            rarityTier,
            isGenesis
        );
        
        processedTransfers[localTransferId] = true;
        
        emit BridgeCompleted(localTransferId, newTokenId, recipient, sourceChainId);
        
        return newTokenId;
    }
    
    // =========================================================================
    // VIEW FUNCTIONS
    // =========================================================================
    
    function getTransfer(bytes32 transferId) external view returns (BridgeTransfer memory) {
        return outgoingTransfers[transferId];
    }
    
    function getTokenTransfer(uint256 tokenId) external view returns (bytes32) {
        return tokenToTransfer[tokenId];
    }
    
    function isTransferProcessed(bytes32 transferId) external view returns (bool) {
        return processedTransfers[transferId];
    }
    
    function canCancel(bytes32 transferId) external view returns (bool) {
        BridgeTransfer memory transfer = outgoingTransfers[transferId];
        return !transfer.burned && 
               !transfer.cancelled && 
               block.timestamp <= transfer.initiatedAt + cancelPeriod;
    }
    
    function canBurn(bytes32 transferId) external view returns (bool) {
        BridgeTransfer memory transfer = outgoingTransfers[transferId];
        return !transfer.burned && 
               !transfer.cancelled && 
               block.timestamp >= transfer.initiatedAt + lockPeriod;
    }
    
    // =========================================================================
    // ADMIN
    // =========================================================================
    
    function setAvatarNFT(address avatarNFT_) external onlyOwner {
        avatarNFT = IEidolonAvatarNFT(avatarNFT_);
    }
    
    function setRelayer(address relayer, bool status) external onlyOwner {
        relayers[relayer] = status;
        emit RelayerUpdated(relayer, status);
    }
    
    function setSupportedChain(uint256 chainId, bool supported, address bridge) external onlyOwner {
        supportedChains[chainId] = supported;
        destBridgeAddress[chainId] = bridge;
        emit ChainUpdated(chainId, supported, bridge);
    }
    
    function setBridgeFee(uint256 fee) external onlyOwner {
        bridgeFee = fee;
    }
    
    function setLockPeriod(uint256 period) external onlyOwner {
        require(period >= 1 minutes && period <= 1 hours, "Invalid lock period");
        lockPeriod = period;
    }
    
    function setCancelPeriod(uint256 period) external onlyOwner {
        require(period >= lockPeriod && period <= 24 hours, "Invalid cancel period");
        cancelPeriod = period;
    }
    
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    function withdrawFees(address payable to) external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No fees to withdraw");
        to.transfer(balance);
    }
    
    // =========================================================================
    // RECEIVE
    // =========================================================================
    
    receive() external payable {}
}
