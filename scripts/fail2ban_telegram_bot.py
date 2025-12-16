#!/home/infocube/fail2ban-bot-env/bin/python3

import telebot
import subprocess
import logging
from datetime import datetime
from telebot import types

# ⚠️ SOSTITUISCI CON IL NUOVO TOKEN
BOT_TOKEN = "Yuor-New-Telegram-Bot-Token-Here"

# 📱 LISTA DI TUTTI I CHAT ID CHE RICEVERANNO LE NOTIFICHE
ADMIN_CHAT_IDS = [
    "Your-Chat-ID"      # L'altro PC (aggiungi qui il chat ID)
    # Aggiungi altri chat ID qui se necessario
]

LOG_FILE = '/var/log/fail2ban-bot.log'

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

bot = telebot.TeleBot(BOT_TOKEN)

# ========== FUNZIONI UTILITY ==========

def send_to_all_chats(message_text, parse_mode='Markdown'):
    """Invia un messaggio a TUTTI i chat ID nella lista"""
    for chat_id in ADMIN_CHAT_IDS:
        try:
            bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode=parse_mode
            )
            logging.info(f"Notifica inviata a chat_id: {chat_id}")
        except Exception as e:
            logging.error(f"Errore invio notifica a {chat_id}: {str(e)}")

