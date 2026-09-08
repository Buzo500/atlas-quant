# Cambios de ATLAS Quant

## v0.2.0-rc.2 · En preparación · 2026-09-08

Preparación de una nueva candidata en `codex/v0.2.0-rc.2`, sobre la [PR #1](https://github.com/Buzo500/atlas-quant/pull/1) ya fusionada en `master` (`e1f6e020a1d75a81bff97eefcbebe726d47bcdb3`). Motor e interfaz usan el identificador rc.2 localmente. CI y etiqueta de rc.2 pendientes; no es una versión estable. El ensayo de 48 horas y su seguimiento permanecen aplazados. [Evidencia de candidata](docs/candidata_v0_2.md).

- Conserva el monolito modular, las transacciones, los controles de simulación y la operación Windows incorporados en rc.1.
- Corrige el agotamiento de archivos del supervisor: comprobaciones HTTP locales sin crear contextos TLS ni consultar proxies, con cierre explícito de respuesta y conexión. La corrección no convierte el ensayo fallido de rc.1 en uno superado.
- Interfaz crema, marfil y cobre para las cinco secciones, adaptada a escritorio y pantallas ultrapanorámicas.
- Confirmación de movimientos vinculada al CSV, conjunto, versión, barras y ledger revisados, con comprobación del token dentro de la transacción.
- Comparaciones del Laboratorio con identidad de ejecución, datos y costes utilizados; aviso cuando el borrador deja de coincidir con el resultado.
- Consultas que descartan respuestas obsoletas, distinguen carga/error/datos conservados y permiten reintentar lecturas; ajustes parciales que no sobrescriben una parada concurrente al guardar un peso.
- Borradores conservados entre pestañas y selecciones recuperables desde la URL; la recarga no conserva una autorización de simulación automática.
- Paneles separados por funcionalidad, formatos comunes EUR/USD/fechas, tabla accesible de las curvas y paginación de 50 filas. La reducción del SVG conserva los datos completos.
- Pruebas de comportamiento con Vitest/Testing Library y CI ampliada. **Antecedente validado:** `3f1d990ac15c391e638302828d1a720d99d78003` superó [CI de Windows](https://github.com/Buzo500/atlas-quant/actions/runs/34241300060) con 421 pruebas Python, 91 subtests y 126 pruebas de interfaz; esa ejecución no valida cambios posteriores de rc.2.
- Recorridos E2E con interfaz compilada, API real y Chromium sobre una base nueva por ejecución; presupuesto cero y cierre comprobado de los procesos propios. El PID del intérprete se verifica mediante su pertenencia al grupo del servidor; una integridad o cierre incorrectos impiden dar la prueba por superada.
- Foco persistente al importar datos, crear un experimento y confirmar CSV, respetando cambios de campo o sección durante la espera. El mensaje de importación permanece tras actualizar la versión del conjunto.
- Hora de consulta visible fuera de los anuncios accesibles; carga inicial, errores, recuperación y reintentos anunciados sin repetir sondeos normales.
- Aislamiento de pytest antes de recoger e importar módulos, evitando abrir la base habitual al construir la aplicación global.
- Validación local: **446 pruebas Python y 91 subtests** (38,34 s, dos avisos previos), **140 pruebas Vitest en 15 archivos** (13,34 s), **5/5 E2E** (9,6 s), TypeScript, contratos, lint, `pip check` y compilación correctos. Conservación del contenido de la base habitual verificada frente a su copia; resultados fallidos anteriores preservados.
- Escalado físico de Windows al 125 % y 150 % pendiente: la herramienta de control bloqueó la operación y no se modificó la escala. Los tamaños CSS comprobados anteriormente no sustituyen esta validación.

No incorpora gráficos avanzados del backlog, aprendizaje, acceso remoto, móvil, conexión a bróker ni órdenes reales. Se mantiene el recorrido sintético sin claves y con presupuesto cero.

## v0.2.0-rc.1 · Candidata · 2026-09-06

Candidata histórica: motor, OpenAPI, salud e interfaz se identificaron como 0.2.0-rc.1. No es una etiqueta estable: su CI, recorridos del commit y ensayo interrumpido se conservan en [cierre de candidata](docs/candidata_v0_2.md).

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
