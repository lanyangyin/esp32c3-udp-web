import json

import config


# =============================================================================
# CONFIG 命令处理函数（内部使用）
# =============================================================================

def handle_config_command(parts):
    if len(parts) < 2:
        return "错误: 缺少子命令"

    subcmd = parts[1].strip().lower()

    try:
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

        elif subcmd == "reload":
            config.load_system_config()
            config.load_wifi_config()
            config.load_control_config()
            return "配置已重新加载（系统、WiFi、控制），但部分参数需重启才能完全生效"

        elif subcmd == "save":
            return "配置已保存，即将重启..."

        elif subcmd == "reset":
            files_to_delete = [
                config.SYSTEM_CONFIG_FILE,
                config.WIFI_CONFIG_FILE,
                config.CONTROL_CONFIG_FILE,
                config.NEIGHBORS_FILE,
                config.ROUTE_TABLE_FILE,
                config.NICKNAMES_FILE,
                config.SERVO_CONFIG_FILE,
                config.IR_CONFIG_FILE,
                config.NEIGHBOR_CONFIG_FILE,   # 新增
                config.ROUTE_CONFIG_FILE,      # 新增
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

        elif subcmd == "help":
            return "配置模块命令:\n  config,get - 查看所有配置\n  config,reload - 重新加载配置\n  config,save - 保存并重启\n  config,reset - 恢复出厂设置"
        else:
            return f"未知 config 子命令: {subcmd}，可用: get, reload, save, reset, help"
    except Exception as e:
        return f"config 命令执行异常: {e}"