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
from discovery import ScreenShareDiscovery

class ScreenShareClient:
    def __init__(self, server_host=None, server_port=5000):
        """
        初始化屏幕共享客户端
        
        Args:
            server_host: 服务器地址（如果为 None 则自动发现）
            server_port: 服务器端口
        """
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.running = False
        self.discovery = ScreenShareDiscovery()
        
        # GUI
        self.root = tk.Tk()
        self.root.title("屏幕共享客户端")
        self.root.geometry("1000x700")
        
        # 信息面板
        info_frame = ttk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(info_frame, text="初始化中...", foreground="orange")
        self.status_label.pack(side=tk.LEFT)
        
        self.info_label = ttk.Label(info_frame, text="")
        self.info_label.pack(side=tk.RIGHT)
        
        # 服务发现面板
        self.discovery_frame = ttk.LabelFrame(self.root, text="可用服务", height=100)
        self.discovery_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.service_list = tk.Listbox(self.discovery_frame, height=4)
        self.service_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.service_list.bind('<<ListboxSelect>>', self._on_service_selected)
        
        button_frame = ttk.Frame(self.discovery_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.connect_button = ttk.Button(button_frame, text="连接", command=self._connect_selected)
        self.connect_button.pack(side=tk.LEFT, padx=5)
        
        self.refresh_button = ttk.Button(button_frame, text="刷新", command=self._refresh_services)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        # 屏幕显示区域
        self.canvas = tk.Canvas(self.root, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.photo_image = None
        self.services = {}
        self.selected_service = None
        
        # 如果指定了服务器地址，直接连接
        if server_host:
            self.discovery_frame.pack_forget()
            self.root.after(100, self._connect_and_receive)
        else:
            # 否则开始发现服务
            self.root.after(100, self._refresh_services)
        
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
            self.status_label.config(text=f"已连接 ✓ ({self.server_host}:{self.server_port})", foreground="green")
            print(f"[✓] 已连接到服务器: {self.server_host}:{self.server_port}")
        except Exception as e:
            self.connected = False
            self.socket = None
            raise
    
    def _refresh_services(self):
        """刷新可用服务列表"""
        def discover_thread():
            self.status_label.config(text="扫描局域网服务中...", foreground="orange")
            self.root.update()
            
            services = self.discovery.discover_services(timeout=5)
            
            self.service_list.delete(0, tk.END)
            self.services = {}
            
            for service in services:
                display_text = f"{service['name']} ({service['ip']}:{service['port']}) - {service['os']}"
                self.service_list.insert(tk.END, display_text)
                self.services[display_text] = service
            
            if services:
                self.status_label.config(text=f"发现 {len(services)} 个服务", foreground="green")
                # 自动选中第一个
                self.service_list.selection_set(0)
                self._on_service_selected(None)
            else:
                self.status_label.config(text="未发现任何服务", foreground="red")
        
        thread = threading.Thread(target=discover_thread, daemon=True)
        thread.start()
    
    def _on_service_selected(self, event):
        """选择服务"""
        selection = self.service_list.curselection()
        if selection:
            service_text = self.service_list.get(selection[0])
            self.selected_service = self.services[service_text]
            print(f"[i] 已选择: {service_text}")
    
    def _connect_selected(self):
        """连接选中的服务"""
        if self.selected_service:
            self.server_host = self.selected_service['ip']
            self.server_port = self.selected_service['port']
            
            # 隐藏服务发现面板
            self.discovery_frame.pack_forget()
            
            # 开始连接和接收
            self.root.after(100, self._connect_and_receive)
    
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
        self.discovery.close()
        self.root.destroy()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


if __name__ == '__main__':
    import sys
    
    server_host = None
    server_port = 5000
    
    # 命令行参数
    if len(sys.argv) > 1:
        server_host = sys.argv[1]
    if len(sys.argv) > 2:
        server_port = int(sys.argv[2])
    
    if server_host:
        print(f"[i] 连接到服务器: {server_host}:{server_port}")
    else:
        print(f"[i] 自动发现模式，扫描局域网服务...")
    
    client = ScreenShareClient(server_host, server_port)
    client.run()
