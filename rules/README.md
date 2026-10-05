# rules 目录说明

本目录存放自定义 Clash/Mihomo 规则列表，格式为 Clash classical text，一行一条规则。

## 文件说明
- AI.list：AI 相关站点/服务的手工规则，以及由官方 `chatgpt-voice.json` 自动生成的语音 IP 区块。更新方式见 `../scripts/README.md` 的 `update_chatgpt_voice.py`；不要手工修改 auto 区块。
- CN.txt：用于 iKuai 的自定义运营商 IP 分流，内容为国内 IP。
- Direct.list：直连规则。
- GameDownload.list：游戏下载/更新相关规则。
- Custom_Port_Direct.yaml：非 80/443 端口直连规则，供 Mihomo/Clash rule-provider 使用。
- JP.list：日本相关规则。
- Rules.list：通用补充规则。
- US.list：美国相关规则。

## 格式约定
- 规则关键字示例：DOMAIN、DOMAIN-SUFFIX、DOMAIN-KEYWORD、IP-CIDR、IP-CIDR6（可选 ,no-resolve）。
- 每行只写一条规则，避免空行和多余空格。

## Claude / Claude Code

Claude 域名优先使用 `Claude_Community` 规则提供器：直接订阅 [MetaCubeX 的 Anthropic MRS](https://github.com/MetaCubeX/meta-rules-dat/blob/meta/geo/geosite/anthropic.list)，客户端每 86400 秒拉取更新，并分流到 `🤖 AI节点`。这份规则来自持续维护的社区域名数据；[v2fly 上游](https://github.com/v2fly/domain-list-community/commits/master/data/anthropic) 在 2026-10-02 新增了 `claude.dev`，核对时 MetaCubeX 的发布记录为 2026-10-05。

`AI.list` 通过 `Custom_AI` 保留官方服务 IP、辅助服务及兼容补充项，同样使用 `🤖 AI节点`。`anthropic.com` 已覆盖 API、`statsig.anthropic.com` 和 `mcp-proxy.anthropic.com` 等子域名；`claude.com` 覆盖 `platform.claude.com` 的 OAuth 令牌交换与刷新。主 YAML 与 JS 生成器均接入上述两个规则提供器；JS 的 `🤖 AI节点` 转交现有 `🥦 OPENAI` 组选择出口。

补充清单核对日期：2026-10-06。

| 范围 | 规则目标 |
| --- | --- |
| Claude 产品及内容域名 | `claude.ai`、`anthropic.com`、`claude.com`、`claude.dev`、`claudeusercontent.com`、`claudemcpclient.com`、`claudemcpcontent.com`、`clau.de` |
| 官网 CDN | `servd-anthropic-website.b-cdn.net` |
| 功能开关、分析与遥测 | `cdn.growthbook.io`、`cdn.usefathom.com`、`http-intake.logs.us5.datadoghq.com` |
| 更新与插件元数据 | `downloads.claude.ai`（已由域名后缀规则覆盖）、`storage.googleapis.com` |
| 官方服务接入 IP | `160.79.104.0/23`、`2607:6bc0::/48`，作为直接连接 IP 时的补充 |

Google Cloud Storage 是共享服务，`storage.googleapis.com` 规则会将这个主机的所有连接交给 AI 节点；域名规则无法按存储桶路径区分 Claude 下载。Anthropic 的 `160.79.104.0/21` 是服务端发起工具调用等请求的出口范围，本清单使用官方公布的接入范围 `/23`。

来源：[MetaCubeX Anthropic 规则](https://github.com/MetaCubeX/meta-rules-dat/blob/meta/geo/geosite/anthropic.list)、[Claude Code 官方网络清单](https://code.claude.com/docs/en/network-config#network-access-requirements)、[官方 IP 地址](https://platform.claude.com/docs/en/api/ip-addresses)、[v2fly 社区 Anthropic 域名](https://github.com/v2fly/domain-list-community/blob/master/data/anthropic)、[blackmatrix7 Claude 规则](https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Clash/Claude/Claude.list)、[社区扩展规则](https://github.com/xiaolai/anthropic-claude-surge-rules-set/blob/main/domains.yaml)。`cdn.growthbook.io` 和 Datadog 的具体主机也核对过 Claude Code 2.1.220 的二进制域名字符串。ACL4SSR 的 Claude 清单核对时仅有两个基础域名；blackmatrix7 的清单有三个目标，作为辅助服务参考。

首次接入需要更新配置订阅；此后刷新 Clash 的 `Claude_Community` / `Custom_AI` 规则提供器即可生效，无需重启 TUN。第三方 API 网关不属于这些官方域名，需要按实际网关另行设置规则；这份清单覆盖网络分流，无法保证服务端的账号或地区判定结果。
