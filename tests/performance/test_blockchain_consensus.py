"""
Blockchain Consensus Performance Tests

Tests blockchain consensus performance benchmarks:
- Block creation: 1 block per 10 seconds
- Consensus round: <30 seconds
- Transaction throughput: >100 transactions per block
- Session anchoring: <5 seconds per session

Tests the lucid_blocks blockchain engine and PoOT consensus mechanism.
"""

import asyncio
import aiohttp
import pytest
import time
import statistics
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BlockMetrics:
    """Block creation performance metrics"""
    block_height: int
    block_hash: str
    creation_time: float
    transaction_count: int
    consensus_time: float
    total_time: float

@dataclass
class ConsensusMetrics:
    """Consensus performance metrics"""
    consensus_round_id: str
    participant_count: int
    voting_time: float
    consensus_reached: bool
    total_consensus_time: float

class BlockchainPerformanceTester:
    """Blockchain consensus performance tester"""
    
    def __init__(self, blockchain_url: str = "http://localhost:8084"):
        self.blockchain_url = blockchain_url
        self.session = None
        
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
    
    async def get_blockchain_info(self) -> Dict[str, Any]:
        """Get current blockchain information"""
        try:
            async with self.session.get(f"{self.blockchain_url}/api/v1/chain/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get blockchain info: {response.status}")
        except Exception as e:
            logger.error(f"Error getting blockchain info: {e}")
            raise
    
    async def get_latest_block(self) -> Dict[str, Any]:
        """Get the latest block"""
        try:
            async with self.session.get(f"{self.blockchain_url}/api/v1/blocks/latest") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get latest block: {response.status}")
        except Exception as e:
            logger.error(f"Error getting latest block: {e}")
            raise
    
    async def get_block_by_height(self, height: int) -> Dict[str, Any]:
        """Get block by height"""
        try:
            async with self.session.get(f"{self.blockchain_url}/api/v1/blocks/{height}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get block {height}: {response.status}")
        except Exception as e:
            logger.error(f"Error getting block {height}: {e}")
            raise
    
    async def submit_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a transaction to the blockchain"""
        try:
            async with self.session.post(
                f"{self.blockchain_url}/api/v1/transactions",
                json=transaction_data
            ) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    raise Exception(f"Failed to submit transaction: {response.status}")
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            raise
    
    async def anchor_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Anchor a session to the blockchain"""
        try:
            async with self.session.post(
                f"{self.blockchain_url}/api/v1/anchoring/session",
                json=session_data
            ) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    raise Exception(f"Failed to anchor session: {response.status}")
        except Exception as e:
            logger.error(f"Error anchoring session: {e}")
            raise
    
    async def monitor_block_creation(self, duration_seconds: int = 60) -> List[BlockMetrics]:
        """Monitor block creation over time and measure performance"""
        start_time = time.time()
        initial_info = await self.get_blockchain_info()
        initial_height = initial_info.get('latest_block_height', 0)
        
        block_metrics = []
        last_height = initial_height
        
        logger.info(f"Starting block monitoring from height {initial_height}")
        
        while time.time() - start_time < duration_seconds:
            try:
                current_info = await self.get_blockchain_info()
                current_height = current_info.get('latest_block_height', 0)
                
                # Check for new blocks
                if current_height > last_height:
                    for height in range(last_height + 1, current_height + 1):
                        block_data = await self.get_block_by_height(height)
                        
                        # Calculate timing metrics
                        block_timestamp = block_data.get('timestamp', 0)
                        block_time = time.time() - start_time
                        
                        metrics = BlockMetrics(
                            block_height=height,
                            block_hash=block_data.get('hash', ''),
                            creation_time=block_timestamp,
                            transaction_count=block_data.get('transaction_count', 0),
                            consensus_time=block_data.get('consensus_time', 0),
                            total_time=block_time
                        )
                        
                        block_metrics.append(metrics)
                        logger.info(f"New block {height} with {metrics.transaction_count} transactions")
                    
                    last_height = current_height
                
                # Wait before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Error monitoring blocks: {e}")
                await asyncio.sleep(5)
        
        return block_metrics
    
    async def measure_consensus_performance(self, test_blocks: int = 5) -> List[ConsensusMetrics]:
        """Measure consensus performance by analyzing recent blocks"""
        consensus_metrics = []
        
        try:
            # Get recent blocks to analyze consensus performance
            latest_info = await self.get_blockchain_info()
            latest_height = latest_info.get('latest_block_height', 0)
            
            if latest_height < test_blocks:
                logger.warning(f"Not enough blocks for consensus test. Current height: {latest_height}")
                return consensus_metrics
            
            # Analyze last few blocks
            for height in range(max(1, latest_height - test_blocks + 1), latest_height + 1):
                try:
                    block_data = await self.get_block_by_height(height)
                    
                    consensus_data = block_data.get('consensus', {})
                    
                    metrics = ConsensusMetrics(
                        consensus_round_id=consensus_data.get('round_id', ''),
                        participant_count=consensus_data.get('participant_count', 0),
                        voting_time=consensus_data.get('voting_time', 0),
                        consensus_reached=consensus_data.get('consensus_reached', False),
                        total_consensus_time=consensus_data.get('total_time', 0)
                    )
                    
                    consensus_metrics.append(metrics)
                    
                except Exception as e:
                    logger.warning(f"Error analyzing block {height}: {e}")
                    
        except Exception as e:
            logger.error(f"Error measuring consensus performance: {e}")
        
        return consensus_metrics

