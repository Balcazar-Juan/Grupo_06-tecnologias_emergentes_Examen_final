# Casuísticas multiagente — HyperMat IA

Son **expectativas** hasta que se ejecuten en la instalación desplegada. El seed crea **precondiciones**, nunca resultados.

| Caso | Causa | Agente decisor | Estado esperado | Evidencia mínima |
|---|---|---|---|---|
| C01 | Datos conformes | Todos | APPROVED | Handoffs 5 agentes, enrollments, PDF, notificación |
| C02 | Estado académico INACTIVE | Coordinador | REJECTED | Traza solo Coordinador; no Academic/Executor |
| C03 | Dos asignaturas con igual horario | Académico | REJECTED | Intersección y ausencia de Financial/Executor |
| C04 | Falta prerrequisito 54 de Taller Tesis II | Académico | REJECTED si se envía por API | UI deshabilita curso; backend también impide registrar |
| C05 | Deuda S/320 | Financiero | REJECTED | No se ejecuta Ejecutor |
| C06 | Pago PENDING | Financiero | OBSERVED | Pausa, cambio admin a PAID, revalidación PREVALIDATED |
| C07 | Monto 130 vs 450 / MISMATCH | Financiero | OBSERVED | Regularización y segunda corrida con run_id distinto |
| C08 | Seguro EXPIRED | Financiero | OBSERVED | Bloqueo de confirmación hasta VALID |
| C09 | Sección 62 sin vacantes | Académico | REJECTED si se envía por API | UI deshabilita + backend valida SECTION_FULL |
| C10 | No hay requisitos administrativos | Financiero | OBSERVED | Alta del documento, revalidación |

Si no se puede seleccionar C04 o C09 en UI porque está bloqueado **eso es correcto**; validar la seguridad de backend mediante Swagger o prueba automatizada con token de una cuenta demo. No afirmar que se envió una matrícula usando esos cursos desde la interfaz.

## Reset controlado

`python scripts/seed_atlas.py --test-data --reset-test-context --reset-test-flow`

Este comando borra únicamente registros de los 10 códigos demo; no elimina otros estudiantes. En una base compartida no ejecutarlo sin copia de respaldo. Usar cuenta admin creada por el propio equipo y nunca compartir claves reales de MongoDB o Gemini.
