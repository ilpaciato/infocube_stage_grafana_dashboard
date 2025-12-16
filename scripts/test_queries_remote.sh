#!/bin/bash

# =========================================================
# 0. PRE-CHECK: Esecuzione come Root
# =========================================================
if [ "$EUID" -ne 0 ]
  then echo "❌ Errore: Per favore esegui questo script con 'sudo'"
  exit
fi

# =========================================================
# 1. CONFIGURAZIONE
# =========================================================
MODSEC_LOG="/var/log/nginx/modsec_audit.log"
FAIL2BAN_LOG="/var/log/fail2ban.log"
AUTH_LOG="/var/log/auth.log"
NGINX_ACCESS_LOG="/var/log/nginx/access.log"

# Variabili Tempo (CORRETTE: Usano l'ora locale, non UTC)
TIMESTAMP_ISO=$(date +%Y-%m-%dT%H:%M:%S%z)       # Formato ISO per JSON
TIMESTAMP_SYSLOG=$(date +'%b %d %H:%M:%S')       # Formato Syslog (Nov 18 15:00:00)
TIMESTAMP_FAIL2BAN=$(date +'%Y-%m-%d %H:%M:%S')  # Formato Fail2ban
TIMESTAMP_NGINX=$(date +'%d/%b/%Y:%H:%M:%S %z')  # Formato Nginx Log

# Dati Simulati
TEST_IP="192.168.1.100"
TEST_URI="/api/v1/user/login"

# Reset ModSecurity (CORRETTO: Svuota senza creare righe vuote)
> $MODSEC_LOG

echo "--- 🚀 Script di Test Monitoraggio Avviato (Timezone Locale) ---"

# =========================================================
# 2. TEST LOGQL (ModSecurity)
# Query: {job="modsecurity"} | regexp ...
# =========================================================
echo "1. Simulazione attacco ModSecurity..."

# JSON Payload (Formato piatto come da tuo ultimo test)
MODSEC_PAYLOAD="{\"client_ip\":\"${TEST_IP}\",\"time_stamp\":\"${TIMESTAMP_ISO}\",\"uri\":\"${TEST_URI}\",\"message\":\"SQL Injection attempt detected (SQLi)\"}"

echo $MODSEC_PAYLOAD | tee -a $MODSEC_LOG
echo "   ✅ Scritto in: $MODSEC_LOG"
sleep 1

# =========================================================
# 3. TEST LOGQL (Fail2ban)
# Query: sum by (job) (... |= "fail2ban.actions" ...)
# =========================================================
echo "2. Simulazione ban Fail2ban..."

FAIL2BAN_MESSAGE="$TIMESTAMP_FAIL2BAN fail2ban.actions: [sshd] Ban 1.2.3.4"

echo $FAIL2BAN_MESSAGE | tee -a $FAIL2BAN_LOG
echo "   ✅ Scritto in: $FAIL2BAN_LOG"
sleep 1

# =========================================================
# 4. TEST LOGQL (Errori Generici & Specifica "error")
# Query: ... |~ "Failed password" ...
# Query: ... |= "error" ...
# =========================================================
echo "3. Simulazione errori Nginx/Auth..."

# a) Auth Error (Modificato per includere la parola "error")
AUTH_ERROR_MESSAGE="$TIMESTAMP_SYSLOG ict-campus-lab sshd[1234]: error: Failed password for invalid user root from ${TEST_IP} port 22 ssh2"
echo $AUTH_ERROR_MESSAGE | tee -a $AUTH_LOG
echo "   ✅ Scritto in: $AUTH_LOG (Include 'error' e 'Failed password')"

# b) Nginx Error (404)
NGINX_404_MESSAGE="$TEST_IP - - [$TIMESTAMP_NGINX] \"GET /nonexistent HTTP/1.1\" 404 153 \"-\" \"Mozilla\""
echo $NGINX_404_MESSAGE | tee -a $NGINX_ACCESS_LOG
echo "   ✅ Scritto in: $NGINX_ACCESS_LOG"

sleep 1

# =========================================================
# 5. CHECK METRICHE
# =========================================================
echo "4. Node Exporter check..."
echo "   Le metriche di rete (node_network_receive_bytes_total) sono raccolte automaticamente da Prometheus."

# =========================================================
# 6. FORZATURA INVIO (Restart Promtail)
# =========================================================
echo "--- 🔄 Riavvio Promtail per forzare l'invio immediato dei log... ---"
systemctl restart promtail

echo "--- ✅ Script Completato! ---"
echo "Vai su Grafana (Last 5 minutes) e verifica i dati."
