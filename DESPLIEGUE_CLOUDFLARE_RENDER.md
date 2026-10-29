# HyperMat IA — despliegue gratuito sin Docker

Arquitectura: **Cloudflare Worker** (portal Vinext y proxy `/api/*`) + **Render Free Web Service** (FastAPI + supervisor multiagente) + **MongoDB Atlas M0** (persistencia) + API Gemini opcional. No necesitas Docker, Docker Compose ni VM.

## 1. Preparación y repositorio GitHub

Sube `hypermat_src/` a GitHub. No subas `.env`, `.env.local`, URI MongoDB real, claves Gemini ni tokens. Para simplificar se recomienda que el contenido de `hypermat_src/` sea la raíz del repositorio.

## 2. MongoDB Atlas

Crea el clúster Atlas gratuito que esté disponible en tu región, su usuario de BD y una base `hypermat_ia`. En Network Access, permite exclusivamente las IP de salida informadas por Render cuando sea factible; comprueba conectividad de `mongodb+srv://...` desde Render. **Evita usar `0.0.0.0/0` como configuración definitiva**; si recurres a ello temporalmente para la demostración, conserva credenciales exclusivas del PMV y revoca el acceso abierto luego.

Ejecuta el seed una sola vez desde tu PC, apuntando al cluster Atlas mediante `backend/.env` (archivo privado):

```powershell
cd backend
python -m pip install -r requirements.txt
python scripts/seed_atlas.py
python scripts/seed_atlas.py --test-data --reset-test-context --reset-test-flow
```

**Advertencia**: Los flags de reset alteran los 10 alumnos de prueba, NO ejecutarlos contra una base institucional.

## 3. Render — backend de FastAPI (sin Docker)

En https://dashboard.render.com/ selecciona **New > Web Service** y vincula GitHub.

| Parámetro Render | Valor |
|---|---|
| Language / Runtime | Python 3 |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |
| Health Check Path | `/health` |

Variables de entorno Render: `MONGODB_URI`, `MONGODB_DB_NAME`, `GEMINI_API_KEY` (si se demostrará planificación LLM), `GEMINI_MODEL`, `FRONTEND_ORIGIN`. Las notificaciones con Resend API HTTPS usan opcionalmente `RESEND_API_KEY` y `RESEND_FROM` (remitente verificado); SMTP usa `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` **pero el plan gratis de Render bloquea puertos SMTP 25/465/587**.

Tras el despliegue, copia la URL real provista por Render, p. ej. `https://TU-API.onrender.com`, y comprueba `https://TU-API.onrender.com/health`. **No uses `localhost`** en frontend público.

Render Free suspende instancias tras 15 minutos sin tráfico: la primera petición puede tardar cerca de un minuto. No usar controles externos de ping para fingir disponibilidad: documentar el cold start como limitación y abrir `/health` previamente durante las pruebas de exposición.

## 4. Cloudflare Worker — portal y proxy de la API

En el Worker conectado a GitHub, usa la raíz del repositorio, la rama `main` y `npm run build`. El artefacto generado es `dist/server/wrangler.json`; si tu configuración pide un comando de despliegue, usa `npx wrangler deploy --config dist/server/wrangler.json`. No uses `build:pages` ni el directorio `out` para este flujo.

Configura `API_ORIGIN=https://TU-API.onrender.com` en las variables del Worker. Durante el build también se acepta la variable anterior `NEXT_PUBLIC_API_BASE_URL` y se convierte en `API_ORIGIN`; la URL nunca se envía al navegador como destino directo. Las llamadas `/api/*` entran al Worker y este las reenvía a Render. El Worker escribe `agent_handoff` y `agent_run` con `request_id` y `run_id` tras validar o confirmar una solicitud; `observability` está activada para conservar esos eventos en Workers Logs.

Cloudflare generará un dominio tipo `https://TU-PROYECTO.workers.dev` o usará tu dominio personalizado.

## 5. Conectar CORS (Render)

En Render configura:

`FRONTEND_ORIGIN=https://TU-PROYECTO.workers.dev`

Debe coincidir con el origen exacto del frontend, sin barra final. En el backend hay un middleware CORSMiddleware leyendo `FRONTEND_ORIGIN`. Si cambias el dominio del frontend, actualiza el valor en Render y vuelve a desplegar/reiniciar.

Si cambias la URL del backend, actualiza `API_ORIGIN` en el Worker y vuelve a desplegarlo.

## 6. Pruebas esenciales antes de entregar

1. Abre `https://TU-API.onrender.com/health`: debe responder y conectar MongoDB Atlas.
2. Abre `https://TU-PROYECTO.workers.dev`: login sin datos hardcodeados.
3. Ejecuta C01: aprobada, persistencia real, PDF y traza supervisada.
4. Ejecuta C02 (rechazo) y C06 (observación/revalidación): demuestra que el supervisor detiene el flujo.
5. En el administrador abre `/trace`, verifica `run_id`, `TOOL_CALL`, `VERDICT` y `HANDOFF`.
6. En Cloudflare > Worker > Observability > Logs, filtra `agent_handoff` o `run_id` de la solicitud para ver los traspasos persistidos.
7. Si hay `GEMINI_API_KEY`, demuestra planificación `TOOL_PLAN` de Gemini y explicación; sin clave es solo fallback.
8. En notificaciones comprueba `SENT` solo con Resend validado, o `SIMULATED` si no se configuró el proveedor. **No digas que se envió un correo real cuando el estado sea SIMULATED.**
9. Captura las URLs, la ejecución real, el dashboard de Render, las colecciones de Atlas y el historial de implementaciones de Cloudflare para el cuestionario del profesor.
10. Registra tiempos online considerando separadamente primer acceso (cold start) y solicitudes con API activa.

## 7. Limitaciones conocidas

Render Free no tiene disponibilidad garantizada, puede suspender instancias en reposo y bloquea SMTP estándar; los límites y condiciones de Cloudflare/Render pueden cambiar. El proyecto continúa siendo un PMV con 10 estudiantes sintéticos y no está integrado con los sistemas internos oficiales de la UNFV.
