# ir05t.py
"""
IR05T 红外学习模块 MicroPython 驱动
严格按照官方串口通信协议实现
"""

from machine import UART
import time


class IR05T:
    # 固定帧头/帧尾
    HEAD = b'\xFD\xFD'
    TAIL = b'\xDF'
    TAIL_DOUBLE = b'\xDF\xDF'   # 用于数据帧

    def __init__(self, uart_id=1, tx_pin=4, rx_pin=5, baudrate=9600, timeout=2000):
        """
        初始化 IR05T 模块
        Args:
            uart_id: UART 编号 (建议用 UART1，避免与 REPL 冲突)
            tx_pin:  TX 引脚 (接模块 RX)
            rx_pin:  RX 引脚 (接模块 TX)
            baudrate: 波特率，默认 9600
            timeout:  串口读取超时 (毫秒)
        """
        self.uart = UART(uart_id, baudrate=baudrate, tx=tx_pin, rx=rx_pin, timeout=timeout)
        self.baudrate = baudrate
        self.timeout = timeout
        print(f"[IR05T] 初始化完成，UART{uart_id}, TX={tx_pin}, RX={rx_pin}, {baudrate}bps")

    # ---------- 底层通信 ----------
    def _write(self, data):
        """写入数据并打印调试信息"""
        if isinstance(data, list):
            data = bytes(data)
        self.uart.write(data)
        print(f"[IR05T] 发送: {data.hex().upper()}")

    def _read(self, timeout=None):
        """
        读取数据，持续读取直到超时，拼接所有接收到的字节。
        返回完整的数据（bytes），若超时无数据则返回 b''。
        timeout: 毫秒，None 则使用 self.timeout
        """
        if timeout is None:
            timeout = self.timeout

        start = time.ticks_ms()
        resp = b''
        # 只要有数据就不断读取，直到超时
        while time.ticks_diff(time.ticks_ms(), start) < timeout:
            # 检查是否有数据可读（非阻塞）
            if self.uart.any():
                chunk = self.uart.read()
                if chunk:
                    resp += chunk
            else:
                # 没有数据则短暂休眠，避免空转
                time.sleep_ms(1)

        if resp:
            print(f"[IR05T] 收到: {resp.hex().upper()}")
        return resp

    def _send_command(self, cmd, data=None):
        """
        发送标准命令帧: FD FD + CMD + [DATA] + DF
        """
        frame = bytearray(self.HEAD)
        frame.append(cmd)
        if data is not None:
            if isinstance(data, int):
                frame.append(data)
            elif isinstance(data, (bytes, bytearray)):
                frame.extend(data)
            else:
                raise ValueError("data 必须是 int 或 bytes 类型")
        frame.append(self.TAIL[0])
        self._write(frame)

    def _send_data_frame(self, data):
        """
        发送数据帧: FD FD + DATA + DF DF (用于通用发射)
        """
        frame = bytearray(self.HEAD)
        frame.extend(data)
        frame.extend(self.TAIL_DOUBLE)
        self._write(frame)

    def _wait_response(self, expected=None, timeout=2000):
        """
        等待并检查响应
        Args:
            expected: 期望的响应字节 (如 b'\xF1')，None 表示返回原始数据
            timeout: 超时时间 (毫秒)
        Returns:
            原始响应数据 (bytes) 或 None
        """
        resp = self._read(timeout)
        if expected is not None:
            if resp == expected:
                print(f"[IR05T] 收到预期响应: {expected.hex().upper()}")
                return resp
            else:
                print(f"[IR05T] 预期 {expected.hex().upper()}，实际 {resp.hex().upper() if resp else 'None'}")
                return None
        return resp

    def set_timeout(self, timeout_ms):
        """
        修改串口读取超时时间（毫秒）
        """
        if timeout_ms < 100:
            timeout_ms = 100  # 最小100ms，避免过短
        self.timeout = timeout_ms
        try:
            self.uart.timeout = timeout_ms  # 有些固件支持直接修改
        except AttributeError:
            pass  # 忽略，因为我们使用轮询方式，不依赖硬件超时
        print(f"[IR05T] 超时时间已设为 {timeout_ms}ms")

    # ---------- 1. 进入学习状态 (通用) ----------
    def learn(self):
        """
        进入通用学习状态
        发送: FD FD F1 F2 DF
        返回: 学习到的 232 字节红外数据 (bytes)，失败返回 None
        """
        self._send_command(0xF1, 0xF2)  # FD FD F1 F2 DF
        
        # 等待学习数据: FD FD + 232字节 + DF DF
        resp = self._read(timeout=self.timeout)
        if resp and resp.startswith(self.HEAD) and resp.endswith(self.TAIL_DOUBLE):
            # 提取数据部分 (去掉帧头 2 字节，帧尾 2 字节)
            data = resp[2:-2]
            print(f"[IR05T] 学习成功，获取 {len(data)} 字节数据")
            return data
        else:
            print(f"[IR05T] 学习失败或超时")
            return None

    # ---------- 2. 通用发射指令 ----------
    def send_raw(self, data):
        """
        通用发射: FD FD + 红外数据 + DF DF
        Args:
            data: 232 字节红外数据 (bytes)
        Returns:
            bool: 是否成功 (反馈 F1)
        """
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data 必须是 bytes 类型")
        self._send_data_frame(data)
        resp = self._wait_response(b'\xF1', timeout=1000)
        return resp is not None

    # ---------- 3. 修改波特率 ----------
    def set_baudrate(self, baudrate):
        """
        修改模块波特率 (保存到 EEPROM，下次上电生效)
        发送: FD FD F3 XX DF
        Args:
            baudrate: 4800, 9600, 57600, 115200
        Returns:
            bool: 是否成功 (反馈 F3)
        """
        baud_map = {
            4800: 0x01,
            9600: 0x02,
            57600: 0x03,
            115200: 0x04
        }
        if baudrate not in baud_map:
            raise ValueError("不支持的波特率，可选: 4800, 9600, 57600, 115200")
        
        self._send_command(0xF3, baud_map[baudrate])
        resp = self._wait_response(b'\xF3', timeout=1000)
        if resp:
            self.baudrate = baudrate
            print(f"[IR05T] 波特率已修改为 {baudrate}，下次上电生效")
            return True
        return False

    # ---------- 4. 修改帧头 ----------
    def set_frame_header(self, new_header_byte):
        """
        修改帧头 (FD FD 固定不变，可修改后续识别字节)
        发送: FD FD F5 XX DF
        Args:
            new_header_byte: 0xA0 ~ 0xFE (新帧头的第二个字节)
        Returns:
            bool: 是否成功 (反馈 F5)
        """
        if not (0xA0 <= new_header_byte <= 0xFE):
            raise ValueError("帧头字节必须在 0xA0 ~ 0xFE 之间")
        self._send_command(0xF5, new_header_byte)
        resp = self._wait_response(b'\xF5', timeout=1000)
        return resp is not None

    # ---------- 5. 指定通道学习 ----------
    def learn_channel(self, channel):
        """
        进入指定通道学习状态
        发送: FD FD FA 01 DF (以通道1为例)
        返回: bool (反馈 FA)
        """
        if not 1 <= channel <= 5:
            raise ValueError("通道必须在 1~5 之间")
        self._send_command(0xFA, channel)
        resp = self._wait_response(b'\xFA', timeout=2000)
        if resp:
            print(f"[IR05T] 通道 {channel} 已进入学习状态，请对准模块按下遥控器按钮")
        return resp is not None

    # ---------- 6. 指定通道发射 ----------
    def send_channel(self, channel):
        """
        发射指定通道已学习的红外数据
        发送: FD FD FB 01 DF (以通道1为例)
        返回: bool (反馈 FB)
        """
        if not 1 <= channel <= 5:
            raise ValueError("通道必须在 1~5 之间")
        self._send_command(0xFB, channel)
        resp = self._wait_response(b'\xFB', timeout=1000)
        return resp is not None

    # ---------- 便捷方法 ----------
    def learn_and_save(self, channel=None):
        """
        一键学习并保存到指定通道 (或通用模式)
        Args:
            channel: None=通用学习，1~5=指定通道学习
        Returns:
            学习到的数据 (bytes) 或 None
        """
        if channel is None:
            return self.learn()
        else:
            if self.learn_channel(channel):
                print(f"[IR05T] 通道 {channel} 学习完成，请按遥控器")
                return True
            return False

    # ---------- 资源释放 ----------
    def deinit(self):
        self.uart.deinit()
        print("[IR05T] 已释放 UART")