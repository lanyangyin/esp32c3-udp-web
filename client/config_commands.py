import json

import config


# =============================================================================
# CONFIG 命令处理函数（内部使用）
# =============================================================================

def handle_config_command(parts):
    """
    处理 config 相关命令，返回响应字符串。
    parts: 已按逗号分割的列表，如 ['config', 'get']
    """
    if len(parts) < 2:
        return "错误: 缺少子命令"

    subcmd = parts[1].strip().lower()

    try:
        # ---------- config,get ----------
        if subcmd == "get":
            # 收集所有配置信息
            sys_cfg = {}
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                pass
            wifi_cfg = {"ssid": config.g_sta_ssid, "password": config.g_sta_password}
            ctrl_cfg = {"commands": config.g_commands}
            full = {
                "system": sys_cfg,
                "wifi": wifi_cfg,
                "control": ctrl_cfg
            }
            return "当前所有配置:\n" + json.dumps(full, indent=2)

        # ---------- config,set_sta,<SSID>,<密码> ----------
        elif subcmd == "set_sta":
            if len(parts) < 4:
                return "错误: 缺少参数，格式: config,set_sta,<SSID>,<密码>"
            ssid = parts[2].strip()
            password = parts[3].strip() if len(parts) > 3 else ""
            config.save_wifi_config(ssid, password)
            return f"STA 配置已更新: SSID='{ssid}'，需重启生效"

        # ---------- config,set_ap_ssid,<新SSID> ----------
        elif subcmd == "set_ap_ssid":
            if len(parts) < 3:
                return "错误: 缺少 SSID 参数，格式: config,set_ap_ssid,<新SSID>"
            new_ssid = parts[2].strip()
            if not new_ssid:
                return "错误: SSID 不能为空"
            # 读取当前系统配置
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                sys_cfg = {}
            sys_cfg["ap_ssid"] = new_ssid
            config.save_system_config(sys_cfg)
            config.g_ap_ssid = new_ssid  # 更新全局变量
            return f"AP SSID 已更新为 '{new_ssid}'，需重启生效"

        # ---------- config,set_ap_password,<新密码> ----------
        elif subcmd == "set_ap_password":
            if len(parts) < 3:
                return "错误: 缺少密码参数，格式: config,set_ap_password,<新密码>"
            new_password = parts[2].strip()
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                sys_cfg = {}
            sys_cfg["ap_password"] = new_password
            config.save_system_config(sys_cfg)
            config.g_ap_password = new_password
            return f"AP 密码已更新（长度为 {len(new_password)}），需重启生效"

        # ---------- config,set_ap_ip,<IP> ----------
        elif subcmd == "set_ap_ip":
            if len(parts) < 3:
                return "错误: 缺少 IP 地址"
            ip = parts[2].strip()
            # 简单验证
            parts_ip = ip.split('.')
            if len(parts_ip) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts_ip):
                return "错误: 无效 IP 地址格式"
            # 读取当前系统配置并修改
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                sys_cfg = {}
            sys_cfg["ap_ip"] = ip
            config.save_system_config(sys_cfg)
            config.g_ap_ip = ip  # 更新全局变量
            # 重新计算广播地址
            config.g_ap_broadcast_addr = f"{'.'.join(ip.split('.')[:-1])}.255"
            return f"AP IP 已设置为 {ip}，需重启生效"

        # ---------- config,set_ap_netmask,<掩码> ----------
        elif subcmd == "set_ap_netmask":
            if len(parts) < 3:
                return "错误: 缺少子网掩码"
            mask = parts[2].strip()
            # 简单验证
            parts_mask = mask.split('.')
            if len(parts_mask) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts_mask):
                return "错误: 无效子网掩码格式"
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                sys_cfg = {}
            sys_cfg["ap_subnet"] = mask
            config.save_system_config(sys_cfg)
            config.g_ap_subnet = mask
            return f"AP 子网掩码已设置为 {mask}，需重启生效"

        # ---------- config,set_ap_gateway,<网关> ----------
        elif subcmd == "set_ap_gateway":
            if len(parts) < 3:
                return "错误: 缺少网关地址"
            gw = parts[2].strip()
            parts_gw = gw.split('.')
            if len(parts_gw) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts_gw):
                return "错误: 无效网关地址格式"
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                sys_cfg = {}
            sys_cfg["ap_ip"] = gw  # 同步更新 ap_ip
            sys_cfg["ap_gateway"] = gw  # 保留网关字段（可选）
            config.save_system_config(sys_cfg)
            config.g_ap_ip = gw
            config.g_ap_broadcast_addr = f"{'.'.join(gw.split('.')[:-1])}.255"
            return f"AP IP 和网关已同步设置为 {gw}，需重启生效"

        # ---------- config,set_broadcast_port,<端口> ----------
        elif subcmd == "set_broadcast_port":
            if len(parts) < 3:
                return "错误: 缺少端口号"
            try:
                port = int(parts[2])
                if not (1 <= port <= 65535):
                    raise ValueError
            except:
                return "错误: 端口号必须是 1~65535 的整数"
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                sys_cfg = {}
            sys_cfg["udp_broadcast_port"] = port
            config.save_system_config(sys_cfg)
            config.g_udp_broadcast_port = port
            return f"UDP 广播/回复端口已设置为 {port}，需重启生效"

        # ---------- config,set_recv_port,<端口> ----------
        elif subcmd == "set_recv_port":
            if len(parts) < 3:
                return "错误: 缺少端口号"
            try:
                port = int(parts[2])
                if not (1 <= port <= 65535):
                    raise ValueError
            except:
                return "错误: 端口号必须是 1~65535 的整数"
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                sys_cfg = {}
            sys_cfg["udp_recv_port"] = port
            config.save_system_config(sys_cfg)
            config.g_udp_recv_port = port
            return f"UDP 监听端口已设置为 {port}，需重启生效"

        # ---------- config,set_reply_port,<端口> (兼容旧命令，等同于 set_broadcast_port) ----------
        elif subcmd == "set_reply_port":
            if len(parts) < 3:
                return "错误: 缺少端口号"
            try:
                port = int(parts[2])
                if not (1 <= port <= 65535):
                    raise ValueError
            except:
                return "错误: 端口号必须是 1~65535 的整数"
            try:
                with open(config.SYSTEM_CONFIG_FILE, 'r') as f:
                    sys_cfg = json.load(f)
            except:
                sys_cfg = {}
            sys_cfg["udp_broadcast_port"] = port  # 回复端口与广播端口一致
            config.save_system_config(sys_cfg)
            config.g_udp_broadcast_port = port
            return f"UDP 回复端口已设置为 {port}（与广播端口相同），需重启生效"

        # ---------- config,reload ----------
        elif subcmd == "reload":
            config.load_system_config()
            config.load_wifi_config()
            config.load_control_config()
            return "配置已重新加载（系统、WiFi、控制），但部分参数（如端口、IP）需重启才能完全生效"

        # ---------- config,save ----------
        elif subcmd == "save":
            # 保存当前所有配置（实际已保存，只需重启）
            return "配置已保存，即将重启..."
            # 注意：这里不能直接重启，因为发送响应后需要等待，可以发送后再重启，但为了简单，我们只返回消息，由调用方决定是否重启
            # 实际上，这个命令在控制台使用，我们可以直接返回消息，不自动重启，让用户手动重启。
            # 但原描述是 "保存当前配置到文件并重启"，所以我们可执行重启。
            # 为了实现，我们在 send_response 后调用 machine.reset，但那样会中断回复发送，所以我们在返回消息后，在调用处重启。
            # 此处只返回标识，由调用方处理。

        # ---------- config,reset ----------
        elif subcmd == "reset":
            # 删除所有配置文件（除了必要的？）并重启
            # 安全起见，删除 system-config.json, wifi-config.json, control_config.json, neighbors.json, route_table.json, nicknames.json, servo-config.json, ir05t-data-config.json
            files_to_delete = [
                config.SYSTEM_CONFIG_FILE,
                config.WIFI_CONFIG_FILE,
                config.CONTROL_CONFIG_FILE,
                config.NEIGHBORS_FILE,
                config.ROUTE_TABLE_FILE,
                config.NICKNAMES_FILE,
                config.SERVO_CONFIG_FILE,
                config.IR_DATA_FILE
            ]
            deleted = []
            for f in files_to_delete:
                try:
                    import os
                    os.remove(f)
                    deleted.append(f)
                except:
                    pass
            return f"已删除配置文件: {', '.join(deleted) if deleted else '无文件可删除'}，即将重启..."

        else:
            return f"未知 config 子命令: {subcmd}"

    except Exception as e:
        return f"config 命令执行异常: {e}"


