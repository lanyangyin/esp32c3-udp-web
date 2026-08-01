# info_commands.py
import gc
import config

def get_help_info(module=None, include_config=False):
    config_info = ""
    if include_config:
        config_info = f"--- 当前配置 ---\n"
        config_info += f"STA目标AP: {config.g_sta_ssid}\n"
        config_info += f"自身AP SSID: {config.g_ap_ssid}\n"
        config_info += f"UDP监听端口: {config.g_udp_recv_port}\n"
        config_info += f"UDP广播端口: {config.g_udp_broadcast_port}\n"

    cmd_lines = []
    if module is None:
        # 显示所有模块
        cmd_lines.append("可用命令模块 (输入 help 查看所有命令):")
        modules = list(config.g_commands.keys())
        # 把 system 放在最后
        if "system" in modules:
            modules.remove("system")
            modules.append("system")
        for mod in modules:
            cmds = config.g_commands.get(mod, [])
            if not cmds:
                continue
            cmd_lines.append(f"\n--- {mod.upper()} 模块命令 ---")
            for item in cmds:
                cmd_lines.append(f"  {item['cmd']}  - {item['desc']}")
        return config_info + "\n".join(cmd_lines)
    else:
        mod_cmds = config.g_commands.get(module, [])
        if not mod_cmds:
            return f"错误: 未知模块 '{module}'"
        cmd_lines.append(f"\n--- {module.upper()} 模块命令 ---")
        for item in mod_cmds:
            cmd_lines.append(f"  {item['cmd']}  - {item['desc']}")
        return config_info + "\n".join(cmd_lines)


def get_status_info():
    # 获取 STA IP
    try:
        import network
        sta = network.WLAN(network.STA_IF)
        sta_ip = sta.ifconfig()[0] if sta.isconnected() else "未连接"
    except:
        sta_ip = "N/A"

    return (f"AP SSID: {config.g_ap_ssid}\n"
            f"AP IP: {config.g_ap_ip}\n"
            f"STA SSID: {config.g_sta_ssid}\n"
            f"STA IP: {sta_ip}\n"
            f"UDP 监听端口: {config.g_udp_recv_port}\n"
            f"UDP 广播端口: {config.g_udp_broadcast_port}\n"
            f"设备昵称: {config.g_device_nickname}\n"
            f"邻居广播间隔: {config.g_neighbor_advertise_interval} 秒\n"
            f"路由通告间隔: {config.g_route_advertise_interval} 秒")


def get_memory_info():
    free = gc.mem_free()
    alloc = gc.mem_alloc()
    total = free + alloc
    return f"总内存: {total} 字节\n已用: {alloc} 字节 ({alloc/total*100:.1f}%)\n空闲: {free} 字节"