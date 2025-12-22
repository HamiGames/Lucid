"""
Validation Test for Chunk Processor
Tests chunk encryption and Merkle root calculation functionality.

This script validates that the chunk processor can:
1. Encrypt chunks using AES-256-GCM
2. Build Merkle trees from chunk hashes
3. Generate and verify Merkle proofs
4. Process chunks concurrently
"""

import asyncio
import hashlib
import logging
import time
from typing import List

from .encryption import EncryptionManager, ChunkEncryptor
from .merkle_builder import MerkleTreeBuilder, MerkleTreeManager
from .chunk_processor import ChunkProcessor
from .config import ChunkProcessorConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_encryption():
    """Test encryption functionality."""
    logger.info("Testing encryption functionality...")
    
    # Create encryption manager
    encryption_manager = EncryptionManager()
    
    # Test data
    test_data = b"This is test chunk data for encryption validation"
    session_id = "test_session_001"
    chunk_id = "chunk_001"
    
    try:
        # Encrypt chunk
        encrypted_data, metadata = await encryption_manager.encrypt_chunk(
            session_id, chunk_id, test_data
        )
        
        logger.info(f"Original size: {len(test_data)} bytes")
        logger.info(f"Encrypted size: {len(encrypted_data)} bytes")
        logger.info(f"Compression ratio: {metadata['compression_ratio']:.2f}")
        
        # Decrypt chunk
        decrypted_data, decrypt_metadata = await encryption_manager.decrypt_chunk(
            session_id, chunk_id, encrypted_data
        )
        
        # Verify data integrity
        if test_data == decrypted_data:
            logger.info("✅ Encryption test PASSED: Data integrity verified")
            return True
        else:
            logger.error("❌ Encryption test FAILED: Data integrity check failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Encryption test FAILED: {str(e)}")
        return False


async def test_merkle_tree():
    """Test Merkle tree functionality."""
    logger.info("Testing Merkle tree functionality...")
    
    try:
        # Create Merkle tree builder
        tree_builder = MerkleTreeBuilder()
        
        # Generate test chunk hashes
        test_chunks = [
            b"chunk_data_001",
            b"chunk_data_002", 
            b"chunk_data_003",
            b"chunk_data_004",
            b"chunk_data_005"
        ]
        
        chunk_hashes = [hashlib.sha256(chunk).hexdigest() for chunk in test_chunks]
        
        # Add leaves to tree
        for i, chunk_hash in enumerate(chunk_hashes):
            tree_builder.add_leaf(chunk_hash)
            logger.info(f"Added leaf {i}: {chunk_hash[:16]}...")
        
        # Build tree
        root_hash = await tree_builder.build_tree()
        logger.info(f"Merkle root: {root_hash}")
        
        # Generate proof for first chunk
        proof = tree_builder.generate_proof(0)
        if proof:
            logger.info(f"Generated proof for leaf 0: {len(proof.path)} path elements")
            
            # Verify proof
            if tree_builder.verify_proof(proof):
                logger.info("✅ Merkle tree test PASSED: Proof verification successful")
                return True
            else:
                logger.error("❌ Merkle tree test FAILED: Proof verification failed")
                return False
        else:
            logger.error("❌ Merkle tree test FAILED: Could not generate proof")
            return False
            
    except Exception as e:
        logger.error(f"❌ Merkle tree test FAILED: {str(e)}")
        return False


async def test_chunk_processing():
    """Test chunk processing functionality."""
    logger.info("Testing chunk processing functionality...")
    
    try:
        # Create configuration
        config = ChunkProcessorConfig(
            max_workers=5,  # Reduced for testing
            queue_size=100,
            max_chunk_size=1024 * 1024,  # 1MB
            encryption_key="test_encryption_key_for_validation_only"
        )
        
        # Create chunk processor
        processor = ChunkProcessor(config)
        
        # Start processor
        await processor.start()
        
        # Test data
        session_id = "test_session_002"
        test_chunks = [
            (f"chunk_{i:03d}", f"test_chunk_data_{i:03d}".encode())
            for i in range(10)
        ]
        
        # Process chunks
        start_time = time.time()
        results = await processor.process_chunks_batch(session_id, test_chunks)
        processing_time = time.time() - start_time
        
        # Check results
        successful_chunks = [r for r in results if r.success]
        failed_chunks = [r for r in results if not r.success]
        
        logger.info(f"Processed {len(test_chunks)} chunks in {processing_time:.2f} seconds")
        logger.info(f"Successful: {len(successful_chunks)}, Failed: {len(failed_chunks)}")
        
        # Get Merkle root
        merkle_root = await processor.get_session_merkle_root(session_id)
        if merkle_root:
            logger.info(f"Session Merkle root: {merkle_root}")
        
        # Finalize session
        final_merkle_root = await processor.finalize_session(session_id)
        if final_merkle_root:
            logger.info(f"Final Merkle root: {final_merkle_root}")
        
        # Stop processor
        await processor.stop()
        
        if len(successful_chunks) == len(test_chunks) and final_merkle_root:
            logger.info("✅ Chunk processing test PASSED: All chunks processed successfully")
            return True
        else:
            logger.error("❌ Chunk processing test FAILED: Some chunks failed or no Merkle root")
            return False
            
    except Exception as e:
        logger.error(f"❌ Chunk processing test FAILED: {str(e)}")
        return False


async def test_merkle_tree_manager():
    """Test Merkle tree manager functionality."""
    logger.info("Testing Merkle tree manager functionality...")
    
    try:
        # Create manager
        manager = MerkleTreeManager()
        
        # Test session
        session_id = "test_session_003"
        
        # Add chunk hashes
        test_hashes = [
            hashlib.sha256(f"chunk_{i}".encode()).hexdigest()
            for i in range(5)
        ]
        
        for i, chunk_hash in enumerate(test_hashes):
            index = await manager.add_chunk_hash(session_id, chunk_hash)
            logger.info(f"Added chunk hash {i} at index {index}")
        
        # Finalize session
        merkle_root = await manager.finalize_session_tree(session_id)
        if merkle_root:
            logger.info(f"Session Merkle root: {merkle_root}")
        
        # Generate proof
        proof = manager.generate_chunk_proof(session_id, 0)
        if proof:
            logger.info(f"Generated proof for chunk 0")
            
            # Verify proof
            if manager.verify_chunk_proof(session_id, proof):
                logger.info("✅ Merkle tree manager test PASSED: Proof verification successful")
                return True
            else:
                logger.error("❌ Merkle tree manager test FAILED: Proof verification failed")
                return False
        else:
            logger.error("❌ Merkle tree manager test FAILED: Could not generate proof")
            return False
            
    except Exception as e:
        logger.error(f"❌ Merkle tree manager test FAILED: {str(e)}")
        return False


async def run_all_tests():
    """Run all validation tests."""
    logger.info("Starting chunk processor validation tests...")
    
    tests = [
        ("Encryption", test_encryption),
        ("Merkle Tree", test_merkle_tree),
        ("Chunk Processing", test_chunk_processing),
        ("Merkle Tree Manager", test_merkle_tree_manager)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} Test")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests PASSED! Chunk processor is working correctly.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests FAILED. Please check the implementation.")
        return False


if __name__ == "__main__":
    # Run validation tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
