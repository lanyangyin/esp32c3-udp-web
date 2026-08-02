#!/usr/bin/env python3
import socket
import sys

def main():
    if len(sys.argv) != 3:
        print("用法: python udp_send.py <目标IP> <目标端口>")
        print("示例: python udp_send.py 192.168.8.213 8888")
        sys.exit(1)

    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[发送] 目标 {target_ip}:{target_port}，输入消息后按回车发送。输入 'exit' 退出。")

    while True:
        try:
            msg = input("> ")
            if msg.lower() == 'exit':
                print("退出发送程序。")
                break
            sock.sendto(msg.encode(), (target_ip, target_port))
        except KeyboardInterrupt:
            print("\n用户中断，退出发送程序。")
            break
        except Exception as e:
            print(f"发送错误: {e}")
            break

    sock.close()

if __name__ == "__main__":
    main()