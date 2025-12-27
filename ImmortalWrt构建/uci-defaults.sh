#!/bin/sh

# 1. Network
# WAN static, IPv6 off
if ! uci get network.wan >/dev/null 2>&1; then
    uci set network.wan=interface
fi
uci set network.wan.device='eth1'
uci set network.wan.proto='static'
uci set network.wan.ipaddr='192.168.9.3'
uci set network.wan.gateway='192.168.9.1'
uci set network.wan.broadcast='192.168.9.255'
uci set network.wan.netmask='255.255.255.0'
uci set network.wan.ipv6='0'
uci set network.wan.delegate='0'

# DNS
uci -q del network.wan.dns
uci add_list network.wan.dns='192.168.9.20'

# LAN static, IPv6 off
uci set network.lan.device='eth0'
uci set network.lan.proto='static'
uci set network.lan.ipaddr='192.168.8.1'
uci set network.lan.netmask='255.255.255.0'
uci set network.lan.ipv6='0'
uci set network.lan.delegate='0'

uci commit network

# 2. DHCP
# LAN DHCP/IPv6 off
uci set dhcp.lan.ignore='1'
uci set dhcp.lan.ra='disabled'
uci set dhcp.lan.dhcpv6='disabled'

# WAN IPv6 off
uci set dhcp.wan.ra='disabled'
uci set dhcp.wan.dhcpv6='disabled'

# DNS options
uci set dhcp.@dnsmasq[0].dnssec='0'
uci set dhcp.@dnsmasq[0].dnssec_check_unsigned='0'
uci set dhcp.@dnsmasq[0].rebind_protection='0'
uci set dhcp.@dnsmasq[0].dns_redirect='0'

uci commit dhcp

# 3. Firewall (accept all)
uci set firewall.@defaults[0].input='ACCEPT'
uci set firewall.@defaults[0].output='ACCEPT'
uci set firewall.@defaults[0].forward='ACCEPT'
uci set firewall.@defaults[0].syn_flood='0'
uci set firewall.@defaults[0].fullcone='0'

# LAN/WAN zones
uci set firewall.@zone[0].input='ACCEPT'
uci set firewall.@zone[0].output='ACCEPT'
uci set firewall.@zone[0].forward='ACCEPT'

wan_zone_index=$(uci show firewall | grep ".name='wan'" | cut -d '[' -f2 | cut -d ']' -f1)
if [ -n "$wan_zone_index" ]; then
    uci set firewall.@zone[$wan_zone_index].input='ACCEPT'
    uci set firewall.@zone[$wan_zone_index].output='ACCEPT'
    uci set firewall.@zone[$wan_zone_index].forward='ACCEPT'
    uci set firewall.@zone[$wan_zone_index].masq='1'
fi

uci commit firewall

# 4. System/SSH
uci set system.@system[0].hostname='ImmortalWrt'
uci set system.@system[0].zonename='Asia/Shanghai'
uci set system.@system[0].timezone='CST-8'
uci commit system

# LuCI
uci set luci.main.mediaurlbase='/luci-static/argon'
uci set luci.main.lang='zh_cn'
uci commit luci

# Root password
cat << 'EOF' | passwd root
QSi$xmx6#Rn$$&
QSi$xmx6#Rn$$&
EOF

# Allow root SSH
sed -i 's|/bin/bash|/bin/ash|g' /etc/passwd
sed -i 's|/bin/zsh|/bin/ash|g' /etc/passwd

uci set dropbear.@dropbear[0].PasswordAuth='on'
uci set dropbear.@dropbear[0].RootPasswordAuth='on'
uci set dropbear.@dropbear[0].Interface='lan'
uci commit dropbear

# Stop mihomo
if [ -f /etc/init.d/mihomo ]; then
    /etc/init.d/mihomo disable
    /etc/init.d/mihomo stop
fi

# OpenClash core
mkdir -p /etc/openclash/core
if [ -f /usr/bin/mihomo ]; then
    cp -f /usr/bin/mihomo /etc/openclash/core/clash_meta
    chmod +x /etc/openclash/core/clash_meta
fi

# Use Meta core
uci set openclash.config.core_version='meta'
uci commit openclash

# SquashFS 模式扩容检测脚本
LOG_FILE="/root/resize_log.txt"
DISK="/dev/sda"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_msg "=== 开始执行 SquashFS 模式扩容检测 ==="

if [ -e "${DISK}3" ]; then
    log_msg "检测到分区 3 已存在，跳过扩容操作。"
    exit 0
fi

log_msg "步骤1：尝试修复 GPT 分区表..."
parted -s $DISK print >/dev/null 2>&1 || true

log_msg "步骤2：正在创建新分区 (/dev/sda3) 填满剩余空间..."


END_SECTOR=$(parted -s $DISK unit s print | grep "^ 2" | awk '{print $3}')

if [ -n "$END_SECTOR" ]; then
    log_msg "检测到 sda2 结束于: $END_SECTOR"
    if parted -s $DISK mkpart primary ext4 "$END_SECTOR" 100% >> "$LOG_FILE" 2>&1; then
        log_msg ">>> 分区创建成功。"
        
        sync
        sleep 2
        log_msg "步骤3：正在格式化 ${DISK}3 为 ext4..."
        if mkfs.ext4 -F -L overlay "${DISK}3" >> "$LOG_FILE" 2>&1; then
            log_msg ">>> 格式化成功。"

            log_msg "步骤4：配置 fstab 挂载点..."
            uci -q delete fstab.overlay
            uci set fstab.overlay=mount
            uci set fstab.overlay.device="${DISK}3"
            uci set fstab.overlay.target='/overlay'
            uci set fstab.overlay.enabled='1'
            uci commit fstab
            
            log_msg "SUCCESS: 配置完成！系统将在 5 秒后重启以挂载新的 Overlay..."
            (sleep 5 && reboot) &
        else
            log_msg "!!! 错误：格式化失败 (mkfs.ext4)。"
        fi
    else
        log_msg "!!! 错误：分区创建失败 (parted)。"
    fi
else
    log_msg "!!! 错误：无法获取分区信息。"
fi

exit 0