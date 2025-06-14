"""
Unit tests for API key service.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from services.api_key_service import ApiKeyService
from models.api_key import ApiKeyRequest, ApiKeyResponse, ApiKeyListResponse


class TestApiKeyService:
    """Test cases for ApiKeyService"""
    
    def test_init_api_key_service(self):
        """Test ApiKeyService initialization"""
        service = ApiKeyService()
        assert service is not None
    
    @patch('services.api_key_service.api_key_db')
    def test_create_api_key_success(self, mock_db):
        """Test successful API key creation"""
        # Setup
        mock_db.add_api_key.return_value = {
            'api_key': 'test_abc123',
            'info': {
                'name': 'Test Service',
                'service': 'test',
                'permissions': ['read', 'write'],
                'created_at': '2024-01-01T00:00:00'
            }
        }
        
        service = ApiKeyService()
        request = ApiKeyRequest(
            name='Test Service',
            service='test',
            permissions=['read', 'write']
        )
        
        # Test
        result = service.create_api_key(request)
        
        # Assert
        assert isinstance(result, ApiKeyResponse)
        assert result.api_key == 'test_abc123'
        assert result.name == 'Test Service'
        assert result.service == 'test'
        mock_db.add_api_key.assert_called_once()
    
    @patch('services.api_key_service.api_key_db')
    def test_create_api_key_failure(self, mock_db):
        """Test API key creation failure"""
        # Setup
        mock_db.add_api_key.side_effect = ValueError("Key already exists")
        
        service = ApiKeyService()
        request = ApiKeyRequest(
            name='Test Service',
            service='test',
            permissions=['read']
        )
        
        # Test & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.create_api_key(request)
        
        assert exc_info.value.status_code == 400
        assert "Key already exists" in str(exc_info.value.detail)
    
    @patch('services.api_key_service.settings')
    @patch('services.api_key_service.api_key_db')
    def test_list_api_keys(self, mock_db, mock_settings):
        """Test listing API keys"""
        # Setup
        mock_db.list_api_keys.return_value = {
            'test_abc***': {
                'name': 'Test Key',
                'service': 'test',
                'permissions': ['read'],
                'created_at': '2024-01-01T00:00:00'
            }
        }
        mock_settings.api_keys_list = ['legacy-key']
        
        service = ApiKeyService()
        
        # Test
        result = service.list_api_keys()
        
        # Assert
        assert isinstance(result, ApiKeyListResponse)
        assert result.total_keys >= 1
        assert 'test_abc***' in result.database_keys
        mock_db.list_api_keys.assert_called_once()
    
    @patch('services.api_key_service.api_key_db')
    def test_deactivate_api_key_success(self, mock_db):
        """Test successful API key deactivation"""
        # Setup
        mock_db.deactivate_api_key.return_value = True
        
        service = ApiKeyService()
        
        # Test
        result = service.deactivate_api_key('test-key')
        
        # Assert
        assert result['message'] == 'API Key deactivated successfully'
        assert result['status'] == 'deactivated'
        mock_db.deactivate_api_key.assert_called_once_with('test-key')
    
    @patch('services.api_key_service.api_key_db')
    def test_deactivate_api_key_not_found(self, mock_db):
        """Test API key deactivation when key not found"""
        # Setup
        mock_db.deactivate_api_key.return_value = False
        
        service = ApiKeyService()
        
        # Test & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.deactivate_api_key('nonexistent-key')
        
        assert exc_info.value.status_code == 404
        assert "API Key not found" in str(exc_info.value.detail)
    
    @patch('services.api_key_service.settings')
    @patch('services.api_key_service.api_key_db')
    def test_get_system_status(self, mock_db, mock_settings):
        """Test getting system status"""
        # Setup
        mock_db.list_api_keys.return_value = {'key1': {}, 'key2': {}}
        mock_db.get_all_valid_keys.return_value = ['key1', 'key2', 'key3']
        mock_settings.api_keys_list = ['legacy1', 'legacy2']
        mock_settings.jwt_algorithm = 'HS256'
        mock_settings.api_key_db_file = 'test.json'
        
        service = ApiKeyService()
        
        # Test
        result = service.get_system_status()
        
        # Assert
        assert result['service'] == 'Gateway Authentication Service - Internal'
        assert result['status'] == 'running'
        assert result['legacy_keys_count'] == 2
        assert result['database_keys_count'] == 2
        assert result['total_active_keys'] == 3
        assert result['jwt_algorithm'] == 'HS256'
    
    @patch('services.api_key_service.settings')
    @patch('services.api_key_service.api_key_db')
    def test_get_system_config(self, mock_db, mock_settings):
        """Test getting system configuration"""
        # Setup
        mock_db.list_api_keys.return_value = {'key1': {}}
        mock_settings.jwt_algorithm = 'HS256'
        mock_settings.jwt_access_token_expire_minutes = 30
        mock_settings.api_keys_list = ['legacy1']
        mock_settings.use_legacy_api_keys = True
        mock_settings.api_key_db_file = 'test.json'
        mock_settings.allowed_origins_list = ['http://localhost']
        mock_settings.debug = False
        
        service = ApiKeyService()
        
        # Test
        result = service.get_system_config()
        
        # Assert
        assert result['jwt_algorithm'] == 'HS256'
        assert result['jwt_expire_minutes'] == 30
        assert result['legacy_keys_count'] == 1
        assert result['use_legacy_keys'] is True
        assert result['debug_mode'] is False
    
    @patch('services.api_key_service.settings')
    @patch('services.api_key_service.api_key_db')
    def test_list_api_keys_with_service_filter(self, mock_db, mock_settings):
        """Test listing API keys with service filter"""
        # Setup
        mock_db.list_api_keys.return_value = {
            'webdav_abc***': {
                'name': 'WebDAV Key',
                'service': 'webdav',
                'permissions': ['read', 'write']
            }
        }
        mock_settings.api_keys_list = []
        
        service = ApiKeyService()
        
        # Test
        result = service.list_api_keys(service='webdav')
        
        # Assert
        mock_db.list_api_keys.assert_called_once_with(service='webdav', active_only=True)
        assert 'webdav_abc***' in result.database_keys
    
    @patch('services.api_key_service.settings')
    @patch('services.api_key_service.api_key_db')
    def test_list_api_keys_include_inactive(self, mock_db, mock_settings):
        """Test listing API keys including inactive ones"""
        # Setup
        mock_db.list_api_keys.return_value = {
            'active_key***': {'name': 'Active', 'is_active': True},
            'inactive_key***': {'name': 'Inactive', 'is_active': False}
        }
        mock_settings.api_keys_list = []
        
        service = ApiKeyService()
        
        # Test
        result = service.list_api_keys(active_only=False)
        
        # Assert
        mock_db.list_api_keys.assert_called_once_with(service=None, active_only=False)
        assert len(result.database_keys) == 2 