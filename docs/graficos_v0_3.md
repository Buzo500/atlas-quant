# ATLAS · Gráficos de v0.3

Entrega de desarrollo **0.3.0-dev.1**, iniciada por autorización expresa el 08/09/2026 sobre `v0.2.0-rc.2`. [Alcance y criterios](plan_v0_3.md). El ensayo de 48 horas y su seguimiento siguen aplazados; esta entrega no declara estable v0.2.

## Revisión actual · 09/09/2026

Corregida la ficha que desaparecía en la primera lectura de una curva estrecha al cambiar su altura. Pasan 244 pruebas frontend y los cinco recorridos E2E de gráficos; la suite general queda en **9/10** por una espera intermitente de `/api/state`, aún sin causa acreditada. TypeScript, lint y build correctos. [Revisión completa, incidencias y fuentes probadas](revision_graficos_20260909.md).

Mediciones nuevas con NAV variable y API real: precios de 100.000 observaciones en 1,66 s, curva en 1,98 s, inspección/zoom p95 ≤34,9 ms; hasta 1.000 velas y 20 ciclos de pantalla completa por escenario comprobados. Navegación, actualización de arrastre y rueda p95 inferior a 100 ms, sin aumento de nodos/listeners tras calentamiento. Fuentes locales sin commit ni subida; CI y repetición del escalado físico de los controles actuales pendientes. La evidencia siguiente del 08/09 es histórica.

## Ajuste anterior: navegación y pantalla completa · 08/09/2026

Los botones textuales de desplazamiento se sustituyen por una barra proporcional al tramo visible. Las lupas, restablecimiento y expansión se agrupan junto al gráfico. Precios y todas las curvas comparten navegación y gestos; en pantalla completa permiten arrastrar con el ratón y ampliar/reducir con la rueda. Las fichas junto al cursor continúan disponibles y se alojan dentro del elemento de pantalla completa. No se añaden dependencias ni se modifica el motor.

Validación final local: **241 pruebas frontend en 23 archivos** (19,26 s), TypeScript y lint correctos, build con manifiesto `f2bc34d1dac0512a40af3dda92e2bdb4a7d515d190b698006056bec9cb510815`; **9/9 E2E con API real en 27,1 s**, ejecución `e2e-94be132c780e4337a8e5e0ab818135cb`. Se comprueban pantalla completa nativa en Chromium a 3440×1440 y alternativa que ocupa la ventana a 390×844, barras, lupas, arrastre, rueda hasta una observación y vuelta, fichas, Escape, restauración de foco y rango, y ausencia de desbordamiento global. Ambos servidores cerraron con código 0, puertos libres, integridad `ok` y hashes de la base habitual conservados.

El primer E2E de navegación (`e2e-c6bd2e2d58e04731b57a7875a1c6fdbb`, 8/9) detectó que la lupa nueva ampliaba alrededor del centro y podía excluir el punto seleccionado. Ahora conserva su ancla, con regresiones de fecha y valor originales en precios y backtest. El siguiente pasó 9/9 (`e2e-5f3106ab274a4cb780c24e58b083b5b8`). La revisión adicional reprodujo un bloqueo de rueda por redondeo entre una y dos observaciones: cada paso progresa al menos una cuando los límites lo permiten; queda cubierto por pruebas unitarias y por el E2E final. Los registros intermedios se conservan.

Evidencia local: `output/validation/v03-navigation-frontend-complete.json` y los directorios E2E citados. Los scripts de benchmarks reconocen los iconos y la nueva barra, y pasan comprobación de sintaxis; no se repiten sus mediciones ni el escalado físico de Windows. La suite Python no se repite al no cambiar el motor. Estos ajustes y las fichas siguen locales, sin commit ni subida; CI de v0.3 pendiente y ensayo de 48 horas aplazado.

## Ajuste anterior: inspección junto al cursor · 08/09/2026

Cambio local posterior a `0a5b813`, todavía sin subir a la PR. Se retiran los deslizadores de inspección de todas las instancias de precios y curvas y se añade una ficha flotante compartida en marfil, con borde discreto. Ratón y teclado conservan valores de origen, sin modificar la API, contabilidad ni ejecución. No se añaden dependencias. Este bloque documenta su validación anterior a la barra de navegación del ajuste actual.

Validación del ajuste: **214 pruebas de frontend en 21 archivos** (18,25 s), TypeScript, lint y compilación con manifiesto correctos; **7/7 E2E** con API real (19,5 s), ejecución `e2e-d49a7fad535349bb8b56854448fc1611`. Se comprueban fechas y valores del tooltip, ausencia de sliders, teclado, salida/Escape y ajuste a los bordes en 3440×1440, 1920×1080, 1366×768 y 390×844. Ambos servidores terminaron con código 0, integridad `ok`, puertos libres y base habitual intacta. Fuentes del frontend: `f37b5110081c1a711618178758f54a063a45ccebd38b6e0f7af55de2ae11a7eb`. No se repite el escalado físico de Windows ni se atribuyen sus resultados anteriores al tooltip.

