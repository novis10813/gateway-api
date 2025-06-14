# Gateway Authentication Service

一個使用 FastAPI 和 uv 管理的現代化 API Key 與 JWT 驗證服務。

## 📋 Refactor 計劃 - 新檔案結構設計

基於 FastAPI 最佳實踐，我們將重新組織專案結構，提升程式碼的可維護性和擴展性。

### 🎯 設計原則
- **關注點分離**: 將不同功能模組化
- **領域驅動**: 按功能領域組織檔案
- **可測試性**: 便於單元測試和整合測試
- **可擴展性**: 支援未來功能擴展

### 📁 新檔案結構
```
app/
├── main.py                    # FastAPI 應用程式入口點
├── core/                      # 核心配置和設定
│   ├── __init__.py
│   ├── config.py             # 全域配置 (現有 config.py)
│   ├── security.py           # 安全相關設定 (JWT, 加密等)
│   └── exceptions.py         # 全域例外處理
├── api/                       # API 路由層
│   ├── __init__.py
│   ├── deps.py               # API 依賴注入
│   └── v1/                   # API 版本控制
│       ├── __init__.py
│       ├── router.py         # 主路由聚合器
│       └── endpoints/        # 各功能端點
│           ├── __init__.py
│           ├── auth.py       # 認證相關端點
│           ├── internal.py   # 內部管理端點
│           └── health.py     # 健康檢查端點
├── services/                  # 業務邏輯層
│   ├── __init__.py
│   ├── auth_service.py       # 認證業務邏輯 (從 auth.py 提取)
│   └── api_key_service.py    # API Key 管理業務邏輯
├── models/                    # 資料模型
│   ├── __init__.py
│   ├── auth.py               # 認證相關 Pydantic 模型
│   ├── api_key.py            # API Key 相關模型
│   └── responses.py          # 通用回應模型
├── db/                        # 資料庫相關
│   ├── __init__.py
│   ├── manager.py            # 資料庫管理器 (現有 api_key_manager.py)
│   └── migrations/           # 資料庫遷移腳本
│       └── __init__.py
├── utils/                     # 工具函數
│   ├── __init__.py
│   ├── security.py           # 安全工具函數
│   ├── validators.py         # 驗證器
│   └── helpers.py            # 通用輔助函數
├── cli/                       # 命令列工具
│   ├── __init__.py
│   ├── api_key_cli.py        # API Key 管理 CLI (現有)
│   └── internal_client.py    # 內部客戶端 (現有)
└── tests/                     # 測試檔案
    ├── __init__.py
    ├── conftest.py           # pytest 配置
    ├── test_auth.py          # 認證測試
    ├── test_api_keys.py      # API Key 測試
    └── test_internal.py      # 內部端點測試
```

### 🔄 檔案遷移對應表

| 現有檔案 | 新位置 | 說明 |
|---------|--------|------|
| `config.py` | `core/config.py` | 全域配置 |
| `auth.py` | `services/auth_service.py` + `api/deps.py` | 拆分業務邏輯和依賴注入 |
| `main.py` | `main.py` + `api/v1/router.py` | 保留入口點，路由邏輯分離 |
| `api_key_manager.py` | `db/manager.py` | 資料庫管理器 |
| `api_key_cli.py` | `cli/api_key_cli.py` | CLI 工具 |
| `internal_client.py` | `cli/internal_client.py` | 內部客戶端工具 |
| `generate_api_key.py` | `utils/security.py` | 安全工具函數 |

### 🎯 重構後的優勢

1. **清晰的分層架構**
   - API 層：處理 HTTP 請求和回應
   - 服務層：業務邏輯處理
   - 資料層：資料存取和管理
   - 工具層：通用功能

2. **更好的可測試性**
   - 每個層級都可以獨立測試
   - 依賴注入便於 Mock 測試
   - 測試檔案組織清晰

3. **便於擴展**
   - 新功能可以輕鬆添加新的端點和服務
   - API 版本控制支援
   - 模組化設計便於團隊協作

4. **符合 FastAPI 最佳實踐**
   - 遵循官方推薦的專案結構
   - 支援依賴注入模式
   - 便於 OpenAPI 文檔生成

### 📝 實施步驟

1. **第一階段**: 建立新的目錄結構 ✅
   - 建立所有必要的目錄：`core/`, `api/v1/endpoints/`, `services/`, `models/`, `db/migrations/`, `utils/`, `cli/`, `tests/`
   - 創建所有 `__init__.py` 檔案，建立 Python 模組結構
   - 為每個模組添加適當的文檔字串說明

2. **第二階段**: 遷移核心配置和模型 ✅
   - 遷移 `config.py` → `core/config.py`
   - 遷移 `api_key_manager.py` → `db/manager.py`
   - 遷移 `api_key_cli.py` → `cli/api_key_cli.py` (更新 import 路徑)
   - 遷移 `internal_client.py` → `cli/internal_client.py`
   - 遷移 `generate_api_key.py` 功能 → `utils/security.py`
