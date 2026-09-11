# ATLAS Quant

**Rama local actual: `codex/v0.6-evaluador`.** Primer bloque SMA 20/50 implementado como módulo Python y referencia CLI: [uso y límites](docs/v0_6_evaluador.md). 861 pruebas Python y 91 subcasos correctos. La aplicación conserva la interfaz/API dev.3; no hay simulador económico v0.6 ni nueva etiqueta. Este desarrollo aún no se ha subido a GitHub y está separado de la PR #12.

**v0.5.0-dev.3: CI gratuita correcta y PR #12 preparada.** [Revisión/publicación y coste](docs/v0_5_dev3_entrega.md), [instalación en el portátil](docs/instalacion_portatil.md). Rama `codex/v0.5-comparador`, esquema 5; fusión/etiqueta autorizadas tras la revisión manual pendiente. El comienzo del evaluador SMA de v0.6 se conserva en una rama independiente y no forma parte de esta PR.

**v0.5.0-dev.3 · fichas y comparador de activos.** En Datos: precios EUR/USD, cobertura, volatilidad, caída máxima, comparación en base 100 y correlaciones sobre intervalos comunes, con informes inmutables. [Uso y validación](docs/v0_5_comparador.md), [ejemplo de planificación](docs/v0_5_ejemplo_guiado.md), [revisión del cierre v0.5](docs/v0_5_cierre.md). [Diagnóstico NVIDIA y evidencia pendiente](docs/diagnostico_nvidia_20260911.md).

