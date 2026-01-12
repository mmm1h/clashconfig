# rules 目录说明

本目录存放自定义 Clash/Mihomo 规则列表，格式为 Clash classical text，一行一条规则。

## 文件说明
- AI.list：AI 相关站点/服务的规则。
- CN.txt：用于 iKuai 的自定义运营商 IP 分流，内容为国内 IP。
- Direct.list：直连规则。
- GameDownload.list：游戏下载/更新相关规则。
- JP.list：日本相关规则。
- Rules.list：通用补充规则。
- US.list：美国相关规则。

## 格式约定
- 规则关键字示例：DOMAIN、DOMAIN-SUFFIX、DOMAIN-KEYWORD、IP-CIDR、IP-CIDR6（可选 ,no-resolve）。
- 每行只写一条规则，避免空行和多余空格。