El primer E2E (`e2e-1349ea8e76f74ea9b8b9938ee2be167e`) detectó que `mousemove`, con coordenadas enteras, sobrescribía la selección fraccionaria de `pointermove` y podía mostrar el punto anterior. Se reprodujo con 1.100 observaciones y en Chromium; se eliminó el manejador redundante y se añadió una regresión que fallaba antes. La navegación mantiene un único recorrido de puntero. Un test del Laboratorio consultaba una opción antes de que apareciese: ahora espera su presencia, conservando las aserciones y sin añadir reintentos.

El segundo E2E (`e2e-8e765c743e6d4e3c92280d98429160fe`) pasó los gráficos y otros cinco recorridos, pero una lectura de `/api/state` agotó 10 s; la propia UI tuvo una lectura de 10,109 s. No hubo error Python ni HTTP 5xx. Los registros del proxy contienen un cierre de conexión sin marcas temporales suficientes para atribuirlo a esa espera. La ejecución final pasó sin cambiar límites ni activar reintentos; **la causa de esa espera puntual no está acreditada** y se conserva para la revisión operativa/CI. Los tres entornos verificaron conservación de la base e integridad al cerrar.

Evidencia local: `output/validation/v03-tooltip-frontend-verified.json`, informes anteriores conservados, y `var/validation/e2e-*/playwright.json` con capturas/trazas. Los benchmarks se adaptan al nuevo control y pasan comprobación de sintaxis; sus nuevas mediciones quedan pendientes. El ensayo de 48 horas sigue aplazado.

## Explorar precios en Datos

1. Seleccionar el conjunto y abrir **Datos → Precios del activo**. Elegir el activo del gráfico.
2. Elegir **Velas**, **Línea**, **Área** o **Barras OHLC**; activar o desactivar el volumen. Los precios conservan la moneda y la base recibidas.
3. Pasar el cursor por una vela o punto: una ficha junto al puntero muestra símbolo, moneda, fechas y OHLCV de esa observación. También se puede enfocar el gráfico con Tab y usar flechas e Inicio/Fin. La lectura de referencia conserva el cambio respecto al cierre anterior; si falta el predecesor no se presenta un cambio cero.
4. Elegir **Diario**, **Semanal** o **Mensual**. Las semanas son civiles, de lunes a domingo. La agregación toma primera apertura, máximo de máximos, mínimo de mínimos, último cierre y suma de volúmenes. Un volumen ausente no equivale a cero ni acredita una suma completa.
5. Aplicar fechas inclusivas y usar las lupas **+ / −** junto al gráfico para ampliar o reducir. La barra inferior desplaza el tramo visible, conservando su tamaño; Inicio/Fin llevan a los extremos del histórico y las flechas permiten ajustes por teclado. Las fechas se filtran antes de agregar: una semana o un mes recortado representa solo las sesiones seleccionadas. Se indican los límites y la cobertura no verificada.
6. Desplegar **Datos diarios originales** para revisar las observaciones del rango, en páginas de 50 filas. Cambiar zoom o representación no cambia esa tabla ni los datos almacenados.

La consulta identifica conjunto, versión, activo, procedencia y huella del manifiesto. La API solo lee la versión pedida: no descarga precios ni activa el motor. Al cambiar el contexto se descartan respuestas obsoletas. **Fechas de consulta al motor** permite reducir la lectura si una serie supera las 100.000 observaciones permitidas por respuesta.

Se muestran inicialmente las últimas 120 barras. Cada ventana dibuja como máximo 1.000; la barra de navegación permite recorrer la serie completa. El icono **Restablecer vista** recupera el rango de la consulta y la ventana inicial. El límite se anuncia; no se eliminan barras de origen ni se presentan velas diezmadas como si fueran completas.

## Explorar cartera y backtests

La curva de **Cartera** y los resultados de **Laboratorio** permiten línea o área, fechas inclusivas, zoom, desplazamiento y restablecimiento. La ficha junto al puntero utiliza las observaciones originales, incluso cuando el dibujo reduce puntos para conservar rendimiento. Estrategia y benchmark se leen en la misma fecha. Las curvas de resultados en Agente IA reutilizan esta presentación.

Se retiran los deslizadores de inspección de precios y curvas. Las fichas cambian de lado cerca de los bordes y se ocultan al salir del gráfico, perder foco, desplazar la página, cambiar contexto o pulsar Escape. El teclado puede consultar la misma información junto al punto seleccionado, y se conservan las lecturas de referencia y tablas originales.

