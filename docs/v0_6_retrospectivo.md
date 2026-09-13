# Investigación retrospectiva y exportación reproducible

Alcance autorizado el 13/09/2026: definir el modo retrospectivo, auditar un histórico
EUR, ejecutar desarrollo, ampliar el estudio de cobertura y preparar exportación.
Primera entrega **0.6.0-dev.6 local**, esquema 5, por CLI: sin nuevos formularios o
endpoints, libros o reserva del Laboratorio. Sin subida ni CI remota de esta entrega.

## Política congelada antes del cálculo

`atlas-retrospective-eur-v1`: un instrumento EUR, OHLC diarios no ajustados pedidos
al proveedor, sin huecos respecto a un calendario de fechas declarado y sin eventos
de split/dividendo conocidos en el tramo. La ausencia de eventos en la respuesta
del proveedor es un supuesto revisable, no una certificación exhaustiva.

Los horarios son **modelados**: apertura 09:00, cierre 17:30 y cierre disponible
18:00 en Europe/Berlin. Las sesiones finales de año usan cierre modelado 14:00
y disponibilidad 18:00. El precio de apertura se usa como referencia hipotética
de ejecución a la siguiente apertura; no acredita que pudiera conseguirse.
El cierre modelado no pretende reproducir la subasta real ni su instante de
determinación: todas las decisiones de cierre esperan a las 18:00 del modelo.
Lotes, comisiones y deslizamiento conservan la política económica existente.
No se rellenan precios ni se eliminan sesiones silenciosamente.

Contratos separados de fuente/calendario con `basis_verified=false`,
`verified=false`, clase retrospectiva y huella de supuestos. Nunca se convierten
a `FrozenPriceSource`/`SmaSpec` acreditados. El motor compartido conserva las
reglas de cruce, calentamiento, ejecución, exposición y NativeBook.

La herramienta congela el protocolo y datos antes de calcular. Solo evalúa fechas
anteriores al corte reservado; no ofrece orden de abrir la prueba final. La reserva
es una exclusión del cálculo y de la exportación, no un registro global ni una
garantía de que nadie haya visto precios históricos. No crea una candidata apta
para paper ni un mandato. El Laboratorio acreditado conserva sus controles.

## Primer caso predeclarado

Seleccionado **ZAL.DE (Zalando), ISIN DE000ZAL1111**, por cotizar en EUR y como
candidato para un tramo sin distribuciones/splits, antes de consultar resultados
de estrategia. Primera opción, no selección por rentabilidad. Descargar
02/01/2023–30/12/2025; desarrollo hasta 30/06/2025, reserva desde 01/07/2025.
SMA 20/50, capital 10.000 EUR, peso/límite 1, lote 1, comisión fija 1 EUR más
5 pb y deslizamiento 5 pb. Comprar/mantener y efectivo como referencias, bajo
el mismo periodo y costes. No optimizar ni cambiar fechas al ver resultados.

Contrastar identidad con el emisor y fechas con los calendarios oficiales
Xetra 2023–2025. Conservar instantánea del proveedor, versión, UTC de descarga,
hash y transformación numérica. Bloquear discrepancias o eventos conocidos;
documentar base retrospectiva, correcciones históricas posibles, sesgo de selección
y límites de ejecución. Los datos descargados no se redistribuyen en Git.

## Estudio de cobertura predeclarado

Experimento separado `atlas-robustness-coverage-v2`, semilla maestra 20260913,
100 historias por escenario, n=504, 5.000 réplicas por L=5/10/20 (10 principal).
Seis escenarios: IID normal, AR(1) estacionario con phi=0,6 y phi=0,9,
IID t de Student con 5 grados de libertad y varianza finita igualada, cambio de
varianza por un factor 4 y cambio de media simétrico ±0,5 %. No ajustar el método
después de observar resultados. No se sustituye el experimento v1 ni sus semillas.