def get_fail2ban_status():
    """Ottieni status completo di fail2ban"""
    try:
        result = subprocess.run(
            "sudo fail2ban-client status",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        logging.error(f"Errore get_fail2ban_status: {str(e)}")
        return None

def get_jails_list():
    """Ottieni lista di tutte le jail"""
    try:
        result = subprocess.run(
            "sudo fail2ban-client status",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse: "Jail list: sshd, nginx-http-auth, ..."
            for line in result.stdout.split('\n'):
                if 'Jail list:' in line:
                    jails_str = line.split('Jail list:')[1].strip()
                    return [j.strip() for j in jails_str.split(',') if j.strip()]
        return []
    except Exception as e:
        logging.error(f"Errore get_jails_list: {str(e)}")
        return []

def get_jail_info(jail_name):
    """Ottieni info dettagliate di una jail (IPs bannati)"""
    try:
        result = subprocess.run(
            f"sudo fail2ban-client status {jail_name}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        logging.error(f"Errore get_jail_info: {str(e)}")
        return None

def get_currently_banned_count(jail_name):
    """Ottieni il numero di IPs attualmente bannati in una jail"""
    try:
        info = get_jail_info(jail_name)
        if not info:
            return 0
        
        for line in info.split('\n'):
            if 'Currently banned:' in line:
                return int(line.split(':')[1].strip())
        return 0
    except Exception as e:
        logging.error(f"Errore get_currently_banned_count: {str(e)}")
        return 0

def get_jails_with_bans():
    """Ottieni SOLO le jail che hanno IPs bannati"""
    try:
        all_jails = get_jails_list()
        jails_with_bans = []
        
        for jail in all_jails:
            banned_count = get_currently_banned_count(jail)
            if banned_count > 0:
                jails_with_bans.append((jail, banned_count))
        
        return jails_with_bans
    except Exception as e:
        logging.error(f"Errore get_jails_with_bans: {str(e)}")
        return []

def get_total_banned_ips():
    """Ottieni il numero TOTALE di IPs bannati in TUTTE le jail"""
    try:
        jails_with_bans = get_jails_with_bans()
        return sum(count for _, count in jails_with_bans)
    except Exception as e:
        logging.error(f"Errore get_total_banned_ips: {str(e)}")
        return 0

def unban_ip(jail, ip):
    """Sbanna un IP da una jail"""
    try:
        result = subprocess.run(
            f"sudo fail2ban-client set {jail} unbanip {ip}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def unban_all_jail(jail):
    """Sbanna TUTTI gli IP da una jail"""
    try:
        # Ottieni lista IPs
        info = get_jail_info(jail)
        if not info:
            return False, "Impossibile recuperare IPs"
        
        ips = []
        for line in info.split('\n'):
            if 'Banned IP list:' in line:
                ip_str = line.split('Banned IP list:')[1].strip()
                ips = [ip.strip() for ip in ip_str.split() if ip.strip()]
                break
        
        if not ips:
            return True, "Nessun IP bannato in questa jail"
        
        # Sbanna tutti
        failed = []
        for ip in ips:
            success, _ = unban_ip(jail, ip)
            if not success:
                failed.append(ip)
        
        if failed:
            return False, f"Sbannati: {len(ips)-len(failed)}/{len(ips)}. Falliti: {', '.join(failed)}"
        else:
            return True, f"Tutti {len(ips)} IPs sbannati da {jail}"
    
    except Exception as e:
        logging.error(f"Errore unban_all_jail: {str(e)}")
        return False, str(e)

def unban_all_global_ips():
    """Sbanna TUTTI gli IPs da TUTTE le jail"""
    try:
        jails_with_bans = get_jails_with_bans()
        
        if not jails_with_bans:
            return True, "Nessun IP bannato in alcuna jail"
        
        total_ips = 0
        total_failed = 0
        failed_jails = []
        
        for jail, _ in jails_with_bans:
            info = get_jail_info(jail)
            if not info:
                continue
            
            ips = []
            for line in info.split('\n'):
                if 'Banned IP list:' in line:
                    ip_str = line.split('Banned IP list:')[1].strip()
                    ips = [ip.strip() for ip in ip_str.split() if ip.strip()]
                    break
            
            for ip in ips:
                total_ips += 1
                success, _ = unban_ip(jail, ip)
                if not success:
                    total_failed += 1
                    failed_jails.append((jail, ip))
        
        if total_failed == 0:
            return True, f"✅ Tutti {total_ips} IPs sbannati da tutte le jail!"
        else:
            return False, f"Sbannati: {total_ips - total_failed}/{total_ips}. Falliti: {total_failed}"
    
    except Exception as e:
        logging.error(f"Errore unban_all_global_ips: {str(e)}")
        return False, str(e)

# ========== COMANDO /start ==========

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
🔐 *Fail2ban Telegram Monitor v2*
━━━━━━━━━━━━━━━━━━━━━━

*MODALITÀ: READ-ONLY + UNBAN INTERATTIVO*

📢 Riceverai notifiche automatiche:
• 🔐 Avvio del servizio
• 🚨 Quando un IP viene bannato
• ✅ Quando un IP viene sbannato

✅ Comandi disponibili:
• /status - Status con BOTTONI unban
• /unban <ip> -j <jail> - Sbanna manualmente
• /help - Lista comandi

💡 *NOVITÀ:* Click direttamente sui pulsanti per sbannare!
    """
    bot.reply_to(message, welcome_text, parse_mode='Markdown')
    logging.info(f"User {message.chat.id} ha richiesto /start")

# ========== COMANDO /status CON INLINE BUTTONS - SOLO JAIL CON BAN ==========

@bot.message_handler(commands=['status'])
def send_status(message):
    try:
        jails_with_bans = get_jails_with_bans()
        
        if not jails_with_bans:
            bot.reply_to(message, """
✅ *TUTTO OK!*
━━━━━━━━━━━━━━━━━━━━━━

🟢 Nessuna jail ha IPs bannati al momento.

Le notifiche appariranno quando un IP verrà bannato.
            """, parse_mode='Markdown')
            logging.info(f"User {message.chat.id} ha richiesto /status - Nessuna jail con ban")
            return
        
        # Calcola totale IPs
        total_ips = sum(count for _, count in jails_with_bans)
        
        # Messaggio principale
        status_text = f"""
📊 *FAIL2BAN STATUS - JAIL CON BAN*
━━━━━━━━━━━━━━━━━━━━━━

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*🚨 Jail Attive con Ban:* {len(jails_with_bans)}
*🚫 IPs Bannati Totali:* {total_ips}

━━━━━━━━━━━━━━━━━━━━━━

Clicca su una jail per vedere gli IPs bannati e sbannarli:
        """
        
        # Inline keyboard - 1 pulsante per jail con ban
        markup = types.InlineKeyboardMarkup()
        for jail, ban_count in jails_with_bans:
            btn = types.InlineKeyboardButton(
                text=f"📁 {jail} ({ban_count}🚫)",
                callback_data=f"view_jail:{jail}"
            )
            markup.add(btn)
        
        # Divider
        markup.add(types.InlineKeyboardButton(
            text="━━━━━━━━━━━━━━━━━━",
            callback_data="noop"
        ))
        
        # Sbanna TUTTO globale
        markup.add(types.InlineKeyboardButton(
            text=f"🚀 SBANNA TUTTO ({total_ips})",
            callback_data="unban_all_global"
        ))
        
        bot.send_message(
            message.chat.id,
            status_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        logging.info(f"User {message.chat.id} ha richiesto /status - {len(jails_with_bans)} jail con ban, {total_ips} IPs totali")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Errore: {str(e)}")
        logging.error(f"Errore /status: {str(e)}")

# ========== CALLBACK: Mostra IPs di una jail ==========

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_jail:'))
def view_jail(call):
    try:
        jail_name = call.data.split(':')[1]
        info = get_jail_info(jail_name)
        
        if not info:
            bot.answer_callback_query(call.id, "❌ Errore nel recuperare info", show_alert=True)
            return
        
        # Parse info
        currently_banned = 0
        ips = []
        for line in info.split('\n'):
            if 'Currently banned:' in line:
                currently_banned = int(line.split(':')[1].strip())
            elif 'Banned IP list:' in line:
                ip_str = line.split('Banned IP list:')[1].strip()
                ips = [ip.strip() for ip in ip_str.split() if ip.strip()]
        
        # Messaggio
        detail_text = f"""
📁 *JAIL: {jail_name}*
━━━━━━━━━━━━━━━━━━━━━━

🚫 IPs Bannati: {currently_banned}
        """
        
        if currently_banned == 0:
            detail_text += "\n✅ Nessun IP bannato!"
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=detail_text,
                parse_mode='Markdown'
            )
            return
        
        detail_text += f"\n\n*IPs:*\n"
        for ip in ips:
            detail_text += f"• `{ip}`\n"
        
        # Keyboard con pulsanti per ogni IP + bottone sbanna tutto
        markup = types.InlineKeyboardMarkup()
        
        for ip in ips:
            btn = types.InlineKeyboardButton(
                text=f"🔓 {ip}",
                callback_data=f"unban_ip:{jail_name}:{ip}"
            )
            markup.add(btn)
        
        # Divider
        markup.add(types.InlineKeyboardButton(
            text="━━━━━━━━━━━━━━━━━━",
            callback_data="noop"
        ))
        
        # Sbanna TUTTI
        markup.add(types.InlineKeyboardButton(
            text=f"🚀 SBANNA TUTTI ({currently_banned})",
            callback_data=f"unban_all:{jail_name}"
        ))
        
        # Torna a status
        markup.add(types.InlineKeyboardButton(
            text="← Torna a Status",
            callback_data="back_to_status"
        ))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=detail_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Errore: {str(e)}", show_alert=True)
        logging.error(f"Errore view_jail: {str(e)}")

# ========== CALLBACK: Sbanna singolo IP ==========

@bot.callback_query_handler(func=lambda call: call.data.startswith('unban_ip:'))
def unban_single_ip(call):
    try:
        parts = call.data.split(':')
        jail = parts[1]
        ip = parts[2]
        
        # Sbanna
        success, message = unban_ip(jail, ip)
        
        if success:
            result_text = f"""
✅ *UNBAN ESEGUITO*
━━━━━━━━━━━━━━━━━━━━━━

🎯 IP: `{ip}`
📁 Jail: {jail}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            bot.answer_callback_query(call.id, f"✅ {ip} sbannato!", show_alert=True)
            logging.info(f"IP {ip} sbannato da {jail}")
            
            # 📢 INVIA NOTIFICA A TUTTI
            send_to_all_chats(result_text)
        else:
            result_text = f"""
❌ *ERRORE UNBAN*
━━━━━━━━━━━━━━━━━━━━━━

🎯 IP: `{ip}`
📁 Jail: {jail}
📋 Errore: {message}
            """
            bot.answer_callback_query(call.id, f"❌ Errore: {message}", show_alert=True)
            logging.error(f"Errore unban {ip}: {message}")
            
            # 📢 INVIA NOTIFICA ERRORE A TUTTI
            send_to_all_chats(result_text)
        
        # Aggiorna messaggio
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=result_text,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Errore: {str(e)}", show_alert=True)
        logging.error(f"Errore unban_single_ip: {str(e)}")

# ========== CALLBACK: Sbanna TUTTI gli IPs di una jail ==========

@bot.callback_query_handler(func=lambda call: call.data.startswith('unban_all:'))
def unban_all_ips(call):
    try:
        jail = call.data.split(':')[1]
        
        # Sbanna tutti
        success, message = unban_all_jail(jail)
        
        if success:
            result_text = f"""
✅ *UNBAN MASSIVO ESEGUITO*
━━━━━━━━━━━━━━━━━━━━━━

📁 Jail: {jail}
📋 {message}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            bot.answer_callback_query(call.id, f"✅ {message}", show_alert=True)
            logging.info(f"Sbannati tutti gli IPs da {jail}")
            
            # 📢 INVIA NOTIFICA A TUTTI
            send_to_all_chats(result_text)
        else:
            result_text = f"""
⚠️ *UNBAN PARZIALE / ERRORE*
━━━━━━━━━━━━━━━━━━━━━━

📁 Jail: {jail}
📋 {message}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            bot.answer_callback_query(call.id, f"⚠️ {message}", show_alert=True)
            logging.error(f"Errore unban_all {jail}: {message}")
            
            # 📢 INVIA NOTIFICA A TUTTI
            send_to_all_chats(result_text)
        
        # Aggiorna messaggio
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=result_text,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Errore: {str(e)}", show_alert=True)
        logging.error(f"Errore unban_all_ips: {str(e)}")

# ========== CALLBACK: Sbanna TUTTO GLOBALMENTE ==========

@bot.callback_query_handler(func=lambda call: call.data == 'unban_all_global')
def unban_all_globally_callback(call):
    try:
        total_before = get_total_banned_ips()
        
        # Sbanna tutto globalmente - CHIAMA LA FUNZIONE CON IL NOME CORRETTO
        success, message = unban_all_global_ips()
        
        if success:
            result_text = f"""
✅ *UNBAN GLOBALE ESEGUITO*
━━━━━━━━━━━━━━━━━━━━━━

🌍 Operazione Globale
📋 {message}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            bot.answer_callback_query(call.id, f"✅ {message}", show_alert=True)
            logging.info(f"Sbannati GLOBALMENTE tutti gli IPs: {total_before} IPs in totale")
            
            # 📢 INVIA NOTIFICA A TUTTI
            send_to_all_chats(result_text)
        else:
            result_text = f"""
⚠️ *UNBAN GLOBALE PARZIALE / ERRORE*
━━━━━━━━━━━━━━━━━━━━━━

🌍 Operazione Globale
📋 {message}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            bot.answer_callback_query(call.id, f"⚠️ {message}", show_alert=True)
            logging.error(f"Errore unban_all_global_ips: {message}")
            
            # 📢 INVIA NOTIFICA A TUTTI
            send_to_all_chats(result_text)
        
        # Aggiorna messaggio
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=result_text,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Errore: {str(e)}", show_alert=True)
        logging.error(f"Errore unban_all_globally_callback: {str(e)}")

# ========== CALLBACK: Torna a Status ==========

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_status')
def back_to_status(call):
    try:
        jails_with_bans = get_jails_with_bans()
        
        if not jails_with_bans:
            status_text = """
✅ *TUTTO OK!*
━━━━━━━━━━━━━━━━━━━━━━

🟢 Nessuna jail ha IPs bannati al momento.
            """
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=status_text,
                parse_mode='Markdown'
            )
            return
        
        total_ips = sum(count for _, count in jails_with_bans)
        
        status_text = f"""
📊 *FAIL2BAN STATUS - JAIL CON BAN*
━━━━━━━━━━━━━━━━━━━━━━

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*🚨 Jail Attive con Ban:* {len(jails_with_bans)}
*🚫 IPs Bannati Totali:* {total_ips}

━━━━━━━━━━━━━━━━━━━━━━

Clicca su una jail per vedere gli IPs bannati:
        """
        
        markup = types.InlineKeyboardMarkup()
        for jail, ban_count in jails_with_bans:
            btn = types.InlineKeyboardButton(
                text=f"📁 {jail} ({ban_count}🚫)",
                callback_data=f"view_jail:{jail}"
            )
            markup.add(btn)
        
        # Divider
        markup.add(types.InlineKeyboardButton(
            text="━━━━━━━━━━━━━━━━━━",
            callback_data="noop"
        ))
        
        # Sbanna TUTTO globale
        markup.add(types.InlineKeyboardButton(
            text=f"🚀 SBANNA TUTTO ({total_ips})",
            callback_data="unban_all_global"
        ))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=status_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Errore back_to_status: {str(e)}")

# ========== CALLBACK: No-op ==========

@bot.callback_query_handler(func=lambda call: call.data == 'noop')
def noop(call):
    bot.answer_callback_query(call.id)

# ========== COMANDO /unban (LEGACY) ==========

@bot.message_handler(commands=['unban'])
def unban_ip_legacy(message):
    try:
        args = message.text.split()
        
        if len(args) < 4 or args[2] != '-j':
            bot.reply_to(message, """
❌ Formato errato!

Usa: /unban <ip> -j <jail>

Esempio:
/unban 192.168.1.100 -j sshd
/unban 10.0.0.5 -j nginx-http-auth

💡 O usa /status per i pulsanti interattivi!
            """)
            return
        
        ip = args[1]
        jail = args[3]
        
        # Valida IP
        parts = ip.split('.')
        if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            bot.reply_to(message, f"❌ IP non valido: {ip}")
            return
        
        # Sbanna
        success, msg = unban_ip(jail, ip)
        
        if success:
            response = f"""
✅ *UNBAN ESEGUITO*
━━━━━━━━━━━━━━━━━━━━━━

🎯 IP: `{ip}`
📁 Jail: {jail}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            logging.info(f"User {message.chat.id} sbannato {ip} da {jail}")
            
            # 📢 INVIA NOTIFICA A TUTTI
            send_to_all_chats(response)
        else:
            response = f"""
❌ *ERRORE UNBAN*
━━━━━━━━━━━━━━━━━━━━━━

🎯 IP: `{ip}`
📁 Jail: {jail}
📋 Errore: {msg}
            """
            logging.error(f"Errore unban {ip}: {msg}")
            
            # 📢 INVIA NOTIFICA A TUTTI
            send_to_all_chats(response)
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Errore: {str(e)}")
        logging.error(f"Errore /unban: {str(e)}")

# ========== COMANDO /help ==========

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
📖 *Comandi Disponibili*
━━━━━━━━━━━━━━━━━━━━━━

**/status**
Mostra solo le jail che hanno IPs bannati
Clicca su una jail per vedere i dettagli

**/unban <ip> -j <jail>**
Sbanna manualmente un IP
Esempio: `/unban 192.168.1.100 -j sshd`

**/help**
Questo messaggio

━━━━━━━━━━━━━━━━━━━━━━

*🎯 FUNZIONALITÀ:*

✅ Mostra SOLO jail con IPs bannati
✅ Inline buttons per scegliere jail
✅ Lista interattiva di IPs bannati
✅ Sbanna singolo IP con 1 click
✅ Sbanna TUTTI gli IPs di una jail
✅ 🚀 **SBANNA TUTTO** - Sbanna tutte le jail in una azione!
✅ 📢 **Notifiche a più device** - Le notifiche arrivano a entrambi i PC!
✅ Notifiche automatiche di ban/unban

*⚠️ MODALITÀ: READ-ONLY + UNBAN INTERATTIVO*
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

# ========== HANDLER MESSAGGI SCONOSCIUTI ==========

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    response = """
❓ Comando non riconosciuto

Comandi disponibili:
/start - Benvenuto
/status - Status con pulsanti (solo jail con ban)
/unban <ip> -j <jail> - Sbanna manualmente
/help - Lista comandi
    """
    bot.reply_to(message, response)

# ========== MAIN ==========

if __name__ == '__main__':
    logging.info("Bot avviato in MODALITÀ READ-ONLY + UNBAN INTERATTIVO")
    logging.info(f"Notifiche inviate a {len(ADMIN_CHAT_IDS)} chat(s): {ADMIN_CHAT_IDS}")
    print(f"✅ Bot avviato - Modalità: READ-ONLY + UNBAN INTERATTIVO")
    print(f"📱 Notifiche inviate a {len(ADMIN_CHAT_IDS)} chat(s): {ADMIN_CHAT_IDS}")
    bot.infinity_polling()
