# v0.3 · Revisión final y aceptación de desarrollo

**Cierre vigente · 09/09/2026: G1–G6 aceptadas para `0.3.0-dev.1`.** El usuario confirma la pantalla completa en precios y cartera y acepta expresamente el timeout como incidencia conocida. Autoriza actualizar y fusionar la PR #3 y publicar la etiqueta `v0.3.0-dev.1`. La incidencia de API permanece abierta, sin causa ni corrección acreditadas. La CI `34346311068` valida el código y las pruebas de `d5c3b09`; los commits posteriores solo actualizan documentación e instrucciones del proyecto. No se declara una versión estable ni se reactiva el ensayo de 48 horas. Los apartados siguientes conservan la evidencia y decisiones previas a esta aceptación.

9 de septiembre de 2026. **0.3.0-dev.1**, rama `codex/v0.3-graficos`. Este documento reúne la evidencia vigente y las decisiones pendientes; no declara la versión estable ni autoriza una publicación.

## Cambios preparados

Los gráficos ya incluyen fichas junto al cursor, lectura por teclado, barras de navegación, lupas, restablecimiento y vista ampliada con arrastre y rueda. Conservan observaciones originales, tablas, identidad de datos y límites de representación. [Uso](graficos_v0_3.md) y [revisión del código](revision_graficos_20260909.md).

La preparación final añade diagnóstico optativo de API, sus protecciones y pruebas, y documentación consolidada. El arranque habitual, motor, frontend, contratos y dependencias no cambian. La instrumentación se carga únicamente mediante `tools/diagnostics/run_api_diagnostic.py` sobre un entorno E2E nuevo.

## Evidencia aplicable

