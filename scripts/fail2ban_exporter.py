#!/usr/bin/env python3

import subprocess
import time
from prometheus_client import start_http_server, Gauge

# Crea la metrica Gauge
banned_ips = Gauge('fail2ban_banned_total', 'Total banned IPs per jail', ['jail'])

def get_fail2ban_status():
    """Raccoglie i dati da fail2ban"""
    try:
        # Ottieni la lista dei jail
        result = subprocess.run(['fail2ban-client', 'status'],
                              capture_output=True, text=True, timeout=5)

        if result.returncode != 0:
            print(f"Errore nel recupero dello stato: {result.stderr}")
            return

        lines = result.stdout.split('\n')
        jails = []

        # Estrai i jail dalla riga "Jail list:"
        for line in lines:
            if 'Jail list:' in line:
                # Prendi tutto dopo "Jail list:" e rimuovi spazi
                jail_part = line.split('Jail list:')[1].strip()
                # Rimuovi le parentesi quadre se presenti
                jail_part = jail_part.strip('[]')
                # Dividi per virgola
                jails = [j.strip() for j in jail_part.split(',')]
                break

        print(f"Jail trovate: {jails}")

        # Per ogni jail, ottieni il numero di IP bannati
        for jail in jails:
            try:
                result = subprocess.run(['fail2ban-client', 'status', jail],
                                      capture_output=True, text=True, timeout=5)

                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Currently banned' in line:
                            # Estrai il numero dopo i due punti
                            banned_count = int(line.split(':')[1].strip())
                            banned_ips.labels(jail=jail).set(banned_count)
                            print(f"Jail '{jail}': {banned_count} bannati")
                            break
            except Exception as e:
                print(f"Errore per jail {jail}: {e}")

    except Exception as e:
        print(f"Errore generale: {e}")

if __name__ == '__main__':
    # Avvia il server HTTP sulla porta 9000
    start_http_server(9000)
    print("Fail2ban Exporter avviato sulla porta 9000")

    # Aggiorna le metriche ogni 15 secondi
    while True:
        get_fail2ban_status()
        time.sleep(15)

