# generate_jsons.py
import json
import os

# 从原 constants.py 复制以下内容
DEFAULT_COMMANDS = {
    "commands": {
        "servo": [
            {"cmd": "servo,list", "desc": "列出所有舵机名称和引脚"},
            {"cmd": "servo,set_pin,<舵机名称>,<引脚>", "desc": "设置舵机引脚（需 reload 生效）"},
            {"cmd": "servo,delete,<舵机名称>", "desc": "删除舵机（从配置移除并释放 PWM）"},
            {"cmd": "servo,set_init_angle,<舵机名称>,<初始化角度>", "desc": "设置舵机初始化角度（需 reload 生效）"},
            {"cmd": "servo,set,<舵机名称>,<角度>", "desc": "直接设置指定舵机角度"},
            {"cmd": "servo,record,<舵机名称>,<动作组名称>,<角度1>,<角度2>,...", "desc": "录制动作组（角度列表）"},
            {"cmd": "servo,play,<舵机名称>,<动作组名称>", "desc": "执行指定动作组（每个角度间隔0.7秒）"},
            {"cmd": "servo,stop", "desc": "停止当前正在播放的舵机动作组"},
            {"cmd": "servo,delete_group,<舵机名称>,<动作组名称>", "desc": "删除指定动作组"},
            {"cmd": "servo,list_groups,<舵机名称>", "desc": "列出舵机的所有动作组"},
            {"cmd": "servo,help", "desc": "显示舵机模块的帮助信息"}
        ],
        "ir05t": [
            {"cmd": "ir05t,list_devices", "desc": "列出所有 IR 设备"},
            {"cmd": "ir05t,add,<设备名>,<tx_pin>,<rx_pin>[,<baudrate>[,<timeout>]]", "desc": "添加并初始化 IR 设备"},
            {"cmd": "ir05t,delete,<设备名>", "desc": "删除 IR 设备"},
            {"cmd": "ir05t,set_pin,<设备名>,<tx_pin>,<rx_pin>", "desc": "修改设备引脚"},
            {"cmd": "ir05t,list,<设备名>", "desc": "列出设备下所有已学习的数据"},
            {"cmd": "ir05t,get,<设备名>,<数据名>", "desc": "获取指定数据内容"},
            {"cmd": "ir05t,learn,<设备名>", "desc": "通用学习（不保存）"},
            {"cmd": "ir05t,learn_save,<设备名>,<数据名>", "desc": "学习并保存数据"},
            {"cmd": "ir05t,send,<设备名>,<数据名>", "desc": "发送已保存的数据"},
            {"cmd": "ir05t,delete_data,<设备名>,<数据名>", "desc": "删除指定数据"},
            {"cmd": "ir05t,learn_channel,<设备名>,<1~5>", "desc": "通道学习"},
            {"cmd": "ir05t,send_channel,<设备名>,<1~5>", "desc": "发送通道"},
            {"cmd": "ir05t,send_raw,<设备名>,<hex数据>", "desc": "发送原始数据"},
            {"cmd": "ir05t,set_baud,<设备名>,<波特率>", "desc": "修改波特率"},
            {"cmd": "ir05t,set_timeout,<设备名>,<毫秒>", "desc": "修改超时"},
            {"cmd": "ir05t,set_header,<设备名>,<0xA0~0xFE>", "desc": "修改帧头"},
            {"cmd": "ir05t,help", "desc": "显示 IR05T 模块的帮助信息"}
        ],
        "neighbor": [
            {"cmd": "neighbor,list", "desc": "显示当前邻居表"},
            {"cmd": "neighbor,set_interval,<秒数>", "desc": "修改邻居广播间隔（默认120秒）"},
            {"cmd": "neighbor,help", "desc": "显示邻居模块的帮助信息"}
        ],
        "route": [
            {"cmd": "route,list", "desc": "显示当前路由表"},
            {"cmd": "route,set_interval,<秒数>", "desc": "修改路由通告间隔（默认120秒）"},
            {"cmd": "route,help", "desc": "显示路由模块的帮助信息"}
        ],
        "nickname": [
            {"cmd": "nickname,set,<新昵称>", "desc": "修改设备昵称（立即生效）"},
            {"cmd": "nickname,help", "desc": "显示昵称模块的帮助信息"}
        ],
        "config": [
            {"cmd": "config,get", "desc": "获取当前所有配置（JSON格式）"},
            {"cmd": "config,save", "desc": "保存当前配置到文件并重启"},
            {"cmd": "config,reload", "desc": "重新加载配置文件（不重启）"},
            {"cmd": "config,reset", "desc": "删除配置文件并重启（恢复出厂设置）"},
            {"cmd": "config,help", "desc": "显示配置模块的帮助信息"}
        ],
        "ap": [
            {"cmd": "ap,set_ssid,<新SSID>", "desc": "修改 AP 的 SSID（需重启生效）"},
            {"cmd": "ap,set_password,<新密码>", "desc": "修改 AP 的 Wi-Fi 密码（需重启生效）"},
            {"cmd": "ap,set_ip,<IP>", "desc": "修改 AP IP 地址（需 reload 生效）"},
            {"cmd": "ap,set_netmask,<掩码>", "desc": "修改 AP 子网掩码（需 reload 生效）"},
            {"cmd": "ap,set_gateway,<网关>", "desc": "修改 AP 网关（需 reload 生效）"},
            {"cmd": "ap,help", "desc": "显示 AP 配置模块的帮助信息"}
        ],
        "sta": [
            {"cmd": "sta,set_ssid,<SSID>", "desc": "修改 STA 目标 AP 的 SSID（需重启生效）"},
            {"cmd": "sta,set_password,<密码>", "desc": "修改 STA 目标 AP 的密码（需重启生效）"},
            {"cmd": "sta,set_timeout,<秒数>", "desc": "修改 STA 连接超时（需重启生效）"},
            {"cmd": "sta,help", "desc": "显示 STA 配置模块的帮助信息"}
        ],
        "reset": [
            {"cmd": "reset,set_pin,<引脚>", "desc": "设置重置引脚（需重启生效）"},
            {"cmd": "reset,set_time,<秒数>", "desc": "设置重置保持时间（需重启生效）"},
            {"cmd": "reset,status", "desc": "查看重置引脚状态"},
            {"cmd": "reset,help", "desc": "显示重置模块的帮助信息"}
        ],
        "system": [
            {"cmd": "help", "desc": "显示所有模块的帮助信息"},
            {"cmd": "status", "desc": "显示当前配置信息"},
            {"cmd": "memory", "desc": "显示内存使用情况"},
            {"cmd": "servo,help", "desc": "显示舵机模块的帮助信息"},
            {"cmd": "ir05t,help", "desc": "显示 IR05T 模块的帮助信息"},
            {"cmd": "neighbor,help", "desc": "显示邻居模块的帮助信息"},
            {"cmd": "route,help", "desc": "显示路由模块的帮助信息"},
            {"cmd": "nickname,help", "desc": "显示昵称模块的帮助信息"},
            {"cmd": "config,help", "desc": "显示配置模块的帮助信息"},
            {"cmd": "ap,help", "desc": "显示 AP 配置模块的帮助信息"},
            {"cmd": "sta,help", "desc": "显示 STA 配置模块的帮助信息"}
        ]
    }
}

