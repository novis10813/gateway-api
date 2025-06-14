"""
Unit tests for auth service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from services.auth_service import AuthService
from models.auth import TokenData


class TestAuthService:
    """Test cases for AuthService"""
    
    def test_init_auth_service(self):
        """Test AuthService initialization"""
        auth_service = AuthService()
        assert auth_service is not None
    
    @patch('services.auth_service.api_key_db')
    def test_verify_api_key_valid_database_key(self, mock_db):
        """Test API key verification with valid database key"""
        # Setup
        mock_db.validate_api_key.return_value = {
            'valid': True,
            'service': 'test',
            'permissions': ['read'],
            'name': 'Test Key'
        }
        
        auth_service = AuthService()
        
        # Test
        result = auth_service.verify_api_key('test-key')
        
        # Assert
        assert result['valid'] is True
        assert result['service'] == 'test'
        mock_db.validate_api_key.assert_called_once_with('test-key', None)
    
    @patch('services.auth_service.settings')
    @patch('services.auth_service.api_key_db')
    def test_verify_api_key_valid_legacy_key(self, mock_db, mock_settings):
        """Test API key verification with valid legacy key"""
        # Setup
        mock_db.validate_api_key.return_value = {'valid': False}
        mock_settings.use_legacy_api_keys = True
        mock_settings.api_keys_list = ['legacy-key']
        
        auth_service = AuthService()
        
        # Test
        result = auth_service.verify_api_key('legacy-key')
        
        # Assert
        assert result['valid'] is True
        assert result['service'] == 'legacy'
        assert 'admin' in result['permissions']
    
    def test_verify_api_key_missing_key(self):
        """Test API key verification with missing key"""
        auth_service = AuthService()
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_api_key(None)
        
        assert exc_info.value.status_code == 401
        assert "Missing API Key" in str(exc_info.value.detail)
    
    @patch('services.auth_service.api_key_db')
    @patch('services.auth_service.settings')
    def test_verify_api_key_invalid_key(self, mock_settings, mock_db):
        """Test API key verification with invalid key"""
        # Setup
        mock_db.validate_api_key.return_value = {'valid': False}
        mock_settings.use_legacy_api_keys = False
        mock_settings.api_keys_list = []
        
        auth_service = AuthService()
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_api_key('invalid-key')
        
        assert exc_info.value.status_code == 401
        assert "Invalid API Key" in str(exc_info.value.detail)
    
    @patch('services.auth_service.settings')
    @patch('services.auth_service.jwt.encode')
    def test_create_access_token(self, mock_jwt_encode, mock_settings):
        """Test JWT token creation"""
        # Setup
        mock_settings.jwt_access_token_expire_minutes = 30
        mock_settings.jwt_secret_key = 'test-secret'
        mock_settings.jwt_algorithm = 'HS256'
        mock_jwt_encode.return_value = 'test-token'
        
        auth_service = AuthService()
        
        # Test
        token = auth_service.create_access_token({'sub': 'testuser'})
        
        # Assert
        assert token == 'test-token'
        mock_jwt_encode.assert_called_once()
    
    @patch('services.auth_service.settings')
    @patch('services.auth_service.jwt.decode')
    def test_verify_jwt_token_valid(self, mock_jwt_decode, mock_settings):
        """Test JWT token verification with valid token"""
        # Setup
        mock_settings.jwt_secret_key = 'test-secret'
        mock_settings.jwt_algorithm = 'HS256'
        mock_jwt_decode.return_value = {
            'sub': 'testuser',
            'scopes': ['read', 'write']
        }
        
        auth_service = AuthService()
        
        # Test
        result = auth_service.verify_jwt_token('valid-token')
        
        # Assert
        assert isinstance(result, TokenData)
        assert result.username == 'testuser'
        assert result.scopes == ['read', 'write']
    
    @patch('services.auth_service.settings')
    @patch('services.auth_service.jwt.decode')
    def test_verify_jwt_token_invalid(self, mock_jwt_decode, mock_settings):
        """Test JWT token verification with invalid token"""
        # Setup
        mock_settings.jwt_secret_key = 'test-secret'
        mock_settings.jwt_algorithm = 'HS256'
        from jose import JWTError
        mock_jwt_decode.side_effect = JWTError("Invalid token")
        
        auth_service = AuthService()
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_jwt_token('invalid-token')
        
        assert exc_info.value.status_code == 401
    
    @patch('services.auth_service.api_key_db')
    def test_authenticate_request_with_api_key(self, mock_db):
        """Test request authentication with API key"""
        # Setup
        mock_db.validate_api_key.return_value = {
            'valid': True,
            'service': 'test',
            'permissions': ['read'],
            'name': 'Test Key'
        }
        
        auth_service = AuthService()
        
        # Test
        result = auth_service.authenticate_request(api_key='test-key')
        
        # Assert
        assert result['auth_type'] == 'api_key'
        assert result['service'] == 'test'
    
    @patch('services.auth_service.settings')
    @patch('services.auth_service.jwt.decode')
    def test_authenticate_request_with_jwt(self, mock_jwt_decode, mock_settings):
        """Test request authentication with JWT token"""
        # Setup
        mock_settings.jwt_secret_key = 'test-secret'
        mock_settings.jwt_algorithm = 'HS256'
        mock_jwt_decode.return_value = {
            'sub': 'testuser',
            'scopes': ['read']
        }
        
        auth_service = AuthService()
        
        # Test
        result = auth_service.authenticate_request(jwt_token='valid-token')
        
        # Assert
        assert result['auth_type'] == 'jwt'
        assert result['user'] == 'testuser'
    
    def test_authenticate_request_no_credentials(self):
        """Test request authentication with no credentials"""
        auth_service = AuthService()
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.authenticate_request()
        
        assert exc_info.value.status_code == 401
        assert "Valid API Key or JWT token required" in str(exc_info.value.detail) 