**Entrega publicada: [v0.5.0-dev.2](https://github.com/Buzo500/atlas-quant/tree/v0.5.0-dev.2) · planificación y escenarios.** En Cartera v2: comparar aportaciones y rebalanceo con lotes/costes, combinar objetivos de estrategias con un presupuesto compartido, comparar TWR con una referencia total-return EUR por CSV y simular cambios de precios/FX. Informes revisados y guardados con fuentes y contexto; sin operaciones ni cambios en el libro. [Uso, reglas y alcance](docs/v0_5_planificacion.md). Esquema 5 conservado. [PR #11](https://github.com/Buzo500/atlas-quant/pull/11) fusionada, [CI gratuita](https://github.com/Buzo500/atlas-quant/actions/runs/34525527095) correcta; 0 USD facturables. [Estado de entrega](docs/CONTINUIDAD.md).

**Entrega publicada: v0.5.0-dev.1 · objetivos manuales, bandas y desviaciones.** [PR #10](https://github.com/Buzo500/atlas-quant/pull/10), [CI gratuita correcta](https://github.com/Buzo500/atlas-quant/actions/runs/34517010948): 739 Python + 91 subcasos, 283 frontend, ocho pruebas de transporte y 19 E2E. En Cartera v2 puedes guardar/activar versiones de objetivos y comparar su distribución con un patrimonio guardado. Diagnósticos trazables, sin propuestas de operaciones ni envíos. [Guía y límites](docs/v0_5_objetivos.md). Esquema 5 y libros anteriores conservados. Proxy local con conexiones y cancelaciones controladas; [evidencia](docs/diagnostico_api_20260910.md).

**Entrega publicada: [v0.4.0-dev.6](https://github.com/Buzo500/atlas-quant/tree/v0.4.0-dev.6) · D7/D8, esquema SQLite 5.** Rentabilidad por fechas en cartera v2: P&L, TWR y MWR/XIRR, costes y flujos, calidad y guardado de informes inmutables. Reutiliza libro y fuentes D6. [Uso D7](docs/v0_4_d7.md) y [evidencia D8](docs/v0_4_d8.md). [PR #9](https://github.com/Buzo500/atlas-quant/pull/9), squash `53cca20`, [CI gratuita correcta](https://github.com/Buzo500/atlas-quant/actions/runs/34509155203): 709 Python + 91 subcasos, 278 frontend y 19 E2E. Motor/interfaz habituales comprobados; [continuidad](docs/CONTINUIDAD.md). Entrega de desarrollo, no estable.

**Entrega anterior: [v0.4.0-dev.5](https://github.com/Buzo500/atlas-quant/tree/v0.4.0-dev.5)**, D6 completo integrado en [PR #8](https://github.com/Buzo500/atlas-quant/pull/8), CI gratuita [34503177151](https://github.com/Buzo500/atlas-quant/actions/runs/34503177151) correcta sobre `a356112`, squash `a308f81`. Libro/formularios EUR/USD, CSV de precios y FX, vínculos y patrimonio trazable. 677 Python + 91 subcasos, 270 frontend y 19 E2E. [Guía D6](docs/v0_4_d6_cierre.md). Desarrollo, no estable.

Las carteras anteriores conservan `legacy-eur-v1`, sus gráficos y CSV v1. Las nuevas permiten libro exacto `atlas-accounting-v2`, saldos/coste EUR/USD y NAV EUR con calidad y procedencia. D7 añade rentabilidad nativa por fechas con estados explícitos de ausencia o calidad provisional. Dividendos ordinarios: un pago completo por derecho; splits exactos y fracciones solo acreditadas y representables. Sin liquidación de fracciones ni fiscalidad automática. La evidencia de calidad debe ser declarada y contrastada.

**Entrega de desarrollo aceptada: `v0.3.0-dev.1`.** G1–G6 cerradas por el usuario el 09/09/2026, con pantalla completa comprobada manualmente en precios y cartera y CI completa correcta. Se acepta una incidencia conocida de espera intermitente en `/api/state`, todavía sin causa determinada. [Cierre y evidencia](docs/revision_final_v0_3.md). El ensayo de 48 horas sigue aplazado; esta aceptación no declara una versión estable.

Alcance aprobado de [v0.4 · Datos y contabilidad trazables](docs/plan_v0_4.md): D1–D8, CSV propio y EUR/USD. D1 especificado y D2–D8 integrados/publicados como desarrollo. El [primer alcance v0.5](docs/v0_5_alcance_inicial.md) está publicado como desarrollo. El estado de validación y publicación se recoge en [continuidad](docs/CONTINUIDAD.md).

[Comprobación habitual D5 del 10/09](docs/comprobacion_d5_20260910.md): migración 3→4, saldos/dividendos/split sintéticos y carteras anteriores conservados. En la comprobación posterior de v0.5, el adaptador Yahoo descarga realmente los dos históricos NVD.DE hasta el 09/09 y conserva íntegramente sus versiones anteriores; [evidencia y límites](docs/v0_5_planificacion.md). [Diagnóstico API actualizado](docs/diagnostico_api_20260910.md): cancelaciones y cierre de conexiones corregidos en v0.5, con evidencia local y límites explícitos.

[Arquitectura objetivo y contratos entre módulos](docs/arquitectura_objetivo.md): recorridos de investigación y ejecución, estrategia compartida, construcción de cartera, riesgo continuo, mandatos y conciliación. Es planificación autorizada; concreta v0.5–v0.7 sin renumerar versiones ni añadir bloques a v0.4. El paper externo automático se prevé en v0.7 y la automatización real en v1.3.

Versión anterior: **0.3.0-dev.1 · gráficos interactivos**. Conserva como antecedente `0.2.0-rc.2`, candidata publicada con CI verificada; el ensayo de 48 horas sigue aplazado y v0.2 no se declara estable. El [plan de v0.3](docs/plan_v0_3.md) fija el alcance, y la [guía de gráficos](docs/graficos_v0_3.md) explica su uso y validación. La [hoja de ruta](docs/hoja_de_ruta.md) recoge las entregas previstas y [CHANGELOG.md](CHANGELOG.md) sus cambios.

Aplicación local para analizar una cartera en EUR, comparar estrategias de acciones/ETF y ejecutar experimentos acotados con OpenAI o Anthropic. Incluye simulación de órdenes; no está conectada a ningún bróker.

Estado de entrega y comprobaciones pendientes: [revisión final de v0.3](docs/revision_final_v0_3.md). Incluye el diagnóstico optativo de API y la evidencia actual de escalado; no declara la versión estable.

Preferencias confirmadas: OpenAI y Anthropic seleccionables desde la app, integración preparada sin consumo hasta decidir un presupuesto y primera etapa en el PC. El presupuesto inicial sigue en cero. La entrega se ha probado en Windows; Ubuntu no se ha validado todavía.

Los gráficos de v0.3 se desarrollan por autorización expresa del usuario. Aprendizaje acumulativo, indicadores nuevos, móvil, ejecución remota e informes LaTeX mantienen su alcance futuro en el [backlog](docs/backlog_planificacion.md).

Para trabajar en otro equipo: [traslado al sobremesa y conversación nueva en Codex](docs/traslado_sobremesa.md). El contexto para retomar el proyecto está en [CONTINUIDAD.md](docs/CONTINUIDAD.md); Git no traslada automáticamente el chat original ni los experimentos locales.

Interfaz local actual: [diseño crema y cobre, adaptación ultrapanorámica y validación](docs/frontend_crema_cobre.md). Incluye las cinco secciones existentes; los informes LaTeX siguen en planificación.

Consolidación posterior: [nueve mejoras de fiabilidad, trazabilidad y pruebas del frontend](docs/frontend_consolidacion.md), más correcciones de foco, anuncios de estado y aislamiento de pruebas. [PR #2](https://github.com/Buzo500/atlas-quant/pull/2) fusionada y `v0.2.0-rc.2` publicada sobre `9aee422`; la [CI de la etiqueta](https://github.com/Buzo500/atlas-quant/actions/runs/34251099444) pasó con 446 pruebas del motor y 91 subtests, 140 de interfaz y cinco E2E. **[Escalado físico de Windows al 125 % y 150 % comprobado](docs/validacion_escalado_windows.md)** en el monitor 3440 × 1440 de este PC, con el 100 % inicial restaurado. Ensayo de 48 horas y seguimiento aplazados. [Evidencia, incidencias y límites](docs/candidata_v0_2.md).

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
2. **Cartera** muestra efectivo, posiciones, aportaciones, P&L y TWR diario. Su curva permite consultar una ficha junto al cursor o por teclado, elegir línea/área o TWR desde el origen, filtrar fechas y navegar con barra y lupas. En pantalla completa admite arrastre y zoom con la rueda; precios y resultados comparten estos controles.
3. **Laboratorio** compara mantener y dos cruces de medias con selección cronológica 60/20/20, comisiones, deslizamiento y un mismo límite de posición para estrategia y benchmark.
4. **Agente IA** crea un experimento de duración y presupuesto limitados. Sin clave, usa «Catálogo fijo · sin IA». Se genera un informe y se observa la regla congelada sobre nuevas sesiones.
5. **Datos** permite explorar precios de cada activo: velas, línea, área o barras OHLC, volumen y agregación diaria/semanal/mensual. También importa CSV y permite conectar Yahoo diario en EUR. Las importaciones de movimientos se previsualizan antes de confirmar y omiten IDs ya importados.
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

- **0.3.0-dev.1, CI de Windows superada el 09/09/2026:** [ejecución 34340199451](https://github.com/Buzo500/atlas-quant/actions/runs/34340199451), fuentes `c8f4eb6`: **477 pruebas Python y 91 subtests, 244 de frontend y 10/10 E2E**, instalación limpia, build, tipos, contratos, lint, arranque y parada correctos. Dentro de la cuota gratuita comprobada. [PR #3](https://github.com/Buzo500/atlas-quant/pull/3) en borrador; sin fusión ni etiqueta nueva. El cierre documental posterior no cambia las fuentes validadas.

- **0.3.0-dev.1, revisión local del 09/09/2026:** 244 pruebas de frontend, TypeScript, lint y build con manifiesto correctos. Los cinco recorridos E2E de gráficos pasan; aquel intento local queda en **9/10** por una espera intermitente de 10 s en `/api/state`, todavía sin causa acreditada. La CI posterior pasa 10/10 sin aumentar límites ni añadir reintentos; no acredita resuelta la intermitencia. Rendimiento medido con 100.000 observaciones y 1.000 velas visibles. [Revisión, incidencias y evidencia](docs/revision_graficos_20260909.md). El escalado físico 125 %/150 % corresponde a la entrega inicial y sigue pendiente repetirlo sobre los controles actuales; ensayo sostenido aplazado.

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
