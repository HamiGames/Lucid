"""
Custom error classes for GUI Hardware Manager
"""


class HardwareError(Exception):
    """Base exception for hardware-related errors"""
    pass


class DeviceNotFoundError(HardwareError):
    """Device not found"""
    pass


class DeviceNotConnectedError(HardwareError):
    """Device not connected"""
    pass


class WalletNotFoundError(HardwareError):
    """Wallet not found"""
    pass


class SigningError(HardwareError):
    """Transaction signing error"""
    pass


class InvalidTransactionError(HardwareError):
    """Invalid transaction"""
    pass


class DeviceTimeoutError(HardwareError):
    """Device operation timeout"""
    pass


class USBError(HardwareError):
    """USB communication error"""
    pass
