import requests
import os
import socket
import re
from datetime import datetime, timezone, timedelta

# --- 核心配置 ---
SOURCE_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/bytedance.txt"
OUTPUT_FILE = "force_ttl_rules.txt"

# 主 DNS (字节跳动权威DNS)
PRIMARY_DNS = "180.184.1.1" 
# 备用 DNS (阿里DNS)
FALLBACK_DNS = "223.5.5.5"
DNS_PORT = 53

# 严格的格式校验正则：确保是 域名@IP:端口 格式
# 例如: douyin.com@180.184.1.1:53
VALID_RULE_PATTERN = re.compile(r'^[a-zA-Z0-9][-a-zA-Z0-9.]+\.[a-zA-Z]{2,}@\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')

def get_current_time_str():
    """获取北京时间字符串"""
    utc_dt = datetime.now(timezone.utc)
    bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
    return bj_dt.strftime('%Y-%m-%d %H:%M:%S')

def test_dns_connectivity(ip, port):
    """测试 DNS 服务器连通性 (TCP)"""
    print(f"正在测试 DNS 连通性: {ip}:{port} ...", end="", flush=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3) # 3秒超时
    try:
        s.connect((ip, port))
        s.close()
        print(" [✅ 正常]")
        return True
    except Exception as e:
        print(f" [❌ 失败: {e}]")
        return False

def determine_target_dns():
    """确定最终使用的 DNS"""
    if test_dns_connectivity(PRIMARY_DNS, DNS_PORT):
        return f"{PRIMARY_DNS}:{DNS_PORT}"
    
    print(f"⚠️ 主 DNS ({PRIMARY_DNS}) 无法连接，尝试切换备用 DNS...")
    
    if test_dns_connectivity(FALLBACK_DNS, DNS_PORT):
        print(f"✅ 已切换至备用 DNS: {FALLBACK_DNS}")
        return f"{FALLBACK_DNS}:{DNS_PORT}"
    
    print("❌ 所有 DNS 服务器均不可达，停止生成以防止配置错误！")
    return None

def fetch_and_process():
    # 1. 确定 DNS
    target_dns = determine_target_dns()
    if not target_dns:
        exit(1) # 非 0 退出码会让 GitHub Action 报错提醒你

    # 2. 获取数据
    print(f"正在下载规则源: {SOURCE_URL}")
    try:
        response = requests.get(SOURCE_URL, timeout=15)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        exit(1)

    valid_lines = []
    # 手动补充的关键域名
    custom_domains = [
        "douyin.com", "snssdk.com", "ixigua.com", "pstatp.com", 
        "toutiao.com", "byteimg.com", "amemv.com"
    ]

    print("正在清洗并验证数据...")
    
    # 3. 数据清洗
    temp_domains = set(custom_domains) # 使用集合自动去重
    
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("include:"):
            continue
        
        # 提取域名 (移除 @!cn, full: 等修饰符)
        parts = line.split()
        if not parts: continue
        domain = parts[0].replace("full:", "")
        
        # 基础域名合法性检查 (至少包含一个点)
        if "." in domain:
            temp_domains.add(domain)

    # 4. 生成并进行最终格式校验
    final_rules = []
    
    for domain in sorted(list(temp_domains)):
        # 组装配置行
        rule_line = f"{domain}@{target_dns}"
        
        # --- 关键步骤：最终格式正则校验 ---
        if VALID_RULE_PATTERN.match(rule_line):
            final_rules.append(rule_line)
        else:
            print(f"⚠️ 警告：检测到非法格式，已丢弃: {rule_line}")

    if not final_rules:
        print("❌ 错误：生成的有效规则数量为 0，终止写入！")
        exit(1)

    # 5. 写入文件 (带头部信息)
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            # 写入 Header
            f.write(f"# ==========================================\n")
            f.write(f"# PaoPaoDNS Force TTL Rules (Bytedance)\n")
            f.write(f"# Updated: {get_current_time_str()} (Beijing Time)\n")
            f.write(f"# Count:   {len(final_rules)} domains\n")
            f.write(f"# DNS:     {target_dns}\n")
            f.write(f"# Source:  {SOURCE_URL}\n")
            f.write(f"# Author:  GitHub Action Bot\n")
            f.write(f"# ==========================================\n\n")
            
            # 写入规则
            f.write("\n".join(final_rules))
            
        print(f"✅ 成功生成文件: {OUTPUT_FILE} (共 {len(final_rules)} 条)")
        
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_process()