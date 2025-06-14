"""
Integration tests for API endpoints.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app


class TestHealthEndpoints:
    """Test cases for health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root health check endpoint"""
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Gateway Authentication Service"
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"
    
    def test_dashboard_endpoint(self):
        """Test dashboard endpoint"""
        client = TestClient(app)
        response = client.get("/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "FastAPI Authentication Service is running" in data["message"]
    
    def test_api_v1_root_endpoint(self):
        """Test API v1 root endpoint"""
        client = TestClient(app)
        response = client.get("/api/v1/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Gateway Authentication Service"


class TestAuthEndpoints:
    """Test cases for authentication endpoints"""
    
    @patch('api.v1.endpoints.auth.settings')
    def test_login_with_valid_api_key(self, mock_settings):
        """Test login with valid API key"""
        mock_settings.api_keys_list = ['test-key']
        mock_settings.jwt_access_token_expire_minutes = 30
        
        client = TestClient(app)
        response = client.post("/auth/login", json={
            "api_key": "test-key",
            "username": "testuser"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @patch('api.v1.endpoints.auth.settings')
    def test_login_with_invalid_api_key(self, mock_settings):
        """Test login with invalid API key"""
        mock_settings.api_keys_list = ['valid-key']
        
        client = TestClient(app)
        response = client.post("/auth/login", json={
            "api_key": "invalid-key",
            "username": "testuser"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid API Key" in data["detail"]
    
    @patch('services.auth_service.api_key_db')
    def test_verify_with_valid_api_key(self, mock_db):
        """Test verification with valid API key"""
        mock_db.validate_api_key.return_value = {
            'valid': True,
            'service': 'test',
            'permissions': ['read'],
            'name': 'Test Key'
        }
        
        client = TestClient(app)
        response = client.get("/auth/verify", headers={
            "X-API-Key": "valid-key"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["auth_type"] == "api_key"
    
    def test_verify_without_credentials(self):
        """Test verification without any credentials"""
        client = TestClient(app)
        response = client.get("/auth/verify")
        
        assert response.status_code == 401
        data = response.json()
        assert "Valid API Key or JWT token required" in data["detail"]
    
    @patch('services.auth_service.api_key_db')
    def test_verify_api_key_only(self, mock_db):
        """Test API key only verification endpoint"""
        mock_db.validate_api_key.return_value = {
            'valid': True,
            'service': 'test',
            'permissions': ['read'],
            'name': 'Test Key'
        }
        
        client = TestClient(app)
        response = client.get("/auth/verify-api-key", headers={
            "X-API-Key": "valid-key"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["auth_type"] == "api_key"
    
    @patch('services.auth_service.jwt.decode')
    @patch('services.auth_service.settings')
    def test_verify_jwt_only(self, mock_settings, mock_jwt_decode):
        """Test JWT only verification endpoint"""
        mock_settings.jwt_secret_key = 'test-secret'
        mock_settings.jwt_algorithm = 'HS256'
        mock_jwt_decode.return_value = {
            'sub': 'testuser',
            'scopes': ['read']
        }
        
        client = TestClient(app)
        response = client.get("/auth/verify-jwt", headers={
            "Authorization": "Bearer valid-jwt-token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["auth_type"] == "jwt"
        assert data["user"] == "testuser"


class TestInternalEndpoints:
    """Test cases for internal management endpoints"""
    
    @patch('api.deps.is_internal_request')
    @patch('services.api_key_service.api_key_db')
    @patch('services.api_key_service.settings')
    def test_internal_status(self, mock_settings, mock_db, mock_internal):
        """Test internal status endpoint"""
        mock_internal.return_value = True
        mock_db.list_api_keys.return_value = {'key1': {}, 'key2': {}}
        mock_db.get_all_valid_keys.return_value = ['key1', 'key2']
        mock_settings.api_keys_list = ['legacy1']
        mock_settings.jwt_algorithm = 'HS256'
        mock_settings.api_key_db_file = 'test.json'
        
        client = TestClient(app)
        response = client.get("/internal/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Gateway Authentication Service - Internal"
        assert data["status"] == "running"
        assert "legacy_keys_count" in data
        assert "database_keys_count" in data
    
    @patch('api.deps.is_internal_request')
    def test_internal_status_external_access_denied(self, mock_internal):
        """Test internal status endpoint denies external access"""
        mock_internal.return_value = False
        
        client = TestClient(app)
        response = client.get("/internal/status")
        
        assert response.status_code == 403
        data = response.json()
        assert "Access denied" in data["detail"]
    
    @patch('api.deps.is_internal_request')
    @patch('services.api_key_service.api_key_db')
    def test_generate_api_key(self, mock_db, mock_internal):
        """Test API key generation endpoint"""
        mock_internal.return_value = True
        mock_db.add_api_key.return_value = {
            'api_key': 'test_abc123',
            'info': {
                'name': 'Test Service',
                'service': 'test',
                'permissions': ['read'],
                'created_at': '2024-01-01T00:00:00'
            }
        }
        
        client = TestClient(app)
        response = client.post("/internal/generate-api-key", json={
            "name": "Test Service",
            "service": "test",
            "permissions": ["read"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["api_key"] == "test_abc123"
        assert data["name"] == "Test Service"
        assert data["service"] == "test"
    
    @patch('api.deps.is_internal_request')
    @patch('services.api_key_service.api_key_db')
    @patch('services.api_key_service.settings')
    def test_list_api_keys(self, mock_settings, mock_db, mock_internal):
        """Test list API keys endpoint"""
        mock_internal.return_value = True
        mock_db.list_api_keys.return_value = {
            'test_abc***': {
                'name': 'Test Key',
                'service': 'test',
                'permissions': ['read']
            }
        }
        mock_settings.api_keys_list = ['legacy-key']
        
        client = TestClient(app)
        response = client.get("/internal/list-api-keys")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_keys" in data
        assert "keys" in data
        assert "database_keys" in data
        assert "legacy_keys" in data
    
    @patch('api.deps.is_internal_request')
    @patch('services.api_key_service.api_key_db')
    def test_deactivate_api_key(self, mock_db, mock_internal):
        """Test API key deactivation endpoint"""
        mock_internal.return_value = True
        mock_db.deactivate_api_key.return_value = True
        
        client = TestClient(app)
        response = client.post("/internal/deactivate-api-key", json={
            "api_key": "test-key-to-deactivate"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "API Key deactivated successfully"
        assert data["status"] == "deactivated"
    
    @patch('api.deps.is_internal_request')
    @patch('services.api_key_service.api_key_db')
    @patch('services.api_key_service.settings')
    def test_get_config(self, mock_settings, mock_db, mock_internal):
        """Test get configuration endpoint"""
        mock_internal.return_value = True
        mock_db.list_api_keys.return_value = {'key1': {}}
        mock_settings.jwt_algorithm = 'HS256'
        mock_settings.jwt_access_token_expire_minutes = 30
        mock_settings.api_keys_list = ['legacy1']
        mock_settings.use_legacy_api_keys = True
        mock_settings.api_key_db_file = 'test.json'
        mock_settings.allowed_origins_list = ['http://localhost']
        mock_settings.debug = False
        
        client = TestClient(app)
        response = client.get("/internal/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["jwt_algorithm"] == "HS256"
        assert data["jwt_expire_minutes"] == 30
        assert data["use_legacy_keys"] is True


class TestLegacyEndpoints:
    """Test cases for legacy/backward compatibility endpoints"""
    
    @patch('services.auth_service.api_key_db')
    def test_legacy_your_api_endpoint(self, mock_db):
        """Test legacy /your-api endpoint"""
        mock_db.validate_api_key.return_value = {
            'valid': True,
            'service': 'test',
            'permissions': ['read'],
            'name': 'Test Key'
        }
        
        client = TestClient(app)
        response = client.get("/your-api", headers={
            "X-API-Key": "valid-key"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "Welcome to your home API!" in data["message"] 