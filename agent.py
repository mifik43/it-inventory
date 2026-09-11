#!/usr/bin/env python3
import json
import platform
import socket
import psutil
import requests
from datetime import datetime

# Настройки
SERVER_URL = "http://192.168.23.148:5000/api/submit"  # замените на IP вашего сервера

def correct_size(bts, ending='iB'):
    size = 1024
    for item in ["", "K", "M", "G", "T", "P"]:
        if bts < size:
            return f"{bts:.2f}{item}{ending}"
        bts /= size
    return f"{bts:.2f}P{ending}"

def get_system_info():
    info = {}

    # Система
    info["hostname"] = platform.node()
    info["os"] = f"{platform.system()} {platform.release()}"
    info["kernel"] = platform.version()
    info["machine"] = platform.machine()
    info["system"] = platform.system()
    info["timestamp"] = datetime.now().isoformat()

    # CPU
    cpu = {
        "model": platform.processor() or "Unknown",
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "max_frequency_mhz": psutil.cpu_freq().max if psutil.cpu_freq() else None
    }
    info["cpu"] = cpu

    # RAM
    mem = psutil.virtual_memory()
    info["memory"] = {
        "total_gb": round(mem.total / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "percent": mem.percent
    }

    # Диски
    disks = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            })
        except PermissionError:
            continue
    info["disks"] = disks
    info["disk_count"] = len(disks)

    # GPU (упрощённо через lspci на Linux, WMI на Windows)
    gpu = []
    if platform.system() == "Windows":
        try:
            import wmi
            w = wmi.WMI()
            for g in w.Win32_VideoController():
                gpu.append({"name": g.Name, "driver": g.DriverVersion})
        except:
            pass
    elif platform.system() == "Linux":
        try:
            out = subprocess.check_output("lspci | grep -i vga", shell=True).decode().strip()
            if out:
                gpu.append({"name": out})
        except:
            pass
    info["gpu"] = gpu if gpu else "None"

    # Сетевые интерфейсы
    net = []
    for ifname, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                mac = addr.address
            elif addr.family == socket.AF_INET:
                ip = addr.address
        net.append({
            "interface": ifname,
            "ip": ip if 'ip' in locals() else None,
            "mac": mac if 'mac' in locals() else None
        })
    info["network"] = net

    return info

def send_data(data):
    try:
        response = requests.post(SERVER_URL, json=data, timeout=10)
        if response.status_code == 200:
            print("Данные успешно отправлены")
        else:
            print(f"Ошибка отправки: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Не удалось отправить данные: {e}")

if __name__ == "__main__":
    data = get_system_info()
    print("Собранная информация:")
    print(json.dumps(data, indent=4, ensure_ascii=False))
    send_data(data)