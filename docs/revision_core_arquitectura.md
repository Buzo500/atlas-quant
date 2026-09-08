# ATLAS Quant · Revisión del núcleo y la arquitectura

Fecha: 6 de septiembre de 2026. Revisión del árbol de trabajo sobre `97520b8`, con las mejoras locales de v0.2 todavía sin publicar. El usuario prioriza corrección del núcleo y buenas prácticas antes de ampliar funciones. Esta revisión no modifica el programa ni sus datos de uso.

> Actualización posterior: el usuario autorizó la corrección y se ha implementado la [consolidación del núcleo](consolidacion_core.md), con 328 pruebas y 91 subtests superados. Los hallazgos y referencias de líneas de este documento describen el estado anterior; consultar la consolidación para su resolución y los pendientes.

## Valoración

Hay una base razonable de aplicación local modular, con decisiones acertadas de cálculo, validación y recuperación. No corresponde afirmar que el diseño esté terminado ni que permita escalar horizontalmente sin cambios. Se ha encontrado un defecto actual de concurrencia y varias deudas concretas de mantenimiento y verificación.

Ampliación funcional significa poder añadir estrategias, proveedores y pantallas conservando reglas comunes. Escala horizontal significa repartir trabajo entre varios procesos o equipos sin duplicación ni pérdida de actualizaciones. La primera está parcialmente facilitada; la segunda no está soportada por el ejecutor actual. Varias pantallas que consultan un único servidor tampoco equivalen a varios motores procesando la misma cola.

## Buenas bases verificadas en código

- El cálculo contable, los backtests, la política de promoción y la simulación están separados de HTTP y de los proveedores externos. `analytics.py`, `backtest.py` y `paper.py` pueden probarse con datos controlados, sin red ni navegador. Las funciones de simulación evitan modificar la cuenta de entrada si fallan.
- Validación explícita de datos y entradas, importes contables con Decimal, rechazo de valores no finitos y supuestos de ejecución documentados. Los tests comprueban resultados esperados, causalidad de señales, costes y límites, además de respuestas HTTP.
- La IA está limitada a propuestas e informes; no genera código ejecutable ni transmite órdenes. Las reservas de presupuesto se guardan antes de la llamada externa y la recuperación trata explícitamente los trabajos interrumpidos.
- SQLite usa transacciones; las versiones de datos se conservan, hay migración validada y copias/restauración probadas. Las mejoras operativas controlan procesos propios y rechazan compilaciones ausentes o modificadas.
- Dependencias fijadas, factoría `create_app(..., run_worker=False)` para pruebas y un workflow de validación con permisos de lectura y acciones fijadas por commit.

Estos puntos son útiles y verificables, pero no demuestran por sí solos cumplimiento exhaustivo de SOLID, ausencia de defectos o capacidad distribuida. Las 254 pruebas y 91 subtests de la última validación registrada cubren sus escenarios; no son una medición completa de calidad arquitectónica.

## Hallazgos y prioridad

### CORE-001 · Prioritaria para el cierre: una descarga fallida puede deshacer la versión activa de datos

Referencias: `backend/atlas_quant/service.py:64` y `:79`; importación concurrente en `backend/atlas_quant/app.py:158`; escritura completa en `backend/atlas_quant/store.py:87`.

`refresh_feed` conserva una copia del conjunto antes de esperar la red. Si la consulta falla, guarda de nuevo esa copia para registrar el error. Mientras espera, la importación CSV puede actualizar ese conjunto porque no comparte el bloqueo de la consulta. El guardado posterior del objeto antiguo sustituye también las barras y la versión activa.

**Reproducción aislada:** conjunto v1 con una barra; descarga simulada en espera; importación v2 con dos barras; fallo de descarga. Resultado: el conjunto activo vuelve a v1 y a una barra. La tabla de versiones conserva v1 y v2, pero v2 deja de ser el estado activo visible. No se provocó este caso en la base del usuario.

**Corrección prioritaria propuesta:** actualizar únicamente los metadatos de la fuente en una transacción sobre el estado vigente, con control de revisión cuando corresponda. Evitar escrituras completas de snapshots antiguos después de un `await`; comprobar también el recorrido de descarga correcta concurrente. Añadir regresión de ambos casos antes de dar por cerrado este defecto.

### CORE-002 · Media: los controles esperan a que terminen cálculos largos

Referencias: `backend/atlas_quant/service.py:233` y `backend/atlas_quant/app.py:240`.

`tick()` mantiene un bloqueo durante la investigación y la observación; el controlador de pausa/cancelación necesita el mismo bloqueo. **Reproducción aislada:** durante un backtest controlado, la petición de cancelación queda pendiente; se termina y guarda la investigación antes de aplicar `cancelled`.

Esto no es una cancelación inmediata. Antes de ampliar la carga, separar solicitudes de control, ejecución y publicación de resultados, mantener cortas las secciones críticas y definir puntos de cancelación. Cancelar una tarea asíncrona no debe confundirse con haber detenido el cálculo que delegó a otro hilo. Los resultados terminados después de una cancelación no deben reactivar el trabajo.

### CORE-003 · Media: contratos incompletos entre motor e interfaz

Referencias: `frontend/app/workbench.tsx:36`, `frontend/app/page.tsx:30`; respuestas en `backend/atlas_quant/app.py:141`, `:183` y `:232`.

Las entradas HTTP están validadas, pero el cliente devuelve `Promise<any>` y los estados principales también usan `any`. Los tres endpoints de estado, cartera y experimento exponen un esquema de respuesta vacío en OpenAPI. Cambiar un campo puede romper una pantalla sin que TypeScript detecte la incompatibilidad.

