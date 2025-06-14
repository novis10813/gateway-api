# Gateway Authentication Service

一個使用 FastAPI 和 uv 管理的現代化 API Key 與 JWT 驗證服務。

## 功能特色

- **🔑 智能 API Key 管理**: 每個服務獨立的 API Key，支援權限控制
- **📊 使用統計**: 追蹤 API Key 使用情況和頻率
- **🔄 動態管理**: 即時創建、停用 API Keys，無需重啟服務
- **🛡️ 權限系統**: 細粒度權限控制 (read, write, admin)
- **📈 向後兼容**: 平滑遷移舊的配置方式
- **🔐 JWT Token**: 可將 API key 轉換為 JWT token
- **🌐 CORS 支援**: 可配置允許的來源
- **⚡ uv 管理**: 使用 uv 進行快速依賴管理

## 環境變量配置

創建 `.env` 文件並設置以下變量：

```env
# JWT 配置
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Key 配置 (向後兼容)
API_KEYS=your-secret,another-key
USE_LEGACY_API_KEYS=true
API_KEY_DB_FILE=api_keys.json

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
**⚠️ 這些端點僅能從內部網路訪問 (localhost:8000)，對外網路會返回 403 錯誤**
- `GET /internal/status` - 內部服務狀態和統計信息
- `POST /internal/generate-api-key` - 創建新的 API Key
- `GET /internal/list-api-keys` - 列出所有 API Keys (遮掩版本)
- `POST /internal/deactivate-api-key` - 停用指定的 API Key
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

## 🔧 API Key 管理

### 方法 1: 命令行工具 (推薦)
```bash
# 列出所有 API Keys
docker compose exec app python api_key_cli.py list

# 列出特定服務的 Keys
docker compose exec app python api_key_cli.py list --service webdav

# 創建新的 API Key
docker compose exec app python api_key_cli.py add \
  --name "WebDAV Service" \
  --service "webdav" \
  --permissions read write

# 創建管理員權限的 Key
docker compose exec app python api_key_cli.py add \
  --name "Admin Key" \
  --service "admin" \
  --permissions admin

# 使用自定義 Key
docker compose exec app python api_key_cli.py add \
  --name "Custom Key" \
  --service "custom" \
  --custom-key "my-custom-key-123"

# 驗證 API Key
docker compose exec app python api_key_cli.py verify \
  --key "your-api-key-here"

# 驗證特定權限
docker compose exec app python api_key_cli.py verify \
  --key "your-api-key-here" \
  --permission "write"

# 停用 API Key
docker compose exec app python api_key_cli.py deactivate \
  --key "your-api-key-here"

# 查看統計信息
docker compose exec app python api_key_cli.py stats

# 顯示包括停用的 Keys
docker compose exec app python api_key_cli.py list --show-all
```

### 方法 2: HTTP API (內部訪問)
**⚠️ 僅能從 localhost:8000 訪問**

```bash
# 查看系統狀態
curl -s http://localhost:8000/internal/status

# 創建新的 API Key
curl -X POST http://localhost:8000/internal/generate-api-key \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Immich Photo Service",
    "service": "immich", 
    "permissions": ["read", "write", "admin"]
  }'

# 列出所有 API Keys
curl -s http://localhost:8000/internal/list-api-keys

# 停用 API Key
curl -X POST http://localhost:8000/internal/deactivate-api-key \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key-here"}'

# 查看配置
curl -s http://localhost:8000/internal/config
```

### 方法 3: 容器內直接操作
```bash
# 進入容器
docker compose exec app sh

# 使用 Python 直接操作
python -c "
from api_key_manager import api_key_db
result = api_key_db.add_api_key('Test Service', 'test', ['read'])
print(f'Created: {result[\"api_key\"]}')
"
```

## 📊 權限系統

### 可用權限
- `read` - 讀取權限
- `write` - 寫入權限  
- `admin` - 管理員權限 (包含所有權限)

### 權限檢查
```bash
# 驗證是否有特定權限
curl -H "X-API-Key: your-key" \
  "https://novis.tplinkdns.com/auth/verify?required_permission=write"
```

## 🔍 使用統計

每次使用 API Key 時，系統會自動記錄：
- 最後使用時間
- 使用次數
- 使用的服務

查看統計：
```bash
# 查看詳細統計
docker compose exec app python api_key_cli.py stats

# 查看特定服務的使用情況
docker compose exec app python api_key_cli.py list --service immich
```

## 🔄 遷移指南

### 從舊系統遷移
1. 舊的 API Keys 會自動遷移到新系統
2. 舊 Keys 標記為 "legacy" 服務，擁有 admin 權限
3. 建議為每個服務創建專用的 API Key
4. 逐步替換舊的通用 Keys

### 建議的服務 Keys
```bash
# WebDAV 服務
docker compose exec app python api_key_cli.py add \
  --name "WebDAV File Access" --service "webdav" --permissions read write

# Immich 照片服務  
docker compose exec app python api_key_cli.py add \
  --name "Immich Photo Service" --service "immich" --permissions read write admin

# N8N 自動化
docker compose exec app python api_key_cli.py add \
  --name "N8N Automation" --service "n8n" --permissions read

# Portainer 管理
docker compose exec app python api_key_cli.py add \
  --name "Portainer Management" --service "portainer" --permissions admin
```

## 🚨 安全注意事項

1. **API Key 安全**：
   - 創建後立即保存，系統不會再次顯示完整 Key
   - 定期輪換 API Keys
   - 為不同服務使用不同的 Keys

2. **權限最小化**：
   - 只給予服務所需的最小權限
   - 避免過度使用 admin 權限

3. **監控使用**：
   - 定期檢查 API Key 使用統計
   - 停用不再使用的 Keys

## 🔧 故障排除

### 常見問題

**Q: API Key 驗證失敗**
```bash
# 檢查 Key 是否存在且活躍
docker compose exec app python api_key_cli.py verify --key "your-key"
```

**Q: 權限不足錯誤**
```bash
# 檢查 Key 的權限
docker compose exec app python api_key_cli.py list --service your-service
```

**Q: 內部端點無法訪問**
```bash
# 確認端口映射
docker compose ps
# 應該看到 127.0.0.1:8000->8000/tcp
```

### 日誌查看
```bash
# 查看服務日誌
docker compose logs app --tail=50

# 實時監控日誌
docker compose logs app -f
```
