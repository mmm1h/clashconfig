# scripts 目录说明

本目录存放本仓库的辅助脚本。建议在仓库根目录执行脚本，以保证相对路径正确。

## update_direct_from_cn.py

用途：
- 读取 `rules/CN.txt`，把中国 IP 段合并到 `rules/Direct.list` 中。
- 自动维护 `# --- CN.txt START (auto) ---` 与 `# --- CN.txt END (auto) ---` 标记之间的区块。

使用：
```bash
python scripts/update_direct_from_cn.py
```

说明：
- 输入：`rules/CN.txt`
- 输出：更新 `rules/Direct.list`

## update_dns.py

用途：
- 生成 PaoPaoDNS 的 `force_ttl_rules.txt`（抖音/字节相关域名）。
- 自动从多个源拉取并去重。

使用：
```bash
python scripts/update_dns.py
```

说明：
- 依赖：`python3`、`requests`、联网
- 输出：`force_ttl_rules.txt`
- 可在脚本顶部调整 `SOURCE_URLS` 与 DNS 相关配置

## update_dns_rules.sh

用途：
- 在服务器上下载最新的 `force_ttl_rules.txt` 并覆盖到本地路径。
- 可选执行重启命令（如重启 PaoPaoDNS）。

使用：
```bash
sh scripts/update_dns_rules.sh
```

说明：
- 需要先修改脚本内的 `REMOTE_URL`、`LOCAL_FILE`、`RESTART_CMD`
- 默认使用 `wget --no-check-certificate` 下载（适配旧环境）
- 适合配合 cron 定时更新

## update_zashboard.sh

用途：
- 在 OpenWrt 上更新 OpenClash 的 Zashboard 前端文件。
- 目标路径为 `/usr/share/openclash/ui/zashboard`。

使用：
```bash
sh scripts/update_zashboard.sh
```

安装每天早上 5 点执行的 cron：
```bash
sh scripts/update_zashboard.sh --install-cron
/etc/init.d/cron enable && /etc/init.d/cron restart
```

说明：
- 依赖：`unzip`，以及下载工具 `wget`/`uclient-fetch`/`curl` 任一
- 可在脚本内修改：
  - `DOWNLOAD_URL`：下载地址（已支持国内代理）
  - `DOWNLOAD_TOOL`：`auto`/`wget`/`uclient-fetch`/`curl`
  - `DASHBOARD_DIR`：OpenClash UI 目录（默认 `/usr/share/openclash/ui`）
  - `CRON_SCHEDULE`：默认 `0 5 * * *`
- 默认静默；出错才会输出到 stderr
- 若需记录日志，可设置 `QUIET=0` 或改写 `CRON_REDIRECT`
