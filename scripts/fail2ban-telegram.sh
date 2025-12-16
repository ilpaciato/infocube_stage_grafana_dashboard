#!/bin/bash

TOKEN="8313901235:AAEzgEGbYe-gqptG2elz_YdHQOeHPWPkbZ0"
CHAT_IDS=("266411419" "815953650")  # Sostituisci con i tuoi chat ID

IP=$1
JAIL=$2
ACTION=$3

if [ "$ACTION" == "bannato" ]; then
    MESSAGE="🚨 <b>Fail2Ban Alert</b>%0AIP: <code>$IP</code>%0AJail: <b>$JAIL</b>%0AAction: <b>BANNATO</b>"
elif [ "$ACTION" == "sbannato" ]; then
    MESSAGE="✅ <b>Fail2Ban Alert</b>%0AIP: <code>$IP</code>%0AJail: <b>$JAIL</b>%0AAction: <b>SBANNATO</b>"
else
    MESSAGE="ℹ️ <b>Fail2Ban</b>%0AJail: <b>$JAIL</b>%0AAction: <b>$ACTION</b>"
fi

for CHAT_ID in "${CHAT_IDS[@]}"; do
    curl -s -X POST https://api.telegram.org/bot${TOKEN}/sendMessage \
      -d chat_id=$CHAT_ID \
      -d text="$MESSAGE" \
      -d parse_mode="HTML" > /dev/null 2>&1
done

