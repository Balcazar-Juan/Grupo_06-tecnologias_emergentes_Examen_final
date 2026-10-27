# HyperMat IA — PMV con supervisión multiagente

## Qué cambió respecto al primer PMV

La primera versión ejecutaba varias validaciones dentro de una sola rutina de FastAPI y enviaba cada resultado a Gemini para explicarlo. La versión revisada separa 5 agentes con conjuntos de herramientas permitidas, un supervisor que enruta por estado, traspasos JSON entre agentes, planificación limitada de herramientas y traza de cada herramienta. El resultado de Gemini **no sustituye** reglas académicas ni financieras.

## Archivos esenciales

- `backend/app/services/multiagent.py`: cinco agentes + supervisor con máquina de estados.
- `backend/app/main.py`: API real, autenticación, vista de trazas por solicitud.
- `backend/data/demo_cases.json`: diez casos nuevos de prueba sintética.
- `backend/scripts/seed_atlas.py`: carga/reinicio selectivo de datos demo sin insertar resultados predeterminados.
- `backend/tests/`: 13 pruebas unitarias de reglas, estados y agentes.
- `app/page.tsx`: portal alumno y panel admin con consulta de mensajes, herramientas y traza.
- `backend/README.md`: instrucciones paso a paso, variables y limitaciones.
- `PRUEBAS_10_CASUISTICAS.md`: matriz y recorrido de pruebas.

## Estados

`DRAFT → PREVALIDATED → APPROVED` (solo al persistir enrollment y ejecutar RPA). Si hay `OBSERVED`, el supervisor se detiene y el administrador puede regularizar datos para volver a validar la misma solicitud. Si hay `REJECTED`, es final para esa solicitud. En caso de fallo inesperado se registra `ERROR`, nunca se atribuye matrícula aprobada.

## Prueba docente

La API `GET /api/enrollment-requests/{id}/trace` devuelve `run_id`, `agent_traces` y `agent_messages` protegidos por autenticación. Abre detalle de solicitud desde Admin para ver herramienta invocada, traspaso y veredicto. Requiere **ejecutar sobre MongoDB Atlas** y conectar Gemini por clave en backend para mostrar planificación realmente generada por LLM.

> No hay evidencias de hosting online, URL pública o latencia de producción incluidas en el ZIP. Antes de presentar, desplegar frontend **y** API con HTTPS y realizar capturas reales de C01, C02, C03 y C06.

## Hosting para entrega final

La modalidad seleccionada es **Cloudflare Pages + Render Free + MongoDB Atlas**, sin Docker. Revisa [`DESPLIEGUE_CLOUDFLARE_RENDER.md`](./DESPLIEGUE_CLOUDFLARE_RENDER.md).
