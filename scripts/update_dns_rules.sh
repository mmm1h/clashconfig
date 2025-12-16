#!/bin/sh

#存到alpine中
#chmod +x /root/update_dns_rules.sh
#crontab -e
# 每天早上 5:30 自动拉取更新
# 30 5 * * * /root/update_dns_rules.sh


# ================= 配置区域 =================
# 1. 你的 GitHub Raw 链接 (请替换为你的真实地址)
REMOTE_URL="github.com/mmm1h/clashconfig/raw/refs/heads/main/force_ttl_rules.txt"

# 2. 本地文件路径 (PaoPaoDNS 读取的那个路径)
LOCAL_FILE="/root/paopao/force_ttl_rules.txt"

# 3. 临时下载路径 (不要改)
TEMP_FILE="/tmp/force_ttl_rules.tmp"

# 4. (可选) 重启 PaoPaoDNS 的命令
# 如果脚本运行在宿主机，可能是: docker restart paopaodns
# 如果脚本运行在容器内，PaoPaoDNS 可能支持热重载，或者留空
RESTART_CMD=""
# ===========================================

echo "Starting DNS rules update: $(date)"

# 1. 下载文件到临时目录 (-q: 安静模式, -O: 输出文件)
# --no-check-certificate 防止老旧 Alpine 根证书缺失导致报错
wget --no-check-certificate -q -O "$TEMP_FILE" "$REMOTE_URL"

# 2. 检查下载命令是否成功 (Exit Code 为 0)
if [ $? -ne 0 ]; then
    echo "❌ Error: Download failed. Network issue or URL wrong."
    rm -f "$TEMP_FILE"
    exit 1
fi

# 3. 检查文件大小是否正常 (防止下载到一个空文件)
# -s 表示文件存在且大小大于0
if [ ! -s "$TEMP_FILE" ]; then
    echo "❌ Error: Downloaded file is empty."
    rm -f "$TEMP_FILE"
    exit 1
fi

# 4. 简单的内容校验 (防止下载到 GitHub 的 404 页面 HTML)
# 检查前几行是否包含 '#' (我们的文件头肯定有 #)
HEAD_CHECK=$(head -n 1 "$TEMP_FILE" | grep "#")
if [ -z "$HEAD_CHECK" ]; then
    echo "❌ Error: File content invalid (looks like HTML or garbage)."
    rm -f "$TEMP_FILE"
    exit 1
fi

# 5. 安全覆盖 (原子操作)
# 只有上面都通过了，才覆盖正式文件
mv "$TEMP_FILE" "$LOCAL_FILE"
echo "✅ Success: Rules updated."

# 6. 重启服务 (如果有配置)
if [ -n "$RESTART_CMD" ]; then
    echo "Restarting service..."
    $RESTART_CMD
fi

exit 0

