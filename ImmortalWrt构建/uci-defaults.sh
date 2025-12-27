#!/bin/sh

# ==========================================================
# 1. 网络接口配置 (Network)
# ==========================================================

# --- WAN 口 (静态IP, 关闭IPv6) ---
if ! uci get network.wan >/dev/null 2>&1; then
    uci set network.wan=interface
fi
uci set network.wan.device='eth1'
uci set network.wan.proto='static'
uci set network.wan.ipaddr='192.168.9.3'
uci set network.wan.gateway='192.168.9.1'
uci set network.wan.broadcast='192.168.9.255'
uci set network.wan.netmask='255.255.255.0'
uci set network.wan.ipv6='0'           # 关闭 WAN IPv6
uci set network.wan.delegate='0'       # 禁止分发 IPv6

# 处理 DNS
uci -q del network.wan.dns
uci add_list network.wan.dns='192.168.9.20'

# --- LAN 口 (静态IP, 关闭IPv6) ---
uci set network.lan.device='eth0'
uci set network.lan.proto='static'
uci set network.lan.ipaddr='192.168.8.1'
uci set network.lan.netmask='255.255.255.0'
uci set network.lan.ipv6='0'           # 关闭 LAN IPv6
uci set network.lan.delegate='0'

uci commit network

# ==========================================================
# 2. DHCP 设置 (关闭 IPv6 DHCP 和 LAN DHCP 服务)
# ==========================================================

# --- LAN DHCP ---
# 既然你要求“DHCP功能全部关闭”，通常指不提供 DHCP 服务
uci set dhcp.lan.ignore='1'            # 忽略 LAN 接口 DHCP 请求 (关闭 DHCP 服务)
uci set dhcp.lan.ra='disabled'         # 关闭 IPv6 路由通告
uci set dhcp.lan.dhcpv6='disabled'     # 关闭 DHCPv6

# --- WAN DHCP ---
# WAN 口本身作为客户端，配置为 static 协议其实已经不使用 DHCP 了
# 这里确保 WAN 不会产生 IPv6 相关交互
uci set dhcp.wan.ra='disabled'
uci set dhcp.wan.dhcpv6='disabled'

# --- DNS 安全设置 (关闭 DNSSEC, 重绑定保护) ---
uci set dhcp.@dnsmasq[0].dnssec='0'
uci set dhcp.@dnsmasq[0].dnssec_check_unsigned='0'
uci set dhcp.@dnsmasq[0].rebind_protection='0'
uci set dhcp.@dnsmasq[0].dns_redirect='0'

uci commit dhcp

# ==========================================================
# 3. 防火墙配置 (Firewall - 全开模式)
# ==========================================================

# --- 常规设置 ---
uci set firewall.@defaults[0].input='ACCEPT'
uci set firewall.@defaults[0].output='ACCEPT'
uci set firewall.@defaults[0].forward='ACCEPT'
uci set firewall.@defaults[0].syn_flood='0'    # 关闭 SYN-flood 保护
uci set firewall.@defaults[0].fullcone='0'     # 关闭 FullCone NAT

# --- 区域设置 (LAN & WAN 全接受) ---
# 修改 lan 区域
uci set firewall.@zone[0].input='ACCEPT'
uci set firewall.@zone[0].output='ACCEPT'
uci set firewall.@zone[0].forward='ACCEPT'

# 修改 wan 区域 (通常是 index 1，但用名字更稳妥)
# 查找名为 wan 的 zone 并设置
wan_zone_index=$(uci show firewall | grep ".name='wan'" | cut -d '[' -f2 | cut -d ']' -f1)
if [ -n "$wan_zone_index" ]; then
    uci set firewall.@zone[$wan_zone_index].input='ACCEPT'
    uci set firewall.@zone[$wan_zone_index].output='ACCEPT'
    uci set firewall.@zone[$wan_zone_index].forward='ACCEPT'
    uci set firewall.@zone[$wan_zone_index].masq='1' # 保持 NAT 开启，否则无法上网
fi

uci commit firewall

# ==========================================================
# 4. 系统与账户 (System & SSH)
# ==========================================================

uci set system.@system[0].hostname='ImmortalWrt'
uci set system.@system[0].zonename='Asia/Shanghai'
uci set system.@system[0].timezone='CST-8'
uci commit system

# 界面主题与语言
uci set luci.main.mediaurlbase='/luci-static/argon'
uci set luci.main.lang='zh_cn'
uci commit luci

# 密码设置 (Root)
cat << 'EOF' | passwd root
QSi$xmx6#Rn$$&
QSi$xmx6#Rn$$&
EOF

# SSH 修复与允许 Root 登录
# 确保 root 用户的 shell 是存在的 (ash)，防止因缺少 bash 导致无法登录
sed -i 's|/bin/bash|/bin/ash|g' /etc/passwd
sed -i 's|/bin/zsh|/bin/ash|g' /etc/passwd

uci set dropbear.@dropbear[0].PasswordAuth='on'
uci set dropbear.@dropbear[0].RootPasswordAuth='on'
uci set dropbear.@dropbear[0].Interface='lan'  # 仅允许 LAN 口登录 SSH (更安全)
uci commit dropbear

exit 0