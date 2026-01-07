// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title EidolonAvatarNFT
 * @notice ERC-721 NFT for Eidolon avatars
 * @dev Supports both Ethereum and BSC (BEP-721 compatible)
 * 
 * Features:
 * - Mint at vault creation (genesis avatar)
 * - Multiple avatars per vault (collection)
 * - Bridge-ready (can be locked/burned for cross-chain)
 * - Royalties support (EIP-2981)
 */
contract EidolonAvatarNFT is ERC721, ERC721URIStorage, ERC721Enumerable, Ownable, ReentrancyGuard {
    using Counters for Counters.Counter;
    
    // =========================================================================
    // STATE
    // =========================================================================
    
    Counters.Counter private _tokenIdCounter;
    
    // Bridge contract address (can lock/burn tokens)
    address public bridgeContract;
    
    // Minter addresses (can mint new avatars)
    mapping(address => bool) public minters;
    
    // Genesis avatars (one per vault)
    mapping(bytes32 => uint256) public vaultGenesisAvatar; // vaultId => tokenId
    mapping(uint256 => bytes32) public tokenVaultId;       // tokenId => vaultId
    
    // Avatar metadata
    struct AvatarInfo {
        bytes32 vaultId;
        uint256 vaultNumber;
        bool isGenesis;
        uint256 mintedAt;
        string rarityTier;
    }
    mapping(uint256 => AvatarInfo) public avatarInfo;
    
    // Bridge lock
    mapping(uint256 => bool) public isLocked;
    mapping(uint256 => uint256) public lockTimestamp;
    
    // Royalties (EIP-2981)
    address public royaltyReceiver;
    uint96 public royaltyBps = 500; // 5%
    
    // Base URI
    string private _baseTokenURI;
    
    // =========================================================================
    // EVENTS
    // =========================================================================
    
    event AvatarMinted(
        uint256 indexed tokenId,
        address indexed owner,
        bytes32 indexed vaultId,
        bool isGenesis
    );
    
    event AvatarLocked(uint256 indexed tokenId, uint256 destChainId);
    event AvatarUnlocked(uint256 indexed tokenId);
    event AvatarBurned(uint256 indexed tokenId, uint256 destChainId);
    event BridgeContractUpdated(address indexed newBridge);
    event MinterUpdated(address indexed minter, bool status);
    
    // =========================================================================
    // MODIFIERS
    // =========================================================================
    
    modifier onlyMinter() {
        require(minters[msg.sender] || msg.sender == owner(), "Not a minter");
        _;
    }
    
    modifier onlyBridge() {
        require(msg.sender == bridgeContract, "Only bridge");
        _;
    }
    
    modifier notLocked(uint256 tokenId) {
        require(!isLocked[tokenId], "Token is locked for bridge");
        _;
    }
    
    // =========================================================================
    // CONSTRUCTOR
    // =========================================================================
    
    constructor(
        string memory name_,
        string memory symbol_,
        string memory baseURI_
    ) ERC721(name_, symbol_) {
        _baseTokenURI = baseURI_;
        royaltyReceiver = msg.sender;
        minters[msg.sender] = true;
    }
    
    // =========================================================================
    // MINTING
    // =========================================================================
    
    /**
     * @notice Mint genesis avatar for a vault
     * @param to Owner address
     * @param vaultId Unique vault identifier
     * @param vaultNumber Vault registration number
     * @param tokenURI_ Metadata URI
     * @param rarityTier Rarity tier string
     */
    function mintGenesis(
        address to,
        bytes32 vaultId,
        uint256 vaultNumber,
        string memory tokenURI_,
        string memory rarityTier
    ) external onlyMinter nonReentrant returns (uint256) {
        require(vaultGenesisAvatar[vaultId] == 0, "Vault already has genesis avatar");
        
        uint256 tokenId = _mintAvatar(to, vaultId, vaultNumber, tokenURI_, rarityTier, true);
        vaultGenesisAvatar[vaultId] = tokenId;
        
        return tokenId;
    }
    
    /**
     * @notice Mint additional avatar for a vault
     * @param to Owner address
     * @param vaultId Vault identifier
     * @param vaultNumber Vault number
     * @param tokenURI_ Metadata URI
     * @param rarityTier Rarity tier
     */
    function mint(
        address to,
        bytes32 vaultId,
        uint256 vaultNumber,
        string memory tokenURI_,
        string memory rarityTier
    ) external onlyMinter nonReentrant returns (uint256) {
        return _mintAvatar(to, vaultId, vaultNumber, tokenURI_, rarityTier, false);
    }
    
    /**
     * @notice Mint from bridge (cross-chain transfer)
     * @param to Recipient address
     * @param vaultId Original vault ID
     * @param vaultNumber Original vault number
     * @param tokenURI_ Metadata URI
     * @param rarityTier Rarity tier
     * @param wasGenesis Was genesis on source chain
     */
    function mintFromBridge(
        address to,
        bytes32 vaultId,
        uint256 vaultNumber,
        string memory tokenURI_,
        string memory rarityTier,
        bool wasGenesis
    ) external onlyBridge nonReentrant returns (uint256) {
        return _mintAvatar(to, vaultId, vaultNumber, tokenURI_, rarityTier, wasGenesis);
    }
    
    function _mintAvatar(
        address to,
        bytes32 vaultId,
        uint256 vaultNumber,
        string memory tokenURI_,
        string memory rarityTier,
        bool isGenesis
    ) internal returns (uint256) {
        _tokenIdCounter.increment();
        uint256 tokenId = _tokenIdCounter.current();
        
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, tokenURI_);
        
        tokenVaultId[tokenId] = vaultId;
        avatarInfo[tokenId] = AvatarInfo({
            vaultId: vaultId,
            vaultNumber: vaultNumber,
            isGenesis: isGenesis,
            mintedAt: block.timestamp,
            rarityTier: rarityTier
        });
        
        emit AvatarMinted(tokenId, to, vaultId, isGenesis);
        
        return tokenId;
    }
    
    // =========================================================================
    // BRIDGE FUNCTIONS
    // =========================================================================
    
    /**
     * @notice Lock token for bridge transfer
     * @param tokenId Token to lock
     * @param destChainId Destination chain ID
     */
    function lockForBridge(uint256 tokenId, uint256 destChainId) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(!isLocked[tokenId], "Already locked");
        
        isLocked[tokenId] = true;
        lockTimestamp[tokenId] = block.timestamp;
        
        emit AvatarLocked(tokenId, destChainId);
    }
    
    /**
     * @notice Unlock token (cancel bridge)
     * @param tokenId Token to unlock
     */
    function unlockFromBridge(uint256 tokenId) external {
        require(ownerOf(tokenId) == msg.sender || msg.sender == bridgeContract, "Not authorized");
        require(isLocked[tokenId], "Not locked");
        
        isLocked[tokenId] = false;
        lockTimestamp[tokenId] = 0;
        
        emit AvatarUnlocked(tokenId);
    }
    
    /**
     * @notice Burn token for bridge (called by bridge contract)
     * @param tokenId Token to burn
     * @param destChainId Destination chain ID
     */
    function burnForBridge(uint256 tokenId, uint256 destChainId) external onlyBridge {
        require(isLocked[tokenId], "Token must be locked first");
        
        // Clear mappings
        bytes32 vaultId = tokenVaultId[tokenId];
        if (avatarInfo[tokenId].isGenesis) {
            vaultGenesisAvatar[vaultId] = 0;
        }
        delete tokenVaultId[tokenId];
        delete avatarInfo[tokenId];
        delete isLocked[tokenId];
        delete lockTimestamp[tokenId];
        
        _burn(tokenId);
        
        emit AvatarBurned(tokenId, destChainId);
    }
    
    // =========================================================================
    // TRANSFER OVERRIDES
    // =========================================================================
    
    function transferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public override(ERC721, IERC721) notLocked(tokenId) {
        super.transferFrom(from, to, tokenId);
    }
    
    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId
    ) public override(ERC721, IERC721) notLocked(tokenId) {
        super.safeTransferFrom(from, to, tokenId);
    }
    
    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId,
        bytes memory data
    ) public override(ERC721, IERC721) notLocked(tokenId) {
        super.safeTransferFrom(from, to, tokenId, data);
    }
    
    // =========================================================================
    // VIEW FUNCTIONS
    // =========================================================================
    
    function getAvatarInfo(uint256 tokenId) external view returns (AvatarInfo memory) {
        require(_exists(tokenId), "Token does not exist");
        return avatarInfo[tokenId];
    }
    
    function getVaultGenesis(bytes32 vaultId) external view returns (uint256) {
        return vaultGenesisAvatar[vaultId];
    }
    
    function isGenesisAvatar(uint256 tokenId) external view returns (bool) {
        return avatarInfo[tokenId].isGenesis;
    }
    
    function totalMinted() external view returns (uint256) {
        return _tokenIdCounter.current();
    }
    
    // =========================================================================
    // ROYALTIES (EIP-2981)
    // =========================================================================
    
    function royaltyInfo(uint256, uint256 salePrice) external view returns (address, uint256) {
        uint256 royaltyAmount = (salePrice * royaltyBps) / 10000;
        return (royaltyReceiver, royaltyAmount);
    }
    
    function setRoyaltyInfo(address receiver, uint96 bps) external onlyOwner {
        require(bps <= 1000, "Max 10% royalty");
        royaltyReceiver = receiver;
        royaltyBps = bps;
    }
    
    // =========================================================================
    // ADMIN
    // =========================================================================
    
    function setBridgeContract(address bridge) external onlyOwner {
        bridgeContract = bridge;
        emit BridgeContractUpdated(bridge);
    }
    
    function setMinter(address minter, bool status) external onlyOwner {
        minters[minter] = status;
        emit MinterUpdated(minter, status);
    }
    
    function setBaseURI(string memory baseURI_) external onlyOwner {
        _baseTokenURI = baseURI_;
    }
    
    // =========================================================================
    // OVERRIDES
    // =========================================================================
    
    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }
    
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal override(ERC721, ERC721Enumerable) {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
    }
    
    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }
    
    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }
    
    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721Enumerable, ERC721URIStorage) returns (bool) {
        // EIP-2981 interface ID
        return interfaceId == 0x2a55205a || super.supportsInterface(interfaceId);
    }
}
