// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title LucidAnchors
 * @dev On-System Data Chain contract for session anchoring and data storage
 * @notice This contract handles the anchoring of encrypted session manifests and chunks
 *         to the On-System Data Chain as specified in SPEC-1B-v2-DISTROLESS.md
 */
contract LucidAnchors {
    struct SessionManifest {
        bytes32 sessionId;
        bytes32 merkleRoot;
        uint256 chunkCount;
        uint256 timestamp;
        address recorder;
        bytes32[] chunkHashes;
    }
    
    struct ChunkAnchor {
        bytes32 sessionId;
        bytes32 chunkHash;
        uint256 chunkIndex;
        uint256 timestamp;
    }
    
    // Events
    event SessionAnchored(bytes32 indexed sessionId, bytes32 merkleRoot, uint256 chunkCount);
    event ChunkAnchored(bytes32 indexed sessionId, bytes32 indexed chunkHash, uint256 chunkIndex);
    
    // State variables
    mapping(bytes32 => SessionManifest) public sessions;
    mapping(bytes32 => mapping(uint256 => ChunkAnchor)) public chunkAnchors;
    mapping(bytes32 => bool) public anchoredSessions;
    
    address public admin;
    address public chainClient;
    
    modifier onlyAuthorized() {
        require(msg.sender == admin || msg.sender == chainClient, "Unauthorized");
        _;
    }
    
    constructor(address _chainClient) {
        admin = msg.sender;
        chainClient = _chainClient;
    }
    
    /**
     * @dev Anchor a session manifest to the chain
     * @param sessionId Unique session identifier
     * @param merkleRoot BLAKE3 merkle root of encrypted chunks
     * @param chunkCount Number of chunks in the session
     * @param chunkHashes Array of chunk hashes
     */
    function anchorSession(
        bytes32 sessionId,
        bytes32 merkleRoot,
        uint256 chunkCount,
        bytes32[] calldata chunkHashes
    ) external onlyAuthorized {
        require(!anchoredSessions[sessionId], "Session already anchored");
        
        sessions[sessionId] = SessionManifest({
            sessionId: sessionId,
            merkleRoot: merkleRoot,
            chunkCount: chunkCount,
            timestamp: block.timestamp,
            recorder: msg.sender,
            chunkHashes: chunkHashes
        });
        
        anchoredSessions[sessionId] = true;
        
        emit SessionAnchored(sessionId, merkleRoot, chunkCount);
    }
    
    /**
     * @dev Anchor individual chunk data
     * @param sessionId Session identifier
     * @param chunkHash Hash of the encrypted chunk
     * @param chunkIndex Index of the chunk in the session
     */
    function anchorChunk(
        bytes32 sessionId,
        bytes32 chunkHash,
        uint256 chunkIndex
    ) external onlyAuthorized {
        require(anchoredSessions[sessionId], "Session not anchored");
        
        chunkAnchors[sessionId][chunkIndex] = ChunkAnchor({
            sessionId: sessionId,
            chunkHash: chunkHash,
            chunkIndex: chunkIndex,
            timestamp: block.timestamp
        });
        
        emit ChunkAnchored(sessionId, chunkHash, chunkIndex);
    }
    
    /**
     * @dev Verify chunk integrity using merkle proof
     * @param sessionId Session identifier
     * @param chunkIndex Index of the chunk to verify
     * @param chunkHash Hash of the chunk to verify
     * @param merkleProof Merkle proof for the chunk
     * @return isValid True if chunk is valid
     */
    function verifyChunk(
        bytes32 sessionId,
        uint256 chunkIndex,
        bytes32 chunkHash,
        bytes32[] calldata merkleProof
    ) external view returns (bool isValid) {
        SessionManifest storage session = sessions[sessionId];
        require(anchoredSessions[sessionId], "Session not found");
        require(chunkIndex < session.chunkCount, "Invalid chunk index");
        
        // Verify merkle proof
        bytes32 currentHash = chunkHash;
        for (uint256 i = 0; i < merkleProof.length; i++) {
            if (chunkIndex % 2 == 0) {
                currentHash = keccak256(abi.encodePacked(currentHash, merkleProof[i]));
            } else {
                currentHash = keccak256(abi.encodePacked(merkleProof[i], currentHash));
            }
            chunkIndex /= 2;
        }
        
        return currentHash == session.merkleRoot;
    }
    
    /**
     * @dev Get session manifest
     * @param sessionId Session identifier
     * @return manifest Session manifest data
     */
    function getSessionManifest(bytes32 sessionId) external view returns (SessionManifest memory manifest) {
        require(anchoredSessions[sessionId], "Session not found");
        return sessions[sessionId];
    }
    
    /**
     * @dev Update chain client address
     * @param newChainClient New chain client address
     */
    function updateChainClient(address newChainClient) external {
        require(msg.sender == admin, "Only admin");
        chainClient = newChainClient;
    }
}
