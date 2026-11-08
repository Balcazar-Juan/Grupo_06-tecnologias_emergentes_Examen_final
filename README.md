# HyperMat IA

Sistema web de matrícula universitaria con validación multiagente. Verifica la información académica, financiera y administrativa antes de registrar los cursos.

## Funcionalidades

- Inicio de sesión para estudiantes y administradores.
- Consulta de cursos y secciones disponibles.
- Validación mediante agentes coordinador, académico, financiero, ejecutor y RPA.
- Registro de mensajes y trazas entre agentes.
- Estados `APPROVED`, `OBSERVED` y `REJECTED`.
- Registro de matrícula y generación de constancia.
- Panel administrativo para revisar solicitudes y evidencias.

## Arquitectura

- **Frontend:** Next.js/Vinext y React.
- **Cloudflare Worker:** sirve el frontend, reenvía las solicitudes `/api/*` y registra los eventos de comunicación entre agentes.
- **Backend:** FastAPI ejecutándose en Render.
- **Base de datos:** MongoDB Atlas.
- **IA opcional:** Google Gemini para generar explicaciones.
- **Correo opcional:** Resend o SMTP.

## Requisitos

- Node.js 22 o superior.
- Python 3.11 o superior.
- Una base de datos MongoDB Atlas.

## Configuración del backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura en `.env` las variables necesarias, especialmente `MONGODB_URI` y `MONGODB_DB_NAME`. No subas este archivo al repositorio.

## Carga inicial de datos

El script `backend/scripts/seed_atlas.py` crea las colecciones, índices, programa académico, cursos, secciones y horarios.

```powershell
python scripts\seed_atlas.py
```

Para cargar los diez estudiantes sintéticos de prueba:

```powershell
python scripts\seed_atlas.py --test-data
```

Para reiniciar el contexto y los flujos de esos estudiantes:

```powershell
python scripts\seed_atlas.py --test-data --reset-test-context --reset-test-flow
```

Los resultados de los agentes no se cargan previamente: se generan al utilizar la aplicación.

## Ejecución local

Inicia la API desde `backend`:

```powershell
uvicorn app.main:app --reload --port 8000
```

En otra terminal, desde la raíz del proyecto:

```powershell
npm install
npm run dev
```

El Worker utiliza `http://localhost:8000` como backend local por defecto. Para usar otra API, configura `API_ORIGIN`.

## Variables de entorno

### Backend en Render

`MONGODB_URI`, `MONGODB_DB_NAME`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `FRONTEND_ORIGIN`, `RESEND_API_KEY`, `RESEND_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` y `SMTP_FROM`.

Gemini, Resend y SMTP son opcionales. Las credenciales deben configurarse como secretos y no deben incluirse en Git.

### Cloudflare Worker

`API_ORIGIN`: URL pública del backend desplegado en Render.

## Despliegue

### Render

- Directorio raíz: `backend`.
- Instalación: `pip install -r requirements.txt`.
- Comando de inicio: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Health check: `/health`.

### Cloudflare Worker

```bash
npm run build
```

Configura `API_ORIGIN` en el Worker y despliega el artefacto generado por Vinext/Wrangler. Las solicitudes del frontend pasan por el Worker y los eventos `agent_handoff` y `agent_run` pueden consultarse en Workers Logs.

## Pruebas

```powershell
cd backend
python -m pytest -q
```

El proyecto utiliza datos sintéticos para demostración. No debe conectarse a expedientes reales sin aplicar las políticas correspondientes de seguridad, privacidad y autorización.
