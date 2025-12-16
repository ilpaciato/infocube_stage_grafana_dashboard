#!/bin/bash

PORT=9000
echo "Starting Fail2ban Exporter on port $PORT"

nc -l -p $PORT -q 1 &
while true; do
  {
    echo "HTTP/1.1 200 OK"
    echo "Content-Type: text/plain"
    echo ""
    echo "# HELP fail2ban_banned_total Total banned IPs per jail"
    echo "# TYPE fail2ban_banned_total gauge"
    
    jails=$(sudo fail2ban-client status | grep "Jail list" | sed 's/.*\[//' | sed 's/\]//' | tr ',' '\n' | xargs)
    
    for jail in $jails; do
      banned=$(sudo fail2ban-client status "$jail" | grep "Currently banned" | awk '{print $NF}')
      echo "fail2ban_banned_total{jail=\"$jail\"} $banned"
    done
  } | nc -l -p $PORT -q 1
done
