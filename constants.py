# constants.py - 全局常量定义
DEBUG_FRAGMENT = False
# ============================================================================
# 网络与通信
# ============================================================================
DEFAULT_AP_IP = "192.168.4.1"
DEFAULT_AP_SUBNET = "255.255.255.0"
DEFAULT_AP_SSID_PREFIX = "ESP32-C3-Setup-"

DEFAULT_STA_SSID = ""
DEFAULT_STA_PASSWORD = ""

DEFAULT_UDP_RECV_PORT = 8888
DEFAULT_UDP_BROADCAST_PORT = 8888
DEFAULT_UDP_POLL_INTERVAL = 2000   # 毫秒

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
            {"cmd": "servo,help", "desc": "显示舵机模块的帮助信息"},
        ],
        "ir05t": [
            {"cmd": "ir05t,list_devices", "desc": "列出所有 IR 设备"},
            {"cmd": "ir05t,add,<设备名>,<tx_pin>,<rx_pin>[,<baudrate>[,<timeout>]]", "desc": "添加并初始化 IR 设备"},
            {"cmd": "ir05t,delete,<设备名>", "desc": "删除 IR 设备"},
            {"cmd": "ir05t,set_pin,<设备名>,<tx_pin>,<rx_pin>", "desc": "修改设备引脚"},
            {"cmd": "ir05t,list,<设备名>", "desc": "列出设备下所有已学习的数据"},
            {"cmd": "ir05t,get,<设备名>,<数据名>", "desc": "获取指定数据内容"},
            {"cmd": "ir05t,learn,<设备名>", "desc": "通用学习（不保存）"},
            {"cmd": "ir05t,learn,save,<设备名>,<数据名>", "desc": "学习并保存数据"},
            {"cmd": "ir05t,send,<设备名>,<数据名>", "desc": "发送已保存的数据"},
            {"cmd": "ir05t,delete_data,<设备名>,<数据名>", "desc": "删除指定数据"},
            {"cmd": "ir05t,learn_channel,<设备名>,<1~5>", "desc": "通道学习"},
            {"cmd": "ir05t,send_channel,<设备名>,<1~5>", "desc": "发送通道"},
            {"cmd": "ir05t,send_raw,<设备名>,<hex数据>", "desc": "发送原始数据"},
            {"cmd": "ir05t,set_baud,<设备名>,<波特率>", "desc": "修改波特率"},
            {"cmd": "ir05t,set_timeout,<设备名>,<毫秒>", "desc": "修改超时"},
            {"cmd": "ir05t,set_header,<设备名>,<0xA0~0xFE>", "desc": "修改帧头"},
            {"cmd": "ir05t,help", "desc": "显示 IR05T 模块的帮助信息"},
        ],
        "neighbor": [
            {"cmd": "neighbor,list", "desc": "显示当前邻居表"},
            {"cmd": "neighbor,set_interval,<秒数>", "desc": "修改邻居广播间隔（默认120秒）"},
            {"cmd": "neighbor,help", "desc": "显示邻居模块的帮助信息"},
        ],
        "route": [
            {"cmd": "route,list", "desc": "显示当前路由表"},
            {"cmd": "route,set_interval,<秒数>", "desc": "修改路由通告间隔（默认120秒）"},
            {"cmd": "route,help", "desc": "显示路由模块的帮助信息"},
        ],
        "nickname": [
            {"cmd": "nickname,set,<新昵称>", "desc": "修改设备昵称（立即生效）"},
            {"cmd": "nickname,help", "desc": "显示昵称模块的帮助信息"},
        ],
        "config": [
            {"cmd": "config,get", "desc": "获取当前所有配置（JSON格式）"},
            {"cmd": "config,save", "desc": "保存当前配置到文件并重启"},
            {"cmd": "config,reload", "desc": "重新加载配置文件（不重启）"},
            {"cmd": "config,reset", "desc": "删除配置文件并重启（恢复出厂设置）"},
            {"cmd": "config,help", "desc": "显示配置模块的帮助信息"},
        ],
        "ap": [
            {"cmd": "ap,set_ssid,<新SSID>", "desc": "修改 AP 的 SSID（需重启生效）"},
            {"cmd": "ap,set_password,<新密码>", "desc": "修改 AP 的 Wi-Fi 密码（需重启生效）"},
            {"cmd": "ap,set_ip,<IP>", "desc": "修改 AP IP 地址（需 reload 生效）"},
            {"cmd": "ap,set_netmask,<掩码>", "desc": "修改 AP 子网掩码（需 reload 生效）"},
            {"cmd": "ap,set_gateway,<网关>", "desc": "修改 AP 网关（需 reload 生效）"},
            {"cmd": "ap,help", "desc": "显示 AP 配置模块的帮助信息"},
        ],
        "sta": [
            {"cmd": "sta,set_ssid,<SSID>", "desc": "修改 STA 目标 AP 的 SSID（需重启生效）"},
            {"cmd": "sta,set_password,<密码>", "desc": "修改 STA 目标 AP 的密码（需重启生效）"},
            {"cmd": "sta,set_timeout,<秒数>", "desc": "修改 STA 连接超时（需重启生效）"},
            {"cmd": "sta,help", "desc": "显示 STA 配置模块的帮助信息"},
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
            {"cmd": "sta,help", "desc": "显示 STA 配置模块的帮助信息"},
        ],
    }
}
# ============================================================================
# 路由与邻居表
# ============================================================================
DEFAULT_ROUTE_TTL = 20      # 路由消息默认TTL（当未知目标时）
ROUTE_TTL_MAX = 4          # 路由表条目最大生存时间（跳数）
ROUTE_STEP = 2             # 路由步距（每跳增加）
NEIGHBOR_TTL_MAX = 2       # 邻居表条目最大TTL
DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL = 120       # 邻居注册申请回复间隔
DEFAULT_ROUTE_ADVERTISE_INTERVAL = 120          # 路由通告间隔

# ============================================================================
# 分片协议
# ============================================================================
FRAGMENT_CACHE_TIMEOUT = 10        # 分片缓存超时（秒）
FRAGMENT_MAX_BYTES = 256           # 单个分片最大字节数（默认）
FRAGMENT_MAX_CACHE_SIZE = 20      # 最大缓存消息数（防内存溢出）
FRAGMENT_DEFAULT_TTL = 16          # 分片消息默认TTL

BROADCAST_TTL = 2

UDP_RECV_BUFFER = 2048

# ============================================================================
# LED 与硬件
# ============================================================================
DEFAULT_LED_PIN = 8

# ============================================================================
# 超时与间隔
# ============================================================================
DEFAULT_STA_TIMEOUT = 60           # STA 连接超时（秒）
HTTP_READ_TIMEOUT = 5              # HTTP 读取超时（秒）
UDP_RESPONSE_MAX_PACKET = 1000     # 简单回复最大包大小（字节）
UDP_RESPONSE_SLEEP = 0.05          # 分段发送间隔（秒）
CACHE_CLEAN_INTERVAL = 30          # 缓存清理间隔（秒）
DEFAULT_IR_BAUDRATE = 9600
DEFAULT_IR_TIMEOUT = 2000   # 毫秒

# ============================================================================
# UDP 消息历史
# ============================================================================
DEFAULT_MAX_UDP_MESSAGES = 5

# ============================================================================
# MAC 地址特殊值
# ============================================================================
BROADCAST_MAC = "FF:FF:FF:FF:FF:FF"
NULL_MAC = "00:00:00:00:00:00"

# ============================================================================
# 端口范围
# ============================================================================
MIN_PORT = 1
MAX_PORT = 65535