# SPDX-License-Identifier: GPL-3.0-only
# SPDX-FileCopyrightText: 2026 lanyangyin <2436725966@qq.com>
#
# This file is part of the ESP32-C3 Multi-Function Control Platform project.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# constants.py - 全局常量定义
import random

DEBUG_FRAGMENT = False
# ============================================================================
# 网络与通信
# ============================================================================
DEFAULT_AP_IP = f"192.168.{random.randint(5,250)}.1"
DEFAULT_AP_SUBNET = "255.255.255.0"
DEFAULT_AP_SSID_PREFIX = "ESP32-C3-Setup-"

DEFAULT_STA_SSID = ""
DEFAULT_STA_PASSWORD = ""

DEFAULT_UDP_RECV_PORT = 8888
DEFAULT_UDP_BROADCAST_PORT = 8888
DEFAULT_UDP_POLL_INTERVAL = 2000   # 毫秒

# ============================================================================
# 路由与邻居表
# ============================================================================
DEFAULT_ROUTE_TTL = 20
ROUTE_TTL_MAX = 4
ROUTE_STEP = 2
NEIGHBOR_TTL_MAX = 4
NEIGHBOR_STEP = 2
DEFAULT_NEIGHBOR_ADVERTISE_INTERVAL = 20
DEFAULT_ROUTE_ADVERTISE_INTERVAL = 90

# ============================================================================
# 分片协议
# ============================================================================
FRAGMENT_CACHE_TIMEOUT = 10
FRAGMENT_MAX_BYTES = 256
FRAGMENT_MAX_CACHE_SIZE = 20
FRAGMENT_DEFAULT_TTL = 16
BROADCAST_TTL = 2
UDP_RECV_BUFFER = 2048

DEFAULT_RESET_HOLD_TIME = 8

# ============================================================================
# LED 与硬件
# ============================================================================
DEFAULT_LED_PIN = 8
DEFAULT_RESET_PIN = 10

# ============================================================================
# 超时与间隔
# ============================================================================
DEFAULT_STA_TIMEOUT = 60
HTTP_READ_TIMEOUT = 5
UDP_RESPONSE_MAX_PACKET = 1000
UDP_RESPONSE_SLEEP = 0.05
CACHE_CLEAN_INTERVAL = 30
DEFAULT_IR_BAUDRATE = 9600
DEFAULT_IR_TIMEOUT = 2000

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