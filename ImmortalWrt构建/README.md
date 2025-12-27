# ImmortalWrt 构建与 ESXi 部署（未完待续）

## 入口

- 固件构建网站：https://firmware-selector.immortalwrt.org/

## 准备

- 自定义软件包：`packages.list`
- UCI 脚本：`uci-defaults.sh`

## 构建流程

1. 在固件选择器中选择 `COMBINED-EFI (SQUASHFS)` 并下载。
2. 使用 StarWind V2V Converter 将镜像从 `.img` 转换为 `.vmdk`：
   - 选择 local img 文件
   - 选择 local file
   - 选择 vmdk
   - 选择 ESXi Server image
   - 选择 ESXi Pre-allocated image
3. 运行 convert，上传生成的文件到 ESXi。

## ESXi 创建虚拟机

1. 创建/注册虚拟机 → 创建新虚拟机。
2. 基本信息：
   - 名称：ImmortalWrt
   - 兼容性：ESXi 7.0/8.0（按版本选择）
   - 客户机操作系统：Linux
   - 客户机操作系统版本：Other 5.x or later Linux (64-bit)
3. 硬件自定义：
   - CPU：建议 4 核（N5105 性能足够）
   - 内存：建议 1 GB 或 2 GB
   - 硬盘 1：删除（点击 X）
   - 网络适配器：VMXNET 3
   - CD/DVD：删除
4. 添加硬盘：
   - 添加硬盘 → 现有硬盘
   - 选择上传的 `.vmdk` 文件
   - 完成后关闭虚拟机选项，再次编辑以修改硬盘容量

## 关键操作：直接扩容

- 硬盘添加后只有默认大小（几百兆）。
- 直接在该界面修改容量，例如 10 GB（或更大）。
- 原理：EXT4/SquashFS 混合镜像，首次启动会自动识别扩展空间。

## 虚拟机选项（VM Options）

- 展开 引导选项 (Boot Options)。
- 固件 (Firmware)：必须选择 EFI（镜像名包含 combined-efi）。
- 若不选 EFI，开机会找不到引导盘。

## 后续步骤

- 预留：首次启动、网口绑定、分区/扩容检查、网络配置等。
