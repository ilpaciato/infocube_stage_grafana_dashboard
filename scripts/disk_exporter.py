#!/usr/bin/env python3
import os
import shutil
from prometheus_client import start_http_server, Gauge, Counter
import time
import subprocess

disk_usage_bytes = Gauge('disk_usage_bytes', 'Disk usage in bytes', ['partition', 'type'])
disk_total_bytes = Gauge('disk_total_bytes', 'Total disk space in bytes', ['partition'])
disk_percent = Gauge('disk_usage_percent', 'Disk usage percentage', ['partition'])
log_dir_size = Gauge('log_directory_size_bytes', 'Size of log directories', ['service'])

def get_disk_metrics():
    stat = shutil.disk_usage('/')
    disk_usage_bytes.labels(partition='/', type='used').set(stat.used)
    disk_usage_bytes.labels(partition='/', type='free').set(stat.free)
    disk_total_bytes.labels(partition='/').set(stat.total)
    disk_percent.labels(partition='/').set((stat.used / stat.total) * 100)

def get_log_sizes():
    log_dirs = {
        'nginx': '/var/log/nginx',
        'mysql': '/var/log/mysql',
        'fail2ban': '/var/log/fail2ban.log',
        'journal': '/var/log/journal',
        'syslog': '/var/log/syslog',
    }
    
    for service, path in log_dirs.items():
        try:
            result = subprocess.run(['du', '-sb', path], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                size = int(result.stdout.split()[0])
                log_dir_size.labels(service=service).set(size)
        except Exception as e:
            pass

def update_metrics():
    while True:
        try:
            get_disk_metrics()
            get_log_sizes()
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Metriche aggiornate")
        except Exception as e:
            print(f"Errore: {e}")
        time.sleep(30)

if __name__ == '__main__':
    start_http_server(9200)
    print("Disk Exporter avviato su http://localhost:9200/metrics")
    update_metrics()
