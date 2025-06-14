# Gateway Authentication Service

一個使用 FastAPI 和 uv 管理的 API Key 與 JWT 驗證服務。

## 功能特色

- **API Key 驗證**: 支援多個 API key 的驗證
- **JWT Token**: 可將 API key 轉換為 JWT token
- **雙重認證**: 支援 API Key 或 JWT 兩種認證方式
- **CORS 支援**: 可配置允許的來源
- **uv 管理**: 使用 uv 進行依賴管理

## 環境變量配置

創建 `.env` 文件並設置以下變量：

```env
# JWT 配置
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Key 配置  
API_KEYS=your-secret,another-secret-key

# 服務配置
DEBUG=false
HOST=0.0.0.0
PORT=8000

# 允許的來源 (CORS)
ALLOWED_ORIGINS=https://novis.tplinkdns.com
```

## API 端點

### 對外端點 (External Endpoints)
- `GET /` - 服務狀態檢查
- `GET /dashboard` - 儀表板 (向後兼容)
- `POST /auth/login` - 使用 API Key 取得 JWT token
- `GET /auth/verify` - 驗證 API Key 或 JWT token
- `GET /auth/verify-api-key` - 僅驗證 API Key
- `GET /auth/verify-jwt` - 僅驗證 JWT token
- `GET /your-api` - 舊版 API (向後兼容)

### 內部管理端點 (Internal Management Endpoints)
**⚠️ 這些端點僅能從內部網路訪問，對外網路會返回 403 錯誤**
- `GET /internal/status` - 內部服務狀態
- `POST /internal/generate-api-key` - 生成新的 API Key
- `GET /internal/list-api-keys` - 列出當前 API Keys (遮掩版本)
- `GET /internal/config` - 獲取內部配置資訊

## 使用方式

### 使用 API Key
```bash
curl -H "X-API-Key: your-secret" https://novis.tplinkdns.com/auth/verify
```

### 取得 JWT Token
```bash
curl -X POST https://novis.tplinkdns.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-secret", "username": "user1"}'
```

### 使用 JWT Token
```bash
curl -H "Authorization: Bearer <your-jwt-token>" https://novis.tplinkdns.com/auth/verify
```

## 內部管理

### 使用內部管理客戶端
```bash
# 查看服務狀態
uv run python internal_client.py status

# 生成新的 API Key
uv run python internal_client.py generate -n "production-key" -p "prod"

# 列出當前 API Keys
uv run python internal_client.py list

# 查看配置
uv run python internal_client.py config
```

### 使用舊版生成腳本
```bash
# 生成單個 API Key
uv run python generate_api_key.py

# 生成多個帶前綴的 Keys
uv run python generate_api_key.py -n 3 -p "internal"
```

### 直接使用內部 API
**僅能在內部網路中訪問**
```bash
# 生成 API Key (在容器內或內部網路中)
curl -X POST http://app:8000/internal/generate-api-key \
  -H "Content-Type: application/json" \
  -d '{"name": "test-key", "prefix": "test", "length": 32}'

# 查看內部狀態
curl http://app:8000/internal/status
```
