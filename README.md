# 小米路由器 4A 千兆版（R4A V1）刷 OpenWrt 实战记录

刷机日期：2026-08-20，结果：✅ OpenWrt 25.12.5 正式版稳定运行。

本仓库公开完整的漏洞利用脚本、刷机流程与踩坑记录，供同为
**R4A 千兆版 V1 + MiWiFi 2.28.x** 的用户参考。

> ⚠️ **风险提示**：刷机可能变砖、失去保修。请务必先按本文完成
> **全片备份**再动闪存；一切操作风险自负。本文仅出于学习研究目的。

## 适用范围

- 型号：小米路由器 4A **千兆版**，硬件 **V1**（16MB SPI NOR 闪存，128MB RAM）
- 原厂固件：MiWiFi 2.28.x（本人在 2.28.91 → 2.28.62 → 2.28.69 上验证）
- **不适用**：4A 千兆版 V2（配额不同，需用 v2 固件，本仓库未验证）

## 原理：为什么原版 OpenWRTInvasion 在 2.28.x 上失败

2.28.x 固件的 `c_upload`（配置备份上传）接口强制校验"配置备份"格式，
普通 tar.gz 一律报 1629 解压失败，原版 OpenWRTInvasion 的上传链路走不通。
本仓库的变体思路：

1. 构造"合法备份骨架 + 夹带 `speedtest_urls.xml`"的混合包上传 `c_upload`
   （`tools/backup_unpack/cfg_backup.{des,mbu}` 即合法骨架，上传文件名须为
   小米备份时间戳格式 `YYYY-MM-DD--HH MM SS.tar.gz`）
2. 调用 netspeed API 触发网速测试 → 固件读取 `/tmp/speedtest_urls.xml`
   → URL 被拼进 shell（CVE-2019-18370 命令注入，注入点在
   `/usr/bin/download_speedtest`）
3. 注入命令约束：XML 属性内禁止 `&`、`<`、`"`（会被拒落地）；
   `;` `|` `>` `'` 合法
4. 关键限制：测速 10 秒后 `done()` 发 SIGINT 杀全进程树 → 长任务（mtd）
   必须用 `( trap '' INT TERM HUP PIPE; cmd > log )` 包裹
   （SIG_IGN 会遗传给子进程，不怕被杀）
5. 刷机命令：PC 起临时 HTTP 服务，让路由器 `busybox wget` 拉固件到
   `/tmp/fw.bin`，再 `mtd -r write /tmp/fw.bin OS1`

## 仓库结构

```
README.md
firmware/           刷机实际使用的 4 个固件（防直链失效，随仓库备份）
  openwrt-25.12.5-ramips-mt7621-xiaomi_mi-router-4a-gigabit-initramfs-kernel.bin
  openwrt-25.12.5-ramips-mt7621-xiaomi_mi-router-4a-gigabit-squashfs-sysupgrade.bin
  miwifi_r4a_2.28.62.bin / miwifi_r4a_2.28.69.bin
tools/
  exploit_local.py    通用注入框架（level A-F，A/B/C 需 OpenWRTInvasion 的
                      busybox/dropbear 文件；E/F 即"备份骨架夹带"路线）
  final14.py          诊断外传（/proc/mtd、mount、df 经 telnet 回传验证链路）
  final15_backup.py   全片备份（cat mtd 分区 | base64 | telnet 回传）
  final19_flash.py    一体化刷写：PC 起 :9999 HTTP 服务 → 路由器 wget
                      initramfs 到 /tmp/fw.bin → trap 包裹 mtd 刷写重启
  final23_shell.py    反弹 shell 方式刷写（交互式，备用）
  final25_flash.py    最终实用版：fw.bin 已在 /tmp 时直接刷写并回传日志
  rssh.py             刷机后非交互 SSH 辅助（uv + paramiko）
  setup_lan_static.ps1  Windows：有线网卡设静态 IP（无网关）脚本
  set_dhcp.ps1        Windows：有线网卡恢复 DHCP 脚本
  backup_unpack/      合法配置备份骨架（cfg_backup.des / cfg_backup.mbu）
  OpenWRTInvasion-master/speedtest_urls_template.xml  上游模板（vendored）
```

## 准备工作

1. **Python 环境**：Python 3.10+，`pip install requests`（或直接用
   `uv run --with requests xxx.py`）
