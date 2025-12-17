import requests
import socket
import re
from datetime import datetime, timezone, timedelta

# --- 核心配置 ---
# 规则源列表 (支持多源)
SOURCE_URLS = [
    # 源1: v2fly (纯域名/full格式)
    "https://raw.githubusercontent.com/v2fly/domain-list-community/refs/heads/master/data/bytedance",
    # 源2: Blackmatrix7 (Clash格式)
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/DouYin/DouYin.list"
]

OUTPUT_FILE = "force_ttl_rules.txt"

# 主 DNS (字节跳动权威DNS)
PRIMARY_DNS = "180.184.1.1" 
# 备用 DNS (阿里DNS)
FALLBACK_DNS = "223.5.5.5"
DNS_PORT = 53

# 严格的格式校验正则：确保是 域名@IP:端口 格式
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
    """确定最终使用的 DNS (主备切换逻辑)"""
    if test_dns_connectivity(PRIMARY_DNS, DNS_PORT):
        return f"{PRIMARY_DNS}:{DNS_PORT}"
    
    print(f"⚠️ 主 DNS ({PRIMARY_DNS}) 无法连接，尝试切换备用 DNS...")
    
    if test_dns_connectivity(FALLBACK_DNS, DNS_PORT):
        print(f"✅ 已切换至备用 DNS: {FALLBACK_DNS}")
        return f"{FALLBACK_DNS}:{DNS_PORT}"
    
    print("❌ 所有 DNS 服务器均不可达，停止生成以防止配置错误！")
    return None

def parse_domain(line):
    """
    智能解析每一行，提取纯域名
    支持: v2fly格式, Clash格式, 纯域名
    """
    line = line.strip()
    # 忽略空行、注释、引用
    if not line or line.startswith("#") or line.startswith("//") or line.startswith("include:"):
        return None
    
    # 忽略 Clash 的非域名规则
    if any(k in line for k in ["IP-CIDR", "PROCESS-NAME", "USER-AGENT"]):
        return None

    # 1. 处理 Clash 格式 (逗号分隔: DOMAIN-SUFFIX,douyin.com,Proxy)
    if "," in line:
        parts = line.split(",")
        if len(parts) >= 2:
            return parts[1].strip()
    
    # 2. 处理 v2fly 格式 (full:douyin.com)
    if "full:" in line:
        return line.replace("full:", "").strip()
    
    # 3. 处理纯域名 (可能带有注释)
    parts = line.split()
    if parts:
        domain = parts[0]
        # 简单合法性检查: 必须包含点，且不含冒号
        if "." in domain and ":" not in domain:
            return domain
            
    return None

def fetch_and_process():
    # 1. 确定 DNS
    target_dns = determine_target_dns()
    if not target_dns:
        exit(1)

    unique_domains = set()
    
    # 手动补充的关键域名 (确保这些一定存在)
    custom_domains = [
        "douyin.com", "snssdk.com", "ixigua.com", "pstatp.com", 
        "toutiao.com", "byteimg.com", "amemv.com", "douyinvod.com"
    ]
    unique_domains.update(custom_domains)

    # 2. 遍历下载所有源
    print(f"开始处理 {len(SOURCE_URLS)} 个规则源...")
    
    for url in SOURCE_URLS:
        print(f"⬇️ 正在下载: {url}")
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            content = response.text
            
            count = 0
            for line in content.splitlines():
                domain = parse_domain(line)
                if domain:
                    unique_domains.add(domain)
                    count += 1
            print(f"   -> 提取到 {count} 条有效记录")
            
        except Exception as e:
            print(f"   ❌ 下载或解析失败: {e}")
            # 一个源失败不影响整体，继续下一个
            continue

    if not unique_domains:
        print("❌ 错误：所有源处理完毕后，有效域名数量为 0，终止写入！")
        exit(1)

    print("正在进行最终验证与生成...")

    # 3. 生成并进行格式正则校验
    final_rules = []
    
    for domain in sorted(list(unique_domains)):
        rule_line = f"{domain}@{target_dns}"
        
        # 正则校验
        if VALID_RULE_PATTERN.match(rule_line):
            final_rules.append(rule_line)
        else:
            # 仅在调试时开启，避免日志过多
            # print(f"⚠️ 丢弃非法格式: {rule_line}")
            pass

    print(f"🔍 校验通过: {len(final_rules)} 条")

    # 4. 写入文件
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"# ==========================================\n")
            f.write(f"# PaoPaoDNS Force TTL Rules (Bytedance)\n")
            f.write(f"# Updated: {get_current_time_str()} (北京时间)\n")
            f.write(f"# Count:   {len(final_rules)} domains\n")
            f.write(f"# DNS:     {target_dns}\n")
            for i, url in enumerate(SOURCE_URLS, 1):
                f.write(f"# Source {i}:  {url}\n")
            f.write(f"# Author:  GitHub Action Bot\n")
            f.write(f"# ==========================================\n\n")
            
            f.write("\n".join(final_rules))
            
        print(f"✅ 成功生成文件: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_process()