Flechas e Inicio/Fin cambian la observación; `+`/`−` amplían o reducen la vista y Escape quita la selección. La tabla conserva sus valores y paginación. Los controles mantienen foco visible y el redimensionado no cambia la fecha inspeccionada.

Si la lectura de una curva pasa a ocupar otra línea y reduce internamente la altura del gráfico, la ficha del ratón se conserva y la de teclado se recoloca junto al punto. Un cambio real de ancho o un redimensionado de ventana oculta la ficha, sin borrar la fecha seleccionada.

En Cartera, **TWR desde el origen** representa `(twr_index − 1) × 100`. Un rango visible distinto no cambia ese origen ni recalcula las métricas globales. NAV y patrimonio de backtest no disponen de OHLC intradía y no se convierten en velas.

## Barra de navegación y pantalla completa

Precios, cartera y resultados comparten herramientas de lupa para ampliar/reducir, restablecimiento y pantalla completa. La barra inferior representa el tamaño del tramo visible sobre las observaciones disponibles; desplazarla cambia su posición, no su cantidad ni los datos almacenados. Cuando ya se ve todo el histórico, primero hay que ampliar para poder desplazarse.

El icono de expansión solicita pantalla completa del navegador. Si no está disponible o se rechaza, el gráfico ocupa la ventana de la aplicación. En ambos casos se mantienen el gráfico, la selección y el rango; **Escape** o el icono de salida devuelven el foco al control de expansión.

En pantalla completa, arrastrar con el botón izquierdo mueve horizontalmente el gráfico. La rueda amplía o reduce alrededor de la posición del puntero. Fuera de esa vista, la rueda conserva el desplazamiento normal de la página; Ctrl y otros modificadores no se capturan para zoom del gráfico. Los gestos respetan los límites del histórico y, en precios, las 1.000 barras visibles. La ficha del cursor se oculta mientras se arrastra y vuelve al inspeccionar una observación.

## Límites de interpretación

- El eje horizontal distribuye observaciones equidistantes; los huecos de calendario no se rellenan ni se dibujan como nuevas sesiones.
- El eje vertical se ajusta al intervalo visible. El área parte del mínimo visible, no necesariamente de cero.
- Los metadatos describen lo recibido. Un precio del proveedor sin ajuste automático no certifica un precio bruto de bolsa. Splits y dividendos siguen como información de procedencia; no hay marcadores ni listado de eventos en el gráfico, no se aplican ajustes ni se interpreta un salto como rentabilidad total.
- No se modifica la contabilidad, el cálculo de backtests, los precios de ejecución ni los controles por explorar un gráfico. No hay nuevos indicadores, datos intradía, órdenes reales ni llamadas pagadas.
- No se requiere GPU ni una biblioteca nueva. Se amplía el SVG existente, con funciones puras de selección y agregación, consultas tipadas y componentes separados por funcionalidad.

## Validación inicial de v0.3, anterior a los ajustes de interacción

Para la medición inicial del sobremesa se fija un presupuesto de primera representación de 5 s con 100.000 observaciones, p95 de inspección/zoom inferior a 100 ms y heap JavaScript tras recogida inferior a 180 MiB. Se separa la importación inicial del coste de abrir una serie ya guardada. Los cambios repetidos de pestaña deben conservar el número de nodos/listeners después del calentamiento; son un diagnóstico corto, no una prueba de memoria sostenida.

Validación local del 08/09/2026 en Windows nativo, Python 3.14.4 y Node 24.15.0:

| Comprobación | Resultado |
|---|---|
| Motor completo | 477 pruebas y 91 subtests; 40,57 s, dos avisos previos de TestClient |
| Frontend completo final | 201 pruebas en 20 archivos; 20,58 s |
| Navegador con API real | 7/7 recorridos; 18,0 s; Chromium, sin respuestas simuladas |
| Contratos, TypeScript, lint, dependencias | Correctos; ninguna dependencia nueva |
| Compilación para uso diario | Manifiesto generado y comprobado por `tools/build_frontend.py` |
| Viewports CSS | 3440×1440, 1920×1080, 1366×768 y 390×844 en curvas/precios, sin desbordamiento global |
| Windows físico | Monitor 2, 3440×1440, 125 % y 150 %, Chrome visible con zoom 100 %; 100 % inicial restaurado |

E2E final: `e2e-ff1a7f3c5a944c77af2ce68098d5d12b`; anterior al ajuste de decimales: `e2e-4c2f22ca18a2420e868f5eff15aa682f`, también 7/7. En ambos, cierres de servidores con código 0, integridad `ok`, puertos libres y hashes de la base habitual conservados. El ensayo manual de rendimiento/escalado `e2e-f121fd8c8efe477dafa95ce29d57aaa6` también terminó con resultado 0 y las mismas garantías. No se ejecuta el ensayo de 48 horas.

