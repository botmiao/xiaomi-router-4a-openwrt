# AGENTS.md — xiaomi-router-4a-openwrt

本目录既是小米路由器 4A 千兆版刷 OpenWrt 的工作区，也是公开仓库
`github.com/botmiao/xiaomi-router-4a-openwrt` 的工作副本（2026-08-20
发布）。入库内容已全部脱敏：脚本密码一律通过环境变量 `ROUTER_PWD`
（小米后台管理密码）/ `RSSH_PASSWORD`（OpenWrt root 密码）传入，
本文件不记录任何真实密码、SSID 或设备序列号。

`.gitignore` 采用**白名单模式**：默认忽略一切，仅显式放行的文件入库。
**永远不要放行**：`backup/`（原厂全片备份、uci 快照，含隐私；2026-08-20
用户决定不做云端异地备份，此文件**全球仅本地一份**，绝不入库）、各过程
日志/探针脚本；也不要把真实凭据写回任何入库文件。firmware/ 下 4 个实际
使用的固件已按用户决定入库（防直链失效的备份）。

## Agent 协作须知

- 刷机已全部完成（2026-08-20）：路由器运行 OpenWrt 25.12.5，
  管理地址 http://192.168.1.1。
- 当前工作模式（2026-08-20 起）：无线中继/client（STA）——radio1(5GHz)
  连上游 5G 热点（SSID 已脱敏），wwan DHCP（上游 172.16.0.0/24，与 LAN
  不冲突），PC 走网线接 LAN 上网；两个默认 AP 已禁用，**管理只能走网线**。
  改动前的 uci 快照保存在本地 `backup/uci_before_wwan_20260820.txt`（未入库）。
  非交互 SSH 用 `tools/rssh.py`（需先设 `RSSH_PASSWORD`）。
- 排障备忘：验证"有线上网"必须强制走有线（`ping -S 192.168.1.182` /
  `curl --interface`），PC 自带 WLAN 会掩盖有线故障；改防火墙 uci 后需
  `/etc/init.d/firewall restart` 才生成 nft 规则（首次配置漏了这步导致
  转发被 REJECT，2026-08-20 已修复并验证）。
- **`backup/fullflash_backup.bin` 是唯一原厂全片备份，只读保护、禁止移动/
  改名/删除**。任何涉及"恢复小米系统"的请求都以它为源；Factory/EEPROM、
  Bdata 等设备唯一分区只存在于这一份文件里（云端私有备份方案已于
  2026-08-20 放弃并删除），**删除＝永久丢失**。
- `tools/` 下 9 个脚本（final14/15/19/23/25、exploit_local.py、rssh.py、
  两个 ps1）已脱敏公开发布，即仓库现状；其余过程迭代脚本、探针与日志
  已于 2026-08-20 清理删除。
- `firmware/rootfs_out/`（小米 2.28.69 固件解包）与 v2 备用固件已于
  2026-08-20 清理；如需逆向可从 `firmware/miwifi_r4a_2.28.69.bin` 重新解包。
- 详细过程与分区偏移见 README.md。

## 环境备忘

- Windows 11 + Git Bash + uv（fnm 管理 npm）；代理 127.0.0.1:11224（按需开启）
- 该网络下 GitHub/HTTPS 常不可达：固件用 USTC 镜像（HTTP），
  GitHub 文本用 jsDelivr（`https://cdn.jsdelivr.net/gh/<user>/<repo>@<branch>/<path>`，
  注意分支名 master/main 区分）
- 路由器在 192.168.31.x 时会 DNS 劫持（断网认证机制），诊断网络问题先想到这一点
