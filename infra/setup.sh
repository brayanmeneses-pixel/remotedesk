#!/usr/bin/env bash
# Instala el servidor RemoteDesk en una VM Ubuntu (Oracle Cloud Always Free).
# Uso (en la VM):  curl -fsSL <url-raw-de-este-archivo> | sudo bash
#            o:    sudo bash setup.sh
# Idempotente: se puede volver a ejecutar sin romper nada.
# Para restaurar claves respaldadas: copia id_ed25519 e id_ed25519.pub a
# /opt/remotedesk/data/ ANTES de ejecutar este script.
set -euo pipefail

REPO_RAW="${REPO_RAW:-}"   # opcional: URL raw del repo para bajar docker-compose.yml
DIR=/opt/remotedesk
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo /tmp)"

[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 1; }

echo "==> Paquetes base, Docker, fail2ban, actualizaciones automáticas"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io docker-compose-v2 fail2ban unattended-upgrades iptables-persistent netcat-openbsd
systemctl enable --now docker fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> Firewall de la VM (Oracle Ubuntu trae iptables restrictivo)"
open_port() { # proto puerto
  iptables -C INPUT -p "$1" --dport "$2" -j ACCEPT 2>/dev/null || \
    iptables -I INPUT 5 -p "$1" --dport "$2" -m state --state NEW -j ACCEPT
}
open_port tcp 21115   # prueba de tipo de NAT
open_port tcp 21116   # registro / señalización
open_port udp 21116   # registro / perforación NAT
open_port tcp 21117   # relay
netfilter-persistent save

echo "==> Archivos del servidor en $DIR"
mkdir -p "$DIR/data"
if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
  cp "$SCRIPT_DIR/docker-compose.yml" "$DIR/docker-compose.yml"
elif [ -n "$REPO_RAW" ]; then
  curl -fsSL "$REPO_RAW/infra/docker-compose.yml" -o "$DIR/docker-compose.yml"
elif [ ! -f "$DIR/docker-compose.yml" ]; then
  echo "No encuentro docker-compose.yml. Pon REPO_RAW=<url raw del repo> o copia el archivo junto a este script."; exit 1
fi
cd "$DIR"

echo "==> Arrancando hbbs/hbbr"
docker compose pull
docker compose up -d

# La clave pública se usa en el nombre del .exe portable; Windows no admite "/"
# en nombres de archivo. Si la clave recién generada lo contiene, se regenera.
# Nunca se regenera una clave restaurada desde respaldo (marca .keep).
for i in $(seq 1 30); do
  for _ in $(seq 1 20); do [ -s data/id_ed25519.pub ] && break; sleep 1; done
  PUB="$(cat data/id_ed25519.pub)"
  if [[ "$PUB" != */* ]] || [ -f data/.keep ]; then break; fi
  echo "   clave con '/', regenerando ($i)..."
  docker compose down
  rm -f data/id_ed25519 data/id_ed25519.pub
  docker compose up -d
done
touch data/.keep

echo "==> Comprobación de puertos locales"
sleep 2
for p in 21115 21116 21117; do nc -z -w3 127.0.0.1 $p && echo "   tcp $p OK" || echo "   tcp $p FALLA"; done

cat <<EOF

========================================================
 Servidor listo.
 CLAVE PÚBLICA (cópiala, va en el cliente):
   $(cat data/id_ed25519.pub)

 RESPALDA AHORA estos dos archivos fuera del servidor
 (gestor de contraseñas o tu PC; NUNCA en GitHub):
   $DIR/data/id_ed25519
   $DIR/data/id_ed25519.pub
 Recuerda abrir también los puertos en la Security List
 de Oracle (ver docs/guias/01-servidor-oracle.md).
========================================================
EOF
