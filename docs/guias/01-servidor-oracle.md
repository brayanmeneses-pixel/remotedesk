# Guía 1 — Servidor gratis en Oracle Cloud (paso a paso)

Tiempo: unos 30 minutos. Costo: $0. Necesitas una tarjeta **solo para verificar identidad** (Oracle no cobra en cuentas Always Free).

> ⚠️ Regla de oro: **nunca** pulses "Upgrade to Pay As You Go". Mientras la cuenta sea *Free Tier*, Oracle no puede cobrarte; si algo supera el límite, simplemente se bloquea.

## 1. Crear la cuenta
1. Entra a <https://signup.cloud.oracle.com> y regístrate.
2. **Home Region:** elige la más cercana (por ejemplo *Colombia Central (Bogotá)* o *Brazil East (São Paulo)*). **No se puede cambiar después.**
3. Verifica la tarjeta. Oracle hace un cargo temporal pequeño que luego reversa.

## 2. Crear la VM
1. Menú → **Compute → Instances → Create instance**.
2. Nombre: `remotedesk-server`.
3. **Image:** Canonical Ubuntu 24.04 (o 22.04).
4. **Shape:** *Change shape* → **Specialty and previous generation → VM.Standard.E2.1.Micro** (debe decir *Always Free-eligible*).
5. **Networking:** crea una VCN nueva con subred **pública** y marca *Assign a public IPv4 address*.
6. **SSH keys:** *Generate a key pair for me* → **descarga la clave privada** y guárdala bien.
7. **Create**. Espera a que el estado diga *Running* y copia la **Public IP**.

### IP fija (gratis)
Por defecto la IP pública puede cambiar si se recrea la VM. Para fijarla:
**Networking → IP Management → Reserved public IPs → Reserve**, y luego asígnala a la VNIC de la instancia (*Instance → Attached VNICs → IPv4 addresses → Edit → Reserved public IP*). Puedes tener una gratis.

## 3. Abrir los puertos en Oracle (Security List)
**Networking → Virtual Cloud Networks → (tu VCN) → Subnets → (subred pública) → Security List → Add Ingress Rules**, con origen `0.0.0.0/0`:

| Protocolo | Puerto destino | Para qué |
|---|---|---|
| TCP | 21115-21117 | Tipo de NAT, registro y relay |
| UDP | 21116 | Registro y perforación NAT (P2P) |

No abras más puertos. El SSH (22) ya viene abierto.

## 4. Instalar el servidor
Desde tu PC (PowerShell), ajustando la ruta de la clave y la IP:

```powershell
scp -i C:\ruta\ssh-key.key infra\setup.sh infra\docker-compose.yml ubuntu@IP_PUBLICA:~
ssh -i C:\ruta\ssh-key.key ubuntu@IP_PUBLICA "sudo bash ~/setup.sh"
```

Al final, el script imprime la **CLAVE PÚBLICA**. Cópiala: la necesitas para el cliente.

## 5. Respaldar las claves (obligatorio)
```powershell
scp -i C:\ruta\ssh-key.key "ubuntu@IP_PUBLICA:/opt/remotedesk/data/id_ed25519*" C:\RespaldoSeguro\
```
(Si da error de permisos: `ssh ... "sudo cp /opt/remotedesk/data/id_ed25519* ~ && sudo chown ubuntu ~/id_ed25519*"` y luego copia desde `~`.)

Guárdalas en un gestor de contraseñas o en una carpeta privada. **Nunca en GitHub.**

## 6. Nombre de dominio gratis (recomendado)
1. Entra a <https://www.duckdns.org> con tu cuenta de Google o GitHub.
2. Crea un subdominio (ejemplo: `kardremote.duckdns.org`) y ponle la IP pública.
3. Usa ese nombre como servidor en el cliente. Si algún día cambia la IP, solo la actualizas en DuckDNS.

## 7. Monitoreo
En el repositorio de GitHub: **Settings → Secrets and variables → Actions → Variables → New variable** `SERVER_HOST` = tu dominio o IP. El workflow `server-health` comprueba cada hora el servidor y abre un *issue* si se cae (te llega por correo).

## Recuperación (si Oracle reclama o borra la VM)
Oracle puede reclamar VMs *Always Free* que considere inactivas. Para reconstruir la tuya:
1. Repite el paso 2 (si reservaste la IP, asígnala a la VM nueva).
2. En la VM nueva: `sudo mkdir -p /opt/remotedesk/data`, copia ahí tus `id_ed25519` e `id_ed25519.pub` respaldados y ejecuta `sudo touch /opt/remotedesk/data/.keep`.
3. Ejecuta el paso 4. Como la clave es la misma, **los clientes no necesitan cambiar nada**.
4. Si la IP cambió y no la reservaste, actualízala en DuckDNS.

## Comandos útiles en la VM
```bash
cd /opt/remotedesk
sudo docker compose ps          # estado
sudo docker compose logs -f     # registros
sudo docker compose pull && sudo docker compose up -d   # actualizar (tras cambiar la versión en el compose)
```
