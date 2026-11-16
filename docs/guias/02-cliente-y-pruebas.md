# Guía 2 — Cliente portable y pruebas de la Fase 1

## Generar el .exe portable (Fase 1a)
Requisito: el servidor de la Guía 1 funcionando y su clave pública.

```powershell
.\tools\make-portable.ps1 -ServerHost kardremote.duckdns.org -PubKey "CLAVE_PUBLICA="
```

El script descarga el cliente oficial de RustDesk 1.5.3, **verifica su SHA-256** y crea en `dist\` un archivo con nombre
`rustdesk-host=<servidor>,key=<clave>.exe`. **No le cambies el nombre:** ahí va la configuración. Cópialo a cada PC y ábrelo; no hace falta instalar nada.

> La versión con nombre e íconos propios (Fase 1b) se compila en GitHub Actions cuando definas el nombre del producto.

### SmartScreen y antivirus
- Si aparece "Windows protegió su PC": **Más información → Ejecutar de todos modos**.
- Si el antivirus lo bloquea, es un falso positivo típico de las herramientas remotas. Envíalo a <https://www.microsoft.com/wdsi/filesubmission> (gratis) y, solo en equipos propios, agrega una exclusión.

## Primer uso
1. En el **PC remoto**: abre el .exe. Verás su **ID** y una **contraseña de un solo uso**.
2. En el **PC técnico**: abre el mismo .exe, escribe el ID en "Control Remote Desktop" → **Conectar** → contraseña. Son 2 clics.
3. Para comprobar que usa tu servidor: ⚙ **Ajustes → Red → Servidor ID/Relay** debe mostrar tu dominio y la clave. Abajo a la izquierda debe decir **"Listo"** (verde).

## Lista de pruebas de la Fase 1 (criterios de "hecho")

| # | Prueba | Cómo | Objetivo | Resultado |
|---|---|---|---|---|
| 1 | PC limpio | Ejecutar el .exe en un Windows sin nada instalado | Abre sin pedir dependencias | |
| 2 | LAN | Ambos PCs en la misma red | Conecta; **Directa** | |
| 3 | Internet | PC remoto en el **hotspot del celular** y técnico en Wi-Fi | Conecta | |
| 4 | Directa/Relay | Durante la sesión: icono de pantalla → **Mostrar monitor de calidad** | Ver la ruta, el retardo, los FPS y el códec | |
| 5 | Latencia LAN | Monitor de calidad, campo *Delay* | ≤ 60 ms | |
| 6 | Latencia internet | Igual, en la prueba 3 | ≤ 150 ms | |
| 7 | FPS | Mover una ventana o reproducir un video | Hasta 60 FPS en LAN (Ajustes → Pantalla → FPS = 60) | |
| 8 | Códec por hardware | Ajustes → Pantalla → Códec → H264/H265; ver el códec en el monitor | Usa la GPU si existe | |
| 9 | Control | Teclado, ratón, rueda, Ctrl+Alt+Supr (menú de la barra) | Todo responde | |
| 10 | Relay forzado | En el servidor: `ALWAYS_USE_RELAY=Y` (ver abajo) y repetir la prueba 3 | Conecta por Relay, fluido | |
| 11 | Cifrado | El icono de candado en la sesión indica conexión cifrada | Cifrado activo | |
| 12 | Costo | Panel de Oracle → *Billing → Cost Analysis* | $0,00 | |

### Forzar relay para la prueba 10
```bash
cd /opt/remotedesk
printf 'services:\n  hbbs:\n    environment:\n      - ALWAYS_USE_RELAY=Y\n' | sudo tee docker-compose.override.yml
sudo docker compose up -d
# al terminar la prueba, vuelve a P2P:
sudo rm docker-compose.override.yml && sudo docker compose up -d
```

### Simular una red mala (opcional, en el PC técnico)
Usa **clumsy** (gratis, open source: <https://jagt.github.io/clumsy/>): filtra `udp or tcp`, agrega 100 ms de *lag* y 2 % de *drop*, y observa los FPS y el retardo en el monitor de calidad.