Para los cuatro escenarios estacionarios, estimando=media poblacional cero;
los dos cambios son pruebas de estrés no estacionarias, contra media esperada
del promedio de la muestra (cero), no prueba de validez de las hipótesis.
Publicar recuentos, intervalos Wilson del error Monte Carlo, anchura media y
colas de error; conservar todas las historias, semillas y hashes, sin seleccionar L.
No modificar los intervalos o etiquetas de robustez del producto en esta entrega.

## Exportación inicial

Paquete local ZIP con JSON canónico del desarrollo y configuración, CSV de precios,
NAV, métricas y operaciones, descripción de supuestos y manifiesto SHA-256 de cada
fichero. Precios/curvas/operaciones solo de desarrollo; de la reserva conserva
fechas, recuento y huella, sin precios. No lee claves ni exporta automáticamente
rutas personales; los textos de procedencia los aporta quien prepara el protocolo.
Escritura nueva sin sobreescribir y verificación sin extraer archivos.
Reproducción recalcula con el motor actual y comprueba hashes de código y resultado;
un hash acredita integridad respecto al manifiesto, no autenticidad del proveedor.
Formato estable inicial por CLI; interfaz y plantilla LaTeX requieren otra entrega.

## Fuente observada auditada el 13/09/2026

Identidad contrastada en la [ficha del emisor](https://corporate.zalando.com/en/investor-relations/zalando-share):
Zalando, ZAL, ISIN DE000ZAL1111, Frankfurt. La descarga devuelve ZAL.DE, EUR,
equity, mercado GER y Europe/Berlin. Esto identifica el instrumento, no certifica
los precios del proveedor ni ausencia histórica de eventos.

Fechas contrastadas con los calendarios oficiales Xetra de
[2023](https://www.cashmarket.deutsche-boerse.com/resource/blob/3317408/4c8fbfbfeea62fd44600f6fe3f14f84e/data/xetra-trading-calendar-2023.pdf),
[2024](https://cashmarket.deutsche-boerse.com/resource/blob/3559262/98ebe1fde231df56c9f116bc766533b2/data/xetra-trading-calendar-2024.pdf)
y [2025](https://www.cashmarket.deutsche-boerse.com/resource/blob/4064968/4079a2d5a9fec324905942b807b398ed/data/xetra-trading-calendar-2025.pdf).
El [archivo oficial](https://www.cashmarket.deutsche-boerse.com/cash-en/trading/trading-calendar-and-trading-hours/trading-calendar)
conserva las notas de las sesiones finales de año. Fechas modeladas abreviadas:
29/12/2023, 30/12/2024 y 30/12/2025; no se supone liquidez fuera de sesión.

Descarga gratuita mediante el adaptador existente: yfinance 1.7.0, TLS verificado,
`auto_adjust=false`, `back_adjust=false`, `repair=false`; recepción UTC
`2026-09-13T15:25:49.746048+00:00`. No se han instalado dependencias ni usado claves.
Instantánea conservada del DataFrame serializado, **no respuesta HTTP original**:
SHA-256 `9f49bed7bd1e7aca142093f2bb2c486ef81bc63b725981d8725b7445682ebd37`.
Conversión explícita a 12 decimales con ROUND_HALF_EVEN, desviación máxima
`4,92 × 10^-13 EUR` respecto a esa representación. Fechas UTC convertidas a la
fecha local de Europe/Berlin; no se transforman rendimientos ni se rellenan filas.

762 filas, exactamente las 762 fechas esperadas, sin huecos/duplicados/extras.
OHLC coherente y volumen positivo; dividendos/splits cero en la respuesta y
`Adj Close == Close` en todas las filas. **Apta solo para esta política
retrospectiva**. La comprobación no convierte ausencia de eventos del proveedor en
acreditación exhaustiva, disponibilidad histórica verificable o serie point-in-time.
El CSV de NVIDIA anterior y los requisitos del Laboratorio permanecen intactos.

Los originales, recibo y auditoría están excluidos de Git en
`output/validation/v06-retrospective-zal/`. `request-final.json` completa la
procedencia antes del primer cálculo; conserva los parámetros económicos de la
predeclaración. `frozen-final.json` tiene huella
`caa6ce809359fe99bb808a121fd2f7466f53107c913f2abb06ae601e428c41e7`.
La reserva se valida estructuralmente al congelar el CSV completo, después sus
precios no llegan al replay. Esto no prueba que el histórico fuera desconocido
fuera de la herramienta ni registra una reserva global del Laboratorio.

## Resultado observado de desarrollo

02/01/2023–30/06/2025, 634 sesiones; SMA comienza sin posición ni historia previa,
con calentamiento de 50 sesiones. Comprar/mantener invierte en la primera apertura
del periodo: incluye el coste de oportunidad del calentamiento de la estrategia.
Comisiones y deslizamiento conforme al protocolo; sin liquidación forzada al final,
impuestos ni remuneración del efectivo. Las cifras originales se conservan en JSON.

| Cuenta hipotética | Patrimonio final EUR | Rentabilidad | Caída máxima | Ejecuciones | Comisiones EUR |
| --- | ---: | ---: | ---: | ---: | ---: |
| SMA 20/50 | 8.246,07 | −17,5393 % | 30,8830 % | 16 | 87,43 |
| Comprar/mantener | 8.358,97 | −16,4103 % | 64,0570 % | 1 | 5,99 |
| Efectivo | 10.000,00 | 0 % | 0 % | 0 | 0,00 |

Cero órdenes hipotéticas rechazadas o expiradas. SMA pierde más que comprar/mantener
en este desarrollo, con menor caída máxima; no demuestra ventaja, robustez ni
aptitud para operar. No se han optimizado medias o costes ni realizado una prueba
estadística de estos retornos observados. La ampliación de cobertura de abajo es
un experimento sintético independiente, no evidencia sobre Zalando.

Reserva 01/07/2025–30/12/2025, 128 sesiones, **no calculada**. El paquete solo
conserva su huella `db5631e01155ac35a436a1b2b1de7cf84949c8e30cdece284a2cb0ba644d10c9`
y metadatos. Informe reproducido desde el ZIP con huella
`437efdd47b1c944f4d0eb29f267ecc124233a488ec981f8e2bc6c57945ce2522`.

## Cobertura ampliada: resultado completo por longitud

Ejecución Windows/Python 3.14.4, NumPy 2.5.2, 508,18 s. Recuentos sobre 100
historias independientes por escenario (600 historias, 1.800 intervalos estimados).
El intervalo Wilson describe la incertidumbre Monte Carlo de la cobertura estimada;
no es el intervalo de la media de retornos calculado por bootstrap.

| Escenario | L=5 | L=10 principal | L=20 | Wilson 95 % para cobertura L=10 | Anchura media L=10 (pp) |
| --- | ---: | ---: | ---: | --- | ---: |
| IID normal | 93/100 | 94/100 | 92/100 | 87,52–97,22 % | 0,17156 |
| AR(1), phi=0,6 | 90/100 | 91/100 | 92/100 | 83,77–95,19 % | 0,30642 |
| AR(1), phi=0,9 | 68/100 | 73/100 | 82/100 | 63,57–80,73 % | 0,50727 |
| IID t(5) | 95/100 | 95/100 | 95/100 | 88,82–97,85 % | 0,16691 |
| Cambio de varianza (estrés) | 95/100 | 94/100 | 92/100 | 87,52–97,22 % | 0,27204 |
| Cambio de media (estrés) | 100/100 | 100/100 | 100/100 | 96,30–100 % | 0,40197 |

La infracobertura con dependencia fuerte es clara en este diseño; no es defendible
presentar el 95 % nominal como cobertura garantizada. El 100/100 del cambio de media
tampoco valida el método: el estimando es el promedio esperado de esa muestra y
se incumple la estacionariedad. No se cambia L=10 al observar que L=20 cubre más.
Ninguna de las longitudes queda certificada para una serie de mercado.

Artefactos completos: `output/validation/robustness-coverage-v2/plan.json`,
`histories.jsonl` y `results.json`. Plan:
`93fc5aa7cc9bf5c3f032cbf16fdd30c87af037f0013de7c9cad5f43887525368`;
resultado: `3bfd1c3005f17c8d57521822417f1f8a3f39c4089fc4df820670891e95ade34b`.
Se conservan semillas, todas las muestras, hashes de índices y errores por cola.
En las filas, `false_positive` representa límite inferior > 0 y `false_negative`
límite superior < 0: son direcciones de exclusión errónea de cero, **no** sensibilidad
o especificidad de un clasificador. El resumen usa `misses_above`/`misses_below`.
Los tiempos y la plataforma pueden cambiar al reproducir el estudio; comparar
valores/semillas/historias, no exigir igualdad del hash de esos metadatos operativos.

## Uso local y reproducción

Desde la raíz del proyecto, con la `.venv` existente:

```powershell
.\.venv\Scripts\python.exe tools/run_retrospective.py verify output/validation/v06-retrospective-zal/atlas-zal-desarrollo.zip
```

Para crear otro informe desde un protocolo preparado, cada salida debe ser nueva:

```powershell
.\.venv\Scripts\python.exe tools/run_retrospective.py freeze --request solicitud.json --prices precios.csv --output congelado.json
.\.venv\Scripts\python.exe tools/run_retrospective.py run congelado.json --output informe.json
.\.venv\Scripts\python.exe tools/run_retrospective.py export informe.json --output paquete.zip
.\.venv\Scripts\python.exe tools/run_retrospective.py verify paquete.zip
```

La solicitud cumple `RetrospectiveRequest` en `backend/atlas_quant/retrospective.py`:
identidad y mercado, fechas esperadas completas, sesiones abreviadas, corte reservado,
medias, configuración `SimulationConfig`, procedencia, fuentes del calendario,
revisión de eventos, SHA-256 de los bytes UTF-8 del CSV y
`acknowledge_assumptions: true`. El ejemplo completo local es `request-final.json`.
Cabecera CSV exacta: `date,open,high,low,close,volume,dividends,splits`; fechas ISO,
punto decimal y sin separadores de miles. Sin eventos, como máximo 2.000 sesiones,
CSV de hasta 2 MB y particiones de al menos ventana lenta + 2 sesiones.

El ZIP tiene siete miembros fijos, orden y marcas temporales deterministas.
La verificación rechaza alteraciones, nombres extraños, duplicados, cifrado o
contenido descomprimido mayor de 20 MB. Reconstruye todos los CSV y vuelve a
calcular el desarrollo. Requiere las mismas fuentes de código; normaliza CRLF/LF
al comparar sus hashes. No ejecuta contenido del paquete ni extrae rutas.
Comprueba reproducibilidad del desarrollo, no autenticidad del proveedor ni la
correspondencia del hash del CSV completo cuyos precios reservados están ausentes.
No importa el informe en una base ni permite abrir la reserva.

Para repetir la cobertura en una carpeta nueva (trabajo CPU local, unos 8,5 min
en esta ejecución; no forma parte del arranque ni de la suite rápida):

```powershell
.\.venv\Scripts\python.exe tools/diagnostics/robustness_coverage_v2.py --output output/validation/cobertura-nueva
```

## Verificación de implementación

1.104 pruebas Python + 91 subcasos correctos, incluidos 40 casos nuevos: oráculo
manual de P&L, contratos acreditados que rechazan supuestos, fallos de CSV,
independencia numérica del desarrollo al cambiar precios reservados, cambios de
horarios/identidad incluso recalculando hashes, exportación reproducible,
alteración de CSV/resultados/código, miembros duplicados y rutas inesperadas.
Los tests usan datos sintéticos y bases aisladas, sin descargas.
Build canónico, contratos, TypeScript y lint correctos; cuatro recorridos E2E v0.6
correctos (desarrollo/reserva, walk-forward, sensibilidad/candidatas y robustez).
Servidores aislados con salida 0, puertos liberados, integridad correcta y base
habitual intacta. [Cierre operativo y captura API](CONTINUIDAD.md).

El caso observado y la exportación reproducida son comprobaciones adicionales
locales, no parte de la CI anterior. La versión dev.6 no tiene CI remota nueva.
