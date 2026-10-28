# Quantumult X 维护说明

`../QuantumultX.conf` 面向 iOS 商店最新版，继续由现有 Actions 注入两个订阅 URL 和原 MITM 证书后发布到私有 Gist。公开配置中的占位符不能直接用作节点订阅，不另建发布流程。

## 策略与使用方式

| 场景 / 策略 | 当前设置 |
| --- | --- |
| `派大星`、`wifi2` | `all_direct`，代理与 AI 出口交给家庭路由器 |
| 蜂窝及其他 Wi-Fi | `filter`，由 QuanX 分流 |
| `🤖 AI节点` | 手动选择具体节点，收录 DediOne、Lightsail、xiaohai 等候选；不引用自动组 |
| `♻️ 自动选择` | 香港和 xiaohai 候选，排除 4x，配置为每 30 秒检测，`alive-checking=true` |
| `🔙 全节点故障转移` | 原生 `available`，按订阅候选顺序找可用节点，排除 4x 及明显的订阅提示项 |
| 地区组 | 保留手动选择；名称与 Mihomo 对齐，DediOne 在美国候选，明确标注 JP 的 Lightsail 不混入新加坡 |

首次导入时，AI 组默认 `REJECT`，需要手动选择具体节点，例如订阅里已有的 `Xiaohai-HK` 或 `Lightsail-SG`。默认拒绝用于避免空候选时隐式直连；不要将 AI 改选普通自动组。`Xiaohai-HK` 仅按名称收录，本次没有验证实际出口国家。

`available` 与 Mihomo 的香港 → 日本 → 新加坡等地区回退链不同，这里不承诺相同顺序。自动测速的配置周期为 30 秒，全局检测超时为 3000 毫秒；实际恢复还受 iOS 调度、检测结果和应用重试影响。已有连接需要重建，不保证无缝迁移。更频繁的检测会增加后台请求与电量消耗。

已移除“节点选择”和“游戏专用”的相互引用，避免选出循环路径。普通代理、媒体、游戏和漏网之鱼默认提供故障转移选项；更新前的客户端选择可能继续恢复，导入后应检查一次。

## DNS 与 AI 边界

家中两个 SSID 使用 `server = /*/192.168.9.20, included_ssids=...`，通过特定域名绑定覆盖通用 DoH，把解析交给现有 AdGuard / PaoPaoDNS。此时是全直连模式，手机上的 AI 组不控制最终出口，需要由家中 Mihomo 保证 AI 路径。

其他网络关闭系统 DNS 和 AAAA 回答，国内直连及节点引导解析使用阿里两个 IP 地址的 DoH。AI 域名规则位于广告、直连及服务大类之前；命中代理的域名交给节点远端解析。本配置没有套用 Mihomo 的 `#🤖 AI节点` DNS 参数，也不声称 QuanX 内置 DoH 能按该语法选择策略组。

所有远程分流显式设置 `inserted-resource=true`，按配置顺序置于本地兜底前。本地 `host-keyword, ., 🐟 漏网之鱼` 负责未匹配域名，避免为检查 `GEOIP,CN` 先执行本地解析；代价是未收录的国内域名可能走代理。`.cn`、局域网域名及已有国内清单继续直连，纯 IP 请求保留地址规则和 GeoIP 判断。已移除 `2000::/3` 全直连，避免公网 IPv6 一概绕过策略。

这是配置预期与静态检查结果，不是 iOS 上的零 DNS 泄露证明。应用自带解析、DNS 排除域名及家中的外层 DNS 路径仍需实机检查。

## 分流与重写维护

- Apple 国内域名、国内标记和更新服务直连，其余 Apple 服务走节点选择；源为 MetaCubeX 的 `classical` 文本，通过现有资源解析器转换。
- 国内游戏与下载优先直连；`GameDownload.list` 补充 `steamcontent.com`、`xboxlive.com`、`playstation.net`，与 Mihomo 既有显式直连规则一致，其余游戏仍交游戏组。
- 保留 BoxJS、Sub-Store、墨鱼专属 VIP、TestFlight 以及已有有效的去广告模块；Sub-Store 改用项目当前组织的配置地址。MITM 证书占位符、证书校验和原本的本地主机名设置保留。
- STUN 不再全局丢弃，按分流规则和节点 UDP 能力处理。`fallback_udp_policy=reject` 继续拒绝不支持 UDP 的代理连接，不设直连回退。
- 12306 和高德的三个指定广告主机由 `rules/QXRewriteDirect.list` 提前放行，供响应重写处理。它只用于 QuanX，不加入 Mihomo；不要扩大到整个广告域名后缀。

