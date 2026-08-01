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
        cmd_lines.append("\n--- 系统命令 ---")
        cmds = config.g_commands.get("system", [])
        for item in cmds:
            cmd_lines.append(f"  {item['cmd']}  - {item['desc']}")
    else:
        mod_cmds = config.g_commands.get(module, [])
        if not mod_cmds:
            return f"错误: 未知模块 '{module}'"
        cmd_lines.append(f"\n--- {module.upper()} 模块命令 ---")
        for item in mod_cmds:
            cmd_lines.append(f"  {item['cmd']}  - {item['desc']}")
    return config_info + "\n".join(cmd_lines)

def get_status_info():
    return (f"AP SSID: {config.g_ap_ssid}\n"
            f"AP IP: {config.g_ap_ip}\n"
            f"STA SSID: {config.g_sta_ssid}\n"
            f"STA IP: {config.g_sta_ip if hasattr(config, 'g_sta_ip') else 'N/A'}\n"
            f"UDP 监听端口: {config.g_udp_recv_port}\n"
            f"UDP 广播端口: {config.g_udp_broadcast_port}\n"
            f"设备昵称: {config.g_device_nickname}")

def get_memory_info():
    free = gc.mem_free()
    alloc = gc.mem_alloc()
    total = free + alloc
    return f"总内存: {total} 字节\n已用: {alloc} 字节 ({alloc/total*100:.1f}%)\n空闲: {free} 字节"