API_CATALOG = {
    "system": [
        {"path": "/api/get_ap_status", "method": "GET", "desc": "获取 AP 状态"},
        {"path": "/api/get_sta_status", "method": "GET", "desc": "获取 STA 状态"},
        {"path": "/api/get_ap_ssid_password", "method": "GET", "desc": "获取 AP SSID 和密码"},
        {"path": "/api/get_sta_ssid_password", "method": "GET", "desc": "获取 STA SSID 和密码"},
        {"path": "/api/set_sta_ssid_password", "method": "POST", "desc": "设置 STA SSID 和密码"},
        {"path": "/api/get_udp_recv_port", "method": "GET", "desc": "获取 UDP 接收端口"},
        {"path": "/api/get_udp_broadcast_port", "method": "GET", "desc": "获取 UDP 广播端口"},
        {"path": "/api/get_udp_poll_interval", "method": "GET", "desc": "获取 UDP 轮询间隔"},
        {"path": "/api/get_self_mac", "method": "GET", "desc": "获取本机 MAC"},
        {"path": "/api/get_led_pin", "method": "GET", "desc": "获取 LED 引脚"},
        {"path": "/api/get_led_status", "method": "GET", "desc": "获取 LED 状态"},
        {"path": "/api/get_sta_timeout", "method": "GET", "desc": "获取 STA 超时"},
        {"path": "/api/memory", "method": "GET", "desc": "获取内存使用情况"},
        {"path": "/api/config_get", "method": "GET", "desc": "获取所有配置"},
        {"path": "/api/config_reload", "method": "POST", "desc": "重新加载配置"},
        {"path": "/api/config_reset", "method": "POST", "desc": "重置配置并重启"},
        {"path": "/api/reboot", "method": "POST", "desc": "重启设备"},
        {"path": "/api/set_reset_pin", "method": "POST", "desc": "设置重置引脚（需重启生效）"},
        {"path": "/api/set_reset_hold_time", "method": "POST", "desc": "设置重置保持时间（秒，需重启生效）"},
        {"path": "/api/get_reset_status", "method": "GET", "desc": "获取重置引脚和保持时间"}
    ],
    "ap": [
        {"path": "/api/set_ap_ip", "method": "POST", "desc": "设置 AP IP"},
        {"path": "/api/set_ap_ssid_password", "method": "POST", "desc": "设置 AP SSID 和密码"},
        {"path": "/api/set_ap_netmask", "method": "POST", "desc": "设置 AP 子网掩码"},
        {"path": "/api/set_ap_gateway", "method": "POST", "desc": "设置 AP 网关"},
        {"path": "/api/reset_ap_config", "method": "POST", "desc": "重置 AP 配置"},
        {"path": "/api/set_ap_net_segment", "method": "POST", "desc": "设置 AP 网段"}
    ],
    "sta": [
        {"path": "/api/set_sta_timeout", "method": "POST", "desc": "设置 STA 超时"}
    ],
    "udp": [
        {"path": "/api/set_udp_recv_port", "method": "POST", "desc": "设置 UDP 接收端口"},
        {"path": "/api/set_udp_broadcast_port", "method": "POST", "desc": "设置 UDP 广播端口"},
        {"path": "/api/set_udp_poll_interval", "method": "POST", "desc": "设置 UDP 轮询间隔"},
        {"path": "/api/udp_messages", "method": "GET", "desc": "获取 UDP 消息列表"},
        {"path": "/api/clear_udp_messages", "method": "POST", "desc": "清空 UDP 消息列表"},
        {"path": "/api/udp_send_ip", "method": "POST", "desc": "发送 UDP 到指定 IP"},
        {"path": "/api/udp_send_ap", "method": "POST", "desc": "发送 UDP 到 AP 网段 IP 尾号"},
        {"path": "/api/udp_send_sta", "method": "POST", "desc": "发送 UDP 到 STA 网段 IP 尾号"},
        {"path": "/api/send_to_nick", "method": "POST", "desc": "按昵称发送 UDP"},
        {"path": "/api/send_route_message", "method": "POST", "desc": "发送路由消息"},
        {"path": "/api/udp_broadcast", "method": "POST", "desc": "AP 广播"},
        {"path": "/api/udp_broadcast_sta", "method": "POST", "desc": "STA 广播"},
        {"path": "/api/udp_broadcast_apsta", "method": "POST", "desc": "AP+STA 广播"}
    ],
    "neighbor": [
        {"path": "/api/get_nicknames", "method": "GET", "desc": "获取所有昵称"},
        {"path": "/api/get_macs", "method": "GET", "desc": "获取已连接设备的 MAC 列表"},
        {"path": "/api/list_auth", "method": "GET", "desc": "获取已认证设备列表"},
        {"path": "/api/clear_neighbors", "method": "POST", "desc": "清空邻居表"},
        {"path": "/api/delete_device", "method": "POST", "desc": "删除设备"},
        {"path": "/api/set_nickname", "method": "POST", "desc": "设置设备昵称"},
        {"path": "/api/set_self_nickname", "method": "POST", "desc": "设置本机昵称"},
        {"path": "/api/set_neighbor_interval", "method": "POST", "desc": "设置邻居广播间隔"},
        {"path": "/api/get_neighbor_interval", "method": "GET", "desc": "获取邻居广播间隔"},
        {"path": "/api/auth_request", "method": "POST", "desc": "发送 AP 邻居注册请求"},
        {"path": "/api/auth_request_sta", "method": "POST", "desc": "发送 STA 邻居注册请求"},
        {"path": "/api/auth_request_apsta", "method": "POST", "desc": "发送 AP+STA 邻居注册请求"},
        {"path": "/api/neighbor_sta_update_request", "method": "POST", "desc": "发送 STA 邻居更新请求"},
        {"path": "/api/neighbor_ap_update_request", "method": "POST", "desc": "发送 AP 邻居更新请求"}
    ],
    "route": [
        {"path": "/api/route_table", "method": "GET", "desc": "获取路由表"},
        {"path": "/api/route_table_with_nick", "method": "GET", "desc": "获取路由表（含昵称）"},
        {"path": "/api/route_delete", "method": "POST", "desc": "删除路由"},
        {"path": "/api/set_route_interval", "method": "POST", "desc": "设置路由通告间隔"},
        {"path": "/api/get_route_interval", "method": "GET", "desc": "获取路由通告间隔"},
        {"path": "/api/route_clear", "method": "POST", "desc": "清空路由表"},
        {"path": "/api/route_ap_register_request", "method": "POST", "desc": "发送 AP 路由注册请求"},
        {"path": "/api/route_sta_update_request", "method": "POST", "desc": "发送 STA 路由更新请求"},
        {"path": "/api/route_sta_learn_request", "method": "POST", "desc": "发送 STA 路由学习请求"},
        {"path": "/api/route_sta_advertise_request", "method": "POST", "desc": "发送 STA 路由通告"},
        {"path": "/api/route_sta_sync_request", "method": "POST", "desc": "发送 STA 路由同步请求"}
    ],
    "led": [
        {"path": "/api/set_led_pin", "method": "POST", "desc": "设置 LED 引脚"}
    ]
}

# 生成 commands/ 目录
os.makedirs('../PublicModule/commands', exist_ok=True)
for module, cmds in DEFAULT_COMMANDS['commands'].items():
    with open(f'../PublicModule/commands/{module}.json', 'w', encoding="utf-8") as f:
        json.dump(cmds, f, indent=2)
    print(f'生成 commands/{module}.json')

# 生成 api_catalog/ 目录
os.makedirs('../PublicModule/api_catalog', exist_ok=True)
for api_type, apis in API_CATALOG.items():
    with open(f'../PublicModule/api_catalog/{api_type}.json', 'w', encoding="utf-8") as f:
        json.dump(apis, f, indent=2)
    print(f'生成 api_catalog/{api_type}.json')

print("所有 JSON 文件生成完成！")