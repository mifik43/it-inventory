import subprocess
import ipaddress
import platform
import socket
import threading
import time
from datetime import datetime
import json

class NetworkScanner:
    def __init__(self):
        self.active_devices = []
        self.scan_progress = 0
        self.is_scanning = False
        
    def ping_sweep(self, network_range, timeout=1):
        """
        Ping сканирование сети
        """
        devices = []
        network = ipaddress.ip_network(network_range, strict=False)
        total_hosts = len(list(network.hosts()))
        scanned_hosts = 0
        
        def ping_host(ip):
            try:
                param = "-n 1 -w {}".format(timeout * 1000) if platform.system().lower() == "windows" else "-c 1 -W {}".format(timeout)
                command = f"ping {param} {ip}"
                response = subprocess.run(
                    command, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL, 
                    shell=True
                )
                return response.returncode == 0
            except:
                return False
        
        threads = []
        results = {}
        
        def check_host(host):
            if ping_host(str(host)):
                device_info = self.get_device_info(str(host))
                devices.append(device_info)
            
            nonlocal scanned_hosts
            scanned_hosts += 1
            self.scan_progress = (scanned_hosts / total_hosts) * 100
        
        # Сканируем все хосты в сети
        for host in network.hosts():
            if not self.is_scanning:
                break
                
            thread = threading.Thread(target=check_host, args=(host,))
            threads.append(thread)
            thread.start()
            
            # Ограничиваем количество одновременных потоков
            if len(threads) >= 50:
                for t in threads:
                    t.join()
                threads = []
        
        # Ждем завершения оставшихся потоков
        for t in threads:
            t.join()
            
        return devices
    
    def arp_scan(self, interface=None):
        """
        ARP сканирование локальной сети
        """
        devices = []
        
        try:
            if platform.system().lower() == "windows":
                # Для Windows используем arp -a
                result = subprocess.run(
                    ["arp", "-a"], 
                    capture_output=True, 
                    text=True, 
                    encoding='cp866'
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'dynamic' in line.lower() or 'static' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                ip = parts[0]
                                mac = parts[1]
                                if self.is_valid_ip(ip) and self.is_valid_mac(mac):
                                    device_info = self.get_device_info(ip)
                                    device_info['mac_address'] = mac
                                    device_info['vendor'] = self.get_vendor_from_mac(mac)
                                    devices.append(device_info)
            
            else:
                # Для Linux используем arp-scan или ip neighbor
                try:
                    result = subprocess.run(
                        ["arp-scan", "--localnet"], 
                        capture_output=True, 
                        text=True
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 2 and self.is_valid_ip(parts[0]):
                                ip = parts[0]
                                mac = parts[1]
                                device_info = self.get_device_info(ip)
                                device_info['mac_address'] = mac
                                device_info['vendor'] = ' '.join(parts[2:]) if len(parts) > 2 else ''
                                devices.append(device_info)
                except:
                    # Fallback на ip neighbor
                    result = subprocess.run(
                        ["ip", "neighbor", "show"], 
                        capture_output=True, 
                        text=True
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 5 and parts[3] == "REACHABLE":
                                ip = parts[0]
                                mac = parts[4]
                                device_info = self.get_device_info(ip)
                                device_info['mac_address'] = mac
                                devices.append(device_info)
                                
        except Exception as e:
            print(f"ARP scan error: {e}")
            
        return devices
    
    def port_scan(self, ip, ports="21,22,23,80,443,3389,8080"):
        """
        Сканирование портов устройства
        """
        open_ports = []
        
        def check_port(port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex((ip, port))
                    if result == 0:
                        open_ports.append(port)
            except:
                pass
        
        threads = []
        port_list = [int(p.strip()) for p in ports.split(',')]
        
        for port in port_list:
            if not self.is_scanning:
                break
            thread = threading.Thread(target=check_port, args=(port,))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        return sorted(open_ports)
    
    def get_device_info(self, ip):
        """
        Получение информации об устройстве
        """
        device_info = {
            'ip_address': ip,
            'hostname': 'Unknown',
            'mac_address': 'Unknown',
            'vendor': 'Unknown',
            'os_info': 'Unknown',
            'response_time': 0,
            'ports': []
        }
        
        try:
            # Получаем hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                device_info['hostname'] = hostname
            except:
                pass
            
            # Измеряем время ответа
            start_time = time.time()
            param = "-n 1 -w 1000" if platform.system().lower() == "windows" else "-c 1 -W 1"
            result = subprocess.run(
                f"ping {param} {ip}", 
                capture_output=True, 
                shell=True
            )
            end_time = time.time()
            
            if result.returncode == 0:
                device_info['response_time'] = round((end_time - start_time) * 1000, 2)
            
            # Сканируем порты (только основные)
            device_info['ports'] = self.port_scan(ip, "21,22,23,80,443,3389,8080")
            
        except Exception as e:
            print(f"Error getting device info for {ip}: {e}")
        
        return device_info
    
    def is_valid_ip(self, ip):
        """Проверка валидности IP-адреса"""
        try:
            ipaddress.ip_address(ip)
            return True
        except:
            return False
    
    def is_valid_mac(self, mac):
        """Проверка валидности MAC-адреса"""
        import re
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return bool(mac_pattern.match(mac))
    
    def get_vendor_from_mac(self, mac):
        """Определение производителя по MAC (упрощенная версия)"""
        # В реальном приложении можно использовать базу OUI
        vendors = {
            '00:50:56': 'VMware',
            '00:0C:29': 'VMware',
            '00:1C:42': 'Parallels',
            '00:16:3E': 'Xen',
            '00:15:5D': 'Microsoft Hyper-V',
            '00:1B:21': 'Cisco',
            '00:1E:68': 'Cisco',
            '00:24:81': 'Cisco',
            '00:26:0B': 'Cisco',
            '00:50:BA': 'D-Link',
            '00:1C:F0': 'Netgear',
            '00:26:F2': 'Netgear',
            '00:1E:2A': 'TP-Link',
            '00:1D:0F': 'TP-Link',
            '00:23:CD': 'TP-Link',
            '00:08:22': 'Samsung',
            '00:12:FB': 'Samsung',
            '00:1C:43': 'Samsung',
            '00:26:5C': 'Samsung',
            '00:E0:4C': 'Realtek',
            '00:13:D4': 'Realtek',
            '00:14:D1': 'Realtek',
            '00:17:31': 'ASUS',
            '00:1D:60': 'ASUS',
            '00:26:18': 'ASUS'
        }
        
        mac_prefix = mac.replace('-', ':').upper()[:8]
        return vendors.get(mac_prefix, 'Unknown')
    
    def start_scan(self, scan_type, target):
        """
        Запуск сканирования
        """
        self.is_scanning = True
        self.scan_progress = 0
        devices = []
        
        try:
            if scan_type == 'ping':
                devices = self.ping_sweep(target)
            elif scan_type == 'arp':
                devices = self.arp_scan()
            elif scan_type == 'custom':
                # Можно добавить кастомное сканирование
                devices = self.ping_sweep(target)
            
            self.scan_progress = 100
            
        except Exception as e:
            print(f"Scan error: {e}")
        finally:
            self.is_scanning = False
            
        return devices