# nickname_commands.py - 配置和系统 UDP 命令
import config
import machine
import util
from neighbor import update_self_nickname


def handle_nickname_command(parts):
    """
    处理 nickname 命令
    格式: nickname,set,<新昵称>
    """
    if len(parts) < 3 or parts[1].strip().lower() != "set":
        return "错误: 格式应为 nickname,set,<新昵称>"

    new_nick = parts[2].strip()
    if not new_nick:
        return "错误: 昵称不能为空"

    # 更新全局变量
    config.g_device_nickname = new_nick
    # 持久化
    sys_cfg = config.load_system_config()
    sys_cfg["device_nickname"] = new_nick
    if not config.save_system_config(sys_cfg):
        return "保存配置失败"
    # 处理冲突并更新昵称表
    update_self_nickname()
    return f"昵称已更新为 '{new_nick}'"