Definir modelos explícitos de respuesta, tipos de cliente coherentes con esos contratos y pruebas de compatibilidad. Hacerlo primero en los límites de estado/cartera/experimento, con migración gradual; no convertir todo el proyecto a otra arquitectura de golpe.

### CORE-004 · Media: responsabilidades y políticas que conviene consolidar

- `app.py:188`, `:240` y `:265` contienen lógica de importación contable, transiciones y controles de riesgo dentro de endpoints. Extraer esos casos de uso a la capa de aplicación permitiría reutilizarlos desde HTTP, pruebas u otros clientes con las mismas reglas.
- `service.py:153` ejecuta SQL directamente sobre `versions`. `Store` existe, pero la frontera de persistencia todavía no encapsula todos los accesos.
- Las señales y el dimensionamiento de compras aparecen tanto en `backtest.py:62`/`:78` como en `paper.py:52`/`:69`. No se ha demostrado una divergencia actual: la deuda es el riesgo de modificar una copia al añadir una estrategia. Compartir esas políticas y comprobar su equivalencia conserva las diferencias legítimas entre replay histórico y ejecución incremental.
- `frontend/app/workbench.tsx` reúne 1.227 líneas con peticiones, formularios, sondeo y paneles. La longitud sola no demuestra un defecto, pero esas responsabilidades ya ofrecen separaciones concretas: cliente API, tipos, hooks y paneles por función.

### CORE-005 · Media: controles de calidad aún incompletos

El lint existente de frontend, ejecutado sin correcciones automáticas, terminó con código 1. Incluye diagnósticos de tipos, hooks, claves React y accesibilidad, algunos en componentes base; se deben revisar individualmente y no contar cada aviso como un bug confirmado.

El workflow actual comprueba Python, TypeScript, compilación y smoke HTTP; no exige lint ni incorpora regresiones automatizadas de interacción en navegador. Las comprobaciones manuales de UI registradas sí existen. La ejecución remota de CI y la prueba sostenida siguen pendientes.

Resolver o configurar justificadamente el lint del código mantenido; incorporar el control a CI y añadir regresiones útiles de importación/previsualización, experimento sin gasto y controles durante ejecución. No sustituir estas comprobaciones por un objetivo arbitrario de número de tests.

## Límite específico de escala horizontal

El arranque habitual usa un único ejecutor. `Service.lock` y `Store.lock` pertenecen a sus objetos/procesos; los trabajos se leen en una lista y se guardan después, sin reclamación atómica que reserve cada trabajo para un trabajador. La factoría de aplicación arranca un worker y recupera estados al iniciar (`app.py:96`).

**Reproducción aislada de dos ejecutores:** dos instancias de Service sobre la misma SQLite temporal, con dos trabajos en cola. Secuencia observada: A ejecuta el nuevo, B el antiguo y A vuelve a ejecutar el antiguo desde su lista inicial. Es un impedimento para añadir trabajadores; no describe el funcionamiento habitual con un solo worker.

SQLite WAL permite un escritor a la vez y requiere que los procesos que comparten su memoria de coordinación estén en el mismo equipo. Compartir el archivo WAL por red no convierte este diseño en una base distribuida. [Documentación oficial de SQLite](https://www.sqlite.org/wal.html).

Antes de varios ejecutores harán falta identidad de solicitudes, reclamación persistente de trabajos, control de versiones al escribir, tratamiento de posesión/interrupciones y coordinación de efectos externos. Aumentar `--workers` crea procesos adicionales, no añade esas garantías de negocio. [Documentación de workers de FastAPI](https://fastapi.tiangolo.com/deployment/server-workers/).

No se propone introducir ahora microservicios, Kubernetes o sustituir SQLite por anticipación. Mantener un monolito modular y un único ejecutor es una elección proporcionada al alcance personal; hay que declarar y comprobar ese límite, y mejorar las fronteras que permitirán cambiarlo cuando exista una necesidad medida.

## Orden de consolidación recomendado

1. Corregir CORE-001 y añadir regresiones deterministas de escrituras concurrentes. Es un defecto del núcleo actual y precede al cierre de v0.2.
2. Precisar y probar pausa/cancelación, actualización de estado y publicación de resultados. Mantener explícitamente un único ejecutor mientras no existan garantías multiproceso.
3. Extraer los casos de uso HTTP y compartir políticas de estrategia/ejecución; conservar resultados mediante pruebas de equivalencia y datos de referencia.
4. Tipar los contratos del motor y el cliente; separar responsabilidades de los paneles al intervenir sobre ellas.
5. Completar los controles de calidad, CI, mediciones de respuesta con cargas representativas, recuperación y ensayo sostenido. Registrar escenarios, umbrales y resultados antes de declarar una versión estable.

Las nuevas funciones de móvil, red remota, gráficos y aprendizaje permanecen en sus hitos futuros. Esta revisión no los implementa y no inicia aún los refactores descritos. El defecto y las deudas quedan registrados para trabajar sobre ellos antes de ampliar el producto.

## Evidencia de esta revisión

`output/validation/core_review_probes.py` conserva las reproducciones de actualización concurrente, espera de cancelación y dos ejecutores. El resultado está en `output/validation/core_review_probes.json` (06/09/2026, 16:24 UTC). Se usaron proveedores simulados y bases temporales, eliminadas al terminar; no hubo llamadas de red o IA ni cambios en la base real. Estos dos archivos están excluidos de Git. Las reproducciones demuestran los escenarios descritos y todavía no son pruebas de regresión incorporadas a la suite.

El lint existente se ejecutó en lectura, sin `--fix`. No se repitió la suite completa ni el ensayo de interfaz para este informe, porque no se ha modificado el programa; los 254 tests corresponden a la validación anterior registrada, no a una nueva ejecución en esta revisión.
