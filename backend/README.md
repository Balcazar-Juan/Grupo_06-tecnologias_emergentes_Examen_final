# HyperMat IA — Backend multiagente (PMV académico)

Versión mejorada sobre el proyecto original; no está certificada como desplegada. Incluye agentes separados (`services/multiagent.py`), supervisor secuencial con control de estados, traspasos JSON persistidos en MongoDB, planificación acotada de herramientas con Gemini, veredictos deterministas, constancia y notificación en aprobación.

## Ejecución en Windows

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Configure MONGODB_URI y MONGODB_DB_NAME dentro de .env
python scripts\seed_atlas.py
python scripts\seed_atlas.py --test-data --reset-test-context --reset-test-flow
uvicorn app.main:app --reload --port 8000
```

La carga **modifica exclusivamente las diez cuentas de prueba, sus contextos y flujos** cuando se usan los flags de reset. No ejecutar sobre estudiantes reales. Las colecciones `enrollment_requests`, `agent_verdicts`, `agent_messages`, `agent_traces`, `orchestration_runs`, `enrollments` y `notifications` **no** son sembradas con resultados: se llenan al usar la aplicación.

Arranque frontend en el directorio `hypermat_src`:

```powershell
npm install
npm run dev
```

Crear `.env.local` en el frontend con `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`; configurar `FRONTEND_ORIGIN` backend según URL efectiva del frontend.

## Endpoints para mostrar evidencia

- `/health`: conecta con MongoDB.
- `/docs`: OpenAPI, utilizable en local o con HTTPS.
- `POST /api/enrollment-requests`: crea solicitud real.
- `POST /api/enrollment-requests/{request_id}/validate`: solo prevalidación; `PREVALIDATED` no implica matrícula registrada.
- `POST /api/enrollment-requests/{request_id}/confirm`: confirmación y, únicamente si agentes previos aprueban, Ejecutor y RPA.
- `GET /api/enrollment-requests/{request_id}`: veredictos, mensajes y trazas.
- `GET /api/enrollment-requests/{request_id}/trace`: run_id, eventos correlacionados y mensajes de traspaso; necesita autenticación.
- `GET /api/enrollment-requests/{request_id}/certificate`: únicamente con registro `APPROVED` y documento `enrollments`.

## Flujo y reglas de control

`coordinator -> academic -> financial -> executor -> rpa`.

- `REJECTED`: terminal, no se delega al siguiente agente; para cambiar contexto crear solicitud nueva.
- `OBSERVED`: pausa de atención; estudiante puede revalidar la misma solicitud luego de que ADMIN actualice pagos o documentos.
- `PREVALIDATED`: tres agentes conformes, pero no se ha registrado nada. Se permite seleccionar/confirmar.
- `APPROVED`: exclusivamente después de persistir `enrollments` y terminar RPA.
- `ERROR`: fallo técnico, nunca aprobación inventada.

Con `GEMINI_API_KEY` se solicita a cada agente una planificación acotada del **orden de herramientas permitidas** y luego la explicación de reglas. Sin clave o por fallo de API, se usa plan fijo y explicación determinista. El modelo no fija el estado de matrícula ni ejecuta escrituras fuera de los agentes autorizados.

## Configuración de IA y correo

`GEMINI_MODEL=gemini-3.5-flash-lite` es el identificador configurado; compruebe que el proyecto/API de Google tenga acceso y que sea válido durante las pruebas. Si SMTP no está configurado, el correo tendrá estado `SIMULATED` (no equivale a enviado). Los roles y datos de prueba son académicos, no deben incluir DNIs o contraseñas reales.

## Tests

```powershell
cd backend
python -m pytest -q
```

Estos tests comprueban las reglas puras de estados y horarios; **no prueban integración online**, MongoDB Atlas, API real de Gemini, concurrencia ni SMTP. Deben añadirse pruebas E2E antes de declarar validación final.

## Despliegue gratuito sin Docker

La entrega se realizará con **Cloudflare Pages (frontend estático Next.js)** + **Render Free (FastAPI)** + **MongoDB Atlas**. Consulta `../DESPLIEGUE_CLOUDFLARE_RENDER.md` para los comandos y las variables.

En Render, configurar raíz `backend`, build `pip install -r requirements.txt` y start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. En Cloudflare Pages, compilar `pnpm run build:pages` y publicar directorio `out`, con variable `NEXT_PUBLIC_API_BASE_URL` apuntando a la API HTTPS real. No se usan Dockerfile ni docker-compose.

Render Free no permite SMTP en puertos 25/465/587. Se añadió **Resend HTTP API** opcional mediante `RESEND_API_KEY` y `RESEND_FROM` (requiere un remitente validado por el proveedor); sin proveedor de correo configurado, el estado es `SIMULATED`.

## Limitaciones conocidas

- Simulación académica con catálogo/horarios demostrativos y diez expedientes ficticios, sin conexión al ERP/SIS oficial de la UNFV.
- Reserva de vacantes utiliza actualizaciones condicionales y compensación; para concurrencia real multiusuario se recomiendan transacciones MongoDB con replica set e índices operacionales completos.
- El orden de herramientas se planifica con IA cuando está disponible; los controles universitarios son deterministas.
- Costos, latencia y porcentajes E2E requieren medición online; no se inventan.
- El login demo usa DNI inicial (hash), recomendado sustituir por contraseña temporal + cambio obligatorio en producción.
- Se requiere documentación de permisos y políticas de tratamiento si se usa información real.
