# CLAUDE.md — RemoteDesk (nombre provisional)

Herramienta de acceso remoto tipo AnyDesk para soporte interno de Kardinc: 1 PC Windows al principio, máximo 2-3. **Regla n.º 1: costo $0.**

## Decisiones clave (ver docs/ARQUITECTURA.md)
- Fork de **RustDesk** (AGPL-3.0) con nombre propio, en un repositorio **público** de GitHub. Versión base del cliente: 1.5.3; servidor: 1.1.16.
- Servidor: `hbbs` (IDs) + `hbbr` (relay) en **Oracle Cloud Always Free** (VM E2.1.Micro), con docker compose y `-k _` (solo nuestra clave).
- Vercel Hobby: solo página de descargas y guías (Fase 4). **Sin Supabase ni Cloudflare TURN.**
- Nunca pasar Oracle a "Pay As You Go". Nunca usar servicios que cobren por uso.
- Prioridad: estabilidad y fluidez antes que funciones extra.
- Branding (1b): parchear en CI `libs/hbb_common/src/config.rs` (`RENDEZVOUS_SERVERS`, `RS_PUB_KEY`, `APP_NAME`); RustDesk no acepta estos valores por variables de entorno.

## Estructura
- `infra/` — `docker-compose.yml` + `setup.sh` (idempotente, firewall, regenera la clave si contiene "/").
- `tools/make-portable.ps1` — Fase 1a: cliente oficial verificado por SHA-256 y renombrado `rustdesk-host=…,key=….exe`.
- `.github/workflows/health.yml` — chequeo horario del servidor (variable `SERVER_HOST`).
- `docs/` — ARQUITECTURA.md y guías en español.

## Convenciones
- Documentos y textos para el usuario en español; código y commits en inglés.
- Secretos (`id_ed25519`, `.key`, contraseñas) **nunca** en el repo (están en `.gitignore`).
- Los `.ps1` se guardan en UTF-8 **con BOM** (PowerShell 5.1); los `.sh`/`.yml` con LF (`.gitattributes`).
- Cada fase termina con: compilar, probar, demostrar los criterios, hacer commit y actualizar este archivo.
- Nada de código simulado ni TODO silenciosos.

## Comandos
- Generar el portable: `.\tools\make-portable.ps1 -ServerHost <dominio> -PubKey "<clave>"`
- Instalar el servidor: ver `docs/guias/01-servidor-oracle.md`.

## Cuentas y recursos
- GitHub: `brayanmeneses-pixel` (gh). Repos: `remotedesk` (este) y `remotedesk-client` (fork, rama por defecto `remotedesk`, basada en el tag 1.5.3).
- Build del cliente: workflow `remotedesk-windows.yml` del fork (generado por `remotedesk/gen_workflow.py`); variables del repo `RD_APP_NAME`, `RD_SERVER`, `RD_KEY`. Un tag `rd-*` publica una Release.
- Oracle: región sa-bogota-1, VCN `remotedesk-vcn`, VM `remotedesk-server` (A1.Flex). API key en `~/.oci/` (fuera del repo); SDK en el venv `C:\ov`.
- SSH a la VM: `ssh -i ~/.ssh/remotedesk_oracle ubuntu@<IP>`.

## Estado
- [x] Fase 0: arquitectura (el usuario indicó "trabaja en todo" = aprobada)
- [~] Fase 1a: código listo y probado localmente; **falta** la VM de Oracle (la crea el usuario) y las pruebas reales de la guía 02
- [x] Fase 1b: fork con nombre propio; build de Windows OK (portable + MSI en la Release `rd-nightly`)
- [~] Servidor: red creada; la VM espera capacidad A1 en Bogotá (`python infra/oci_provision.py` reintenta)
- [ ] Fases 2-6
