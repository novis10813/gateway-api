"""
Secure hashing utilities for API Key management.

Uses Argon2id for secure password hashing (OWASP recommended)
and SHA256 for creating fast lookup prefixes.
"""
import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Argon2id configuration (OWASP recommendations)
# https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
_ph = PasswordHasher(
    time_cost=2,        # Number of iterations
    memory_cost=19456,  # Memory usage in KiB (19 MiB)
    parallelism=1,      # Number of parallel threads
    hash_len=32,        # Length of the hash in bytes
    salt_len=16         # Length of the salt in bytes
)


def generate_api_key(service: str, length: int = 32) -> tuple[str, str, str]:
    """
    Generate a new API Key with secure random bytes.
    
    Args:
        service: Service name to use as prefix
        length: Length of the random part (default: 32)
    
    Returns:
        tuple: (raw_key, key_prefix, key_hash)
            - raw_key: The full API key to give to the user (only shown once)
            - key_prefix: SHA256 prefix for database indexing (16 chars)
            - key_hash: Argon2id hash for secure verification
    """
    # Generate cryptographically secure random bytes
    random_part = secrets.token_urlsafe(length)
    raw_key = f"{service}_{random_part}"
    
    # Create prefix for fast lookup (first 16 chars of SHA256)
    key_prefix = hashlib.sha256(raw_key.encode()).hexdigest()[:16]
    
    # Create Argon2id hash (includes auto-generated salt)
    key_hash = _ph.hash(raw_key)
    
    return raw_key, key_prefix, key_hash


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against the stored hash.
    
    Args:
        raw_key: The API key provided by the client
        stored_hash: The Argon2id hash stored in the database
    
    Returns:
        bool: True if the key is valid, False otherwise
    """
    try:
        _ph.verify(stored_hash, raw_key)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def get_key_prefix(raw_key: str) -> str:
    """
    Get the prefix of an API key for database lookup.
    
    Args:
        raw_key: The API key to get the prefix for
    
    Returns:
        str: The first 16 characters of the SHA256 hash
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()[:16]


def check_needs_rehash(stored_hash: str) -> bool:
    """
    Check if a stored hash needs to be rehashed with updated parameters.
    
    This is useful when upgrading hash parameters over time.
    
    Args:
        stored_hash: The Argon2id hash to check
    
    Returns:
        bool: True if the hash should be updated
    """
    return _ph.check_needs_rehash(stored_hash)
