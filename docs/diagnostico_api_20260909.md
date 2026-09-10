# Diagnóstico de la espera intermitente de API · 09/09/2026

**Resultado: no reproducida; causa todavía sin determinar.** Se ha seguido la petición entre cliente, proxy y motor sobre bases sintéticas nuevas. No se ha aplicado una corrección a la aplicación, aumentado tiempos de espera ni añadido reintentos. La CI correcta y los ensayos de este documento no convierten en resuelto el fallo local anterior de `/api/state`.

**[Nueva captura autorizada en D5, 10/09/2026](diagnostico_api_20260910.md):** 18/18 E2E instrumentados, sin reproducir la espera original. Dos errores de socket se correlacionan con lecturas ya abandonadas y envíos ASGI menores de 90 ms; no se atribuye a esos errores la causa de los 10 s. La incidencia sigue abierta.

## Decisión de seguimiento tras revisar la CI final

**Aceptación expresa del usuario · 09/09/2026:** se acepta esta incidencia conocida para la entrega de desarrollo `0.3.0-dev.1` y se autoriza el cierre de G6. Se mantienen la incidencia abierta, los límites y el procedimiento de captura si reaparece. Esta decisión sustituye las referencias inferiores a una aceptación pendiente; no demuestra una corrección.

Revisión del 09/09/2026, autorizada por el usuario: **mantener como incidencia conocida abierta, sin otra repetición genérica ahora**. Siete repeticiones del recorrido original, lecturas concurrentes, pruebas con pausas y suite instrumentada no reprodujeron el síntoma; las CI `34340199451` y `34346311068` también terminaron con 10/10 E2E. No hay evidencia nueva que discrimine una hipótesis concreta. La falta de reproducción no permite estimar su frecuencia ni descartarlo en otras carteras.

Impacto demostrado: demora de lectura de estado y fallo de un recorrido automatizado. No se ha observado corrupción de datos en estos ensayos, pero eso no acredita ausencia de otros efectos ni permite atribuir la causa al motor, proxy o navegador. No se cambian tiempos, reintentos, dependencias o lógica de ejecución por conjetura.

Si reaparece, conservar hora, acción, identificador de ejecución y logs antes de otra prueba. En una base E2E nueva, usar el diagnóstico optativo y emparejar la petición lenta entre cliente, proxy y ASGI según el procedimiento inferior. Conservar también respuestas fallidas y el cierre seguro del entorno; no dejar procesos activos para preservar evidencia que ya está en disco. Una recurrencia identificada, fallos de controles o pérdida de coherencia obligarían a reabrir la investigación antes de aceptar la entrega afectada.

**Recomendación de entrega:** puede proponerse como limitación explícita de `0.3.0-dev.1` para uso local supervisado, sujeta a aceptación del usuario; no se declara corregida ni se cierra G6 por esta decisión. No se añade seguimiento automático ni se reactiva el ensayo de 48 horas. Las trazas siguen desactivadas en el arranque habitual.

## Qué se ha observado

El fallo original sigue en `e2e-08bd90a1b5ac4b31b17bcdf153f93389`: un GET de Playwright agotó 10.013,609 ms; una lectura simultánea del navegador terminó con 200 tras 10.094,533 ms. El proxy registró `UND_ERR_SOCKET`, pero carecía de tiempos e identificadores para vincularlo a una petición concreta. El detalle de ese antecedente se conserva en `output/validation/v03-review-state-timeout-20260909.json`.

En el diagnóstico actual:

- **Siete repeticiones del recorrido original**, cada una con una base nueva: siete correctas. Sin cambiar el test ni sus límites de espera.
- **100 ciclos de POST de demo seguido de tres lecturas concurrentes**: 100 GET directos al motor, 100 por el proxy con `APIRequestContext` y 100 desde Chromium. Los 300 responden correctamente; cada cliente conserva un límite de 10 s y no reintenta. Los POST son idempotentes sobre la demo aislada, no operaciones sobre la cartera habitual.
- **32 lecturas adicionales** alrededor de pausas de 4,8–5,2 s, próximas al cierre de conexiones inactivas del motor: todas correctas. Las conexiones de entrada de la sonda son nuevas; el proxy conserva su propio pool hacia el motor. Tráfico ajeno al test puede afectar la inactividad efectiva, por lo que esto no certifica una carrera exacta en el límite.
- **Suite E2E completa con trazas:** 10/10, 29,5 s, ejecución `e2e-14667ae05ed848b5ad853e9835ef65ae`. Incluye controles, importación, Laboratorio y gráficos. No se ejecuta el ensayo de 48 horas.

