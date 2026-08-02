import socket
import threading
import sys

def receive(port):
    """接收线程：绑定到本地端口，持续打印收到的消息"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', port))
    print(f"[接收] 监听端口 {port}，等待消息...")
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            # 打印收到的消息，并重新显示输入提示符（因为可能被中断）
            print(f"\n[收到来自 {addr[0]}:{addr[1]}]: {data.decode()}")
            print("> ", end='', flush=True)   # 重新显示提示
        except Exception as e:
            print(f"接收错误: {e}")
            break

def send(target_ip, target_port):
    """发送主线程：从终端读取输入并发送"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[发送] 目标 {target_ip}:{target_port}，输入消息后按回车发送。")
    while True:
        msg = input("> ")
        if msg.lower() == 'exit':
            print("退出程序...")
            sys.exit(0)
        try:
            sock.sendto(msg.encode(), (target_ip, target_port))
        except Exception as e:
            print(f"发送错误: {e}")

def main():
    if len(sys.argv) != 4:
        print("用法: python udp_chat.py <目标IP> <目标端口> <本地接收端口>")
        print("示例: python udp_chat.py 192.168.1.100 8888 9999")
        sys.exit(1)

    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])
    local_port = int(sys.argv[3])

    # 启动接收线程（守护线程，主线程结束时自动退出）
    recv_thread = threading.Thread(target=receive, args=(local_port,), daemon=True)
    recv_thread.start()

    # 主线程用于发送
    send(target_ip, target_port)

if __name__ == "__main__":
    main()