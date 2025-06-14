#!/bin/bash

# SSL 證書設置腳本
# 用法: ./setup-ssl.sh

echo "🔒 開始 SSL 證書設置..."

# 檢查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose 未安裝"
    exit 1
fi

# 創建必要的目錄
echo "📁 創建證書目錄..."
mkdir -p ./certbot/conf/live/novis.tplinkdns.com
mkdir -p ./certbot/www

# 創建臨時自簽證書（用來啟動 nginx）
echo "🔑 創建臨時證書..."
docker run --rm -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    certbot/certbot:latest \
    sh -c "openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/novis.tplinkdns.com/privkey.pem \
    -out /etc/letsencrypt/live/novis.tplinkdns.com/fullchain.pem \
    -subj '/CN=localhost'"

echo "🚀 啟動服務..."
docker-compose up -d nginx app

# 等待 nginx 啟動
sleep 5

echo "📜 請求真實證書..."
docker-compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email dddrumydd@gmail.com \
    --agree-tos \
    --no-eff-email \
    -d novis.tplinkdns.com

if [ $? -eq 0 ]; then
    echo "✅ 證書獲取成功！"
    echo "🔄 重新載入 nginx..."
    docker-compose exec nginx nginx -s reload
    
    echo "🎉 設置完成！現在啟動完整服務..."
    docker-compose up -d
    
    echo "✅ 全部完成！"
    echo "🌐 您的網站現在應該可以通過 https://novis.tplinkdns.com 訪問"
else
    echo "❌ 證書獲取失敗"
    echo "請檢查："
    echo "1. 域名 novis.tplinkdns.com 是否正確指向此服務器"
    echo "2. 80 端口是否可從外部訪問"
    echo "3. 防火牆設定是否正確"
fi 