| Cliente, bajo las tres lecturas concurrentes | Mediana | p95 | Máximo |
|---|---:|---:|---:|
| Directo al motor | 55,7 ms | 68,6 ms | 102,4 ms |
| Proxy, cliente de pruebas | 61,7 ms | 73,9 ms | 111,7 ms |
| Navegador mediante el proxy | 64,6 ms | 77,1 ms | 132,6 ms |

Las 32 lecturas con pausas tuvieron p95 de 81,7 ms y máximo de 89,8 ms. En la suite completa, las 53 lecturas de estado del motor terminaron el envío ASGI en un máximo de 95,4 ms; las 53 respuestas 200 de estado del proxy terminaron en un máximo de 102,6 ms. Estos son tiempos del servidor, distintos de los tiempos completos del cliente de la tabla.

Se observó tráfico GET fuera del intervalo de ejecución de Playwright, incluso antes de que el motor estuviera listo y después de su cierre. Allí aparecen rechazos `ECONNREFUSED` rápidos. Es tráfico ajeno a ese test; no se ha identificado el cliente que lo origina. **No explica por sí mismo la espera histórica de 10 s ni equivale al `UND_ERR_SOCKET` anterior.**

## Instrumentación y límites

Se añaden herramientas optativas en `tools/diagnostics/`, separadas de los lanzadores habituales:

- `run_api_diagnostic.py` reutiliza `run_e2e.py` y sus bases nuevas, bloqueo, procesos propios, límites, comprobación de presupuesto y cierre. Solo en ese proceso cambia las órdenes de arranque para cargar las trazas.
- `api_proxy.cjs` registra llegada y fin/cierre HTTP, creación/envío/cabeceras/final/error de la petición upstream mediante los canales de diagnóstico de Node. Un identificador se propaga al motor. También detecta retrasos del bucle de eventos superiores a 100 ms.
- `api_backend.py` envuelve la aplicación ASGI para registrar entrada, cabeceras y fin de cuerpo, con el mismo identificador. Conserva los controles, ejecutor y configuración de servidor existentes.
- `api_clients.cjs` ejecuta los 100 ciclos concurrentes solo sobre un entorno E2E activo e identificado; bloquea rutas de navegador externas y mutaciones distintas de la demo.

No se registran cuerpos, cookies, claves, cabeceras de autorización ni consultas URL. No cambian el motor de negocio, contratos, esquema, dependencias, interfaz compilada ni la política HTTP normal. **Las trazas no están activadas en el arranque habitual.** La instrumentación sí modifica el ritmo de ejecución y añade una cabecera técnica en los dos últimos entornos: no se puede descartar que altere una carrera intermitente.

Los primeros siete ensayos correlacionan por secuencia, socket y tiempo; los dos últimos propagan además el identificador explícito. Las mediciones corresponden a la demo, no a todas las posibles carteras ni a una carga prolongada. No se han acreditado ni un bloqueo SQLite, ni una saturación del motor, ni un defecto concreto del proxy como causa del fallo original. Corregir cualquiera de ellos ahora sería especulativo.

## Reproducción y evidencia

Con ATLAS detenido y el build verificado, desde PowerShell en la raíz:

```powershell
.\.venv\Scripts\python.exe tools\diagnostics\run_api_diagnostic.py --grep 'cartera vacía' --timeout 60
```

Omitir `--grep` y usar `--timeout 120` ejecuta la suite completa. Para las lecturas concurrentes, iniciar el modo manual y utilizar en otra consola el identificador que imprima:

```powershell
.\.venv\Scripts\python.exe tools\diagnostics\run_api_diagnostic.py --manual --timeout 600
node tools/diagnostics/api_clients.cjs e2e-IDENTIFICADOR
.\.venv\Scripts\python.exe tools/run_e2e.py --stop-run e2e-IDENTIFICADOR
```

