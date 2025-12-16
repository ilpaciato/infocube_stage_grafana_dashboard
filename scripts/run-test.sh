#!/usr/bin/env bash
# Dependencies (local): sshpass, curl, mysql-client
set -euo pipefail

# ========== CONFIG ==========
HOST="10.99.88.114"
#TEST CREDENTIALS
USER="testuser"
PASS="testpassword"
#WORKING CREDENTIALS
wUSER="infocube"
wPASS="password"
# ============================

# dependency check
for cmd in sshpass curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd"
    echo "Install it and retry (e.g. sudo apt install sshpass curl)"
    exit 2
  fi
done

# mysql client optional check
if ! command -v mysql >/dev/null 2>&1; then
  echo "WARNING: mysql client not found. MySQL steps will try tcp probe fallback."
fi


###
#SSH NO AUTH
###
echo "##### - STEP 1: SSH NO AUTH"
sshpass -p "${PASS}" ssh -o StrictHostKeyChecking=no "${USER}@${HOST}" 'uptime' 2>/dev/null || true
sshpass -p "${PASS}" ssh -o StrictHostKeyChecking=no "${USER}@${HOST}" 'whoami' 2>/dev/null || true
sshpass -p "${PASS}" ssh -o StrictHostKeyChecking=no "${USER}@${HOST}" 'cat /etc/passwd' 2>/dev/null || true


###
#SSH AUTH FAIL EDIT
###
echo "##### - STEP 2: SSH WITH AUTH - COMMANDS NOT AUTHORIZED"
sshpass -p "${wPASS}" ssh -o StrictHostKeyChecking=no "${wUSER}@${HOST}" 'rm /etc/shadow' 2>/dev/null || true
sshpass -p "${wPASS}" ssh -o StrictHostKeyChecking=no "${wUSER}@${HOST}" 'echo . >> /etc/passwd' 2>/dev/null || true
sshpass -p "${wPASS}" ssh -o StrictHostKeyChecking=no "${wUSER}@${HOST}" 'mv /etc/sudoers /etc/sudoers_old' 2>/dev/null || true


###
#HTTP (nginx/apache)
###
echo "###### - STEP 3: NGINX-PHP - CURL NON EXISTING PAGES"
curl -sS -o /dev/null -w "  URL:%{url_effective} HTTP:%{http_code} TIME:%{time_total}\n" "http://${HOST}/this-page-does-not-exist.php?x=1" || true
curl -sS -o /dev/null -w "  URL:%{url_effective} HTTP:%{http_code} TIME:%{time_total}\n" "http://${HOST}/also-not-here.php?user=${USER}&q=probe" || true
curl -sS -X POST -d "field=val&user=${USER}" -o /dev/null -w "  POST to http://${HOST}/post_missing.php HTTP:%{http_code} TIME:%{time_total}\n" "http://${HOST}/post_missing.php" || true

###
#MySQL
###
echo "###### - STEP 4: MYSQL FAILED AUTH"
if command -v mysql >/dev/null 2>&1; then
  mysql -h "${HOST}" -u"${USER}" -p"${PASS}" --connect-timeout=5 -e "SHOW DATABASES;" 2>&1 | sed 's/^/  /' || true
else
  echo "  mysql client not installed -> fallback: tcp open probe to port 3306"
  curl -sS --connect-timeout 5 "tcp://${HOST}:3306" -I 2>&1 | sed 's/^/  /' || true
fi

if command -v mysql >/dev/null 2>&1; then
  mysql -h "${HOST}" -u"${USER}" -p"${PASS}BAD" --connect-timeout=5 -e "quit" 2>&1 | sed 's/^/  /' || true
else
  curl -sS --connect-timeout 5 "tcp://${HOST}:3306" -I 2>&1 | sed 's/^/  /' || true
fi

if command -v mysql >/dev/null 2>&1; then
  mysql -h "${HOST}" -u"${USER}" -p"${PASS}" --connect-timeout=5 -e "THIS IS NOT SQL;" 2>&1 | sed 's/^/  /' || true
else
  curl -sS --connect-timeout 5 "tcp://${HOST}:3306" -I 2>&1 | sed 's/^/  /' || true
fi



###
#MySQL AUTH
###
echo "##### - STEP 5 - MYSQL SUCCEDED AUTH"
mysql -h "${HOST}" -uwpuser -ppassword -e "SELECT 1;" 2>/dev/null || true
mysql -h "${HOST}" -uwpuser -ppassword -e "DROP TABLE nonesiste;" 2>/dev/null || true


###
#FTP (vsftpd)
###
echo "###### - STEP 6: VSFTPD NO AUTH"
curl -v --connect-timeout 8 "ftp://${USER}:${PASS}@${HOST}/" --silent --show-error 2>&1 | sed 's/^/  /' || true
curl -v --connect-timeout 8 "ftp://${USER}:${PASS}@${HOST}/no_such_file.txt" --silent --show-error 2>&1 | sed 's/^/  /' || true
curl -v --connect-timeout 8 "ftp://${USER}:${PASS}BAD@${HOST}/" --silent --show-error 2>&1 | sed 's/^/  /' || true

echo "=== Finished ==="
echo "Check logs on remote server with:"
echo "cd /var/log && tail -f nginx/*.log mysql/*.log php8.3-fpm.log auth.log vsftpd.log audit/audit.log"
