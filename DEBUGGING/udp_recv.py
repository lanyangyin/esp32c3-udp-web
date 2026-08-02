#!/usr/bin/env python3
import socket
import sys

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("用法: python udp_recv.py <本地监听端口> [允许的源IP]")
        print("示例（接收所有）: python udp_recv.py 8888")
        print("示例（仅接收来自 192.168.8.213）: python udp_recv.py 8888 192.168.8.213")
        sys.exit(1)

    local_port = int(sys.argv[1])
    allowed_ip = sys.argv[2] if len(sys.argv) == 3 else "0.0.0.0"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', local_port))

    if allowed_ip == "0.0.0.0":
        print(f"[接收] 监听端口 {local_port}，接收所有来源的消息。按 Ctrl+C 退出。")
    else:
        print(f"[接收] 监听端口 {local_port}，仅接收来自 {allowed_ip} 的消息。按 Ctrl+C 退出。")

    try:
        while True:
            data, addr = sock.recvfrom(1024)
            if allowed_ip == "0.0.0.0" or addr[0] == allowed_ip:
                print(f"[收到来自 {addr[0]}:{addr[1]}]: {data.decode()}")
    except KeyboardInterrupt:
        print("\n用户中断，退出接收程序。")
    finally:
        sock.close()

if __name__ == "__main__":
    main()