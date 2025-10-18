#!/usr/bin/env python3
"""
Test script for Payment Acceptor Module
Tests the basic functionality of payment acceptance, processing, and validation
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from payment_acceptor import (
    PaymentRequestModel, PaymentType, PaymentMethod, PaymentPriority,
    ProcessingJobModel, ProcessingType, SettlementType,
    ValidationRequestModel, ValidationType,
    create_payment_request, process_incoming_payment, get_payment_status,
    create_processing_job, get_job_status,
    validate_payment, get_validation_result
)

async def test_payment_acceptor():
    """Test payment acceptor functionality"""
    print("=== Testing Payment Acceptor ===")
    
    # Create a test payment request
    request = PaymentRequestModel(
        payment_type=PaymentType.SESSION_PAYMENT,
        payment_method=PaymentMethod.USDT_TRC20,
        amount=10.0,
        recipient_address="TTestRecipientAddress1234567890123456789012345",
        session_id="test_session_123",
        description="Test session payment"
    )
    
    print(f"Creating payment request: {request.amount} {request.token_type}")
    response = await create_payment_request(request)
    print(f"Payment created: {response.payment_id}")
    print(f"Status: {response.status}")
    print(f"Message: {response.message}")
    
    # Get payment status
    status = await get_payment_status(response.payment_id)
    if status:
        print(f"Payment status: {status['status']}")
        print(f"Amount: {status['amount']}")
        print(f"Created at: {status['created_at']}")
    
    return response.payment_id

async def test_payment_processor(payment_id: str):
    """Test payment processor functionality"""
    print("\n=== Testing Payment Processor ===")
    
    # Create a processing job
    job_request = ProcessingJobModel(
        payment_id=payment_id,
        processing_type=ProcessingType.IMMEDIATE,
        settlement_type=SettlementType.INTERNAL,
        amount=10.0,
        token_type="USDT",
        source_address="TTestSourceAddress1234567890123456789012345",
        destination_address="TTestDestAddress1234567890123456789012345"
    )
    
    print(f"Creating processing job for payment: {payment_id}")
    response = await create_processing_job(job_request)
    print(f"Job created: {response.job_id}")
    print(f"Status: {response.status}")
    print(f"Message: {response.message}")
    
    # Get job status
    status = await get_job_status(response.job_id)
    if status:
        print(f"Job status: {status['status']}")
        print(f"Processing type: {status['processing_type']}")
        print(f"Settlement type: {status['settlement_type']}")
    
    return response.job_id

async def test_payment_validator(payment_id: str):
    """Test payment validator functionality"""
    print("\n=== Testing Payment Validator ===")
    
    # Create a validation request
    validation_request = ValidationRequestModel(
        payment_id=payment_id,
        validation_type=ValidationType.COMPREHENSIVE,
        amount=10.0,
        token_type="USDT",
        sender_address="TTestSenderAddress1234567890123456789012345",
        recipient_address="TTestRecipientAddress1234567890123456789012345",
        payment_type="session_payment"
    )
    
    print(f"Validating payment: {payment_id}")
    result = await validate_payment(validation_request)
    print(f"Validation ID: {result.validation_id}")
    print(f"Status: {result.status}")
    print(f"Risk Level: {result.risk_level}")
    print(f"Compliance Status: {result.compliance_status}")
    print(f"Score: {result.score}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    print(f"Flags: {result.flags}")
    
    # Get validation details
    details = await get_validation_result(result.validation_id)
    if details:
        print(f"Validation details available: {len(details)} fields")
        if details.get('compliance_checks'):
            print(f"Compliance checks: {len(details['compliance_checks'])}")
        if details.get('risk_assessment'):
            print(f"Risk assessment: {details['risk_assessment']['risk_level']}")
    
    return result.validation_id

async def test_integration():
    """Test integration between components"""
    print("\n=== Testing Integration ===")
    
    # Test processing incoming payment
    print("Testing incoming payment processing...")
    payment_id = await process_incoming_payment(
        txid="test_transaction_hash_1234567890abcdef",
        amount=10.0,
        sender_address="TTestSenderAddress1234567890123456789012345",
        recipient_address="TTestRecipientAddress1234567890123456789012345",
        token_type="USDT"
    )
    
    if payment_id:
        print(f"Incoming payment processed: {payment_id}")
    else:
        print("No matching payment request found for incoming payment")

async def main():
    """Main test function"""
    print("Starting Payment Acceptor Module Tests")
    print("=" * 50)
    
    try:
        # Test payment acceptor
        payment_id = await test_payment_acceptor()
        
        # Test payment processor
        job_id = await test_payment_processor(payment_id)
        
        # Test payment validator
        validation_id = await test_payment_validator(payment_id)
        
        # Test integration
        await test_integration()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print(f"Payment ID: {payment_id}")
        print(f"Job ID: {job_id}")
        print(f"Validation ID: {validation_id}")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