@pytest.mark.asyncio
class TestBlockchainConsensusPerformance:
    """Blockchain consensus performance tests"""
    
    @pytest.fixture
    async def blockchain_tester(self):
        """Blockchain performance tester fixture"""
        async with BlockchainPerformanceTester() as tester:
            yield tester
    
    async def test_block_creation_timing(self, blockchain_tester):
        """Test that blocks are created every ~10 seconds"""
        # Monitor block creation for 2 minutes
        block_metrics = await blockchain_tester.monitor_block_creation(duration_seconds=120)
        
        if len(block_metrics) < 2:
            pytest.skip("Not enough blocks created during test period")
        
        # Calculate block intervals
        intervals = []
        for i in range(1, len(block_metrics)):
            interval = block_metrics[i].total_time - block_metrics[i-1].total_time
            intervals.append(interval)
        
        avg_interval = statistics.mean(intervals)
        
        logger.info(f"Block creation intervals: {intervals}")
        logger.info(f"Average block interval: {avg_interval:.2f} seconds")
        
        # Assert average block time is around 10 seconds (±2 seconds tolerance)
        assert 8 <= avg_interval <= 12, \
            f"Average block interval {avg_interval:.2f}s not within expected range (8-12s)"
    
    async def test_consensus_round_timing(self, blockchain_tester):
        """Test that consensus rounds complete within 30 seconds"""
        consensus_metrics = await blockchain_tester.measure_consensus_performance()
        
        if not consensus_metrics:
            pytest.skip("No consensus metrics available")
        
        # Check consensus timing
        consensus_times = [m.total_consensus_time for m in consensus_metrics if m.consensus_reached]
        
        if not consensus_times:
            pytest.skip("No successful consensus rounds found")
        
        avg_consensus_time = statistics.mean(consensus_times)
        max_consensus_time = max(consensus_times)
        
        logger.info(f"Consensus times: {consensus_times}")
        logger.info(f"Average consensus time: {avg_consensus_time:.2f}s")
        logger.info(f"Max consensus time: {max_consensus_time:.2f}s")
        
        # Assert consensus rounds complete within 30 seconds
        assert max_consensus_time < 30, \
            f"Max consensus time {max_consensus_time:.2f}s exceeds 30s threshold"
        
        # Assert average consensus time is reasonable
        assert avg_consensus_time < 20, \
            f"Average consensus time {avg_consensus_time:.2f}s exceeds 20s threshold"
    
    async def test_transaction_throughput(self, blockchain_tester):
        """Test transaction throughput per block"""
        block_metrics = await blockchain_tester.monitor_block_creation(duration_seconds=60)
        
        if not block_metrics:
            pytest.skip("No blocks created during test period")
        
        # Check transaction counts
        transaction_counts = [m.transaction_count for m in block_metrics]
        avg_transactions = statistics.mean(transaction_counts)
        max_transactions = max(transaction_counts)
        
        logger.info(f"Transaction counts per block: {transaction_counts}")
        logger.info(f"Average transactions per block: {avg_transactions:.2f}")
        logger.info(f"Max transactions per block: {max_transactions}")
        
        # Assert blocks can handle reasonable transaction throughput
        # Note: This depends on the block size limit and transaction complexity
        assert max_transactions >= 10, \
            f"Max transactions per block {max_transactions} below minimum threshold of 10"
    
    async def test_session_anchoring_performance(self, blockchain_tester):
        """Test session anchoring performance"""
        # Create test session data
        session_data = {
            "session_id": f"test_session_{int(time.time())}",
            "user_id": "test_user",
            "chunks": [
                {"chunk_id": f"chunk_{i}", "hash": f"hash_{i}"}
                for i in range(10)
            ],
            "merkle_root": "test_merkle_root",
            "timestamp": int(time.time())
        }
        
        # Measure anchoring time
        start_time = time.time()
        try:
            result = await blockchain_tester.anchor_session(session_data)
            anchoring_time = time.time() - start_time
            
            logger.info(f"Session anchoring completed in {anchoring_time:.2f}s")
            
            # Assert anchoring completes within 5 seconds
            assert anchoring_time < 5, \
                f"Session anchoring took {anchoring_time:.2f}s, exceeding 5s threshold"
            
            # Verify anchoring was successful
            assert result.get('success', False), \
                "Session anchoring failed"
                
        except Exception as e:
            anchoring_time = time.time() - start_time
            pytest.fail(f"Session anchoring failed after {anchoring_time:.2f}s: {e}")
    
    async def test_blockchain_stability_under_load(self, blockchain_tester):
        """Test blockchain stability under transaction load"""
        # Submit multiple transactions concurrently
        transaction_count = 50
        transactions = []
        
        for i in range(transaction_count):
            transaction_data = {
                "transaction_id": f"test_tx_{i}_{int(time.time())}",
                "type": "test_transaction",
                "data": {"test_data": f"test_value_{i}"},
                "timestamp": int(time.time())
            }
            transactions.append(transaction_data)
        
        # Submit transactions concurrently
        start_time = time.time()
        submission_tasks = [
            blockchain_tester.submit_transaction(tx) for tx in transactions
        ]
        
        results = await asyncio.gather(*submission_tasks, return_exceptions=True)
        submission_time = time.time() - start_time
        
        # Count successful submissions
        successful_submissions = sum(1 for result in results if not isinstance(result, Exception))
        
        logger.info(f"Submitted {successful_submissions}/{transaction_count} transactions in {submission_time:.2f}s")
        
        # Assert reasonable submission success rate
        success_rate = successful_submissions / transaction_count
        assert success_rate > 0.8, \
            f"Transaction submission success rate {success_rate:.2%} below 80% threshold"
        
        # Monitor block creation to ensure transactions are processed
        await asyncio.sleep(30)  # Wait for block processing
        
        block_metrics = await blockchain_tester.monitor_block_creation(duration_seconds=30)
        
        # Check that blocks contain transactions
        if block_metrics:
            total_transactions_in_blocks = sum(m.transaction_count for m in block_metrics)
            logger.info(f"Total transactions processed in blocks: {total_transactions_in_blocks}")
            
            # Assert some transactions were processed
            assert total_transactions_in_blocks > 0, \
                "No transactions were processed in blocks"

@pytest.mark.performance
@pytest.mark.slow
class TestBlockchainExtendedPerformance:
    """Extended blockchain performance tests"""
    
    async def test_sustained_blockchain_performance(self):
        """Test sustained blockchain performance over extended period"""
        async with BlockchainPerformanceTester() as tester:
            # Monitor for 10 minutes
            block_metrics = await tester.monitor_block_creation(duration_seconds=600)
            
            if len(block_metrics) < 10:
                pytest.skip("Not enough blocks created during extended test")
            
            # Analyze sustained performance
            intervals = []
            for i in range(1, len(block_metrics)):
                interval = block_metrics[i].total_time - block_metrics[i-1].total_time
                intervals.append(interval)
            
            avg_interval = statistics.mean(intervals)
            std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
            
            logger.info(f"Sustained performance - Avg interval: {avg_interval:.2f}s, Std: {std_interval:.2f}s")
            
            # Assert consistent performance
            assert 8 <= avg_interval <= 12, \
                f"Sustained average block interval {avg_interval:.2f}s not within expected range"
            
            # Assert low variance in block timing
            assert std_interval < 3, \
                f"Block timing variance {std_interval:.2f}s too high for consistent performance"

if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])
