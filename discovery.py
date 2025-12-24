#!/usr/bin/env python3
"""
局域网服务发现 - 自动检测和配对屏幕共享服务
"""
import socket
import struct
import threading
import time
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
import platform

class ScreenShareDiscovery:
    """使用 mDNS 进行服务发现和注册"""
    
    SERVICE_NAME = "_screenshare._tcp.local."
    
    def __init__(self):
        self.zeroconf = None
        self.services = {}
        self.lock = threading.Lock()
    
    def register_service(self, hostname, port, quality=60, fps=10):
        """
        注册屏幕共享服务到局域网
        
        Args:
            hostname: 服务器主机名
            port: 服务器端口
            quality: 图像质量
            fps: 帧率
        """
        try:
            from zeroconf import ServiceInfo, Zeroconf
            
            self.zeroconf = Zeroconf()
            
            # 获取本机 IP
            local_ip = self._get_local_ip()
            
            # 创建服务信息
            service_info = ServiceInfo(
                self.SERVICE_NAME,
                f"{hostname}.{self.SERVICE_NAME}",
                addresses=[socket.inet_aton(local_ip)],
                port=port,
                properties={
                    'quality': str(quality),
                    'fps': str(fps),
                    'os': platform.system(),
                    'hostname': hostname,
                },
                server=f"{hostname}.local."
            )
            
            # 注册服务
            self.zeroconf.register_service(service_info)
            print(f"[✓] 服务已发布: {hostname} ({local_ip}:{port})")
            print(f"[i] 局域网内的设备可以自动发现此服务")
            
        except Exception as e:
            print(f"[!] 服务注册失败: {e}")
            print("[i] 客户端仍可以手动连接")
    
    def discover_services(self, callback=None, timeout=10):
        """
        发现局域网内的屏幕共享服务
        
        Args:
            callback: 发现服务时的回调函数 (service_info)
            timeout: 发现超时时间（秒）
        
        Returns:
            服务列表 [{'name', 'ip', 'port', 'quality', 'fps', 'os'}, ...]
        """
        try:
            from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange
            
            self.zeroconf = Zeroconf()
            
            def on_service_state_change(zeroconf, service_type, name, state_change):
                if state_change == ServiceStateChange.Added:
                    self._handle_service_added(zeroconf, service_type, name, callback)
                elif state_change == ServiceStateChange.Removed:
                    self._handle_service_removed(name, callback)
            
            # 开始服务发现
            ServiceBrowser(
                self.zeroconf,
                self.SERVICE_NAME,
                handlers=[on_service_state_change]
            )
            
            print(f"[i] 正在扫描局域网中的屏幕共享服务（{timeout}秒）...")
            time.sleep(timeout)
            
            with self.lock:
                return list(self.services.values())
            
        except Exception as e:
            print(f"[!] 服务发现失败: {e}")
            return []
    
    def _handle_service_added(self, zeroconf, service_type, name, callback):
        """处理发现的服务"""
        try:
            from zeroconf import Zeroconf as ZeroconfClass
            
            info = zeroconf.get_service_info(service_type, name)
            if info:
                addresses = info.parsed_addresses()
                ip = addresses[0] if addresses else "unknown"
                port = info.port
                
                service_data = {
                    'name': name.replace(self.SERVICE_NAME, '').rstrip('.'),
                    'ip': ip,
                    'port': port,
                    'quality': info.properties.get(b'quality', b'60').decode() if b'quality' in info.properties else '60',
                    'fps': info.properties.get(b'fps', b'10').decode() if b'fps' in info.properties else '10',
                    'os': info.properties.get(b'os', b'Unknown').decode() if b'os' in info.properties else 'Unknown',
                }
                
                with self.lock:
                    self.services[name] = service_data
                
                print(f"[+] 发现服务: {service_data['name']} ({service_data['ip']}:{service_data['port']}) - {service_data['os']}")
                
                if callback:
                    callback(service_data)
                    
        except Exception as e:
            print(f"[!] 解析服务信息失败: {e}")
    
    def _handle_service_removed(self, name, callback):
        """处理移除的服务"""
        with self.lock:
            if name in self.services:
                service_data = self.services.pop(name)
                print(f"[-] 服务离线: {service_data['name']}")
    
    def _get_local_ip(self):
        """获取本机局域网 IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def close(self):
        """关闭 Zeroconf"""
        if self.zeroconf:
            self.zeroconf.close()
    
    @staticmethod
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


if __name__ == '__main__':
    # 测试服务发现
    discovery = ScreenShareDiscovery()
    
    print("=" * 60)
    print("屏幕共享 - 服务发现")
    print("=" * 60)
    print()
    
    # 发现服务
    services = discovery.discover_services(timeout=5)
    
    if services:
        print(f"\n[✓] 发现 {len(services)} 个服务:")
        print("-" * 60)
        for i, service in enumerate(services, 1):
            print(f"\n{i}. {service['name']}")
            print(f"   IP: {service['ip']}:{service['port']}")
            print(f"   操作系统: {service['os']}")
            print(f"   质量: {service['quality']}, 帧率: {service['fps']} FPS")
    else:
        print("\n[i] 未发现任何屏幕共享服务")
        print("[i] 请确保在同一局域网内，并且服务器已启动")
    
    discovery.close()
