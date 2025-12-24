#!/usr/bin/env python3
"""
屏幕共享客户端 - 接收并显示远程屏幕
"""
import socket
import struct
import threading
import io
import time
from PIL import Image
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk

class ScreenShareClient:
    def __init__(self, server_host, server_port=5000):
        """
        初始化屏幕共享客户端
        
        Args:
            server_host: 服务器地址
            server_port: 服务器端口
        """
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.running = False
        
        # GUI
        self.root = tk.Tk()
        self.root.title(f"远程屏幕 - {server_host}:{server_port}")
        self.root.geometry("1000x700")
        
        # 信息面板
        info_frame = ttk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(info_frame, text="连接中...", foreground="orange")
        self.status_label.pack(side=tk.LEFT)
        
        self.info_label = ttk.Label(info_frame, text="")
        self.info_label.pack(side=tk.RIGHT)
        
        # 屏幕显示区域
        self.canvas = tk.Canvas(self.root, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.photo_image = None
        
        # 启动连接线程
        self.root.after(100, self._connect_and_receive)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _connect_and_receive(self):
        """连接到服务器并接收屏幕数据"""
        try:
            if not self.connected:
                self._connect()
            
            if self.connected:
                self._receive_frame()
            
            # 递归调用，保持接收循环
            self.root.after(10, self._connect_and_receive)
            
        except Exception as e:
            print(f"[!] 错误: {e}")
            self.connected = False
            self.status_label.config(text=f"连接失败: {e}", foreground="red")
            self.root.after(2000, self._connect_and_receive)
    
    def _connect(self):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.status_label.config(text="已连接 ✓", foreground="green")
            print(f"[✓] 已连接到服务器: {self.server_host}:{self.server_port}")
        except Exception as e:
            self.connected = False
            self.socket = None
            raise
    
    def _receive_frame(self):
        """接收并显示一帧"""
        if not self.socket:
            raise ConnectionError("Socket 未初始化")
        
        try:
            # 接收帧大小（4字节）
            size_data = self.socket.recv(4)
            if not size_data:
                raise ConnectionError("服务器断开连接")
            
            frame_size = struct.unpack('>I', size_data)[0]
            
            # 接收帧数据
            frame_data = b''
            while len(frame_data) < frame_size:
                chunk = self.socket.recv(min(frame_size - len(frame_data), 65536))
                if not chunk:
                    raise ConnectionError("接收数据中断")
                frame_data += chunk
            
            # 解码图像
            image = Image.open(io.BytesIO(frame_data))
            
            # 获取Canvas大小
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # 缩放图像以适应Canvas（保持宽高比）
                image.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage
            self.photo_image = ImageTk.PhotoImage(image)
            
            # 清空Canvas并显示新图像
            self.canvas.delete("all")
            self.canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                image=self.photo_image
            )
            
            # 更新信息
            img_size = len(frame_data) / 1024
            self.info_label.config(text=f"分辨率: {image.size[0]}x{image.size[1]} | 帧大小: {img_size:.1f} KB")
            
        except socket.timeout:
            # 超时重新连接
            self.connected = False
        except Exception as e:
            print(f"[!] 接收出错: {e}")
            self.connected = False
            raise
    
    def on_closing(self):
        """关闭窗口"""
        print("[i] 关闭客户端...")
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.root.destroy()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


if __name__ == '__main__':
    import sys
    
    server_host = 'localhost'
    server_port = 5000
    
    # 命令行参数
    if len(sys.argv) > 1:
        server_host = sys.argv[1]
    if len(sys.argv) > 2:
        server_port = int(sys.argv[2])
    
    print(f"[i] 连接到服务器: {server_host}:{server_port}")
    
    client = ScreenShareClient(server_host, server_port)
    client.run()
