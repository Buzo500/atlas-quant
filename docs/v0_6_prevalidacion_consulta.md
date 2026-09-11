# v0.6 · Prevalidación, consulta y captura de incidencias

El usuario autoriza «Vale, haz las 5»: buscar un dataset observado acreditado,
prevalidación visual del CSV, capturar la próxima recurrencia API, búsqueda y
comparación de candidatas y concretar las pruebas estadísticas antes de programarlas.
Entrega local **0.6.0-dev.4**, rama `codex/v0.6-evaluador`, esquema 5.

## Prevalidación antes de configurar

En **Laboratorio → Simulación SMA con protocolo temporal**, selecciona una versión
CSV nativa EUR y pulsa **Prevalidar CSV antes de configurar**. La consulta muestra
barras y rango, base y calendario declarados, identidad/mercado, huecos de cobertura,
disponibilidad ausente o anterior al cierre y eventos conocidos.

Es un inventario de **toda esa versión**, no una aprobación del protocolo: un fallo
en una fila puede quedar fuera del periodo que finalmente elijas. Base/identidad
incompatibles sí bloquean la versión. La ausencia de eventos en la base no prueba
que no existieron; siguen pendientes las aperturas, calentamiento, disponibilidad
antes de la siguiente apertura, ausencia de eventos y reserva del periodo elegido.
No se muestran precios, métricas ni señales en esta consulta.

La prevalidación no importa, acredita, crea protocolo, expone reserva ni escribe
auditoría/libro. Es una instantánea de solo lectura: cambiar versión descarta la
respuesta anterior. El cálculo vuelve a comprobar su contexto completo; una
prevalidación anterior nunca autoriza omitir controles. Los controles comunes de
identidad/base/calendario se comparten con la congelación del protocolo.

API de lectura: `GET /api/lab/sources/preflight?series_id=...&series_version=...`.
Versión explícita, máximo 100.000 barras como la frontera existente del Laboratorio;
incluye hash de fuente/contexto y revisión de eventos. No modifica hashes antiguos.

## Recuperar hipótesis y comparar revisiones

En **Hipótesis y candidatas de investigación**, abre **Buscar hipótesis, descartes
y comparar revisiones**. El texto busca en nombre, hipótesis y motivo de **todas
las revisiones**, sin distinguir mayúsculas Unicode. No elimina tildes. `%` y `_`
son caracteres literales, no comodines. El filtro de estado corresponde a la
revisión histórica, no necesariamente al estado actual de la candidata.

Selecciona entre dos y cuatro revisiones; pueden ser de una misma candidata.
La selección se conserva entre búsquedas/páginas y se muestra explícitamente.
**Comparar revisiones seleccionadas** utiliza esos números de revisión, nunca
los sustituye silenciosamente por la última versión. La consulta no guarda ni
activa nada. Cambiar la selección invalida el resultado anterior.

La tabla contrasta desarrollo neto SMA, comprar/mantener, efectivo y condiciones
económicas. Conserva motivos y constancia de prueba final capturada. Abrir después
una reserva no incorpora sus resultados a una revisión anterior. No calcula ni
promedia rendimientos entre informes ni ordena una clasificación de ganadoras.

Señala contexto diferente o evidencia insuficiente si faltan informes o no
coinciden fuente/versionado/evidencia, identidad, periodo, política o configuración
económica. Los parámetros SMA pueden diferir; «mismo contexto de desarrollo» no
declara equivalentes las configuraciones de walk-forward/sensibilidad ni atribuye
significación estadística. Las condiciones económicas y hashes se pueden consultar.

API: `GET /api/lab/candidates/search?q=...&status=discarded&offset=0&limit=20`
(omitir status para todos) y `POST /api/lab/candidates/compare`, cuerpo
`{"items":[{"candidate_id":"<hash>","revision":1},{"candidate_id":"<hash>","revision":2}]}`.
Dos a cuatro referencias distintas, lectura en una única transacción, comparación
del hash de desarrollo con la evidencia capturada; discrepancias se rechazan.
Mantiene protección local del POST, sin reintentos automáticos.

