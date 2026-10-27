# clashconfig

公开 artifact repo，用于分发 `Mihomo / Clash` 相关配置、规则与生成物。

## 定位

- 按维护者当前要求，直接维护本机 `clashconfig` 仓库；旧 `network_debug` 工作流已停用。
- 公开配置保留订阅占位符，GitHub Actions 注入私有 URL 后更新 Gist。
- 现网继续使用现有 raw / Gist / Worker 地址。

## 上游参考

- 当前配置按 [JackieWuu 的 Nikki Fake-IP v11](https://github.com/JackieWuu/mihomo_config/blob/d7740217d1657637e9f0f2f161a47f64855aaf94/nikki/nikki-Fake-IP-v11.yaml) 逐模块核对；参考基线为 `d7740217`（2026-09-03）。
- ACL4SSR 原始配置参考：
  `https://github.com/ACL4SSR/ACL4SSR/blob/master/Clash/config/ACL4SSR_Online_Full.ini`

## 共用配置与客户端职责

`mihomo.yaml` 是唯一维护的 Mihomo 配置，供 OpenWrt 的 OpenClash 和各设备的 Clash Party 共用。旧 JS 生成器已停用。

代理空组使用 `empty-fallback: REJECT`，需要 Mihomo v1.19.27 或更新版本。本次配置校验使用 v1.19.33。

- 订阅沿用现有下载方式、更新间隔和健康检查；云洞与爪云的私有 URL 仍由 Actions 注入。
- 通用参数启用 TCP 并发连接和统一延迟测量，连接保活参数参考 Nikki v11；保留 `find-process-mode: strict`，供桌面端按需匹配进程规则。
- 代理端口、LAN 访问权限、UI 路径、控制接口、TUN 启停及自动路由由各客户端管理。路由器的 `device: nikki`、GSO 等平台专用调优和写系统时钟的 NTP 设置不纳入共用配置。
- GeoIP / GeoSite 沿用现有下载地址与每日更新；保留完整 `geoip.dat`，供现有规则匹配使用。

### TUN 绕行

按 Nikki v11 排除 Apple 推送和私有、共享及保留地址段，需要客户端开启 `auto-route`。进入系统绕行路由的流量不会再经过 Mihomo 的分流规则。

`route-exclude-address-set: [cn_ip]` 的国内 IP 集绕行仅支持 Linux + nftables，并要求 `auto-route`、`auto-redirect` 同时开启；它与 `routing-mark` 冲突。OpenClash 有自己的防火墙和路由管理，须结合实际模式设置，不能直接照搬 Nikki 的 `auto-redirect`。Windows/macOS 不应用这个规则集绕行，国内 IP 仍由规则层 `cn_ip` 直连处理。

OpenClash 配套订阅模块改用其原生绕行：`china_ip_route=1` 负责国内 IP，固定绕行网段从 YAML 自动生成原生列表；核心的自动路由关闭，避免两套接管并存。订阅地址、维护入口和资源更新方式见 [openclash/README.md](openclash/README.md)。

参考：[Mihomo TUN 文档](https://wiki.metacubex.one/config/inbound/tun/#route-exclude-address-set)。

### 域名嗅探

启用 HTTP/TLS/QUIC 嗅探，识别尚无域名的连接并辅助分流；`override-destination: false` 保留原连接目标，不按嗅探结果重选目标地址。保留 Nikki v11 的 Apple 推送和内网服务排除项。

### 代理组与故障转移

保留现有 AI、媒体和游戏大类，新增 `🔙 全节点故障转移`，依次尝试香港 → 日本 → 新加坡 → 台湾 → 美国 → 其他地区。各地区继续自动测速，原有其他地区手动组保留，另加自动组供最后一级回退。

普通代理、国外媒体、漏网之鱼默认优先选择故障转移；境外 DNS 及公共加密 DNS 分流直接使用该组。`♻️ 自动选择` 保留为香港节点测速选项，AI 组继续独立手动选择，不默认使用香港回退链。代理组为空时明确拒绝，避免空组退回直连。

DediOne 按美国归组，Lightsail 按新加坡归组；普通自动选择继续排除 4x 节点，游戏专线仍按原有筛选。升级后若客户端恢复了旧的分组选择，需要手动选择新的故障转移选项。

### 分流取舍

- Apple / iCloud 的国内域名及 Apple 更新服务直连，其余跟随 `🚀 节点选择`；Apple 推送的固定 IP 段仍按 TUN 排除处理。
- 国内游戏、Steam 下载 CDN、`xboxlive.com` 和 `playstation.net` 直连；其余游戏交给 `🎮 游戏专用`。游戏组改为手动选择，默认故障转移，也可选 DIRECT 或原有专线。
- 保留 Android Play Store 的进程特例，`Custom_AI` 优先于广告屏蔽和服务大类；微软下载等自定义规则仍优先于国内与各服务分流。补充 Telegram / Discord、Cloudflare 和 `.cn` 域名兜底。
- 最后对未匹配的 80/8080/443/8443 端口使用节点选择，其余交给漏网之鱼。旧非标准端口清单保留兼容用途，主配置已不再订阅它。

## 分发说明

- 公开 repo 的 `raw.githubusercontent.com/mmm1h/clashconfig/...` 继续作为 artifact endpoint。
- 私有 Gist、Cloudflare Worker 与相关 consumer 可以继续复用现有地址。
- `rules/CN.txt` 为冻结的 legacy compatibility artifact，不再纳入主迁移目标。

## DNS 策略与客户端设置

按维护者选择采用 Nikki v11 的解析取舍，并为 AI 增加独立出口：`Custom_AI` 中的域名使用经 `🤖 AI节点` 连接的 Cloudflare / Google DoH；Apple、游戏平台及指定国内服务使用国内 DoH；其余境外分类使用普通代理 DoH，未分类域名默认使用国内 DoH。

| 查询类型 | DNS 上游 |
| --- | --- |
| `Custom_AI` 中的域名，包括 Claude 核心域名和已收录的辅助服务 | Cloudflare / Google DoH，经 `🤖 AI节点` 代理组 |
| DNS 引导解析、代理节点域名、未分类域名 | 阿里 IP 形式的 DoH，直连 |
| Apple、游戏平台、Google 国内域及指定国内服务 | 阿里 / 腾讯 DoH，直连 |
| `steamcommunity.com` 特例、最终命中 `geolocation-!cn` 的域名 | Cloudflare / Google DoH，经 `🔙 全节点故障转移` 代理组 |

`nameserver-policy` 中 `rule-set:Custom_AI` 位于服务大类之前，复用 `rules/AI.list` 的域名规则，IP 规则不参与 DNS 匹配；境外分类放在末尾。AI DoH 使用 IP 地址连接并明确指定 `#🤖 AI节点`，避免为 DoH 主机额外做域名引导解析。AI 组不可用时解析失败，不改用国内 DNS 或普通故障转移组。直连出口没有单独覆盖 DNS，跟随同一套策略；其他未分类域名仍走国内上游。

Fake-IP 过滤负责决定是否返回真实 IP，与 DNS 上游选择分别配置。沿用作者的游戏、Apple、系统连通性检测等过滤，保留原有 Microsoft / OneDrive 及个人域名补充。广告屏蔽继续由规则层的 `🚫 广告屏蔽` 控制。

客户端设置：

- Clash Party 按需开启 TUN 和自动路由，保留严格路由、UDP/TCP 53 劫持。配置文本不会替客户端打开 TUN。
- OpenClash 负责自身的 DNS 监听、dnsmasq 接管和防火墙配置；共用 YAML 保留 `127.0.0.1:1053`，不直接暴露 LAN DNS 服务。导入后需检查最终运行配置，避免 GUI 覆写改变预期 DNS 策略。
- 使用配套 OpenClash 订阅模块后，DNS 与嗅探从主 YAML 自动生成并在插件处理后恢复，避免自动补入明文 DNS；模块补充 TUN DNS 劫持，保留设备管理的监听地址及端口。原手工设置的绿联与 Bitwarden Fake-IP 例外已迁回 YAML；`fakeip_filter` 的引用统一使用有效的 `rule-set:` 前缀。
- `route-exclude-address-set` 的国内 IP 绕行有平台和路由条件，见上文；绕行流量不受核心内规则控制。Windows/macOS 也无法仅靠 TUN DNS 劫持自动接管发往局域网 DNS 的查询。
- 旧配置于 2026-10-06 在 Windows 测试时，Clash Party 的 `post-up` 启动方式比 `log` 更可靠；这是客户端设置，当前配置尚未在各设备重做该项实测。

## 本次验证

2026-10-27：YAML 语法、代理组及规则引用、组依赖无环和订阅占位符检查通过。Mihomo v1.19.33 使用本地替代节点、现有自定义规则及当前 GeoIP / GeoSite 数据完成配置检查；真实订阅下载和各设备网络未纳入此次测试。

本地模拟确认 DediOne 归美国、Lightsail 归新加坡；香港组为空时回退到日本，日本故障后切到新加坡，全部节点不可用时最终拒绝连接。模拟关闭 TUN，仅验证分组与健康检查行为，未验证 OpenClash 防火墙和各设备 TUN 路由。

AI DNS 补充验证：15 个 AI / Claude 核心及辅助域名均命中独立 AI 解析策略；通过本地替代代理确认原始 Cloudflare / Google DoH 地址经 AI 组连接，模拟连接失败时没有查询国内或普通代理 DNS。Claude 核心域名、辅助服务和官方服务 IP 的连接也命中 AI 组。测试关闭 TUN，使用本地替代节点，不代表各客户端或外层 DNS 转发已经生效。

OpenClash 适配已于 2026-10-27 部署到当前路由器（`0.48.002` / `Mihomo alpha-gbc76c13`），并在自动回滚保护下完成重启与可用性检查。运行配置确认 DNS 策略和嗅探设置来自导入 YAML，`respect-rules=true`、AI 规则位于第二条，旧 `.31` 来源规则已移除。控制接口实测 `claude.ai` 命中 `Custom_AI`，连接链为 `🤖 AI节点 → Lightsail-SG`；Cloudflare / Google DoH 也观察到经过同一 AI 组的连接。Claude API 根路径返回 HTTP 404（连通性检查），普通代理检查返回 HTTP 204。

防火墙确认国内 IP 和 Apple 推送网段在打代理标记前绕行；核心自动路由已关闭，重复的 `inet mihomo` 表及 table 2022 路由已消失。普通代理、媒体、游戏及漏网之鱼的现网选择已设为故障转移，AI 保留 `Lightsail-SG`。此前隔离校验也已覆盖空组回退 REJECT、脚本重复运行、原手工网段保留、非法网段拒绝和权限保留。

原设置备份保留在路由器 `/root/openclash-migration-20261027-125927`，验证通过后已确认保留新配置。命令行访问 Claude 官网返回 Cloudflare 人机验证（HTTP 403、`cf-mitigated: challenge`），尚未验证浏览器登录和实际会话。上述现网验证仅覆盖当前 OpenClash；仓库和 Gist 分发不代表其他设备已完成客户端设置或验证。外层 AdGuardHome / PaoPaoDNS 和终端自带 DNS 未纳入这次现网验证，不能据此断言整个家庭网络不存在 DNS 泄露。

同日 15:46，已将自定义适配脚本替换为 [OpenClash 原生订阅模块](openclash/README.md)，模块及绕行列表由主 YAML 自动生成并发布。原生处理链、核心校验及现网 DNS/AI 连接、TUN、防火墙绕行均通过验证；旧脚本已停用，切换前备份另存于 `/root/openclash-subscription-20261027-152414`。资源下载失败与 HTTP 304 的缓存行为也已验证，平时无需在路由器维护 Shell/Ruby。

参考资料：

- [Mihomo DNS 配置](https://wiki.metacubex.one/config/dns/)、[TUN 配置](https://wiki.metacubex.one/config/inbound/tun/)、[代理组空组回退](https://wiki.metacubex.one/config/proxy-groups/#empty-fallback)。
- [JackieWuu/mihomo_config](https://github.com/JackieWuu/mihomo_config)：参考域名分流与加密引导解析；仍须核对代理组是否包含直连。
- [Custom OpenClash Rules](https://github.com/Aethersailor/Custom_OpenClash_Rules)：路由器侧 DNS 接管实践。
- [sing-box HTTPS DNS](https://sing-box.sagernet.org/configuration/dns/server/https/)：解析器选择与连接上游的出口独立配置。
- [Firefox DoH 管理策略](https://firefox-admin-docs.mozilla.org/reference/policies/dnsoverhttps/)、[Chromium DoH](https://www.chromium.org/developers/dns-over-https/)：浏览器解析与回退行为。
