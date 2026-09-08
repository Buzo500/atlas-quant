# ATLAS · Gráficos de v0.3

Entrega de desarrollo **0.3.0-dev.1**, iniciada por autorización expresa el 08/09/2026 sobre `v0.2.0-rc.2`. [Alcance y criterios](plan_v0_3.md). El ensayo de 48 horas y su seguimiento siguen aplazados; esta entrega no declara estable v0.2.

## Explorar precios en Datos

1. Seleccionar el conjunto y abrir **Datos → Precios del activo**. Elegir el activo del gráfico.
2. Elegir **Velas**, **Línea**, **Área** o **Barras OHLC**; activar o desactivar el volumen. Los precios conservan la moneda y la base recibidas.
3. Mover el cursor o usar el deslizador **Inspeccionar barra**, flechas e Inicio/Fin. La lectura muestra fechas, OHLCV y cambio respecto al cierre anterior; si falta el predecesor no se presenta un cambio cero.
4. Elegir **Diario**, **Semanal** o **Mensual**. Las semanas son civiles, de lunes a domingo. La agregación toma primera apertura, máximo de máximos, mínimo de mínimos, último cierre y suma de volúmenes. Un volumen ausente no equivale a cero ni acredita una suma completa.
5. Aplicar fechas inclusivas, acercar, alejar o desplazar la ventana. Las fechas se filtran antes de agregar: una semana o un mes recortado representa solo las sesiones seleccionadas. Se indican los límites y la cobertura no verificada.
6. Desplegar **Datos diarios originales** para revisar las observaciones del rango, en páginas de 50 filas. Cambiar zoom o representación no cambia esa tabla ni los datos almacenados.

La consulta identifica conjunto, versión, activo, procedencia y huella del manifiesto. La API solo lee la versión pedida: no descarga precios ni activa el motor. Al cambiar el contexto se descartan respuestas obsoletas. **Fechas de consulta al motor** permite reducir la lectura si una serie supera las 100.000 observaciones permitidas por respuesta.

Se muestran inicialmente las últimas 120 barras. Cada ventana dibuja como máximo 1.000; los botones de primera/última ventana y desplazamiento permiten recorrer la serie completa. **Restablecer vista** recupera el rango de la consulta y la ventana inicial. El límite se anuncia; no se eliminan barras de origen ni se presentan velas diezmadas como si fueran completas.

## Explorar cartera y backtests

La curva de **Cartera** y los resultados de **Laboratorio** permiten línea o área, fechas inclusivas, zoom, desplazamiento y restablecimiento. La inspección del ratón y del deslizador **Observación de la curva** utiliza las observaciones originales, incluso cuando el dibujo reduce puntos para conservar rendimiento. Estrategia y benchmark se leen en la misma fecha.

Flechas e Inicio/Fin cambian la observación; `+`/`−` amplían o reducen la vista y Escape quita la selección. La tabla conserva sus valores y paginación. Los controles mantienen foco visible y el redimensionado no cambia la fecha inspeccionada.

En Cartera, **TWR desde el origen** representa `(twr_index − 1) × 100`. Un rango visible distinto no cambia ese origen ni recalcula las métricas globales. NAV y patrimonio de backtest no disponen de OHLC intradía y no se convierten en velas.

## Límites de interpretación

- El eje horizontal distribuye observaciones equidistantes; los huecos de calendario no se rellenan ni se dibujan como nuevas sesiones.
- El eje vertical se ajusta al intervalo visible. El área parte del mínimo visible, no necesariamente de cero.
- Los metadatos describen lo recibido. Un precio del proveedor sin ajuste automático no certifica un precio bruto de bolsa. Splits y dividendos siguen como información de procedencia; no hay marcadores ni listado de eventos en el gráfico, no se aplican ajustes ni se interpreta un salto como rentabilidad total.
- No se modifica la contabilidad, el cálculo de backtests, los precios de ejecución ni los controles por explorar un gráfico. No hay nuevos indicadores, datos intradía, órdenes reales ni llamadas pagadas.
- No se requiere GPU ni una biblioteca nueva. Se amplía el SVG existente, con funciones puras de selección y agregación, consultas tipadas y componentes separados por funcionalidad.

## Validación de esta entrega

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

### Rendimiento medido

Chromium 153.0.8010.12, viewport 1440×1000, fixtures sintéticos y API real. Carga incluye navegación, HTTP local, hidratación y dos fotogramas; interacción incluye dos fotogramas tras el evento DOM. No mide hardware del ratón ni una conexión externa.

| Observaciones | Primer gráfico de precios | Primera curva | p95 inspección/zoom |
|---|---:|---:|---:|
| 1.000 | 0,60 s | 0,17 s | ≤34,1 ms |
| 10.000 | 0,54 s | 0,32 s | ≤34,1 ms |
| 100.000 | 2,10 s | 2,44 s | ≤34,1 ms |

La prueba adicional amplía hasta **1.000 velas visibles** sobre 100.000 sesiones originales: 20 posiciones del puntero contrastadas con fecha/OHLCV/cierre previo de la API, p95 **33,8 ms**; 20 alternancias de zoom 1.000↔500, p95 **50,7 ms**. Dibuja 4.025 nodos SVG, con heap tras GC de 25,2 MiB. El escenario de precios y curva usa 31,4 MiB; ocho ciclos entre pestañas mantienen nodos y listeners, con incremento de heap de unos 0,39 MiB entre los ciclos 1 y 8. Estos resultados cumplen el presupuesto inicial y solo describen esa carga técnica corta; no acreditan estabilidad sostenida, memoria total del proceso ni calendario bursátil.

Las mediciones de proyección Python son independientes de HTTP/navegador: 100.000 barras, mediana de proyección 77,29 ms y validación DTO 183,43 ms. Informes locales ignorados por Git: `output/validation/v03-*.json`, pruebas `v03-backend.xml`, capturas y metadatos en `output/validation/v03-windows-scale/`. El escalado físico de rc.2 permanece como evidencia histórica separada.

### Reproducir las medidas

Con ATLAS detenido y la interfaz compilada, iniciar `tools/run_e2e.py --manual --timeout 600` mediante la `.venv`. En otra consola, pasar el identificador `e2e-…` que imprime a:

```powershell
node tools/benchmarks/v03-browser-benchmark.cjs e2e-IDENTIFICADOR
node tools/benchmarks/v03-max-window-benchmark.cjs e2e-IDENTIFICADOR
.\.venv\Scripts\python.exe tools/run_e2e.py --stop-run e2e-IDENTIFICADOR
```

El primer script importa datos sintéticos y un depósito en cada conjunto de la **base aislada**; el segundo solo consulta. Verifican identidad, rutas y procesos antes de actuar, bloquean salidas de red ajenas y conservan informes anteriores. El benchmark Python en memoria se ejecuta con `.\.venv\Scripts\python.exe tools/benchmarks/benchmark_v03_prices.py`. No cargar estos fixtures en la cartera habitual.

**Fuentes: `abf908577c901372e0274aeb34ce95fe4bf1d68a`, [PR #3 en borrador](https://github.com/Buzo500/atlas-quant/pull/3). CI de esta entrega pendiente.** Se conserva el workflow gratuito existente para validar la rama después de comprobar cuota; sus resultados de rc.2 no se atribuyen a v0.3. No se crea una etiqueta estable.
