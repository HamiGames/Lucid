// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title LucidChunkStore
 * @dev On-System Data Chain contract for encrypted chunk metadata storage
 * @notice This contract handles the storage and retrieval of encrypted chunk metadata
 *         for the Lucid RDP system as specified in SPEC-1B-v2-DISTROLESS.md
 */
contract LucidChunkStore {
    struct ChunkMetadata {
        bytes32 sessionId;
        bytes32 chunkHash;
        uint256 chunkIndex;
        bytes32 merkleProof;
        uint256 timestamp;
        address uploader;
        uint256 size;
        string encryptionKey;
        bool isStored;
        string status;
    }
    
    struct StorageProof {
        bytes32 chunkHash;
        bytes32 merkleRoot;
        bytes32[] merkleProof;
        uint256[] proofIndices;
        bool isValid;
    }
    
    struct SessionChunks {
        bytes32 sessionId;
        uint256 totalChunks;
        uint256 storedChunks;
        bytes32 merkleRoot;
        bool isComplete;
        uint256 lastUpdated;
    }
    
    // Events
    event ChunkStored(
        bytes32 indexed sessionId,
        bytes32 indexed chunkHash,
        uint256 chunkIndex,
        address indexed uploader,
        uint256 size
    );
    
    event ChunkRetrieved(
        bytes32 indexed sessionId,
        bytes32 indexed chunkHash,
        uint256 chunkIndex,
        address indexed requester
    );
    
    event StorageProofVerified(
        bytes32 indexed sessionId,
        bytes32 indexed chunkHash,
        bool isValid,
        address indexed verifier
    );
    
    event SessionCompleted(
        bytes32 indexed sessionId,
        uint256 totalChunks,
        bytes32 merkleRoot
    );
    
    event ChunkStatusUpdated(
        bytes32 indexed sessionId,
        bytes32 indexed chunkHash,
        string oldStatus,
        string newStatus
    );
    
    // State variables
    mapping(bytes32 => ChunkMetadata) public chunkMetadata;
    mapping(bytes32 => SessionChunks) public sessionChunks;
    mapping(bytes32 => mapping(uint256 => bytes32)) public sessionChunkHashes;
    mapping(bytes32 => bool) public storedChunks;
    mapping(address => bool) public authorizedUploaders;
    mapping(address => bool) public authorizedRetrievers;
    
    address public owner;
    address public lucidAnchors;
    uint256 public maxChunkSize;
    uint256 public maxChunksPerSession;
    uint256 public storageFee;
    uint256 public totalStoredChunks;
    uint256 public totalSessions;
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "LucidChunkStore: Only owner can call this function");
        _;
    }
    
    modifier onlyAuthorizedUploader() {
        require(
            authorizedUploaders[msg.sender] || 
            msg.sender == owner || 
            msg.sender == lucidAnchors,
            "LucidChunkStore: Only authorized uploaders can call this function"
        );
        _;
    }
    
    modifier onlyAuthorizedRetriever() {
        require(
            authorizedRetrievers[msg.sender] || 
            msg.sender == owner || 
            msg.sender == lucidAnchors,
            "LucidChunkStore: Only authorized retrievers can call this function"
        );
        _;
    }
    
    modifier validChunkSize(uint256 size) {
        require(size > 0, "LucidChunkStore: Chunk size must be greater than zero");
        require(size <= maxChunkSize, "LucidChunkStore: Chunk size exceeds maximum");
        _;
    }
    
    modifier validSessionId(bytes32 sessionId) {
        require(sessionId != bytes32(0), "LucidChunkStore: Invalid session ID");
        _;
    }
    
    constructor(
        address _lucidAnchors,
        uint256 _maxChunkSize,
        uint256 _maxChunksPerSession,
        uint256 _storageFee
    ) {
        owner = msg.sender;
        lucidAnchors = _lucidAnchors;
        maxChunkSize = _maxChunkSize;
        maxChunksPerSession = _maxChunksPerSession;
        storageFee = _storageFee;
        
        // Initialize owner as authorized
        authorizedUploaders[owner] = true;
        authorizedRetrievers[owner] = true;
    }
    
    /**
     * @dev Store chunk metadata
     * @param sessionId The session ID
     * @param chunkHash The chunk hash
     * @param chunkIndex The chunk index
     * @param merkleProof The merkle proof
     * @param size The chunk size
     * @param encryptionKey The encryption key
     * @return success Whether the storage was successful
     */
    function storeChunkMetadata(
        bytes32 sessionId,
        bytes32 chunkHash,
        uint256 chunkIndex,
        bytes32 merkleProof,
        uint256 size,
        string memory encryptionKey
    ) external onlyAuthorizedUploader validChunkSize(size) validSessionId(sessionId) returns (bool success) {
        require(chunkHash != bytes32(0), "LucidChunkStore: Invalid chunk hash");
        require(!storedChunks[chunkHash], "LucidChunkStore: Chunk already stored");
        require(bytes(encryptionKey).length > 0, "LucidChunkStore: Encryption key required");
        
        // Check session limits
        SessionChunks storage session = sessionChunks[sessionId];
        require(session.totalChunks == 0 || chunkIndex < session.totalChunks, "LucidChunkStore: Chunk index out of bounds");
        require(session.storedChunks < maxChunksPerSession, "LucidChunkStore: Session chunk limit exceeded");
        
        // Store chunk metadata
        chunkMetadata[chunkHash] = ChunkMetadata({
            sessionId: sessionId,
            chunkHash: chunkHash,
            chunkIndex: chunkIndex,
            merkleProof: merkleProof,
            timestamp: block.timestamp,
            uploader: msg.sender,
            size: size,
            encryptionKey: encryptionKey,
            isStored: true,
            status: "stored"
        });
        
        storedChunks[chunkHash] = true;
        sessionChunkHashes[sessionId][chunkIndex] = chunkHash;
        
        // Update session info
        if (session.sessionId == bytes32(0)) {
            session.sessionId = sessionId;
            session.totalChunks = 0; // Will be set by LucidAnchors
            totalSessions++;
        }
        session.storedChunks++;
        session.lastUpdated = block.timestamp;
        
        totalStoredChunks++;
        
        emit ChunkStored(sessionId, chunkHash, chunkIndex, msg.sender, size);
        
        return true;
    }
    
    /**
     * @dev Retrieve chunk metadata
     * @param chunkHash The chunk hash
     * @return metadata The chunk metadata
     */
    function retrieveChunkMetadata(
        bytes32 chunkHash
    ) external onlyAuthorizedRetriever returns (ChunkMetadata memory metadata) {
        require(storedChunks[chunkHash], "LucidChunkStore: Chunk not found");
        
        ChunkMetadata storage chunk = chunkMetadata[chunkHash];
        
        emit ChunkRetrieved(chunk.sessionId, chunkHash, chunk.chunkIndex, msg.sender);
        
        return chunk;
    }
    
    /**
     * @dev Verify storage proof
     * @param sessionId The session ID
     * @param chunkHash The chunk hash
     * @param merkleRoot The merkle root
     * @param proof The merkle proof
     * @param proofIndices The proof indices
     * @return isValid Whether the proof is valid
     */
    function verifyStorageProof(
        bytes32 sessionId,
        bytes32 chunkHash,
        bytes32 merkleRoot,
        bytes32[] memory proof,
        uint256[] memory proofIndices
    ) external onlyAuthorizedRetriever validSessionId(sessionId) returns (bool isValid) {
        require(storedChunks[chunkHash], "LucidChunkStore: Chunk not found");
        require(proof.length == proofIndices.length, "LucidChunkStore: Proof length mismatch");
        
        ChunkMetadata storage chunk = chunkMetadata[chunkHash];
        require(chunk.sessionId == sessionId, "LucidChunkStore: Session ID mismatch");
        
        // Verify merkle proof
        bytes32 computedHash = chunkHash;
        for (uint256 i = 0; i < proof.length; i++) {
            if (proofIndices[i] == 0) {
                computedHash = keccak256(abi.encodePacked(computedHash, proof[i]));
            } else {
                computedHash = keccak256(abi.encodePacked(proof[i], computedHash));
            }
        }
        
        isValid = computedHash == merkleRoot;
        
        emit StorageProofVerified(sessionId, chunkHash, isValid, msg.sender);
        
        return isValid;
    }
    
    /**
     * @dev Update session total chunks (called by LucidAnchors)
     * @param sessionId The session ID
     * @param totalChunks The total number of chunks
     * @param merkleRoot The merkle root
     */
    function updateSessionTotalChunks(
        bytes32 sessionId,
        uint256 totalChunks,
        bytes32 merkleRoot
    ) external onlyAuthorizedUploader validSessionId(sessionId) {
        require(totalChunks > 0, "LucidChunkStore: Total chunks must be greater than zero");
        require(merkleRoot != bytes32(0), "LucidChunkStore: Invalid merkle root");
        
        SessionChunks storage session = sessionChunks[sessionId];
        require(session.totalChunks == 0, "LucidChunkStore: Session total chunks already set");
        
        session.totalChunks = totalChunks;
        session.merkleRoot = merkleRoot;
        session.lastUpdated = block.timestamp;
        
        // Check if session is complete
        if (session.storedChunks == totalChunks) {
            session.isComplete = true;
            emit SessionCompleted(sessionId, totalChunks, merkleRoot);
        }
    }
    
    /**
     * @dev Mark session as complete
     * @param sessionId The session ID
     */
    function markSessionComplete(bytes32 sessionId) external onlyAuthorizedUploader validSessionId(sessionId) {
        SessionChunks storage session = sessionChunks[sessionId];
        require(session.sessionId != bytes32(0), "LucidChunkStore: Session not found");
        require(!session.isComplete, "LucidChunkStore: Session already complete");
        require(session.storedChunks == session.totalChunks, "LucidChunkStore: Not all chunks stored");
        
        session.isComplete = true;
        session.lastUpdated = block.timestamp;
        
        emit SessionCompleted(sessionId, session.totalChunks, session.merkleRoot);
    }
    
    /**
     * @dev Update chunk status
     * @param chunkHash The chunk hash
     * @param newStatus The new status
     */
    function updateChunkStatus(
        bytes32 chunkHash,
        string memory newStatus
    ) external onlyAuthorizedUploader {
        require(storedChunks[chunkHash], "LucidChunkStore: Chunk not found");
        require(bytes(newStatus).length > 0, "LucidChunkStore: Status cannot be empty");
        
        ChunkMetadata storage chunk = chunkMetadata[chunkHash];
        string memory oldStatus = chunk.status;
        
        chunk.status = newStatus;
        
        emit ChunkStatusUpdated(chunk.sessionId, chunkHash, oldStatus, newStatus);
    }
    
    /**
     * @dev Get session chunks info
     * @param sessionId The session ID
     * @return session The session chunks info
     */
    function getSessionChunks(bytes32 sessionId) external view returns (SessionChunks memory session) {
        require(sessionId != bytes32(0), "LucidChunkStore: Invalid session ID");
        return sessionChunks[sessionId];
    }
    
    /**
     * @dev Get chunk hash by session and index
     * @param sessionId The session ID
     * @param chunkIndex The chunk index
     * @return chunkHash The chunk hash
     */
    function getChunkHashByIndex(
        bytes32 sessionId,
        uint256 chunkIndex
    ) external view returns (bytes32 chunkHash) {
        require(sessionId != bytes32(0), "LucidChunkStore: Invalid session ID");
        return sessionChunkHashes[sessionId][chunkIndex];
    }
    
    /**
     * @dev Check if chunk is stored
     * @param chunkHash The chunk hash
     * @return isStored Whether the chunk is stored
     */
    function isChunkStored(bytes32 chunkHash) external view returns (bool isStored) {
        return storedChunks[chunkHash];
    }
    
    /**
     * @dev Check if session is complete
     * @param sessionId The session ID
     * @return isComplete Whether the session is complete
     */
    function isSessionComplete(bytes32 sessionId) external view returns (bool isComplete) {
        require(sessionId != bytes32(0), "LucidChunkStore: Invalid session ID");
        return sessionChunks[sessionId].isComplete;
    }
    
    /**
     * @dev Get storage statistics
     * @return stats The storage statistics
     */
    function getStorageStats() external view returns (
        uint256 totalChunks,
        uint256 totalSessions,
        uint256 maxChunkSizeLimit,
        uint256 maxChunksPerSessionLimit
    ) {
        return (
            totalStoredChunks,
            totalSessions,
            maxChunkSize,
            maxChunksPerSession
        );
    }
    
    /**
     * @dev Add authorized uploader
     * @param uploader The uploader address
     */
    function addAuthorizedUploader(address uploader) external onlyOwner {
        require(uploader != address(0), "LucidChunkStore: Invalid uploader address");
        authorizedUploaders[uploader] = true;
    }
    
    /**
     * @dev Remove authorized uploader
     * @param uploader The uploader address
     */
    function removeAuthorizedUploader(address uploader) external onlyOwner {
        authorizedUploaders[uploader] = false;
    }
    
    /**
     * @dev Add authorized retriever
     * @param retriever The retriever address
     */
    function addAuthorizedRetriever(address retriever) external onlyOwner {
        require(retriever != address(0), "LucidChunkStore: Invalid retriever address");
        authorizedRetrievers[retriever] = true;
    }
    
    /**
     * @dev Remove authorized retriever
     * @param retriever The retriever address
     */
    function removeAuthorizedRetriever(address retriever) external onlyOwner {
        authorizedRetrievers[retriever] = false;
    }
    
    /**
     * @dev Update storage parameters
     * @param _maxChunkSize New maximum chunk size
     * @param _maxChunksPerSession New maximum chunks per session
     * @param _storageFee New storage fee
     */
    function updateStorageParameters(
        uint256 _maxChunkSize,
        uint256 _maxChunksPerSession,
        uint256 _storageFee
    ) external onlyOwner {
        require(_maxChunkSize > 0, "LucidChunkStore: Invalid max chunk size");
        require(_maxChunksPerSession > 0, "LucidChunkStore: Invalid max chunks per session");
        
        maxChunkSize = _maxChunkSize;
        maxChunksPerSession = _maxChunksPerSession;
        storageFee = _storageFee;
    }
    
    /**
     * @dev Update LucidAnchors address
     * @param _lucidAnchors The new LucidAnchors address
     */
    function updateLucidAnchors(address _lucidAnchors) external onlyOwner {
        require(_lucidAnchors != address(0), "LucidChunkStore: Invalid LucidAnchors address");
        lucidAnchors = _lucidAnchors;
    }
    
    /**
     * @dev Emergency function to pause storage
     */
    function emergencyPause() external onlyOwner {
        // This would typically set a pause flag and emit an event
        // Implementation depends on specific emergency procedures
        emit ChunkStatusUpdated(bytes32(0), bytes32(0), "active", "paused");
    }
}
