# ATLAS Quant

Versión vigente: **0.2.0-rc.2, candidata con CI verificada**. No es todavía v0.2 estable. El [registro de candidata](docs/candidata_v0_2.md) identifica las fuentes y comprobaciones de cada revisión, incluida la candidata histórica rc.1. La [hoja de ruta](docs/hoja_de_ruta.md) recoge las versiones previstas y el [plan de v0.2](docs/plan_v0_2.md) sus criterios de cierre. El historial de cambios está en [CHANGELOG.md](CHANGELOG.md).

Aplicación local para analizar una cartera en EUR, comparar estrategias de acciones/ETF y ejecutar experimentos acotados con OpenAI o Anthropic. Incluye simulación de órdenes; no está conectada a ningún bróker.

Preferencias confirmadas: OpenAI y Anthropic seleccionables desde la app, integración preparada sin consumo hasta decidir un presupuesto y primera etapa en el PC. El presupuesto inicial sigue en cero. La entrega se ha probado en Windows; Ubuntu no se ha validado todavía.

Cambios solicitados el 06/09/2026, todavía en planificación: [inspección de gráficos, velas y aprendizaje acumulativo de IA](docs/backlog_planificacion.md).

Para trabajar en otro equipo: [traslado al sobremesa y conversación nueva en Codex](docs/traslado_sobremesa.md). El contexto para retomar el proyecto está en [CONTINUIDAD.md](docs/CONTINUIDAD.md); Git no traslada automáticamente el chat original ni los experimentos locales.

Interfaz local actual: [diseño crema y cobre, adaptación ultrapanorámica y validación](docs/frontend_crema_cobre.md). Incluye las cinco secciones existentes; los informes LaTeX siguen en planificación.

