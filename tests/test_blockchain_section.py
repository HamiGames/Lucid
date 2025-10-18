# Test Script for Blockchain Section
# Validates session recording and blockchain anchoring functionality
# Based on LUCID-STRICT requirements

import asyncio
import os
import tempfile
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required modules can be imported"""
    try:
        # Test session recorder imports
        from src.session_recorder import (
            SessionRecorder, SessionManager, SessionEncryption,
            SessionChunk, SessionManifest
        )
        logger.info("✓ Session recorder modules imported successfully")
        
        # Test blockchain anchor imports  
        from src.blockchain_anchor import (
            BlockchainAnchor, AnchorService, AnchorResult,
            OnSystemChainClient, TronChainClient
        )
        logger.info("✓ Blockchain anchor modules imported successfully")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_session_encryption():
    """Test session encryption functionality"""
    try:
        from src.session_recorder import SessionEncryption
        
        # Test key derivation
        session_id = "test-session-123"
        master_key = os.urandom(32)
        
        session_key = SessionEncryption.derive_session_key(session_id, master_key)
        assert len(session_key) == 32, "Session key must be 32 bytes"
        
        # Test encryption/decryption
        encryptor = SessionEncryption(session_key)
        
        test_data = b"Hello, Lucid RDP session data!"
        nonce = os.urandom(12)
        
        encrypted = encryptor.encrypt_chunk(test_data, nonce)
        decrypted = encryptor.decrypt_chunk(encrypted, nonce)
        
        assert decrypted == test_data, "Encryption/decryption roundtrip failed"
        logger.info("✓ Session encryption working correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ Encryption test failed: {e}")
        return False

def test_session_chunk_creation():
    """Test session chunk data structure"""
    try:
        from src.session_recorder import SessionChunk
        from datetime import datetime, timezone
        
        chunk = SessionChunk(
            chunk_id="test-chunk-001",
            session_id="test-session-123",
            sequence_number=0,
            original_size=1000,
            compressed_size=800,
            encrypted_size=850,
            local_path=Path("/tmp/test-chunk.enc"),
            ciphertext_sha256="abcd1234",
            created_at=datetime.now(timezone.utc)
        )
        
        # Test MongoDB format conversion
        doc = chunk.to_dict()
        assert doc["_id"] == "test-chunk-001", "Chunk ID mapping failed"
        assert doc["idx"] == 0, "Sequence number mapping failed"
        
        logger.info("✓ Session chunk creation working correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ Chunk creation test failed: {e}")
        return False

async def test_session_recorder():
    """Test session recorder functionality"""
    try:
        from src.session_recorder import SessionRecorder
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set temporary session data directory
            os.environ["LUCID_SESSION_DATA_DIR"] = temp_dir
            
            session_id = "test-session-456"
            owner_address = "TTestOwnerAddress123456789"
            master_key = os.urandom(32)
            
            recorder = SessionRecorder(session_id, owner_address, master_key)
            
            # Test initialization
            assert recorder.session_id == session_id
            assert recorder.owner_address == owner_address
            assert not recorder.is_recording
            
            # Test session directory creation
            session_dir = Path(temp_dir) / session_id
            assert session_dir.exists(), "Session directory not created"
            
            logger.info("✓ Session recorder initialization working correctly")
            return True
            
    except Exception as e:
        logger.error(f"✗ Session recorder test failed: {e}")
        return False

def test_blockchain_anchor_structures():
    """Test blockchain anchor data structures"""
    try:
        from src.blockchain_anchor import AnchorResult, OnSystemChainClient
        from datetime import datetime, timezone
        
        # Test anchor result
        anchor_result = AnchorResult(
            session_id="test-session-789",
            anchor_txid="0xabcd1234",
            on_chain_txid="0xabcd1234",
            tron_txid=None,
            anchor_timestamp=datetime.now(timezone.utc),
            gas_used=21000,
            anchor_fee=0,
            status="pending"
        )
        
        assert anchor_result.session_id == "test-session-789"
        assert anchor_result.status == "pending"
        
        # Test on-system chain client initialization
        client = OnSystemChainClient("http://localhost:8545", "0x1234567890abcdef")
        assert client.rpc_url == "http://localhost:8545"
        assert client.contract_address == "0x1234567890abcdef"
        
        logger.info("✓ Blockchain anchor structures working correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ Anchor structures test failed: {e}")
        return False

def test_runtime_variables():
    """Test that runtime variables are properly set"""
    try:
        # Test session recorder variables
        from src.session_recorder import (
            CHUNK_MIN_SIZE, CHUNK_MAX_SIZE, COMPRESSION_LEVEL,
            SESSION_DATA_DIR, ONION_STATE_DIR
        )
        
        assert CHUNK_MIN_SIZE == 8388608, "Chunk min size incorrect"  # 8MB
        assert CHUNK_MAX_SIZE == 16777216, "Chunk max size incorrect"  # 16MB
        assert COMPRESSION_LEVEL == 3, "Compression level incorrect"
        
        # Test blockchain anchor variables  
        from src.blockchain_anchor import (
            TRON_NETWORK, ON_CHAIN_RPC_URL, MONGO_URL
        )
        
        assert TRON_NETWORK in ["mainnet", "shasta"], "TRON network invalid"
        assert ON_CHAIN_RPC_URL.startswith("http"), "RPC URL format invalid"
        
        logger.info("✓ Runtime variables configured correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ Runtime variables test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("===== Blockchain Section Testing =====")
    
    tests = [
        ("Import Tests", test_imports),
        ("Session Encryption", test_session_encryption), 
        ("Session Chunks", test_session_chunk_creation),
        ("Runtime Variables", test_runtime_variables),
        ("Anchor Structures", test_blockchain_anchor_structures),
    ]
    
    async_tests = [
        ("Session Recorder", test_session_recorder),
    ]
    
    results = []
    
    # Run synchronous tests
    for test_name, test_func in tests:
        logger.info(f"Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"{test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Run async tests
    for test_name, test_func in async_tests:
        logger.info(f"Running {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"{test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("===== Test Results Summary =====")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        color = "✓" if result else "✗"
        logger.info(f"{color} {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"===== {passed}/{total} tests passed =====")
    
    if passed == total:
        logger.info("🎉 All blockchain tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed")
        return False

if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    exit(0 if success else 1)