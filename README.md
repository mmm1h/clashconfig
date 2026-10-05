# clashconfig

公开 artifact repo，用于分发 `Mihomo / Clash` 相关配置、规则与生成物。

## 定位

- 按维护者当前要求，直接维护本机 `clashconfig` 仓库；旧 `network_debug` 工作流已停用。
- 公开配置保留订阅占位符，GitHub Actions 注入私有 URL 后更新 Gist。
- 现网继续使用现有 raw / Gist / Worker 地址。

## 上游参考

- ACL4SSR 原始配置参考：
  `https://github.com/ACL4SSR/ACL4SSR/blob/master/Clash/config/ACL4SSR_Online_Full.ini`

## 分发说明

- 公开 repo 的 `raw.githubusercontent.com/mmm1h/clashconfig/...` 继续作为 artifact endpoint。
- 私有 Gist、Cloudflare Worker 与相关 consumer 可以继续复用现有地址。
- `rules/CN.txt` 为冻结的 legacy compatibility artifact，不再纳入主迁移目标。

## DNS 隐私策略与客户端设置

`mihomo.yaml` 使用明确的域名策略：国内域名发往阿里 IP 形式的 DoH；国外及未分类域名发往 Cloudflare / Google DoH，明确指定 `♻️ 自动选择` 代理组。节点域名和 DNS 引导解析使用国内加密 DNS，避免启动时依赖尚未可用的代理。`direct-nameserver` 同样遵循域名策略，避免 Apple、游戏、下载等直连规则把国外域名再次发给国内上游。

代理组为空时使用 `empty-fallback: REJECT`，需要 Mihomo v1.19.27 或更新版本；代理不可用时国外解析失败，不回退到国内 DNS。组里不要加入 `DIRECT`。本机验证版本为 Clash Party 2.0.3 / Mihomo v1.19.31。

首次导入需要可用节点或有效的节点缓存。如果订阅下载域名也依赖代理解析，而代理组尚未加载，可能形成启动依赖环；可先导入节点，或仅为确切的订阅服务域名配置独立引导解析策略，不要把所有未知域名改回国内 DNS。本机重启测试使用现有有效订阅缓存。

| 常见做法 | 保护范围与限制 |
| --- | --- |
| 只配置 DoH / DoT | 加密 DNS 链路；仍须明确决定是否通过代理连接上游。加密 DNS 直连会让该服务知道本机出口 IP。 |
| 国内主 DNS + 国外 fallback | 改善污染结果；过滤最终回答不能撤回已经发往国内上游的查询。本配置改为域名策略。 |
| TUN + UDP/TCP 53 劫持 + strict-route | 接管普通 DNS；Windows 严格路由可阻止其他网卡并发查询造成的泄露，需要客户端实际开启 TUN。 |
| 路由器统一接管 | OpenClash / Nikki 可配合 dnsmasq、端口重定向与防火墙覆盖局域网设备，Windows 桌面客户端不能照搬路由器设置。 |
| 浏览器 DoH 管理与 VPN 断网保护 | 自定义 DoH 可能绕过系统解析；完整断网保护还需要覆盖核心退出、其他接口和路由排除的系统策略。 |

在 Clash Party 中确认以下设置实际生效：

- 开启 TUN，开启自动路由与严格路由；DNS 劫持同时包含 `any:53` 和 `tcp://any:53`。
- 配置已经包含完整 DNS 时，可让 DNS 覆写保持关闭；检查最终运行配置中的 `dns.enable: true`，不要仅看订阅文本。
- 本机完整重启测试中，内核启动方式 `log` 出现“内核 DNS / HTTP 代理可用，但 Windows 隧道 DNS 接管未正常完成”的情况；切换为 `post-up` 后连续两次完整重启通过，未触发自动恢复。该设置属于客户端启动流程，YAML 无法替客户端设置它。
- 常见国外 DoH 域名 / IP 与 853 端口优先走代理，放在自定义直连及非标准端口规则之前。未知自定义 DoH 地址需要额外规则或浏览器管理；不要把已知地址清单视为全覆盖。

保护目标是国外及未分类域名不交给国内 DNS，普通 DNS 不从物理网卡明文发出。国内域名、节点域名及引导解析仍会被所选国内 DoH 服务看到。`ipv6: false` 不等于关闭 Windows 网卡 IPv6；核心停止、路由排除、其他 VPN 与程序自行实现的 DNS 仍需要单独验证，不能仅凭 YAML 承诺零泄露。

2026-10-06 本机验证：UDP/TCP 与 A/AAAA/TXT/HTTPS 共 36 项 DNS 查询通过；物理网卡抓包未观察到 53 端口 DNS 或直连国外配置上游，隧道网卡能观察到被接管的 DNS；空代理组和故障代理均让国外查询失败，没有转发给国内 DNS。抓包结论仅适用于验证时的网络和测试流量。

参考资料：

- [Mihomo DNS 配置](https://wiki.metacubex.one/config/dns/)、[TUN 配置](https://wiki.metacubex.one/config/inbound/tun/)、[代理组空组回退](https://wiki.metacubex.one/config/proxy-groups/#empty-fallback)。
- [JackieWuu/mihomo_config](https://github.com/JackieWuu/mihomo_config)：参考域名分流与加密引导解析；仍须核对代理组是否包含直连。
- [Custom OpenClash Rules](https://github.com/Aethersailor/Custom_OpenClash_Rules)：路由器侧 DNS 接管实践。
- [sing-box HTTPS DNS](https://sing-box.sagernet.org/configuration/dns/server/https/)：解析器选择与连接上游的出口独立配置。
- [Firefox DoH 管理策略](https://firefox-admin-docs.mozilla.org/reference/policies/dnsoverhttps/)、[Chromium DoH](https://www.chromium.org/developers/dns-over-https/)：浏览器解析与回退行为。
