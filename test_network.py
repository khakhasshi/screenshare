#!/usr/bin/env python3
"""
网络诊断工具 - 测试连接和网络参数
"""
import socket
import subprocess
import platform
import sys

def get_local_ip():
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def check_port(host, port):
    """检查端口是否开放"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except:
        return False

def get_network_interfaces():
    """获取网络接口信息"""
    try:
        if platform.system() == 'Darwin':
            # Mac
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
        else:
            # Windows
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
        return result.stdout
    except:
        return "无法获取网络信息"

def main():
    print("=" * 60)
    print("屏幕共享 - 网络诊断工具")
    print("=" * 60)
    
    # 获取本机 IP
    local_ip = get_local_ip()
    print(f"\n[i] 本机局域网 IP: {local_ip}")
    print(f"[i] 操作系统: {platform.system()}")
    
    # 测试端口
    print(f"\n[测试] 检查端口 5000...")
    if check_port('localhost', 5000):
        print("[✓] 端口 5000 已被使用（服务器可能在运行）")
    else:
        print("[i] 端口 5000 可用")
    
    # 获取网络接口信息
    print("\n[网络接口信息]")
    print("-" * 60)
    print(get_network_interfaces())
    print("-" * 60)
    
    print("\n[使用提示]")
    print(f"1. 在主机上运行: python server.py")
    print(f"2. 在客户端上运行: python client.py {local_ip}")
    print("\n[i] 确保两台电脑在同一局域网内")

if __name__ == '__main__':
    main()
