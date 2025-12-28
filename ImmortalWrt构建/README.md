# ImmortalWrt 构建与 ESXi 部署（未完待续）

记录 ImmortalWrt 镜像构建、转换与 ESXi 部署流程，包含镜像扩容。

## 入口

- 固件构建网站：https://firmware-selector.immortalwrt.org/

## 准备

- 自定义软件包：`packages.list`
- UCI 脚本：`uci-defaults.sh`
- 工具：StarWind V2V Converter（`.img` → `.vmdk`）、ESXi 7/8

## 构建与转换

1. 在固件选择器中选择 `COMBINED-EFI (SQUASHFS)` 并下载。
2. 使用 StarWind V2V Converter 将镜像从 `.img` 转换为 `.vmdk`：
   - 选择 local img 文件
   - 选择 local file
   - 选择 vmdk
   - 选择 ESXi Server image
   - 选择 ESXi Pre-allocated image
3. 运行 convert，上传生成的 `.vmdk` 到 ESXi 数据存储。

## ESXi 创建虚拟机

1. 创建/注册虚拟机 → 创建新虚拟机。
2. 基本信息：
   - 名称：ImmortalWrt
   - 兼容性：ESXi 7.0/8.0（按版本选择）
   - 客户机操作系统：Linux
   - 客户机操作系统版本：Other 5.x or later Linux (64-bit)
3. 硬件自定义：
   - CPU：建议 4 核
   - 内存：建议 1 GB 或 2 GB
   - 硬盘 1：删除（点击 X）
   - 网络适配器1：VMXNET
   - 网络适配器2：VMXNET
   - CD/DVD：删除
4. 添加硬盘：
   - 添加硬盘 → 现有硬盘
   - 选择上传的 `.vmdk` 文件
   - 完成后关闭虚拟机选项，再次编辑以修改硬盘容量（可选）

## 虚拟机选项（VM Options）

- 展开 引导选项 (Boot Options)。
- 固件 (Firmware)：必须选择 EFI（镜像名包含 combined-efi）。
- 若不选 EFI，开机会找不到引导盘。
- 取消勾选为此虚拟机启用 UEFI 安全引导（关键）。

## 镜像扩容（套娃）

- 适用：需要扩大镜像容量（示例为 +2GB）。
- 环境：任意 Linux/OpenWrt，空余容量需大于扩容目标；确保已安装 `parted`、`gzip`。
- 建议在转换为 `.vmdk` 之前完成扩容，避免重复转换。

```bash
# 解压缩镜像文件
gzip -kd immortalwrt.img.gz

# 在镜像末尾填充 1GB 空数据（count=1000 表示 +1GB）
dd if=/dev/zero bs=1M count=1000 >> immortalwrt.img

# 使用 parted 调整分区，让新增空间生效
parted immortalwrt.img

# 出现提示时输入 OK、Fix
Error: The backup GPT table is corrupt, but the primary appears OK, so that will be used.
OK
Warning: Not all of the space available to /root/immortalwrt.img appears to be used, you can fix the GPT to use all of the space (an extra 2048030 blocks) or continue with the current
setting?
Fix/Ignore? Fix

# 查看分区情况
print
# 调整分区大小（将第 2 个分区扩展至 100%）
resizepart 2 100%
# 查看是否扩展成功
print
# 退出分区工具
quit
```

扩容后的镜像再转换/导入 ESXi 使用。

## 后续步骤

- 迁移物料：
   - root目录下：
      - .ssh文件夹（便于sshpass连接）
      - .bash_history
      - .wget-hsts
   - openclash文件夹（内核、配置）
   - HomePage验证：
      - /usr/share/rpcd/acl.d/homepage.json
      - /etc/config/rpcd
   - etc/config/* （看实际情况）
   - etc/openclash（内核、配置）