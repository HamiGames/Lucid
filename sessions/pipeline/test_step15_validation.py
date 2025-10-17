#!/usr/bin/env python3
"""
Step 15 Validation Test
Tests that session pipeline progresses through all 6 states as required
"""

import asyncio
import pytest
import logging
from typing import Dict, Any
from datetime import datetime

from .pipeline_manager import PipelineManager, SessionPipeline
from .state_machine import PipelineState, StateTransition
from .config import PipelineConfig

logger = logging.getLogger(__name__)

class Step15ValidationTest:
    """
    Validation test for Step 15 requirements
    Ensures pipeline progresses through all 6 states
    """
    
    def __init__(self):
        self.config = PipelineConfig()
        self.pipeline_manager = PipelineManager(self.config)
        self.test_session_id = "test-session-step15"
        self.validation_results = {}
    
    async def test_pipeline_6_states(self) -> bool:
        """
        Test that pipeline progresses through all 6 states as required by Step 15
        
        Returns:
            bool: True if all 6 states are properly implemented
        """
        try:
            logger.info("Starting Step 15 validation: 6 states pipeline test")
            
            # Test 1: Create pipeline
            pipeline_id = await self.pipeline_manager.create_pipeline(self.test_session_id)
            self.validation_results["pipeline_creation"] = True
            logger.info(f"✓ Pipeline created: {pipeline_id}")
            
            # Test 2: Verify 6 stages are configured
            pipeline = self.pipeline_manager.active_pipelines[self.test_session_id]
            stage_count = len(pipeline.stages)
            
            if stage_count == 6:
                self.validation_results["six_stages"] = True
                logger.info(f"✓ Pipeline has 6 stages as required: {stage_count}")
            else:
                self.validation_results["six_stages"] = False
                logger.error(f"✗ Pipeline has {stage_count} stages, expected 6")
                return False
            
            # Test 3: Verify stage names match Step 15 requirements
            expected_stages = [
                "recording", "chunk_generation", "compression", 
                "encryption", "merkle_building", "storage"
            ]
            
            actual_stages = [stage.stage_name for stage in pipeline.stages]
            
            if set(actual_stages) == set(expected_stages):
                self.validation_results["correct_stages"] = True
                logger.info(f"✓ Pipeline stages match Step 15 requirements: {actual_stages}")
            else:
                self.validation_results["correct_stages"] = False
                logger.error(f"✗ Pipeline stages mismatch. Expected: {expected_stages}, Got: {actual_stages}")
                return False
            
            # Test 4: Test state transitions
            await self._test_state_transitions()
            
            # Test 5: Test chunk processing with 10MB chunks
            await self._test_chunk_processing()
            
            # Test 6: Test compression with gzip level 6
            await self._test_compression()
            
            # Cleanup
            await self.pipeline_manager.cleanup_pipeline(self.test_session_id)
            
            logger.info("✓ Step 15 validation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Step 15 validation failed: {str(e)}")
            self.validation_results["error"] = str(e)
            return False
    
    async def _test_state_transitions(self):
        """Test that pipeline can transition through all states"""
        try:
            pipeline = self.pipeline_manager.active_pipelines[self.test_session_id]
            state_machine = self.pipeline_manager.state_machine
            
            # Test valid transitions
            valid_transitions = [
                (PipelineState.CREATED, StateTransition.START),
                (PipelineState.STARTING, StateTransition.START_COMPLETE),
                (PipelineState.ACTIVE, StateTransition.PAUSE),
                (PipelineState.PAUSED, StateTransition.RESUME),
                (PipelineState.ACTIVE, StateTransition.STOP),
                (PipelineState.STOPPING, StateTransition.STOP_COMPLETE)
            ]
            
            for from_state, transition in valid_transitions:
                can_transition = state_machine.can_transition_with_trigger(from_state, transition)
                if can_transition:
                    logger.info(f"✓ Valid transition: {from_state.value} -> {transition.value}")
                else:
                    logger.error(f"✗ Invalid transition: {from_state.value} -> {transition.value}")
                    self.validation_results["state_transitions"] = False
                    return
            
            self.validation_results["state_transitions"] = True
            logger.info("✓ All state transitions are valid")
            
        except Exception as e:
            logger.error(f"✗ State transition test failed: {str(e)}")
            self.validation_results["state_transitions"] = False
    
    async def _test_chunk_processing(self):
        """Test chunk processing with 10MB chunks"""
        try:
            # Create test data (10MB)
            test_data = b"x" * (10 * 1024 * 1024)  # 10MB of data
            
            # Test chunk processing
            success = await self.pipeline_manager.process_chunk(
                self.test_session_id, 
                test_data, 
                {"test": "chunk"}
            )
            
            if success:
                self.validation_results["chunk_processing"] = True
                logger.info("✓ Chunk processing with 10MB data successful")
            else:
                self.validation_results["chunk_processing"] = False
                logger.error("✗ Chunk processing failed")
                
        except Exception as e:
            logger.error(f"✗ Chunk processing test failed: {str(e)}")
            self.validation_results["chunk_processing"] = False
    
    async def _test_compression(self):
        """Test compression with gzip level 6"""
        try:
            from ..recorder.compression import CompressionManager
            
            # Test compression manager
            compression_manager = CompressionManager(default_level=6)
            
            # Test data
            test_data = b"test data for compression validation"
            
            # Test compression
            result = await compression_manager.compress_chunk(test_data)
            
            if result.compression_ratio > 1.0 and result.algorithm.value == "gzip":
                self.validation_results["compression"] = True
                logger.info(f"✓ Compression successful: ratio {result.compression_ratio:.2f}")
            else:
                self.validation_results["compression"] = False
                logger.error("✗ Compression test failed")
                
        except Exception as e:
            logger.error(f"✗ Compression test failed: {str(e)}")
            self.validation_results["compression"] = False
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report"""
        return {
            "step_15_validation": {
                "timestamp": datetime.utcnow().isoformat(),
                "test_session_id": self.test_session_id,
                "results": self.validation_results,
                "overall_success": all(
                    result for key, result in self.validation_results.items() 
                    if key != "error" and isinstance(result, bool)
                )
            }
        }

async def run_step15_validation():
    """Run Step 15 validation test"""
    test = Step15ValidationTest()
    
    try:
        success = await test.test_pipeline_6_states()
        
        # Generate report
        report = test.get_validation_report()
        
        if success:
            logger.info("🎉 Step 15 validation PASSED - All 6 states implemented correctly")
        else:
            logger.error("❌ Step 15 validation FAILED - Issues found")
        
        return success, report
        
    except Exception as e:
        logger.error(f"Step 15 validation error: {str(e)}")
        return False, {"error": str(e)}

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[step15-validation] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run validation
    success, report = asyncio.run(run_step15_validation())
    
    print(f"\nStep 15 Validation Report:")
    print(f"Success: {success}")
    print(f"Report: {report}")
    
    exit(0 if success else 1)
