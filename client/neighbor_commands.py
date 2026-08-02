# neighbor_commands.py - 邻居表 UDP 命令处理
import config
import neighbor
from info_commands import get_help_info
from neighbor import format_neighbor_table


def handle_neighbor_command(parts):
    """
    处理 neighbor 相关命令
    格式: neighbor,list
          neighbor,set_interval,<秒数>
    """
    if len(parts) < 2:
        return "错误: 缺少子命令，可用: list, set_interval, help"

    subcmd = parts[1].strip().lower()

    if subcmd == "list":
        return format_neighbor_table()
    elif subcmd == "set_interval":
        if len(parts) < 3:
            return "错误: 缺少间隔秒数"
        try:
            interval = int(parts[2])
            if interval < 5:
                return "错误: 间隔至少为5秒"
            # 使用 config.py 中的函数更新
            config.update_neighbor_advertise_interval(interval)
            return f"邻居广播间隔已设为 {interval} 秒"
        except ValueError:
            return "错误: 间隔必须是整数"
    elif subcmd == "help":
        return get_help_info("neighbor")
    else:
        return f"未知 neighbor 子命令: {subcmd}，可用: list, set_interval, help"