3. **第三階段**: 重構 API 路由和端點 ✅
   - 創建 Pydantic 模型：`models/auth.py`, `models/api_key.py`
   - 創建 API 依賴注入：`api/deps.py`
   - 分離端點到不同檔案：
     - `api/v1/endpoints/auth.py` - 認證相關端點
     - `api/v1/endpoints/internal.py` - 內部管理端點
     - `api/v1/endpoints/health.py` - 健康檢查和向後兼容端點
   - 創建路由聚合器：`api/v1/router.py`
   - 重構 `main.py` 為簡潔的應用程式入口點
   - 備份舊版本為 `main_old.py`
4. **第四階段**: 分離業務邏輯到服務層 ✅
   - 創建 `services/auth_service.py` - 認證相關業務邏輯
   - 創建 `services/api_key_service.py` - API Key 管理業務邏輯
   - 更新端點使用服務層而非直接調用數據庫
   - 更新依賴注入系統使用服務層
5. **第五階段**: 更新測試和文檔 ✅
   - 修復相對導入問題，改為絕對導入
   - 測試所有服務模組導入成功
   - 使用 Docker 重啟服務並驗證功能
   - 全面測試重構後的端點：
     * 基本健康檢查端點 (`/`, `/dashboard`)
     * 認證端點 (`/auth/verify`, `/auth/verify-api-key`)
     * 內部管理端點 (`/internal/status`, `/internal/generate-api-key`, `/internal/list-api-keys`)
     * API 版本化端點 (`/api/v1/*`)
     * 新舊 API Key 兼容性測試
   - 驗證服務層架構正常工作
   - 確認向後兼容性完整保持
6. **第六階段**: 清理舊檔案和更新部署配置 ✅
   - 創建備份目錄 `.backup_old_files/`
   - 移動舊檔案到備份目錄：
     * `auth.py` → 已遷移到 `services/auth_service.py`
     * `config.py` → 已遷移到 `core/config.py`
     * `api_key_manager.py` → 已遷移到 `db/manager.py`
     * `generate_api_key.py` → 已遷移到 `utils/security.py`
     * `main_old.py` → 舊版本備份
   - 清理 `__pycache__` 目錄
   - 更新 `.gitignore` 忽略備份目錄
   - 驗證清理後應用程式正常運行

### 🧪 測試結果總結

重構後的系統已通過全面測試，所有功能正常運行：

**✅ 系統狀態**
- Legacy Keys: 2 個（來自配置文件）
- Database Keys: 5 個（動態管理）
- Total Active Keys: 7 個
- 服務狀態: 正常運行

**✅ 端點測試通過**
- 健康檢查: `/`, `/dashboard` ✓
- 認證功能: API Key 和 JWT 驗證 ✓
- 內部管理: 創建、列出、停用 API Keys ✓
- API 版本化: `/api/v1/*` 路徑 ✓
- 向後兼容: 所有舊端點正常 ✓

**✅ 架構驗證**
- 服務層分離: 業務邏輯完全分離 ✓
- 依賴注入: FastAPI 依賴系統正常 ✓
- 模組導入: 所有新模組正確載入 ✓
- Docker 部署: 容器化運行穩定 ✓

---

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
docker compose exec gateway python -m app.cli.api_key_cli list

# 列出特定服務的 Keys
docker compose exec gateway python -m app.cli.api_key_cli list --service webdav

# 創建新的 API Key
docker compose exec gateway python -m app.cli.api_key_cli add \
  --name "WebDAV Service" \
  --service "webdav" \
  --permissions read write

# 創建管理員權限的 Key
docker compose exec gateway python -m app.cli.api_key_cli add \
  --name "Admin Key" \
  --service "admin" \
  --permissions admin

# 使用自定義 Key
docker compose exec gateway python -m app.cli.api_key_cli add \
  --name "Custom Key" \
  --service "custom" \
  --custom-key "my-custom-key-123"

# 驗證 API Key
docker compose exec gateway python -m app.cli.api_key_cli verify \
  --key "your-api-key-here"

# 驗證特定權限
docker compose exec gateway python -m app.cli.api_key_cli verify \
  --key "your-api-key-here" \
  --permission "write"

# 停用 API Key
docker compose exec gateway python -m app.cli.api_key_cli deactivate \
  --key "your-api-key-here"

# 查看統計信息
docker compose exec gateway python -m app.cli.api_key_cli stats

# 顯示包括停用的 Keys
docker compose exec gateway python -m app.cli.api_key_cli list --show-all
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
docker compose exec gateway sh

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
docker compose exec gateway python -m app.cli.api_key_cli stats

# 查看特定服務的使用情況
docker compose exec gateway python -m app.cli.api_key_cli list --service immich
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
docker compose exec gateway python -m app.cli.api_key_cli add \
  --name "WebDAV File Access" --service "webdav" --permissions read write

# Immich 照片服務  
docker compose exec gateway python -m app.cli.api_key_cli add \
  --name "Immich Photo Service" --service "immich" --permissions read write admin

# N8N 自動化
docker compose exec gateway python -m app.cli.api_key_cli add \
  --name "N8N Automation" --service "n8n" --permissions read

# Portainer 管理
docker compose exec gateway python -m app.cli.api_key_cli add \
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
docker compose exec gateway python -m app.cli.api_key_cli verify --key "your-key"
```

**Q: 權限不足錯誤**
```bash
# 檢查 Key 的權限
docker compose exec gateway python -m app.cli.api_key_cli list --service your-service
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
docker compose logs gateway --tail=50

# 實時監控日誌
docker compose logs gateway -f
```
