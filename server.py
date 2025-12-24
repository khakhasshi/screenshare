#!/usr/bin/env python3
"""
屏幕共享服务器 - 捕获本机屏幕并通过网络传输
"""
import socket
import time
import threading
import struct
import io
from PIL import ImageGrab
from datetime import datetime

class ScreenShareServer:
    def __init__(self, host='0.0.0.0', port=5000, quality=70, fps=10):
        """
        初始化屏幕共享服务器
        
        Args:
            host: 绑定地址
            port: 监听端口
            quality: JPEG压缩质量 (1-100)
            fps: 帧率
        """
        self.host = host
        self.port = port
        self.quality = quality
        self.fps = fps
        self.server_socket = None
        self.running = False
        self.clients = []
        self.lock = threading.Lock()
        
    def start(self):
        """启动服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        self.running = True
        print(f"[✓] 屏幕共享服务器启动: {self.host}:{self.port}")
        print(f"[i] 质量: {self.quality}, 帧率: {self.fps} FPS")
        
        # 启动屏幕捕获线程
        capture_thread = threading.Thread(target=self._capture_and_broadcast, daemon=True)
        capture_thread.start()
        
        # 启动客户端接受线程
        accept_thread = threading.Thread(target=self._accept_clients, daemon=True)
        accept_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _accept_clients(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_socket, client_addr = self.server_socket.accept()
                print(f"[+] 客户端已连接: {client_addr}")
                
                with self.lock:
                    self.clients.append(client_socket)
                
                # 为每个客户端创建单独线程处理断开连接
                client_thread = threading.Thread(
                    target=self._handle_client_disconnect,
                    args=(client_socket, client_addr),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"[!] 接受客户端出错: {e}")
                break
    
    def _handle_client_disconnect(self, client_socket, client_addr):
        """监听客户端是否断开连接"""
        try:
            # 客户端如果断开连接，这里会抛出异常
            while True:
                data = client_socket.recv(1024)
                if not data:
                    raise ConnectionResetError()
        except:
            print(f"[-] 客户端已断开: {client_addr}")
            with self.lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            try:
                client_socket.close()
            except:
                pass
    
    def _capture_and_broadcast(self):
        """捕获屏幕并广播给所有客户端"""
        frame_count = 0
        last_time = time.time()
        
        while self.running:
            try:
                # 捕获屏幕
                screenshot = ImageGrab.grab()
                
                # 调整大小以减少传输数据（可选，注释掉以保持原始分辨率）
                # 例如将宽度缩小到 1280
                width, height = screenshot.size
                if width > 1280:
                    ratio = 1280 / width
                    new_height = int(height * ratio)
                    screenshot = screenshot.resize((1280, new_height), Image.Resampling.LANCZOS)
                
                # 压缩为JPEG
                buffer = io.BytesIO()
                screenshot.save(buffer, format='JPEG', quality=self.quality, optimize=True)
                frame_data = buffer.getvalue()
                
                # 构建帧数据包：[长度(4字节)] + [数据]
                frame_size = len(frame_data)
                packet = struct.pack('>I', frame_size) + frame_data
                
                # 广播给所有客户端
                with self.lock:
                    disconnected_clients = []
                    for client_socket in self.clients:
                        try:
                            client_socket.sendall(packet)
                        except Exception as e:
                            print(f"[!] 发送数据出错，移除客户端: {e}")
                            disconnected_clients.append(client_socket)
                    
                    # 移除断开连接的客户端
                    for client in disconnected_clients:
                        if client in self.clients:
                            self.clients.remove(client)
                
                frame_count += 1
                
                # 每秒打印一次统计信息
                current_time = time.time()
                if current_time - last_time >= 1:
                    fps = frame_count / (current_time - last_time)
                    connected = len(self.clients)
                    print(f"[i] 帧率: {fps:.1f} FPS | 客户端: {connected} | 帧大小: {frame_size/1024:.1f} KB")
                    frame_count = 0
                    last_time = current_time
                
                # 控制帧率
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                print(f"[!] 捕获或广播出错: {e}")
                time.sleep(1)
    
    def stop(self):
        """停止服务器"""
        print("\n[i] 正在关闭服务器...")
        self.running = False
        
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients.clear()
        
        try:
            self.server_socket.close()
        except:
            pass
        print("[✓] 服务器已关闭")


if __name__ == '__main__':
    import sys
    
    host = '0.0.0.0'
    port = 5000
    quality = 60  # JPEG 质量
    fps = 10      # 帧率
    
    # 命令行参数
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        quality = int(sys.argv[2])
    if len(sys.argv) > 3:
        fps = int(sys.argv[3])
    
    server = ScreenShareServer(host, port, quality, fps)
    server.start()