## Captura de API

`tools/diagnostics/run_api_diagnostic.py` conserva el harness aislado y sus límites.
Añade correlación entre navegador/APIRequestContext, proxy y ASGI; registra etapas
y tiempos sin cuerpo, consultas URL, cookies ni claves. APIRequestContext entrega
respuesta ya almacenada: ese tiempo no se etiqueta como llegada de cabeceras por red.

Al terminar genera `var/validation/e2e-<id>/diagnostic-report.json`, también en la
salida de consola para su conservación en Actions. Agrupa errores y peticiones
de al menos un segundo, señala la última etapa observada y límites de la captura.
No convierte una etapa incompleta en una causa raíz. Un rechazo al arrancar o
una cancelación deliberada del test no equivale al timeout histórico de diez segundos.

El workflow local queda preparado para usar este wrapper en **la próxima CI que
se autorice**. No cambia el tiempo límite, runner, costes, política de reintentos
ni dispara un workflow. No es un monitor de la instalación habitual ni un ensayo
de 48 horas. Ejemplo con ATLAS detenido:

```powershell
.\.venv\Scripts\python.exe tools\diagnostics\run_api_diagnostic.py --grep "navegaci.n gr.fica" --timeout 180
```

Lectura acotada a 32 MiB de cada log; máximo 100 incidencias y 120 eventos por
incidencia, con truncamiento declarado. Las trazas originales permanecen en el
directorio aislado. El primer alcance instrumenta peticiones del navegador y
lecturas del helper E2E `readApi`; llamadas de soporte no instrumentadas aún pueden
aparecer solo en proxy/ASGI. El arranque habitual no activa estas trazas.

## Datos observados y diseño estadístico

La [auditoría de datos](v0_6_csv_observado.md) registra la búsqueda de una fuente
gratuita suficiente y los bloqueos encontrados. **No se ha conseguido acreditar
un dataset observado apto**; no se inventan disponibilidad ni eventos.
El [contrato estadístico propuesto](v0_6_robustez_estadistica.md) define método,
semillas, límites y pruebas; su implementación no forma parte de estas cinco tareas.

## Operación y comprobaciones

ATLAS detenido antes de editar; copia previa
`backups/atlas-20260911T130808392926Z-e4eca471`. Desarrollo sin cambios del esquema
5 ni del libro. Las pruebas destructivas y la revisión visual usan bases E2E nuevas.
Resultado final de pruebas y arranque en [continuidad](CONTINUIDAD.md).
Regresión: **1.004 Python + 91 subcasos, 322 frontend, ocho pruebas Node**;
contratos, TypeScript, lint y build canónico correctos. **23/23 E2E** con captura
en `e2e-48ea8fb5ecc84a728994ca1c2758ac45` (1,7 min), integridad correcta,
base habitual intacta y puertos liberados. Captura: 1.769 peticiones correlacionadas;
74 grupos de error/cancelación, ninguno con duración capturada de al menos 1 s,
sin truncamiento. No reproduce ni resuelve el timeout histórico de diez segundos.

La prueba dirigida previa detectó un desbordamiento a 960 px en la prevalidación
y después un filtro vacío que provocaba HTTP 422 al pedir todos los estados.
Se corrigieron el ancho mínimo/ajuste de texto y la omisión del filtro vacío;
3/3 recorridos dirigidos posteriores pasaron (17,9 s). No se ocultaron fallos
ampliando tiempos o reintentando peticiones. Regresión de componente comprueba
que el filtro ausente no se envía como una cadena vacía.

Revisión visual a 960, 1366 y 3440 px: tablas sin desbordamiento de página,
identificadores abreviados con detalle completo y separación de motivos. Los
textos finales de prevalidación pasaron otras diez pruebas backend y cinco de
componente; compilación posterior. Capturas locales `output/validation/dev4-*.png`.
Estos anchos CSS no sustituyen una validación física nueva del portátil.

No publica nueva CI, PR, fusión o etiqueta. Portátil, ensayo de 48 horas, movimientos
personales, llamadas pagadas y operaciones externas mantienen sus aplazamientos.