2026-10-29 核对的远程资源调整：

| 原内容 | 处理 |
| --- | --- |
| `ddgksf2013.top` 的抓取结果 | 普通网页读取取得首页，用户确认该域名按请求头防抓取；不能据此判定模块失效。墨鱼去开屏保持启用，其余单应用模块按下述方案整理 |
| 知乎 | 保留已有 blackmatrix7 `zheye`，去掉重复模块 |
| B 站 | 换用 app2smile 原生 `bilibili-qx.conf` |
| 小红书、百度网盘、中国广电 | 换用 fmz200 的对应单应用拆分模块，不引入整份综合重写 |
| 墨鱼去开屏 2.0 | 保持官方 `StartUpAds.conf` 地址并启用，由 QuanX 下载；抓取检测需使用适当客户端请求头，本次未验证其规则正文及与单应用模块的重叠 |
| 两套贴吧响应处理 | app2smile 保持启用，JQ 版保留为禁用备用项 |
| As-Lucky 广告列表 | 移除叠加订阅；本次正文约 11 MB / 29 万行，并含 `404: Not Found,REJECT` 错误行。保留本仓库合并广告源和 NobyDa |
| `Proxy+.list` | 移除：正文只剩 `GEOIP,GOOGLE`，不适合作为 QuanX 的通用代理规则 |
| Google.cn 重定向 | 保留远程 General 模块，删除重复的本地重写 |

平时优先改主配置和现有规则源，无需新增定时脚本。`QXRewriteDirect.list` 是三条普通域名规则；仅当相关重写需要额外直连入口时维护。

## 验证与首次应用

本次完成其余 55 个启用资源的正文检查（本仓库资源按本地待发布版本核对，其余使用已获取的 GitHub 正文）、策略及规则引用、依赖无环、资源标签唯一、正则筛选、占位符和 18 个代表域名的静态顺序检查。启用的墨鱼去开屏 2.0 未取得规则正文，不计入这 55 项正文检查。

共享分流中还有 18 条仅桌面端适用的进程规则、4 条复杂游戏域名正则；按本次读取的资源解析器实现，这些会被忽略，不会自动扩大成宽泛匹配。对应游戏 CDN 可能落到其他已有规则或普通代理，不能把 Mihomo 的规则覆盖范围等同于 QuanX。

尚未执行 iOS 导入、资源解析器实际转换、真实节点测速、物理 DNS 抓包和逐个应用回归；不能用静态检查替代这些验证。

发布后首次更新：

1. 等待现有 Actions 成功更新私有 Gist，再刷新主配置及远程资源；Actions 额度不足时，GitHub 文件更新不代表私有 Gist 已同步。本次新增的 `QXRewriteDirect.list` 也必须随仓库发布。
2. 在 AI 组明确选择一个具体节点，并检查地区组改名后的选择。保留已有证书及信任设置，不重新生成证书。
3. 在蜂窝 / 其他 Wi-Fi 下检查 Claude、ChatGPT 连接记录命中 AI，并确认对应域名没有本地 DNS 查询；再在家中确认 DNS 送到 `.9.20`、最终 AI 出口由路由器控制。
4. 检查 12306、高德、微信、B 站、小红书、BoxJS、Sub-Store 和常用语音功能；重写源能下载不代表当前应用版本仍兼容。

参考：[Quantumult X 官方配置示例](https://github.com/crossutility/Quantumult-X/blob/master/sample.conf)、[现有资源解析器](https://github.com/KOP-XIAO/QuantumultX/blob/master/Scripts/resource-parser.js)、[墨鱼作者主页](https://github.com/ddgksf2013/ddgksf2013)、[app2smile](https://github.com/app2smile/rules)、[fmz200 单应用规则](https://github.com/fmz200/wool_scripts/tree/main/QuantumultX/rewrite/split)。
