# Nginx 模組化配置架構

本目錄包含了模組化的 Nginx 配置，將原本的單一 `default.conf` 拆分成多個邏輯分組的配置文件，提高可維護性和可讀性。

## 目錄結構

```
nginx/
├── README.md                    # 本文檔
├── conf/                        # 配置文件目錄
│   ├── nginx.conf              # 主配置文件（新的入口點）
│   ├── default.conf            # 原始配置文件（備份用）
│   ├── global/                 # 全局配置
│   │   ├── resolver.conf       # DNS 解析器配置
│   │   ├── rate-limits.conf    # 速率限制配置
│   │   ├── ssl-params.conf     # SSL/TLS 安全參數
│   │   └── log-format.conf     # 日誌格式定義
│   ├── servers/                # 伺服器配置
│   │   ├── http-redirect.conf  # HTTP to HTTPS 重定向
│   │   └── https-main.conf     # 主 HTTPS 伺服器配置
│   ├── services/               # 各服務的 location 配置
│   │   ├── webdav.conf         # WebDAV 文件服務
│   │   ├── hugo-blog.conf      # Hugo 靜態部落格
│   │   ├── gateway.conf        # Gateway/Dashboard/Auth 服務
│   │   ├── yt-transcript.conf  # YouTube Transcript API
│   │   ├── n8n.conf           # n8n 工作流程自動化
│   │   └── health-checks.conf  # 健康檢查端點
│   ├── security/               # 安全相關配置
│   │   ├── auth-endpoints.conf # 認證相關端點
│   │   └── taiwan-ip-ranges.conf # 台灣 IP 範圍限制（已存在）
│   └── templates/              # 可重用的配置模板
│       └── proxy-headers.conf  # 標準代理頭部設定
```

## 配置模組說明

### 全局配置 (global/)

- **resolver.conf**: DNS 解析器設定，用於動態容器名稱解析
- **rate-limits.conf**: 各種服務的速率限制區域定義
- **ssl-params.conf**: SSL/TLS 安全參數、加密套件、HSTS 等
- **log-format.conf**: 自定義日誌格式定義

### 伺服器配置 (servers/)

- **http-redirect.conf**: HTTP (port 80) 到 HTTPS 的重定向配置
- **https-main.conf**: 主要 HTTPS 伺服器 (port 443) 的基本配置框架

### 服務配置 (services/)

每個服務都有獨立的配置文件，包含：
- 路由規則 (location 指令)
- 代理設定
- 服務特定的配置

- **webdav.conf**: WebDAV 文件服務，包含認證和大文件上傳支援
- **hugo-blog.conf**: Hugo 靜態部落格，包含靜態資源快取
- **gateway.conf**: Gateway 服務的 dashboard、auth、api 端點
- **yt-transcript.conf**: YouTube Transcript API 服務
- **n8n.conf**: n8n 工作流程自動化平台，支援 WebSocket
- **health-checks.conf**: 各服務的健康檢查端點

### 安全配置 (security/)

- **auth-endpoints.conf**: 內部認證端點和錯誤處理
- **taiwan-ip-ranges.conf**: 台灣 IP 範圍白名單（地理位置限制）

### 模板配置 (templates/)

- **proxy-headers.conf**: 標準的代理頭部設定，可被多個服務重用

## 使用方式

主配置文件 `nginx.conf` 使用 `include` 指令來載入各個模組：

```nginx
# 載入全局配置
include /etc/nginx/conf.d/global/*.conf;

# 載入伺服器配置
include /etc/nginx/conf.d/servers/*.conf;
```

在伺服器配置中載入服務配置：

```nginx
server {
    # 基本伺服器設定...
    
    # 載入所有服務配置
    include /etc/nginx/conf.d/services/*.conf;
}
```

## 優點

1. **模組化**: 每個服務獨立管理，易於維護
2. **可重用性**: 共同設定可以模板化，減少重複
3. **可讀性**: 配置結構清晰，易於理解
4. **可維護性**: 修改單一服務不影響其他服務
5. **可擴展性**: 新增服務只需添加對應的配置文件
6. **版本控制友好**: 每個服務的變更都有獨立的提交記錄

## 遷移說明

1. 原始的 `default.conf` 會被保留作為備份
2. 新的 `nginx.conf` 作為主入口點
3. 所有功能保持不變，只是重新組織配置結構
4. Docker Compose 需要更新 nginx 配置的掛載點

## 注意事項

- 確保所有 include 路徑正確
- 維持原有的功能和安全設定
- 測試新配置確保服務正常運行
- 定期備份配置文件
