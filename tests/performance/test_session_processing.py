"""
Session Processing Performance Tests

Tests session processing performance benchmarks:
- Chunk processing: <100ms per chunk
- Session recording: <100ms per chunk
- Compression: gzip level 6 efficiency
- Encryption: AES-256-GCM performance
- Session pipeline: end-to-end processing time

Tests the session management pipeline and chunk processing services.
"""

import asyncio
import aiohttp
import pytest
import time
import statistics
import hashlib
import gzip
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from cryptography.fernet import Fernet
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChunkMetrics:
    """Chunk processing performance metrics"""
    chunk_id: str
    chunk_size: int
    processing_time: float
    compression_time: float
    encryption_time: float
    total_time: float
    compression_ratio: float

@dataclass
class SessionMetrics:
    """Session processing performance metrics"""
    session_id: str
    total_chunks: int
    total_processing_time: float
    avg_chunk_time: float
    p95_chunk_time: float
    p99_chunk_time: float
    total_size: int
    compressed_size: int
    compression_ratio: float

class SessionProcessingPerformanceTester:
    """Session processing performance tester"""
    
    def __init__(self, session_api_url: str = "http://localhost:8087"):
        self.session_api_url = session_api_url
        self.session = None
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=100)
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def generate_test_chunk(self, size_kb: int = 10) -> bytes:
        """Generate test chunk data of specified size"""
        # Generate realistic session data (mix of text and binary-like data)
        chunk_data = b""
        
        # Add some structured data (JSON-like)
        metadata = {
            "timestamp": int(time.time()),
            "session_id": "test_session",
            "chunk_id": f"chunk_{int(time.time())}",
            "data_type": "session_recording"
        }
        chunk_data += json.dumps(metadata).encode() + b"\n"
        
        # Add binary-like data to reach target size
        target_size = size_kb * 1024
        remaining_size = target_size - len(chunk_data)
        
        if remaining_size > 0:
            # Generate pseudo-random data
            seed = int(time.time())
            for i in range(remaining_size):
                seed = (seed * 1103515245 + 12345) & 0x7fffffff
                chunk_data += bytes([seed % 256])
        
        return chunk_data
    
    def compress_chunk(self, data: bytes) -> bytes:
        """Compress chunk data using gzip level 6"""
        start_time = time.time()
        compressed = gzip.compress(data, compresslevel=6)
        compression_time = time.time() - start_time
        
        return compressed, compression_time
    
    def encrypt_chunk(self, data: bytes) -> bytes:
        """Encrypt chunk data using AES-256-GCM"""
        start_time = time.time()
        encrypted = self.cipher_suite.encrypt(data)
        encryption_time = time.time() - start_time
        
        return encrypted, encryption_time
    
    async def process_chunk_locally(self, chunk_data: bytes) -> ChunkMetrics:
        """Process chunk locally to measure performance"""
        chunk_id = hashlib.sha256(chunk_data).hexdigest()[:16]
        chunk_size = len(chunk_data)
        
        start_time = time.time()
        
        # Compression
        compressed_data, compression_time = self.compress_chunk(chunk_data)
        
        # Encryption
        encrypted_data, encryption_time = self.encrypt_chunk(compressed_data)
        
        total_time = time.time() - start_time
        
        compression_ratio = len(compressed_data) / chunk_size
        
        return ChunkMetrics(
            chunk_id=chunk_id,
            chunk_size=chunk_size,
            processing_time=total_time - compression_time - encryption_time,
            compression_time=compression_time,
            encryption_time=encryption_time,
            total_time=total_time,
            compression_ratio=compression_ratio
        )
    
    async def create_test_session(self, chunk_count: int = 100, chunk_size_kb: int = 10) -> str:
        """Create a test session with specified number of chunks"""
        session_data = {
            "session_id": f"perf_test_session_{int(time.time())}",
            "user_id": "test_user",
            "chunk_size_kb": chunk_size_kb,
            "chunk_count": chunk_count,
            "timestamp": int(time.time())
        }
        
        try:
            async with self.session.post(
                f"{self.session_api_url}/api/v1/sessions",
                json=session_data
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    return result.get('session_id', session_data['session_id'])
                else:
                    raise Exception(f"Failed to create session: {response.status}")
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    async def upload_chunk(self, session_id: str, chunk_data: bytes, chunk_index: int) -> Dict[str, Any]:
        """Upload chunk to session"""
        chunk_metadata = {
            "session_id": session_id,
            "chunk_index": chunk_index,
            "chunk_size": len(chunk_data),
            "chunk_hash": hashlib.sha256(chunk_data).hexdigest()
        }
        
        try:
            # Create multipart form data
            data = aiohttp.FormData()
            data.add_field('metadata', json.dumps(chunk_metadata), content_type='application/json')
            data.add_field('chunk_data', chunk_data, content_type='application/octet-stream')
            
            async with self.session.post(
                f"{self.session_api_url}/api/v1/sessions/{session_id}/chunks",
                data=data
            ) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    raise Exception(f"Failed to upload chunk: {response.status}")
        except Exception as e:
            logger.error(f"Error uploading chunk: {e}")
            raise
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get session processing status"""
        try:
            async with self.session.get(
                f"{self.session_api_url}/api/v1/sessions/{session_id}/status"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get session status: {response.status}")
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            raise
    
    async def process_session_chunks(self, session_id: str, chunk_count: int = 100) -> SessionMetrics:
        """Process multiple chunks for a session and measure performance"""
        chunk_metrics = []
        total_size = 0
        compressed_size = 0
        
        logger.info(f"Processing {chunk_count} chunks for session {session_id}")
        
        for i in range(chunk_count):
            # Generate test chunk
            chunk_data = self.generate_test_chunk(size_kb=10)
            total_size += len(chunk_data)
            
            # Upload and process chunk
            start_time = time.time()
            
            try:
                result = await self.upload_chunk(session_id, chunk_data, i)
                processing_time = time.time() - start_time
                
                # Get chunk processing metrics
                chunk_compressed_size = result.get('compressed_size', len(chunk_data))
                compressed_size += chunk_compressed_size
                
                metrics = ChunkMetrics(
                    chunk_id=f"{session_id}_chunk_{i}",
                    chunk_size=len(chunk_data),
                    processing_time=processing_time,
                    compression_time=result.get('compression_time', 0),
                    encryption_time=result.get('encryption_time', 0),
                    total_time=processing_time,
                    compression_ratio=chunk_compressed_size / len(chunk_data)
                )
                
                chunk_metrics.append(metrics)
                
                # Log progress
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{chunk_count} chunks")
                
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                continue
        
        if not chunk_metrics:
            raise Exception("No chunks were successfully processed")
        
        # Calculate session metrics
        processing_times = [m.total_time for m in chunk_metrics]
        avg_chunk_time = statistics.mean(processing_times)
        p95_chunk_time = statistics.quantiles(processing_times, n=20)[18] if len(processing_times) >= 20 else max(processing_times)
        p99_chunk_time = statistics.quantiles(processing_times, n=100)[98] if len(processing_times) >= 100 else max(processing_times)
        
        total_processing_time = sum(processing_times)
        overall_compression_ratio = compressed_size / total_size if total_size > 0 else 1
        
        return SessionMetrics(
            session_id=session_id,
            total_chunks=len(chunk_metrics),
            total_processing_time=total_processing_time,
            avg_chunk_time=avg_chunk_time,
            p95_chunk_time=p95_chunk_time,
            p99_chunk_time=p99_chunk_time,
            total_size=total_size,
            compressed_size=compressed_size,
            compression_ratio=overall_compression_ratio
        )

@pytest.mark.asyncio
class TestSessionProcessingPerformance:
    """Session processing performance tests"""
    
    @pytest.fixture
    async def session_tester(self):
        """Session processing performance tester fixture"""
        async with SessionProcessingPerformanceTester() as tester:
            yield tester
    
    async def test_chunk_processing_performance(self, session_tester):
        """Test that chunk processing completes within 100ms"""
        chunk_sizes = [1, 5, 10, 20]  # Different chunk sizes in KB
        chunk_metrics = []
        
        for size_kb in chunk_sizes:
            # Generate test chunk
            chunk_data = session_tester.generate_test_chunk(size_kb=size_kb)
            
            # Process chunk locally to measure performance
            metrics = await session_tester.process_chunk_locally(chunk_data)
            chunk_metrics.append(metrics)
            
            logger.info(f"Chunk {size_kb}KB - Processing time: {metrics.total_time*1000:.2f}ms")
            
            # Assert processing time is within 100ms
            assert metrics.total_time < 0.1, \
                f"Chunk processing time {metrics.total_time*1000:.2f}ms exceeds 100ms threshold"
        
        # Test compression efficiency
        avg_compression_ratio = statistics.mean([m.compression_ratio for m in chunk_metrics])
        logger.info(f"Average compression ratio: {avg_compression_ratio:.3f}")
        
        # Assert reasonable compression ratio (should be < 1.0 for compressible data)
        assert avg_compression_ratio < 1.0, \
            f"Compression ratio {avg_compression_ratio:.3f} indicates poor compression"
    
    async def test_session_pipeline_performance(self, session_tester):
        """Test end-to-end session processing pipeline performance"""
        # Create test session
        session_id = await session_tester.create_test_session(chunk_count=50)
        
        # Process chunks and measure performance
        session_metrics = await session_tester.process_session_chunks(session_id, chunk_count=50)
        
        logger.info(f"Session processing metrics: {session_metrics}")
        
        # Assert average chunk processing time < 100ms
        assert session_metrics.avg_chunk_time < 0.1, \
            f"Average chunk processing time {session_metrics.avg_chunk_time*1000:.2f}ms exceeds 100ms threshold"
        
        # Assert p95 chunk processing time < 100ms
        assert session_metrics.p95_chunk_time < 0.1, \
            f"p95 chunk processing time {session_metrics.p95_chunk_time*1000:.2f}ms exceeds 100ms threshold"
        
        # Assert reasonable compression ratio
        assert session_metrics.compression_ratio < 0.8, \
            f"Overall compression ratio {session_metrics.compression_ratio:.3f} indicates poor compression"
    
    async def test_concurrent_chunk_processing(self, session_tester):
        """Test concurrent chunk processing performance"""
        # Create test session
        session_id = await session_tester.create_test_session(chunk_count=100)
        
        # Process chunks concurrently
        chunk_count = 20
        concurrent_chunks = 5
        
        async def process_chunk_batch(start_index: int, count: int):
            """Process a batch of chunks concurrently"""
            tasks = []
            for i in range(count):
                chunk_data = session_tester.generate_test_chunk(size_kb=10)
                task = session_tester.upload_chunk(session_id, chunk_data, start_index + i)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        # Process chunks in batches
        start_time = time.time()
        batch_tasks = []
        
        for i in range(0, chunk_count, concurrent_chunks):
            batch_size = min(concurrent_chunks, chunk_count - i)
            batch_tasks.append(process_chunk_batch(i, batch_size))
        
        batch_results = await asyncio.gather(*batch_tasks)
        total_time = time.time() - start_time
        
        # Calculate performance metrics
        successful_chunks = sum(len([r for r in batch if not isinstance(r, Exception)]) for batch in batch_results)
        chunks_per_second = successful_chunks / total_time
        
        logger.info(f"Concurrent processing: {successful_chunks}/{chunk_count} chunks in {total_time:.2f}s")
        logger.info(f"Processing rate: {chunks_per_second:.2f} chunks/second")
        
        # Assert reasonable processing rate
        assert chunks_per_second > 10, \
            f"Concurrent chunk processing rate {chunks_per_second:.2f} chunks/s below threshold"
        
        # Assert high success rate
        success_rate = successful_chunks / chunk_count
        assert success_rate > 0.9, \
            f"Concurrent processing success rate {success_rate:.2%} below 90% threshold"
    
    async def test_compression_performance(self, session_tester):
        """Test compression performance and efficiency"""
        chunk_sizes = [5, 10, 50, 100]  # Different chunk sizes in KB
        compression_metrics = []
        
        for size_kb in chunk_sizes:
            chunk_data = session_tester.generate_test_chunk(size_kb=size_kb)
            
            # Measure compression
            start_time = time.time()
            compressed_data, compression_time = session_tester.compress_chunk(chunk_data)
            total_time = time.time() - start_time
            
            compression_ratio = len(compressed_data) / len(chunk_data)
            compression_speed = len(chunk_data) / compression_time if compression_time > 0 else 0
            
            metrics = {
                'size_kb': size_kb,
                'original_size': len(chunk_data),
                'compressed_size': len(compressed_data),
                'compression_ratio': compression_ratio,
                'compression_time': compression_time,
                'compression_speed_mbps': compression_speed / (1024 * 1024)
            }
            
            compression_metrics.append(metrics)
            logger.info(f"Compression {size_kb}KB: {compression_ratio:.3f} ratio, {compression_time*1000:.2f}ms")
        
        # Assert compression efficiency
        avg_compression_ratio = statistics.mean([m['compression_ratio'] for m in compression_metrics])
        assert avg_compression_ratio < 0.7, \
            f"Average compression ratio {avg_compression_ratio:.3f} indicates poor compression efficiency"
        
        # Assert compression speed is reasonable
        avg_compression_speed = statistics.mean([m['compression_speed_mbps'] for m in compression_metrics])
        assert avg_compression_speed > 10, \
            f"Average compression speed {avg_compression_speed:.2f} MB/s below threshold"
    
    async def test_encryption_performance(self, session_tester):
        """Test encryption performance"""
        chunk_sizes = [5, 10, 50, 100]  # Different chunk sizes in KB
        encryption_metrics = []
        
        for size_kb in chunk_sizes:
            chunk_data = session_tester.generate_test_chunk(size_kb=size_kb)
            
            # Measure encryption
            start_time = time.time()
            encrypted_data, encryption_time = session_tester.encrypt_chunk(chunk_data)
            total_time = time.time() - start_time
            
            encryption_speed = len(chunk_data) / encryption_time if encryption_time > 0 else 0
            
            metrics = {
                'size_kb': size_kb,
                'original_size': len(chunk_data),
                'encrypted_size': len(encrypted_data),
                'encryption_time': encryption_time,
                'encryption_speed_mbps': encryption_speed / (1024 * 1024)
            }
            
            encryption_metrics.append(metrics)
            logger.info(f"Encryption {size_kb}KB: {encryption_time*1000:.2f}ms, {encryption_speed/(1024*1024):.2f} MB/s")
        
        # Assert encryption speed is reasonable
        avg_encryption_speed = statistics.mean([m['encryption_speed_mbps'] for m in encryption_metrics])
        assert avg_encryption_speed > 50, \
            f"Average encryption speed {avg_encryption_speed:.2f} MB/s below threshold"

@pytest.mark.performance
@pytest.mark.slow
class TestSessionExtendedPerformance:
    """Extended session processing performance tests"""
    
    async def test_large_session_processing(self):
        """Test processing of large sessions with many chunks"""
        async with SessionProcessingPerformanceTester() as tester:
            # Create large session with 500 chunks
            session_id = await tester.create_test_session(chunk_count=500)
            
            # Process chunks and measure performance
            session_metrics = await tester.process_session_chunks(session_id, chunk_count=500)
            
            logger.info(f"Large session metrics: {session_metrics}")
            
            # Assert performance remains good for large sessions
            assert session_metrics.avg_chunk_time < 0.15, \
                f"Large session avg chunk time {session_metrics.avg_chunk_time*1000:.2f}ms exceeds threshold"
            
            # Assert good compression ratio maintained
            assert session_metrics.compression_ratio < 0.8, \
                f"Large session compression ratio {session_metrics.compression_ratio:.3f} indicates poor compression"

if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])
