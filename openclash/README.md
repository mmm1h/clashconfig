# OpenClash 订阅覆写

主配置继续订阅原来的 `mihomo.yaml` / 私有 Gist；此模块只适配 OpenClash，不包含私有订阅、节点或密码。DNS 与嗅探从主 YAML 自动生成，DNS 监听地址保留设备值，不需要维护第二份策略。

模块订阅地址：

```text
https://raw.githubusercontent.com/mmm1h/clashconfig/main/openclash/overwrite.conf
```

## 平时修改哪里

| 要修改的内容 | 编辑文件 |
| --- | --- |
| DNS、AI、代理组、分流、嗅探、共用 TUN 排除网段 | 根目录 `mihomo.yaml` |
| OpenClash 专用开关、资源更新时间 | `openclash/overwrite.template.conf` |
| 只供 OpenClash 使用的额外 IPv4 绕行网段 | `openclash/bypass_extra_ipv4.list` |

`overwrite.conf` 和 `bypass_ipv4.list` 自动生成，不手工编辑。相关源文件推送后，`Generate OpenClash Subscription Module` Actions 自动更新它们；不需要修改 Python 生成器。

普通策略修改后更新主配置订阅；OpenClash 适配修改后更新覆写模块订阅，然后重新应用配置或重启插件。生成动作完成后再刷新订阅，避免取到旧产物。

## 一次性安装

1. 在覆写模块页面添加 HTTP 订阅，填入上面的地址并启用。
2. 关联实际使用的主配置。当前路由器为 `/etc/openclash/config/gist_github.yaml`；不要关联到所有无关配置。
3. 首次切换前，把 `bypass_ipv4.list` 放入 `/etc/openclash/custom/openclash_custom_localnetwork_ipv4.list`，作为启动缓存。
4. 备份并停用旧 `openclash_custom_overwrite.sh`，再应用配置。旧脚本在模块之后执行，继续保留会覆盖模块的修改。
5. 检查最终运行配置的 AI DNS、嗅探、TUN 及原生防火墙绕行。

端口、控制接口、密码、面板、TUN 启停和网络栈继续由设备自身设置管理。模块让 OpenClash 独立管理路由，不启用 Mihomo 的第二套自动路由。

当前 OpenClash 会把 `#DIRECT` DNS 也视为代理解析器，并补入明文引导 DNS；共享 YAML 锚点会把变更传播到其他列表。模块在插件处理后按主 YAML 恢复 DNS，清除主配置没有的 fallback / 直连解析覆盖，防止这些隐式修改改变 AI 解析路径。

## 绕行列表的更新

共用 YAML 的固定 IPv4 排除网段与 `bypass_extra_ipv4.list` 合并，生成原生防火墙需要的列表；国内 IP 绕行继续由 OpenClash 的 `CHINA_IP_ROUTE=1` 管理。

模块使用 `DOWNLOAD_FILE` 的 `force=false`：有本地缓存时，每次启动不下载资源。插件单独建立每天本地时间 **04:17** 的资源更新任务，下载失败保留旧列表且不重启；HTTP 304 不重启，返回新版本时重启以重建防火墙。模块订阅本身默认不自动重启。

因此，修改绕行网段后仅刷新主模块，已有列表不会立即被替换；它在下一次资源更新时生效。若要立即生效，可在 OpenClash 的「本地 IPv4 网络绕过列表」中粘贴最新 `bypass_ipv4.list` 并应用，无需编辑脚本。专用补充地址请写回仓库的 `bypass_extra_ipv4.list`，否则下次资源更新会覆盖仅在界面添加的内容。

首次安装必须准备有效缓存；若列表丢失，原生模块会尝试下载，失败时可能跳过该模块。本方案不修改 OpenClash 自身的下载器。

## 本地生成与检查

```bash
pip install -r openclash/requirements.txt
python -B scripts/generate_openclash_overwrite.py
python -B scripts/generate_openclash_overwrite.py --check
python -B -m unittest discover -s tests -p 'test_generate_openclash_overwrite.py'
```

生成器拒绝非法网段、覆盖 Fake-IP 的绕行范围，以及会被 OpenClash 展开为环境变量的 `$` 字符；验证失败时保留已有产物。IPv6 排除不写入这份 IPv4 列表。
