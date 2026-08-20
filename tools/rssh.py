#!/usr/bin/env python3
"""对 OpenWrt 路由器（默认 192.168.1.1）非交互执行命令（刷机后配置用）。

用法: RSSH_PASSWORD=你的root密码 uv run --with paramiko rssh.py "uci show wireless"
环境变量：RSSH_HOST 目标地址（默认 192.168.1.1）；
          RSSH_PASSWORD root 密码，多个候选用英文逗号分隔。
"""
import os
import sys

import paramiko

HOST = os.environ.get("RSSH_HOST", "192.168.1.1")
USER = "root"
PASSWORDS = [p for p in os.environ.get("RSSH_PASSWORD", "").split(",") if p]

if not PASSWORDS:
    raise SystemExit("请先设置环境变量 RSSH_PASSWORD（root 密码，多个候选用逗号分隔）")


def run(cmd: str, timeout: int = 60) -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    last_err: Exception | None = None
    for pw in PASSWORDS:
        try:
            client.connect(HOST, username=USER, password=pw,
                           look_for_keys=False, allow_agent=False, timeout=8)
            break
        except paramiko.AuthenticationException as e:
            last_err = e
            print(f"[auth failed with {pw!r}]")
        else:
            print(f"[auth ok with {pw!r}]")
            break
    else:
        raise SystemExit(f"all passwords rejected: {last_err}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out, end="")
    if err:
        print("[stderr]", err, end="", file=sys.stderr)
    client.close()
    return rc


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
