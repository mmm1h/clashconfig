# clashconfig

公开 artifact repo，用于分发 `Mihomo / Clash` 相关配置、规则与生成物。

## 定位

- 这个目录在 `network_debug` 中是 authoritative source tree。
- 这个目录按主仓普通目录管理；当前维护模型不使用 `git subtree` / `submodule`。
- 同名公开仓库 `mmm1h/clashconfig` 只作为 artifact repo / distribution shell 使用。
- 日常编辑只应发生在私有主仓 `network_debug`，不要在公开 repo 直接手改。
- 现网可继续使用现有 raw / Gist / Worker 地址；这些地址现在被视为“公开分发面”，而不是源码真源。

## 上游参考

- ACL4SSR 原始配置参考：
  `https://github.com/ACL4SSR/ACL4SSR/blob/master/Clash/config/ACL4SSR_Online_Full.ini`

## 分发说明

- 公开 repo 的 `raw.githubusercontent.com/mmm1h/clashconfig/...` 继续作为 artifact endpoint。
- 私有 Gist、Cloudflare Worker 与相关 consumer 可以继续复用现有地址。
- `rules/CN.txt` 为冻结的 legacy compatibility artifact，不再纳入主迁移目标。