Cada ensayo conserva `frontend.log`, `backend.log`, `run.json` y, cuando corresponde, resultados de Playwright en `var/validation/e2e-…/`. El informe agregado `output/validation/api-diagnostic-20260909.json` identifica los nueve entornos, sus resultados, huellas de las herramientas usadas entonces y estadísticas. El ensayo concurrente es `e2e-93ff6bfec5a64917bd3b4b0b81ad8843`; sus dos informes válidos son `api-clients-e2e-93ff6bfec5a64917bd3b4b0b81ad8843.json` y `api-idle-http-e2e-93ff6bfec5a64917bd3b4b0b81ad8843.json`.

Se conservan dos fallos de preparación que **no realizaron peticiones HTTP**: resolución inicial incorrecta de la carpeta de Chromium, corregida configurándola antes de importar Playwright, y una sonda que pasó un objeto Request a un helper que esperaba una URL. No cuentan como fallos de ATLAS ni como lecturas realizadas. El informe agregado señala ambos archivos.

Los nueve entornos finalizaron con código 0 en ambos servidores, puertos liberados, hashes de la base habitual conservados e integridad `ok`. Las herramientas pasan comprobación de sintaxis Python/Node; el manifiesto del frontend sigue verificado. ATLAS estaba detenido al comenzar y queda detenido. No se ha subido código, ejecutado otra CI ni modificado la PR en este diagnóstico.

El siguiente paso útil si reaparece el síntoma es conservar el entorno y emparejar sus eventos: si falta `incoming`, la petición aún no llegó al proxy; si falta `upstream_send`, no salió de su pool; si hay entrada ASGI pero no fin, se localiza en el motor; si ambos servidores terminan pronto, se investigan entrega y cliente. Ese análisis requiere capturar una petición realmente lenta, no inferir su causa de estos ensayos correctos.

## Consolidación posterior para revisión final · 09/09/2026

Se revisaron las herramientas antes de incorporarlas a la entrega. Las protecciones Python ya no usan `assert`: rechazan una base o archivo de parada ajenos incluso con `-O`, antes de importar la aplicación. El preload de Node verifica también las rutas aisladas antes de instalar hooks. El cliente valida descriptor completo, token, URL, rutas resueltas y existencia de los procesos identificados; el lanzador sigue siendo responsable de acreditar la propiedad real de los listeners.

Los tres clientes comprueban HTTP 200 y estado sintético, parada activada, ausencia de proveedores configurados y de experimentos; se añade una lectura previa antes de los POST. Una respuesta de error con JSON aparentemente válido ya no puede marcarse correcta en el cliente de navegador. Las respuestas de APIRequestContext se liberan en `finally` y la carpeta de informes se crea cuando falta, sin sobrescribir informes previos. Ninguna de estas correcciones diagnostica la causa de la espera del programa.

Validación: **27 pruebas Python de diagnóstico/aislamiento en 1,55 s**, incluidas tres pruebas Node. Entorno real nuevo `e2e-a9f9e2f0e3704ea09a0067c2246a4a66`: **301 lecturas correctas** (300 concurrentes y una previa), máximo observado **112,42 ms**. Informe `output/validation/api-clients-e2e-a9f9e2f0e3704ea09a0067c2246a4a66.json`; cierre 0/0, integridad `ok`, hashes habituales conservados y puertos libres. No se repitió la suite E2E completa ni se ejecutó CI para esta consolidación. [Índice de revisión final](revision_final_v0_3.md).

Incidencias de preparación conservadas: pytest no pudo crear su carpeta temporal predeterminada por permisos locales; se usó una carpeta nueva bajo `var/validation/`. Después, una aserción del test de Node falló al decodificar UTF-8 con la codificación de consola de Windows; se corrigió la captura explícita UTF-8. Los controles sí rechazaban el arranque; no fueron fallos de la API. La ejecución final de 27 pruebas es posterior a esas correcciones.

**Revisión de instalación limpia antes de cerrar CI:** se reprodujo que el guard de Node intentaba resolver `var/validation` aunque esa carpeta todavía no existiera en un checkout nuevo. Rechazaba el arranque ajeno mediante `ENOENT`, en lugar del error explícito esperado. Se compara ahora el padre real de los datos contra la ruta bajo la raíz real del proyecto, sin exigir que exista la carpeta esperada. Se añade la variante de checkout nuevo a la regresión: **28 pruebas correctas en 1,65 s**. No cambia el programa ni relaja el rechazo de datos ajenos.
