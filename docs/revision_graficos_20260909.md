# ATLAS · Revisión de gráficos del 09/09/2026

## Actualización posterior: publicación y CI

Las fuentes revisadas se han subido en `c8f4eb615ca40993c7ad021fa195e60c62b61ed7`, [PR #3 en borrador](https://github.com/Buzo500/atlas-quant/pull/3). La [CI 34340199451](https://github.com/Buzo500/atlas-quant/actions/runs/34340199451) pasa en su primer intento: job Windows de 6 min 16 s, **477 pruebas Python y 91 subtests** (24,57 s, dos avisos previos), **244 frontend/23 archivos** (65,68 s), **10/10 E2E** (56,3 s), instalación limpia, build, tipos, contratos, lint, dependencias, arranque, smoke y parada correctos. E2E remoto `e2e-5e7d502b8c0f4b24b06aa35c446551ef`: resultado 0, conservación de la base de control del runner, integridad `ok` y puertos libres.

Cuota comprobada antes de lanzar: 50/2.000 minutos, 0/0,5 GB de almacenamiento y 0 USD facturables; un job estándar con límite de 20 minutos, sin artefactos remotos ni cambios de facturación. Informes locales `output/validation/v03-ci-quota-before-20260909.json`, `v03-ci-34340199451.json` y `v03-ci-34340199451-job.log`. No se ha fusionado ni etiquetado. Este cierre solo cambia documentación respecto a las fuentes verificadas.

El intento local anterior sigue siendo 9/10: que la CI pase no demuestra resuelta la causa de la espera intermitente de `/api/state`. Tampoco sustituye el escalado físico pendiente ni el ensayo de 48 horas aplazado. Los apartados siguientes conservan la revisión local anterior a esta publicación.

## Revisión local anterior a la CI

Revisión local de las fichas, barra de navegación, lupas y pantalla completa de **0.3.0-dev.1**, en `codex/v0.3-graficos`. Se corrige un defecto de la primera ficha en curvas estrechas y se verifican valores, teclado, gestos, rendimiento y restauración de la vista. Los gráficos pasan sus cinco recorridos E2E; la suite general queda en **9/10** por una espera intermitente de `/api/state` que sigue pendiente. Esta revisión no acredita el cierre de G6 ni una versión estable.

Fuentes locales sobre `0a5b8136f7ea5c946f43cf089151e9990c5daec9`, todavía sin commit ni subida. Huella del frontend realmente probado y compilado: `03d013e3a2e4ed500adc2f18e1a081e10e84658cab920e5c38a0256d999547ed`. No se modifican motor, contratos ni dependencias. No se ejecuta CI ni el ensayo de 48 horas.

## Corrección y regresiones

En una curva ampliada a 390×844, la primera lectura podía ocupar otra línea, restar altura al SVG y provocar que `ResizeObserver` borrase la ficha recién mostrada. Se reprodujo en navegador y con pruebas de componente que fallaban antes de corregirlo.

Ahora un ajuste interno de altura conserva el ancla del ratón; la ficha de teclado se recoloca utilizando la geometría SVG ya actualizada. Cambiar el ancho o redimensionar/desplazar la ventana sigue ocultando la ficha, conservando la fecha seleccionada. No se recalculan valores financieros ni se recorren de nuevo las 100.000 observaciones para recolocarla.

- Regresión aislada: 39/41 antes; **41/41** después, en 6,90 s. Informes `v03-curve-resize-regression-before.json` y `v03-curve-resize-regression-final.json` en `output/validation/`.
- Suite frontend: **244/244**, 23 archivos, 21,32 s; TypeScript y lint correctos. Informe `output/validation/v03-review-frontend-final-20260909.json`.
- E2E con API real: **9/10**, 43,3 s, ejecución `e2e-08bd90a1b5ac4b31b17bcdf153f93389`. Pasan los cinco recorridos de gráficos, incluida la primera ficha por ratón y teclado, precios, curvas y pantalla completa nativa/alternativa. Se mantienen los límites originales y no se añaden reintentos.
- Compilación generada y comprobada mediante `tools/build_frontend.py`. La suite Python no se repite: sus 477 pruebas y 91 subtests corresponden a la entrega inicial del motor sin cambios.

## Rendimiento de las fuentes finales

Chromium 153.0.8010.12, Windows nativo, interfaz compilada y API real en base aislada. Las fechas civiles sintéticas parten de 1750: son carga técnica, no historia bursátil acreditada. El fixture incorpora depósito de 10.000 EUR y compra de 50 unidades a 100 EUR; cada NAV se contrasta independientemente con `5000 + 50 × cierre`. Se evitan las comprobaciones triviales de una cartera solo en efectivo.

| Observaciones originales | Primera representación de precios | Primera curva | p95 de lectura/zoom |
|---|---:|---:|---:|
| 1.000 | 560,7 ms | 225,3 ms | ≤34,7 ms |
| 10.000 | 520,3 ms | 355,2 ms | ≤34,4 ms |
| 100.000 | 1.656,4 ms | 1.978,9 ms | ≤34,9 ms |

La primera representación incluye navegación, HTTP local, hidratación y dos fotogramas, excluyendo la importación. Heap JavaScript tras GC: 23,85 MiB en precios y 34,92 MiB al abrir la curva de 100.000 puntos. Ocho cambios de pestaña tras calentamiento: incremento de 467.620 bytes, cero nodos y cero listeners.

Prueba adicional con **1.000 velas visibles**: lectura p95 34,0 ms, zoom 48,9 ms, 4.025 nodos SVG y heap 25,14 MiB. Las fichas se contrastan con las observaciones originales, incluidas fechas y OHLCV.

El nuevo benchmark de navegación realiza 20 muestras por control y 20 ciclos de entrada/salida de pantalla completa por escenario, después de dos ciclos de calentamiento. Precios muestra 1.000 barras; la curva muestra 50.000 puntos sobre 100.000 para permitir desplazarse.

| Escenario ampliado | Barra p95 | Ficha p95 | Actualización de arrastre p95 | Rueda p95 | Entrada en pantalla completa p95 |
|---|---:|---:|---:|---:|---:|
| Precios, nativa 3440×1440 | 57,1 ms | 31,9 ms | 39,5 ms | 67,0 ms | 167,2 ms |
| Curva, nativa 3440×1440 | 34,4 ms | 32,7 ms | 34,2 ms | 50,2 ms | 97,9 ms |
| Precios, alternativa 390×844 | 61,0 ms | 31,8 ms | 39,7 ms | 67,3 ms | 131,1 ms |
| Curva, alternativa 390×844 | 34,1 ms | 32,7 ms | 34,6 ms | 66,7 ms | 79,9 ms |

Las actualizaciones habituales cumplen el objetivo p95 inferior a 100 ms. La entrada/salida de pantalla completa se mide aparte e incluye automatización y cambio de modo del navegador. El gesto completo de arrastre dura entre 83,5 y 185,2 ms p95 e incluye pulsar, tres movimientos, soltar, protocolo y dos fotogramas: no equivale a la latencia de una actualización. Esta última se mide durante un arrastre real con su identificador de puntero y un evento DOM por muestra.

Los cuatro escenarios conservan rango, datos originales, foco, estado previo de `inert` y desplazamiento de página al salir; sin desbordamiento global. Tras 20 ciclos, cero nodos/listeners adicionales y entre 185.756 y 376.200 bytes de incremento de heap. Sin errores JavaScript, HTTP ni peticiones fallidas en este benchmark. Son diagnósticos cortos, no una demostración de ausencia de fugas ni el ensayo sostenido.

Se inspeccionaron capturas de los escenarios ancho/estrecho y de la primera ficha por ratón/teclado. Los **viewports CSS no son escalado físico**: no se repitió Windows 125 %/150 %, pues el control nativo no está disponible en esta sesión. La evidencia física del 08/09 corresponde a los gráficos anteriores a estas fichas y controles.

## Incidencia pendiente de API e intentos conservados

El primer recorrido E2E general agotó 10.013,609 ms al leer `/api/state` después de importar la demo. Una lectura simultánea del navegador respondió 200 después de 10.094,533 ms. El proxy registró `UND_ERR_SOCKET`; el backend no mostró traceback. Faltan timestamps e identificadores que permitan vincular ese cierre al GET o atribuir la demora a un componente. No se amplían tiempos ni se repite la suite para ocultar el fallo. Diagnóstico: `output/validation/v03-review-state-timeout-20260909.json`; trazas y logs en el directorio de aquella ejecución.

Se conservan también dos intentos anteriores del benchmark de navegación:

- `e2e-0926f9f4318e46bb89e6c6ddc4615a46`: falló una aserción del script que esperaba cero nodos `inert`, ignorando las cuatro pestañas inicialmente inactivas. Se corrige para comprobar la restauración exacta de los nodos y atributos previos.
- `e2e-ea4eed36240249f6a66a807402b9b741`: faltó una ficha después de los gestos en la curva estrecha. La investigación reprodujo el defecto mínimo de primera lectura descrito arriba; no se demuestra que explique por sí solo aquella secuencia posterior a los gestos. El intento final pasa con diagnóstico ampliado y sin reintentos.

Los resultados fallidos se conservan y no se convierten en validaciones correctas por haber cerrado bien sus servidores.

## Evidencia y operación

Benchmark final: `e2e-63895c0dbb8f4fd88f92b0cce5e445d1`. Informes en `output/validation/`:

- `v03-browser-benchmark-e2e-63895c0dbb8f4fd88f92b0cce5e445d1.json`, formato 3, método `svg-pointer-tooltip-v3-variable-nav`.
- `v03-max-window-benchmark-e2e-63895c0dbb8f4fd88f92b0cce5e445d1-2026-09-09T10-10-15-569Z.json`.
- `v03-navigation-benchmark-e2e-63895c0dbb8f4fd88f92b0cce5e445d1-2026-09-09T10-10-35-086Z.json`, formato 2. Cada informe registra la huella de su script y del frontend; no se comparan silenciosamente métodos distintos.

Capturas en `var/validation/e2e-63895c0dbb8f4fd88f92b0cce5e445d1/navigation-benchmark-2026-09-09T10-10-35-086Z/`. [Comandos para reproducir](graficos_v0_3.md#reproducir-las-medidas).

ATLAS se detuvo antes de editar y se guardó `backups/atlas-20260909T094122813887Z-4d19d0c4`. Los cuatro entornos aislados cerraron ambos servidores con código 0, liberaron puertos y conservaron hashes de la base habitual con integridad `ok`; el resultado de la suite general sigue siendo 1 por su test fallido.

**Arranque normal restaurado:** `789e5676dfaf4d3aa8e721c21b0db8b0`, modo compilado, salud `ok`, manifiesto verificado. Conjunto habitual v1, tres posiciones, NAV 25.118,66876 EUR, experimento completado y controles conservados. Parada global activada, sin proveedores configurados, presupuesto/gasto/reserva cero. La lectura de estado de este arranque tardó 33,6 ms; no resuelve la intermitencia anterior. Evidencia: `output/validation/v03-review-normal-runtime-20260909.json`, comparada con `v03-review-before-20260909.json`.

Disponible en http://127.0.0.1:3000/; Ctrl+F5 actualiza la interfaz abierta. El usuario decidirá los siguientes pasos. Permanecen pendientes la incidencia de API, la CI y la revisión física de estos controles; el ensayo de 48 horas sigue aplazado.
