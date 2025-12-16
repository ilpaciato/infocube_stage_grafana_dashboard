#!/bin/bash

# ============================================
# Fail2ban Telegram Notification
# READ-ONLY + UNBAN ONLY
# MULTI-USER VERSION WITH UNIFIED TEMPLATE
# ============================================

telegramBotToken='8313901235:AAEzgEGbYe-gqptG2elz_YdHQOeHPWPkbZ0'

# Lista di tutti i chat ID che riceveranno le notifiche
CHAT_IDS=(
    815953650
    266411419
)

function talkToBot() {
    local message=$1
    
    # Invia il messaggio a TUTTI i chat ID nella lista
    for chat_id in "${CHAT_IDS[@]}"; do
        curl -s -X POST https://api.telegram.org/bot${telegramBotToken}/sendMessage \
            -d text="$message" \
            -d chat_id=${chat_id} > /dev/null 2>&1
    done
}

convert_seconds() {
    local seconds=$1
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    local secs=$((seconds % 60))

    if [ $hours -gt 0 ]; then
        echo "${hours}h ${minutes}m"
    elif [ $minutes -gt 0 ]; then
        echo "${minutes}m ${secs}s"
    else
        echo "${secs}s"
    fi
}

# Dizionario con descrizioni dettagliate degli attacchi
# Formato: attack_type[jail]="Titolo Attacco"
declare -A attack_type
attack_type[sshd]="Tentativo di accesso non autorizzato SSH"
attack_type[apache-auth]="Fallimento autenticazione Apache"
attack_type[apache-noscript]="Script non autorizzati su Apache"
attack_type[nginx-http-auth]="Fallimento autenticazione Nginx"
attack_type[nginx-noscript]="Script non autorizzati su Nginx"
attack_type[nginx-badbots]="Bot malintenzionati rilevati"
attack_type[modsecurity]="Tentativo di attacco WAF rilevato"
attack_type[modsec-json]="Attacco JSON su ModSecurity"
attack_type[nginx-sql-injection]="Tentativo di SQL injection rilevato"
attack_type[nginx-rfi]="Remote File Inclusion rilevato"
attack_type[nginx-lfi]="Local File Inclusion rilevato"
attack_type[default]="Attacco non categorizzato"

[ $# -eq 0 ] && { echo "Usage: $0 -b <ip> -j <jail> -t <bantime> | -u <ip> -j <jail>"; exit 1; }

while getopts "b:u:j:t:" opt; do
    case "$opt" in
        b) ban=y; ip_add_ban=$OPTARG ;;
        u) unban=y; ip_add_unban=$OPTARG ;;
        j) jail=$OPTARG ;;
        t) bantime=$OPTARG ;;
    esac
done

# ========== BAN - TEMPLATE UNIFICATO ==========

if [[ "$ban" == "y" ]]; then
    # Ottieni il titolo dell'attacco
    attack_title="${attack_type[$jail]:-${attack_type[default]}}"
    ban_duration=$(convert_seconds "$bantime")

    message="🚨 $attack_title
━━━━━━━━━━━━━━━━━━━━━━
🎯 IP ATTACCANTE: $ip_add_ban

📁 JAIL: $jail

⏱️ DURATA BAN: $ban_duration

⏰ TIMESTAMP: $(date '+%Y-%m-%d %H:%M:%S')"

    talkToBot "$message"
    exit 0

# ========== UNBAN - NOTIFICA ==========

elif [[ "$unban" == "y" ]]; then

    message="✅ IP SBANNATO
━━━━━━━━━━━━━━━━━━━━━━

📁 JAIL: $jail

🎯 IP: $ip_add_unban

⏰ TIMESTAMP: $(date '+%Y-%m-%d %H:%M:%S')"

    talkToBot "$message"
    exit 0

fi
