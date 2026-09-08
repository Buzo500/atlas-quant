# Cambios de ATLAS Quant

## v0.2.0-rc.1 · Candidata · 2026-09-06

Motor, OpenAPI, salud e interfaz identifican la candidata 0.2.0-rc.1. No es una etiqueta estable: CI, recorridos del commit y ensayo sostenido se registran en [cierre de candidata](docs/candidata_v0_2.md).

- Arranque con instancia única, verificación de dependencias, puertos, página y API; estado consultable y parada cooperativa. Los fallos de un servidor detienen ambos sin repetir trabajos.
- Propiedad de procesos mediante Windows Job Objects, incluyendo descendientes. La parada no utiliza un PID guardado para terminar procesos ajenos.
- Interfaz compilada en Node, proxy local al motor y manifiesto que detecta fuentes o artefactos alterados. La ejecución habitual deja de usar el servidor de desarrollo.
- Copias coherentes de SQLite con manifiesto e integridad comprobada; automáticas al iniciar y cada 24 horas, con retención de siete; copias manuales y antes de actualizar.
- Restauración con respaldo del destino, experimentos activos pausados, parada global activada, fuentes automáticas desconectadas y reservas de API conservadas.
- Esquema SQLite versionado; adopción transaccional desde v0.1 sin modificar registros financieros y rechazo de esquemas incompatibles.
- Instalador bloqueado durante la ejecución, dependencias fijadas, compilación verificada, accesos de inicio/parada y guía de actualización/recuperación.
- Pruebas operativas adicionales, workflow manual de validación Windows y hoja de ruta por versiones.
- Datos, ledger, demo y controles extraídos a casos de uso con transacciones sobre el estado vigente; descargas tardías e importaciones concurrentes ya no pierden actualizaciones.
- Pausa/cancelación durante investigación, interrupción cooperativa de cálculo, resultados protegidos y reservas de IA liquidadas sin reactivar trabajos ni repetir fases completadas.
- Riesgo, órdenes y auditoría atómicos; reanudar o desbloquear por peso no ejecuta retrospectivamente sesiones recibidas durante una parada.
- Exclusión explícita de ejecutores y restauraciones sobre la misma base; limpieza de propietarios de ejecución al recuperar/restaurar.
- Contratos Pydantic/OpenAPI, tipos TypeScript generados y cliente extraído; controles de interfaz coherentes con la operación en curso y sondeo protegido frente a respuestas antiguas.
- 74 regresiones nuevas: total 328 pruebas y 91 subtests superados. Contratos y lint de aplicación añadidos al workflow manual. [Evidencia y límites](docs/consolidacion_core.md).

- Diagnóstico archivado por ejecución con identificador, horas y códigos de salida; se conserva tras reiniciar.
- Herramientas reproducibles de validación de candidata y ensayo de 48 horas con evidencia local y detección de interrupciones.

No incorpora cambios de gráficos, aprendizaje, integración con bróker ni operativa real. Continúa disponible el recorrido sintético sin claves y presupuesto cero.

## v0.1 · Base local

Alcance y limitaciones en [version_0_1.md](docs/version_0_1.md). La instalación original del portátil y la posterior validación del sobremesa se registran por separado en [CONTINUIDAD.md](docs/CONTINUIDAD.md).
