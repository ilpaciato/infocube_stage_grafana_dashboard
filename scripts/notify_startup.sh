#!/bin/bash

# ============================================
# Notifica Avvio Fail2ban - VERSIONE CORRETTA
# ============================================

telegramBotToken='8313901235:AAEzgEGbYe-gqptG2elz_YdHQOeHPWPkbZ0'
telegramChatID='815953650'

# Aspetta che fail2ban sia completamente pronto
sleep 3

# Raccogli tutte le jail attive in UNA SOLA RIGA
jail_list=$(/usr/bin/fail2ban-client status 2>/dev/null | grep "Jail list" | sed 's/.*Jail list:\s*//' | sed 's/,//g')

if [ -n "$jail_list" ]; then
    # Formatta con bullet points - TUTTE LE JAIL IN UN UNICO MESSAGGIO
    formatted=$(echo "$jail_list" | tr ' ' '\n' | sed '/^$/d' | sed 's/^/• /')

    message="🔐 FAIL2BAN AVVIATO
━━━━━━━━━━━━━━━━━━━━━━
✅ Jail Attive:
$formatted

⏰ Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

    # INVIO UNICO - UN SOLO MESSAGGIO
    curl -s -X POST "https://api.telegram.org/bot${telegramBotToken}/sendMessage" \
        -d "text=$message" \
        -d "chat_id=${telegramChatID}" \
        -d "parse_mode=Markdown" > /dev/null 2>&1

    exit 0
else
    exit 1
fi
