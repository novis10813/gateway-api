"""
Pytest configuration and fixtures for gateway authentication service tests.
"""
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from core.config import settings
from db.manager import ApiKeyDB


@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)


@pytest.fixture
def temp_db():
    """Temporary database fixture for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_db_path = f.name
        f.write('{}')  # Empty JSON
    
    # Create a temporary ApiKeyDB instance
    temp_api_key_db = ApiKeyDB(temp_db_path)
    
    yield temp_api_key_db
    
    # Cleanup
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    test_settings = {
        'api_keys_list': ['test-key-1', 'test-key-2'],
        'use_legacy_api_keys': True,
        'jwt_secret_key': 'test-secret-key',
        'jwt_algorithm': 'HS256',
        'jwt_access_token_expire_minutes': 30,
        'api_key_db_file': 'test_api_keys.json'
    }
    return test_settings


@pytest.fixture
def sample_api_key_data():
    """Sample API key data for testing"""
    return {
        'name': 'Test Service',
        'service': 'test',
        'permissions': ['read', 'write']
    }


@pytest.fixture
def sample_jwt_payload():
    """Sample JWT payload for testing"""
    return {
        'sub': 'testuser',
        'scopes': ['read', 'write']
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test"""
    # Ensure we're using test configuration
    with patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'test-secret-key-for-testing',
        'API_KEYS': 'test-key-1,test-key-2',
        'USE_LEGACY_API_KEYS': 'true',
        'API_KEY_DB_FILE': 'test_api_keys.json'
    }):
        yield 