El primer intento de Vitest falló por un mock del módulo API que no conservaba el nuevo constructor de rutas y por consultar una opción antes de abrirse su desplegable. Se preserva `output/validation/v03-frontend-tests-first-failure.json`. Se corrigieron las pruebas: API parcialmente simulada, lecturas de precios aisladas en los tests del ledger y espera de aparición de la opción, manteniendo las aserciones y sin reintentos. El recorrido real comprueba juntos precios e importaciones. La revisión física detectó decimales residuales en el cambio calculado: se limita su presentación a seis decimales o notación científica, conservando valores originales; después pasan de nuevo Vitest y E2E completos. La geometría comprobada físicamente no cambia.

### Rendimiento medido antes de las fichas flotantes

Chromium 153.0.8010.12, viewport 1440×1000, fixtures sintéticos y API real. Carga incluye navegación, HTTP local, hidratación y dos fotogramas; interacción incluye dos fotogramas tras el evento DOM. No mide hardware del ratón ni una conexión externa.

Las cifras siguientes corresponden a la implementación inicial con deslizadores. La [revisión del 09/09](revision_graficos_20260909.md) contiene las mediciones actuales con puntero y NAV variable (`report_format: 3`, `interaction_method: svg-pointer-tooltip-v3-variable-nav`) y el benchmark de navegación (`report_format: 2`). Los informes de los distintos métodos deben identificarse por separado.

| Observaciones | Primer gráfico de precios | Primera curva | p95 inspección/zoom |
|---|---:|---:|---:|
| 1.000 | 0,60 s | 0,17 s | ≤34,1 ms |
| 10.000 | 0,54 s | 0,32 s | ≤34,1 ms |
| 100.000 | 2,10 s | 2,44 s | ≤34,1 ms |

La prueba adicional amplía hasta **1.000 velas visibles** sobre 100.000 sesiones originales: 20 posiciones del puntero contrastadas con fecha/OHLCV/cierre previo de la API, p95 **33,8 ms**; 20 alternancias de zoom 1.000↔500, p95 **50,7 ms**. Dibuja 4.025 nodos SVG, con heap tras GC de 25,2 MiB. El escenario de precios y curva usa 31,4 MiB; ocho ciclos entre pestañas mantienen nodos y listeners, con incremento de heap de unos 0,39 MiB entre los ciclos 1 y 8. Estos resultados cumplen el presupuesto inicial y solo describen esa carga técnica corta; no acreditan estabilidad sostenida, memoria total del proceso ni calendario bursátil.

Las mediciones de proyección Python son independientes de HTTP/navegador: 100.000 barras, mediana de proyección 77,29 ms y validación DTO 183,43 ms. Informes locales ignorados por Git: `output/validation/v03-*.json`, pruebas `v03-backend.xml`, capturas y metadatos en `output/validation/v03-windows-scale/`. El escalado físico de rc.2 permanece como evidencia histórica separada.

### Reproducir las medidas

Con ATLAS detenido y la interfaz compilada, iniciar `tools/run_e2e.py --manual --timeout 1200` mediante la `.venv`. En otra consola, pasar el identificador `e2e-…` que imprime a los scripts, secuencialmente para evitar interferir con las medidas:

```powershell
node tools/benchmarks/v03-browser-benchmark.cjs e2e-IDENTIFICADOR
node tools/benchmarks/v03-max-window-benchmark.cjs e2e-IDENTIFICADOR
node tools/benchmarks/v03-navigation-benchmark.cjs e2e-IDENTIFICADOR
.\.venv\Scripts\python.exe tools/run_e2e.py --stop-run e2e-IDENTIFICADOR
```

El primer script importa datos sintéticos, un depósito y una compra en cada conjunto de la **base aislada**, para contrastar una curva que varía con el precio; los otros dos solo consultan el conjunto de 100.000 observaciones de su informe correcto. Verifican identidad, rutas y procesos antes de actuar, bloquean salidas de red ajenas y conservan informes anteriores. El benchmark Python en memoria se ejecuta con `.\.venv\Scripts\python.exe tools/benchmarks/benchmark_v03_prices.py`. No cargar estos fixtures en la cartera habitual.

**Fuentes: `abf908577c901372e0274aeb34ce95fe4bf1d68a`, [PR #3 en borrador](https://github.com/Buzo500/atlas-quant/pull/3). CI de esta entrega pendiente.** Se conserva el workflow gratuito existente para validar la rama después de comprobar cuota; sus resultados de rc.2 no se atribuyen a v0.3. No se crea una etiqueta estable.