Consolidación posterior: [nueve mejoras de fiabilidad, trazabilidad y pruebas del frontend](docs/frontend_consolidacion.md), más correcciones de foco, anuncios de estado y aislamiento de pruebas. La [CI de rc.2](https://github.com/Buzo500/atlas-quant/actions/runs/34249730107) valida `412918b`: 446 pruebas del motor y 91 subtests, 140 de interfaz y cinco E2E con Chromium y API real, además de instalación limpia, compilación, contratos, arranque y parada. El cierre posterior solo modifica documentación; la integración mediante la [PR #2](https://github.com/Buzo500/atlas-quant/pull/2) y la etiqueta `v0.2.0-rc.2` siguen el procedimiento autorizado. El escalado físico de Windows al 125 % y 150 % continúa pendiente: los 35 viewports CSS anteriores no lo sustituyen. Ensayo de 48 horas y seguimiento aplazados. [Evidencia, incidencias y límites](docs/candidata_v0_2.md).

## Abrir la aplicación

Después de instalar las dependencias en cada equipo, haz doble clic en **Abrir-ATLAS.cmd**. Para detener motor e interfaz, usa **Detener-ATLAS.cmd**. También puedes ejecutar `Start-Atlas.ps1 -OpenBrowser`, o iniciar en primer plano desde PowerShell en la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe tools\run_atlas.py --open
```

La interfaz está en **http://127.0.0.1:3000/**. El motor usa el puerto 8000. Ambos escuchan exclusivamente en el ordenador local. Para detenerlos, ejecuta `Stop-Atlas.ps1`; si arrancaste el lanzador en primer plano, también puedes usar Ctrl+C. No cierres ni suspendas el ordenador durante un experimento que quieras mantener activo.

Para instalar: Python 3.12+, Node.js 22.13+ y **pnpm 11.19.0**; después `Install-Atlas.ps1`. El instalador comprueba las versiones, crea una copia previa si existe una base e instala las dependencias fijadas en `requirements.txt` y `frontend/pnpm-lock.yaml`. La interfaz se compila para el arranque habitual. No se arrancará un artefacto ausente o desactualizado.

`Status-Atlas.ps1` consulta la salud de la instancia. `Backup-Atlas.ps1` crea una copia coherente; además, se guardan copias automáticas al iniciar y cada 24 horas de funcionamiento, conservando siete. Para restaurar y actualizar, consulta la [guía de operación en Windows](docs/operacion_windows.md). Incluye los comandos completos, diagnóstico y comportamiento de recuperación.

El sobremesa se ha probado el 06/09/2026 con Python 3.14.4, Node 24.15.0 y pnpm 11.19.0; las versiones, ruta y comprobaciones de cada equipo están en [CONTINUIDAD.md](docs/CONTINUIDAD.md).

## Primer recorrido

1. **Cargar demostración** añade tres activos ficticios y movimientos sintéticos. No descarga una cartera real.
2. **Cartera** muestra efectivo, posiciones, aportaciones, P&L y TWR diario.
3. **Laboratorio** compara mantener y dos cruces de medias con selección cronológica 60/20/20, comisiones, deslizamiento y un mismo límite de posición para estrategia y benchmark.
4. **Agente IA** crea un experimento de duración y presupuesto limitados. Sin clave, usa «Catálogo fijo · sin IA». Se genera un informe y se observa la regla congelada sobre nuevas sesiones.
5. **Datos** importa CSV y permite conectar Yahoo diario en EUR. Las importaciones de movimientos se previsualizan antes de confirmar y omiten IDs ya importados.
6. **Ajustes** controla la parada de ejecución simulada y el límite de peso. La parada está activada por defecto.

## Conectar OpenAI o Anthropic

Copia `.env.example` a `.env` y escribe allí **solo la clave del proveedor que quieras usar**. El lanzador carga ese archivo en el motor Python; no pasa las claves al proceso de la interfaz. No pegues claves en prompts ni las subas al repositorio.

```dotenv
OPENAI_API_KEY=tu_clave_local
ANTHROPIC_API_KEY=
```

Reinicia ATLAS. En Agente IA selecciona proveedor, presupuesto en USD y duración. Crear ese experimento autoriza sus llamadas hasta el presupuesto indicado. La aplicación no hace llamadas de IA al arrancar. Una suscripción a ChatGPT o Claude no configura por sí sola una clave de API.

Modelos incluidos: `gpt-5.4-mini` y `claude-haiku-4-5-20251001`. El coste se estima con precios registrados el 05/09/2026; consulta la factura del proveedor para el importe real. No se ha realizado una llamada pagada durante la validación de esta entrega.

## Qué significa «dejarlo dos días»

El motor propone un máximo de ocho candidatos, ejecuta pruebas, congela el ganador, produce un informe y espera sesiones nuevas. Puede consultar las fuentes diarias cada seis horas y trabajar sin la pestaña abierta. El plazo de 48 horas acaba con una revisión; **no equivale a validar rentabilidad**. Por defecto, la promoción necesita como mínimo 20 sesiones nuevas, 126 observaciones fuera de muestra, 10 ejecuciones, Sharpe ≥0,5, caída ≤15% y resultados comparables bajo costes duplicados. Para observar 20 sesiones debes elegir una duración que realmente las permita, por ejemplo 720–1.080 horas, según calendario.

Si se cumplen los criterios, activaste la simulación automática y la parada global está desactivada, abre una cuenta paper independiente. Una señal al cierre solo puede ejecutarse en una apertura posterior recibida. Los datos sintéticos nunca habilitan esa promoción. No hay endpoint de órdenes reales.

## Estado y validación

- **0.2.0-rc.2 con CI verificada:** 446 pruebas Python y 91 subtests (22,13 s), 140 Vitest en 15 archivos (43,86 s) y 5/5 E2E (18,7 s) en Windows CI. Validación local separada: 446+91 (38,34 s, dos avisos previos), 140 Vitest (13,34 s) y 5/5 E2E (9,6 s). El [registro de candidata](docs/candidata_v0_2.md) conserva también el primer intento remoto fallido y sus correcciones.

- Candidata histórica **0.2.0-rc.1**: **368 pruebas y 91 subtests superados** en Windows, dos avisos anteriores; TypeScript, contratos, lint de aplicación, dependencias y build verificado correctos. Su CI y el ensayo interrumpido se conservan en el registro de candidata.

- Consolidación previa del núcleo de v0.2 en el sobremesa: **328 pruebas y 91 subtests superados**. Corregidas las escrituras concurrentes, pausa/cancelación durante cálculo, aplicación atómica de límites y recuperación de ejecuciones. Contratos OpenAPI/TypeScript comprobados, lint de aplicación y compilación correctos. La demo conservó datos y resultados con presupuesto cero. Garantías y deuda pendiente en [consolidación del núcleo](docs/consolidacion_core.md); validación operativa previa en la [auditoría de v0.2](docs/auditoria_v0_2.md). Estas cifras corresponden al bloque local anterior a las ejecuciones posteriores de GitHub Actions.
- Portátil: 167 pruebas automatizadas y 91 subtests superados en la revisión original de v0.1, con dos avisos de deprecación de TestClient; compilación, TypeScript y recuperación tras reinicio comprobados.
- Sobremesa, 06/09/2026: 167 pruebas y 91 subtests superados de nuevo, con los mismos dos avisos; compilación y TypeScript comprobados. Motor y proxy local responden correctamente. Se han probado en navegador la cartera de demostración, la comparación del Laboratorio y el informe de un experimento sin IA, con presupuesto, gasto y reserva cero. Parada, reinicio, persistencia e integridad SQLite comprobados; detalles en [CONTINUIDAD.md](docs/CONTINUIDAD.md).
- La descarga real de SXR8.DE se verificó en el portátil, con corte explícito anterior al 04/09/2026: 932 barras EUR. La consulta incluyendo el 04/09 falló correctamente porque Yahoo devolvió un cierre ausente con volumen; no se inventó el dato. Ese símbolo fue una prueba técnica, no una recomendación de inversión. La instalación del sobremesa se ha probado con datos sintéticos.
- El soporte WebMCP es opcional y no se ha validado en un navegador compatible.
- No se ha completado satisfactoriamente el ensayo sostenido de 48 horas; su repetición sigue aplazada. No se ha realizado una llamada real a los modelos ni una conexión con IBKR.

Detalles, limitaciones y próximos hitos: [guía de v0.1](docs/version_0_1.md).

```powershell
.\.venv\Scripts\python.exe -m pytest -q
pnpm --dir frontend exec tsc --noEmit
.\.venv\Scripts\python.exe tools\build_frontend.py
```

Detén ATLAS antes de reconstruir. `pnpm --dir frontend dev` queda disponible para desarrollo; el uso diario emplea la compilación verificada por el lanzador.

## Diseño del proyecto completo

- [Diseño completo editable](docs/atlas_quant_diseno.md)
- [Diseño en PDF](output/pdf/atlas_quant_diseno.pdf)
- [PDF en el móvil, con acceso privado](https://atlas-quant-lectura.patosverdes098.chatgpt.site/atlas_quant_diseno.pdf)

El diseño contiene 20 secciones, una matriz de los 16 requisitos solicitados, costes contrastados y seis fases de implementación. Sigue siendo el alcance objetivo; la v0.1 implementa un subconjunto descrito en su guía. El PDF publicado es la especificación original, no un certificado de funcionalidad implementada.

Los archivos `docs/insumos_*` y `docs/base_diseno_quant.md` son material de preparación; el documento definitivo es `docs/atlas_quant_diseno.md`.

`tools/render_design_pdf.py` genera el PDF a partir de la especificación. Utiliza ReportLab, pypdf y las fuentes Calibri de Windows. El resumen de verificación entregado está en `output/pdf/validacion_diseno.json`; el renderizador puede recrear temporales en `tmp/pdfs/`.