| Área | Resultado y alcance |
|---|---|
| CI de los gráficos | [34340199451](https://github.com/Buzo500/atlas-quant/actions/runs/34340199451), fuentes `c8f4eb615ca40993c7ad021fa195e60c62b61ed7`: 477 Python + 91 subtests, 244 frontend y 10/10 E2E. No atribuir esta CI a las herramientas añadidas posteriormente. |
| Rendimiento | 100.000 observaciones; precios 1,66 s y curva 1,98 s. Interacciones habituales p95 inferior a 100 ms en los escenarios registrados. [Métodos y límites](revision_graficos_20260909.md). |
| Escalado físico | Seis recorridos correctos a Windows 125 % y 150 % en 3440×1440. Fichas, lupas, barra por teclado, arrastre, rueda y Escape; 100 % inicial restaurado. [Evidencia](escalado_controles_20260909.md). |
| Diagnóstico consolidado | 27 pruebas Python de diagnóstico/aislamiento correctas en 1,55 s; incluyen tres pruebas Node de los clientes. Prueba real: 100 ciclos, 300 lecturas concurrentes más una comprobación previa, todas correctas; máximo observado 112,42 ms. Sintaxis Node y manifiesto del frontend verificados. |
| Conservación de datos | Entorno `e2e-a9f9e2f0e3704ea09a0067c2246a4a66` cerrado con resultado 0 y salidas 0/0, integridad `ok`, hashes habituales intactos y puertos libres. ATLAS normal detenido. |

## Incidencias y decisiones pendientes

**Actualización manual del usuario · 09/09/2026:** confirma que el procedimiento de pantalla completa funciona correctamente tanto en Datos/precios como en Cartera, incluida la ocultación del marco de Chrome y la restauración con Escape. El pendiente 2 queda cerrado por esa comprobación comunicada por el usuario; los intentos automatizados inferiores se conservan como historia y no se convierten en pruebas correctas. No se ha vuelto a ejecutar el programa ni capturado la pantalla para este registro.

La revisión de criterios y la decisión actual de seguimiento constan en el apartado final «Revisión de los tres puntos solicitados». Los intentos previos se conservan como evidencia histórica.

1. **API: causa sin determinar.** La espera histórica de 10 s en `/api/state` no se reprodujo. La instrumentación y las ejecuciones correctas no son una corrección del fallo. Si reaparece en un entorno instrumentado, guardar logs y correlación antes de atribuirlo a cliente, proxy o motor. Las herramientas actuales son para bases E2E: no capturan automáticamente el uso habitual. [Diagnóstico](diagnostico_api_20260909.md).
2. **Pantalla completa: ocultación del marco de Chrome sin certificar.** Se comprobaron la vista ampliada y sus controles. El intento posterior en Chrome normal fue detenido por Computer Use al no poder determinar la URL con suficiente certeza; no es evidencia de un fallo del gráfico. Entorno `e2e-24c46f40c2584852ae85e7ff268d8aa3` cerrado con resultado 0, integridad `ok`, hashes habituales intactos y puertos libres. Queda una comprobación manual: abrir un gráfico con su botón de pantalla completa, observar si desaparecen pestañas/barra de direcciones y pulsar Escape para comprobar la restauración. F11 no sustituye la prueba del botón.
3. **Integración y publicación.** Fuentes subidas y CI completa correcta sobre `d5c3b09`, según el cierre siguiente. La PR #3 sigue en borrador; quedan la decisión de fusión y su etiqueta de desarrollo. No se ha fusionado ni etiquetado.

G6 permanece abierto. El ensayo de **48 horas sigue aplazado**, así como su seguimiento, y continúa siendo requisito antes de declarar v0.2 estable. La aceptación de esta revisión no inicia v0.4, nuevos indicadores, aprendizaje, móvil, remoto, LaTeX ni operativa real.

## Reproducción del diagnóstico

Desde la raíz, con ATLAS detenido:

```powershell
node --test tools/diagnostics/checks.test.cjs
.\.venv\Scripts\python.exe -m pytest backend/tests/test_api_diagnostics.py backend/tests/test_e2e_isolation.py -q
.\.venv\Scripts\python.exe tools/build_frontend.py --check
.\.venv\Scripts\python.exe tools/diagnostics/run_api_diagnostic.py --manual --timeout 600
```

En otra consola, usar el identificador exacto impreso por el lanzador:

```powershell
node tools/diagnostics/api_clients.cjs e2e-IDENTIFICADOR
.\.venv\Scripts\python.exe tools/run_e2e.py --stop-run e2e-IDENTIFICADOR
```

El cliente rechaza estados HTTP distintos de 200, proveedores configurados, experimentos existentes, datos no sintéticos y descriptores incompletos/inactivos o de otra ejecución. Los wrappers rechazan una base ajena o una parada de otra carpeta antes de cargar la aplicación o instalar hooks; la protección Python sigue activa con `-O`. Estos controles complementan al lanzador, que comprueba la propiedad real de los puertos y conserva el bloqueo de mantenimiento. No son autenticación frente a un proceso local que pueda alterar los archivos de ejecución.

Informes y logs completos permanecen excluidos de Git en `var/validation/` y `output/validation/`. El informe del cliente se crea sin sobrescribir uno previo. Los comandos no cargan claves ni hacen llamadas pagadas.

## Intento de CI conservado y preparación de la corrección

La CI [34345374202](https://github.com/Buzo500/atlas-quant/actions/runs/34345374202), sobre `46df937`, terminó con **243/244 pruebas frontend correctas en 69,05 s**; no llegó a Python ni E2E. Falló la búsqueda inmediata de «Movimientos de cartera» tras abrir el selector en la prueba de lectura CSV pendiente. El DOM registraba el selector cerrado. No se ha demostrado la secuencia exacta que lo cerró; no se atribuye a la API real, que ese test no utiliza.

El test usa ahora la apertura por teclado del selector, espera la opción con el límite existente y comprueba expresamente el cambio de tipo antes de resolver la lectura antigua. Mantiene la aserción de descarte del archivo, sin reintentos ni ampliación de tiempos. Validación local posterior: **244/244 frontend, 23 archivos, 20,45 s**, TypeScript, lint desde la carpeta frontend y build con manifiesto correctos. El build se regenera porque su huella incluye los tests; no se cambió lógica de la aplicación. Se conserva también la corrección del diagnóstico para checkouts nuevos y sus 28 pruebas, descrita en el [diagnóstico](diagnostico_api_20260909.md).

La cancelación que se intentó durante esa CI fue rechazada por la revisión automática al considerar que la autorización para ejecutarla no incluía detenerla. Se dejó terminar; no se sorteó el rechazo. El fallo remoto y su log se conservan en `output/validation/v03-ci-34345374202-job.log`.

## CI final de las fuentes consolidadas

La [CI 34346311068](https://github.com/Buzo500/atlas-quant/actions/runs/34346311068), sobre **`d5c3b0909be477a93f274d2c03f174abd232baf0`**, terminó correctamente: duración total 5 min 12 s, job Windows 5 min 8 s. **244 pruebas frontend en 23 archivos (50,99 s), 482 Python y 91 subtests (19,70 s), 10/10 E2E (45,0 s)**. Se conservan dos avisos de obsolescencia de Starlette/TestClient sobre httpx y BlockingPortal. Instalación limpia, build con manifiesto, TypeScript, contratos, lint, comprobación de dependencias, arranque, recorrido sintético mediante proxy y parada correctos.

El entorno remoto `e2e-7d55d6443ed74f0894273c96c3e98345` terminó con resultado 0, sin errores de limpieza, integridad `ok`, base de control conservada y puertos libres. Son comprobaciones del runner de GitHub, no un ensayo sostenido en el sobremesa. La CI correcta no demuestra resuelta la causa de la espera histórica de API ni certifica la ocultación del marco de Chrome.

Cuota autenticada de Actions: antes de esta ejecución **68,3/2.000 minutos**, después **78,3/2.000**; almacenamiento 0/0,5 GB y **0 USD facturables** en ambas consultas. Un job estándar limitado a 20 minutos, sin artefactos remotos. Log y resumen local: `output/validation/v03-ci-34346311068-job.log` y `v03-ci-34346311068-summary.json`.

ATLAS local permanece detenido, con build verificado y huella de fuentes `3e26de5d896d7ff6a9ae917bf709d47d9ba4b86818f869c5c1ab4e00e2494c5b`. El cierre posterior a `d5c3b09` solo actualiza documentación y la descripción de la PR; no cambia código, pruebas ni workflow. PR en borrador, sin fusión ni etiqueta; G6 y los pendientes anteriores continúan abiertos.

## Revisión de los tres puntos solicitados · 09/09/2026

**1. Pantalla completa en Chrome normal: comprobación bloqueada.** Se abrió el entorno aislado `e2e-1039ec2490db4b3497f7117acf70a17b`, con build verificado. Computer Use localizó una ventana de Chrome, pero detuvo la captura por no poder determinar su URL con suficiente confianza para aplicar su política. No se envió ninguna entrada a Chrome ni se pulsó el botón del gráfico; no hay nueva evidencia visual ni se acredita un fallo de ATLAS. No se intentó sortear esa restricción mediante otro mecanismo de control de Windows.

Se solicitó la parada del entorno propio: resultado 0, servidores 0/0, sin parada forzada, integridad `ok`, hashes habituales conservados y puertos libres. ATLAS habitual queda detenido. La comprobación requiere intervención manual del usuario: abrir ATLAS, entrar en una gráfica con datos, pulsar su botón de pantalla completa y confirmar que desaparecen pestañas/barra de direcciones; pulsar Escape y comprobar restauración del gráfico y foco. Hacerlo en precios y en una curva cubre las dos representaciones compartidas; F11 no sustituye el botón de la aplicación. No marcarlo correcto hasta recibir esa observación.

**2. Timeout: decisión documentada.** Mantenerlo como incidencia conocida abierta, sin repetir ahora los mismos ensayos ni aplicar cambios especulativos. No hay una hipótesis nueva respaldada por evidencia. Si reaparece, conservar la petición lenta y correlacionar cliente/proxy/ASGI en un entorno aislado. [Impacto, criterios de reapertura y límites](diagnostico_api_20260909.md#decisión-de-seguimiento-tras-revisar-la-ci-final). Su aceptación como limitación de una entrega de desarrollo sigue siendo decisión del usuario.

**3. Criterios de v0.3 revisados.** Esta matriz contrasta el plan, las pruebas existentes y los informes; no afirma una nueva ejecución de esas suites. La CI aplicable es `d5c3b09`; desde las fuentes gráficas `c8f4eb6` no cambió la lógica de gráficos, motor ni contratos: se añadieron diagnóstico, pruebas y documentación. Las medidas anteriores conservan sus fechas, métodos y límites.

| Criterio | Valoración y evidencia |
|---|---|
| G1: series inmutables | Cubierto por contratos y pruebas de precios: versión/activo/rango, lectura sin mutación, límites y ampliación concurrente sin mezcla. `backend/tests/test_prices_api.py`, CI final correcta. |
| G2: curvas y observaciones originales | Cubierto por pruebas de curvas, selección, teclado y E2E de NAV/TWR/benchmark; se conserva la corrección de primera lectura en curva estrecha. |
| G3: precios OHLCV | Cubierto por pruebas de consulta/panel/formato y E2E de estilos, valores originales y volumen. Límite visible de 1.000 barras; no se presenta una reducción visual como historial completo. |
| G4: navegación temporal | Cubierto por rangos inclusivos, barra, lupas, gestos y restauración de rango/foco. La vista ampliada y la API de fullscreen están probadas; el usuario confirmó además la ocultación del marco de Chrome y restauración con Escape en precios y cartera el 09/09/2026. |
| G5: semana y mes | Cubierto por fixtures de cambio de año, febrero bisiesto, huecos, rango parcial, ausencia frente a cero y cierre previo; E2E verifica agregación del rango y originales diarios. |
| G6: integración y operación | CI final: 244 frontend, 482 Python + 91 subtests, 10 E2E; instalación/build, tipos, contratos, lint, dependencias, arranque/proxy/parada y conservación de datos correctos. |
| G6: rendimiento | Presupuesto previamente fijado en la guía: primera representación ≤5 s con 100.000 observaciones, heap JS tras GC <180 MiB, interacción habitual p95 <100 ms. Medidas actuales registradas: precios 1,66 s, curva 1,98 s, heap máximo de esos escenarios 34,92 MiB e interacciones habituales dentro del objetivo; nodos/listeners sin incremento tras calentamiento. La entrada a fullscreen se mide aparte, no como interacción habitual. No acredita memoria total ni estabilidad sostenida. |
| G6: adaptación física | Seis recorridos a Windows 125 %/150 % en 3440×1440 correctos; 100 % restaurado. Se conservan además los recorridos de viewport ancho/estrecho. No equivalen a certificar el marco nativo de Chrome. |
| G6: cierre | **Cerrado para la entrega de desarrollo por aceptación expresa del usuario el 09/09/2026**: pantalla completa confirmada manualmente y timeout aceptado como incidencia conocida abierta. No acredita estabilidad sostenida ni resuelve la causa de API. |

Decisión final del usuario: aceptar la incidencia conocida, cerrar G6 y autorizar la actualización documental, fusión de la PR #3 y etiqueta de desarrollo. No hace falta otra CI para cambios exclusivamente documentales sobre las fuentes verificadas. El ensayo sostenido sigue aplazado y v0.2 no se declara estable.
