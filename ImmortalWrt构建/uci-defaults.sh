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

# LAN/WAN zones
uci set firewall.@zone[1].input='ACCEPT'
uci set firewall.@zone[1].output='ACCEPT'
uci set firewall.@zone[1].forward='ACCEPT'

uci commit firewall

# 4. System/SSH
uci set system.@system[0].hostname='HMWrt'
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

exit 0