2. **固件**：已随仓库提供（`firmware/` 下 4 个实际使用的镜像，
   `final19_flash.py` 默认读取其中的 initramfs）。SHA256 与备用直链如下
   （直链于 2026-08 逐一验证可达，下载后按表核对）：

   | 文件（firmware/ 内） | 用途 | SHA256 |
   |---|---|---|
   | `openwrt-25.12.5-...-gigabit-initramfs-kernel.bin` | 临时系统（刷入 OS1） | `01f15cd3220401ed00d23d8230aed94ec4d49dbdb98efd13a6123d58b237c375` |
   | `openwrt-25.12.5-...-gigabit-squashfs-sysupgrade.bin` | 正式固件 | `9299c6c21b0b57927fac5d4310f87b677c37b16dab10bb6fd340cd7bb145f49d` |
   | `miwifi_r4a_2.28.62.bin` | 小米降级固件 | `07d3cead22e3c4fbe98eec29de5d5bea8dad12ade931179972ee56d2ac249060` |
   | `miwifi_r4a_2.28.69.bin` | 小米固件（刷机时停留的版本） | `6010b44e7732a2e9ce59d601aba5dc661e1c30560e666a962d6e0fed662733bc` |

   - OpenWrt（官方与国内镜像同目录，任选其一）：
     `https://downloads.openwrt.org/releases/25.12.5/targets/ramips/mt7621/<文件名>`
     `https://mirrors.ustc.edu.cn/openwrt/releases/25.12.5/targets/ramips/mt7621/<文件名>`
   - 小米 2.28.62：官方 OTA CDN
     `https://cdn.cnbj1.fds.api.mi-img.com/xiaoqiang/rom/r4a/miwifi_r4a_firmware_72d65_2.28.62.bin`
     （同一文件亦由 [OpenWRTInvasion](https://github.com/acecilia/OpenWRTInvasion)
     `firmwares/stock/` 托管，GitHub 直连困难时可用 jsDelivr 中转：
     `https://cdn.jsdelivr.net/gh/acecilia/OpenWRTInvasion@master/firmwares/stock/miwifi_r4a_firmware_72d65_2.28.62.bin`）
   - 小米 2.28.69：官方 OTA CDN
     `https://cdn.cnbj1.fds.api.mi-img.com/xiaoqiang/rom/r4a/miwifi_r4a_all_cddf4_2.28.69.bin`
     （CDN 原文件名带构建号 `cddf4`，仓库内改用短名存放）
   - 更多小米历史版本：ezbox 镜像目录
     `https://mirom.ezbox.idv.tw/miwifi/R4A/roms-stable/`（内容即官方 CDN 直链）
   - V2 硬件请改用同目录 `...-gigabit-v2-*.bin`（未入库，校验和：
     initramfs `4a83ad4cfa5279c503b21d2e971f5b4b475cf65849c45f009ae7115f6495409c`，
     sysupgrade `c56e593931458ce3ba5f78d9461d837bc62b7c1a9c7e3d2162b45046aa69b8c1`）
3. **建目录**：`mkdir backup`（接收全片备份；该目录永不入库）
4. **网络准备**：PC 用网线接路由器 LAN 口，有线网卡设静态 IP
   `192.168.31.228/24` 且**不配网关**（避免抢默认路由），Windows 可直接：
   `powershell -File tools/setup_lan_static.ps1`；Linux/Mac 手动设置即可

## 刷机步骤

以下脚本都在 `tools/` 目录下运行，先设置小米后台管理密码：

```bash
export ROUTER_PWD='你的小米后台密码'        # bash
set ROUTER_PWD=你的小米后台密码             # cmd
$env:ROUTER_PWD='你的小米后台密码'          # PowerShell
```

1. **（如需）降级到 2.28.x**：小米后台手动上传 2.28.62 固件升级
2. **验证注入链路**：`python final14.py` —— 应收到 /proc/mtd、mount、df
   回传内容，确认注入与 telnet 外传均正常
3. **全片备份（最关键一步）**：`python final15_backup.py` ——
   约 1-2 分钟收完 16MB（解码后期望 ~16121856 字节），保存为
   `backup/fullflash_backup.bin`。**这是救砖与恢复小米系统的唯一依靠，
   妥善离线保存，绝不能上传到任何公开场所（内含全部隐私配置）**
4. **刷入 initramfs**：`python final19_flash.py` —— 路由器 wget 固件后
   mtd 写 OS1 并重启（2-5 分钟），期间不要断电
5. **进入 initramfs**：`powershell -File tools/set_dhcp.ps1` 让有线网卡
   重新 DHCP，浏览器打开 `http://192.168.1.1` 应见 OpenWrt 界面
   （此时是内存中的临时系统，断电即回小米）
6. **写入正式固件**：
   ```bash
   scp ../firmware/openwrt-25.12.5-ramips-mt7621-xiaomi_mi-router-4a-gigabit-squashfs-sysupgrade.bin root@192.168.1.1:/tmp/
   ssh root@192.168.1.1 sysupgrade -n /tmp/openwrt-25.12.5-*.bin
   ```
7. 重启后即为正式 OpenWrt，先用 `passwd` 设置 root 密码

## 原厂闪存分区（全片备份内偏移）

Bootloader@0x0, Config@0x30000, Bdata@0x40000,
Factory@0x50000（EEPROM，**勿动**）, crash@0x60000, cfg_bak@0x70000,
overlay@0x80000(1MB), OS1@0x180000(13MB), disk@0xE80000(1.5MB)

恢复小米系统＝把全片备份（或其中 OS1 等分区）经编程器/TTL 或
OpenWrt 下的 `mtd write` 写回。

## 刷机后配置建议

1. 换国内软件源：
   `sed -i 's|downloads.openwrt.org|mirrors.ustc.edu.cn/openwrt|g' /etc/opkg/distfeeds.conf && opkg update`
2. 中文界面：`opkg install luci-i18n-base-zh-cn`
3. 注意：16MB 闪存剩余空间有限（约 3-4MB 可写），不宜装过多插件

## 无线中继（STA/wwan）配置参考

路由器作为**无线客户端（STA，路由型 wwan）**上网，PC 网线接 LAN 口：

- radio1（5GHz，MT7612E）STA 连接上游 5G 热点（密码 psk-mixed），
  信道 auto 跟随上游（实测 VHT80、-51 dBm 稳定）
- 上游网段与 LAN 192.168.1.0/24 不冲突即可（本人上游为 172.16.0.0/24）；
  wwan 接口挂 firewall wan zone（NAT + mtu_fix）
- 两个默认 AP（default_radio0/1）均已禁用 → 路由器不广播热点，
  管理只能走网线
- ⚠️ **踩坑**：改防火墙 uci（wwan 加 zone）后仅 `wifi reload` 不够，
  **必须 `/etc/init.d/firewall restart`**，否则 nft 规则不含 phy1-sta0，
  LAN 转发被 REJECT、NAT 不生效（现象：路由器自身能 ping 通外网、
  PC 的 DNS 可用，但 PC 上不了网）。排障时务必强制走有线验证
  （`ping -S <PC的有线IP> 223.5.5.5`），避免被 PC 自身无线出口掩盖

## 其他备忘

- 小米原厂系统断外网时会 **DNS 劫持**所有域名到 192.168.31.1
  （miwifi 认证页机制），勿在其 LAN 侧挂需要正常上网的设备，
  诊断网络问题先想到这一点
- 一次性脚本运行后会在 tools/ 下产生 router_diag.txt、
  shell_session.txt 等日志，均为本地调试产物

## 致谢与参考

- [acecilia/OpenWRTInvasion](https://github.com/acecilia/OpenWRTInvasion)（GPL-3.0）：
  本仓库 `exploit_local.py` 的注入思路与其 speedtest 模板源自该项目
- [devcxl/R4AG-OpenWRT](https://github.com/devcxl/R4AG-OpenWRT)：2.28.x
  配置备份漏洞的独立实现，可对照参考
- [OpenWrt Wiki — Xiaomi Mi Router 4A Gigabit Edition](https://openwrt.org/toh/xiaomi/xiaomi_mi_router_4a_gigabit_edition)

## License

本仓库整体采用 MIT License（见 [LICENSE](LICENSE)）。其中
`tools/exploit_local.py` 与 vendored 的 `speedtest_urls_template.xml`
源自 [OpenWRTInvasion](https://github.com/acecilia/OpenWRTInvasion)
（GPL-3.0），这两个文件按上游许可以 GPL-3.0 提供。
