# route_commands.py - 路由表 UDP 命令处理
import config
import route
from route import format_route_table


def handle_route_command(parts):
    """
    处理 route 相关命令
    格式: route,list
          route,set_interval,<秒数>
    """
    if len(parts) < 2:
        return "错误: 缺少子命令，可用: list, set_interval"

    subcmd = parts[1].strip().lower()

    if subcmd == "list":
        return format_route_table()

    elif subcmd == "set_interval":
        if len(parts) < 3:
            return "错误: 缺少间隔秒数"
        try:
            interval = int(parts[2])
            if interval < 5:
                return "错误: 间隔至少为5秒"
            # 更新全局变量
            config.g_route_advertise_interval = interval
            # 持久化
            sys_cfg = config.load_system_config()
            sys_cfg["route_advertise_interval"] = interval
            if config.save_system_config(sys_cfg):
                return f"路由通告广播间隔已设为 {interval} 秒"
            else:
                return "保存配置失败"
        except ValueError:
            return "错误: 间隔必须是整数"

    else:
        return f"未知 route 子命令: {subcmd}，可用: list, set_interval"