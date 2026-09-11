import time
from datetime import datetime, timedelta
import platform
import os
import socket

import psutil
from flask import Blueprint, render_template, jsonify, session, request
from templates.base.database_helper import db
from templates.base.requirements import permissions_required, login_required, get_current_user
from templates.roles.permissions import Permissions
from models import User, Log

bluprint_monitoring_routes = Blueprint('monitoring', __name__, url_prefix='/monitoring')


def get_system_info():
    """Основная информация о системе."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        'hostname': socket.gethostname(),
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'cpu_count': psutil.cpu_count(logical=True),
        'cpu_count_physical': psutil.cpu_count(logical=False),
        'boot_time': boot_time.strftime('%d.%m.%Y %H:%M:%S'),
        'uptime': f'{days}д {hours}ч {minutes}м {seconds}с',
    }


def get_cpu_info():
    """Информация о CPU."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    per_cpu = psutil.cpu_percent(interval=0.5, percpu=True)
    freq = psutil.cpu_freq()

    load_avg = None
    if hasattr(os, 'getloadavg'):
        try:
            load_avg = os.getloadavg()
        except Exception:
            load_avg = None

    return {
        'percent': cpu_percent,
        'per_cpu': per_cpu,
        'freq_current': round(freq.current, 1) if freq else None,
        'freq_min': round(freq.min, 1) if freq else None,
        'freq_max': round(freq.max, 1) if freq else None,
        'load_avg': [round(x, 2) for x in load_avg] if load_avg else None,
    }


def get_memory_info():
    """Информация о памяти."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        'total': mem.total,
        'available': mem.available,
        'used': mem.used,
        'percent': mem.percent,
        'total_gb': round(mem.total / (1024 ** 3), 2),
        'used_gb': round(mem.used / (1024 ** 3), 2),
        'available_gb': round(mem.available / (1024 ** 3), 2),
        'swap_total_gb': round(swap.total / (1024 ** 3), 2),
        'swap_used_gb': round(swap.used / (1024 ** 3), 2),
        'swap_percent': swap.percent,
    }


def get_disk_info():
    """Информация о дисках."""
    disks = []
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'fstype': partition.fstype,
                'total_gb': round(usage.total / (1024 ** 3), 2),
                'used_gb': round(usage.used / (1024 ** 3), 2),
                'free_gb': round(usage.free / (1024 ** 3), 2),
                'percent': usage.percent,
            })
        except PermissionError:
            continue
    return disks


def get_network_info():
    """Информация о сети."""
    net_io = psutil.net_io_counters()
    return {
        'bytes_sent_gb': round(net_io.bytes_sent / (1024 ** 3), 2),
        'bytes_recv_gb': round(net_io.bytes_recv / (1024 ** 3), 2),
        'packets_sent': net_io.packets_sent,
        'packets_recv': net_io.packets_recv,
        'errors_in': net_io.errin,
        'errors_out': net_io.errout,
    }


def get_top_processes(limit=10):
    """Топ процессов по CPU и памяти."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
        try:
            info = p.info
            info['memory_mb'] = round(p.memory_info().rss / (1024 ** 2), 1)
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    procs.sort(key=lambda x: (x.get('cpu_percent') or 0), reverse=True)
    return procs[:limit]


def get_active_sessions_data():
    """Активные сессии из БД (по логам входа)."""
    threshold = datetime.utcnow() - timedelta(minutes=30)

    users = User.query.filter_by(is_active=True).all()
    sessions = []
    for u in users:
        last_log = Log.query.filter(
            Log.user == u.username,
            Log.action.ilike('%вход%')
        ).order_by(Log.timestamp.desc()).first()

        if last_log and last_log.timestamp >= threshold:
            sessions.append({
                'id': u.id,
                'username': u.username,
                'full_name': u.full_name or '—',
                'role': u.role,
                'organization': u.organization.name if u.organization else '—',
                'last_seen': last_log.timestamp.strftime('%d.%m.%Y %H:%M:%S'),
                'action': last_log.action,
            })
    return sessions


# ========== МАРШРУТЫ ==========

@bluprint_monitoring_routes.route('/')
@permissions_required([Permissions.roles_manage])
def index():
    """Главная страница мониторинга."""
    return render_template('monitoring/index.html', info=get_system_info())


@bluprint_monitoring_routes.route('/api/summary')
@permissions_required([Permissions.roles_manage])
def api_summary():
    """Быстрые метрики для автобновления."""
    return jsonify({
        'cpu': get_cpu_info(),
        'memory': get_memory_info(),
        'disks': get_disk_info(),
        'network': get_network_info(),
        'timestamp': datetime.now().strftime('%H:%M:%S'),
    })


@bluprint_monitoring_routes.route('/api/processes')
@permissions_required([Permissions.roles_manage])
def api_processes():
    """Топ процессов."""
    return jsonify({'processes': get_top_processes(15)})


@bluprint_monitoring_routes.route('/api/sessions')
@permissions_required([Permissions.roles_manage])
def api_sessions():
    """Активные сессии."""
    return jsonify({'sessions': get_active_sessions_data()})


@bluprint_monitoring_routes.route('/api/full')
@permissions_required([Permissions.roles_manage])
def api_full():
    """Полная информация."""
    return jsonify({
        'system': get_system_info(),
        'cpu': get_cpu_info(),
        'memory': get_memory_info(),
        'disks': get_disk_info(),
        'network': get_network_info(),
        'processes': get_top_processes(15),
        'sessions': get_active_sessions_data(),
        'timestamp': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
    })