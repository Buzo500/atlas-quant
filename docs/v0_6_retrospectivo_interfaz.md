# Retrospectivo desde el Laboratorio · 0.6.0-dev.7

13/09/2026. Cinco tareas autorizadas en [el plan previo](v0_6_dev7_plan.md).
Rama `codex/v0.6-evaluador`, esquema 5. Dev.6 ya subida y con
[CI gratuita correcta](publicacion_v06_dev6.md); esta ampliación es local.

## Usarlo sin consola

1. Iniciar con `Abrir-ATLAS.cmd` y abrir **Laboratorio → Investigación
   retrospectiva con supuestos**. No requiere un conjunto legacy seleccionado.
2. Indicar símbolo, identificador/ISIN, mercado, comienzo de reserva y precios
   CSV (archivo o texto). Cabecera exacta:
   `date,open,high,low,close,volume,dividends,splits`; punto decimal, fechas ISO,
   máximo 2 MB. EUR, horarios Europe/Berlin y precios sin eventos conocidos.
3. Declarar el calendario esperado completo y las sesiones abreviadas, una fecha
   ISO por línea. Se puede cargar un archivo de calendario. Debe proceder de la
   fuente declarada: inferirlo solo de las filas recibidas escondería los huecos.
4. Completar procedencia de precios/calendario y revisión de dividendos/splits,
   medias, capital, lotes, pesos y costes. Aceptar explícitamente los supuestos.
5. **Congelar y revisar protocolo** prepara el contexto sin ejecutar la estrategia.
   Revisar fechas/sesiones de ambos tramos y costes. Marcar la revisión y pulsar
   **Calcular desarrollo retrospectivo**. Editar el borrador invalida la congelación.
6. Examinar tabla y curva frente a comprar/mantener y efectivo. Descargar el
   **informe JSON** para conservarlo o **Exportar paquete JSON/CSV** para el ZIP.
   ATLAS verifica por recálculo antes de exportar.
7. Tras recargar, usar **Informe retrospectivo guardado** para reabrir el JSON.
   El resultado vuelve a calcularse y debe coincidir. El borrador de entrada no
   persiste entre recargas o cambios de pestaña; contraer el panel sí lo conserva.

No hay historial nuevo en SQLite: el guardado de esta primera UI es una descarga
al navegador. La reserva aporta fechas, número de sesiones y huella, sin sus
precios en el informe/paquete. No se calcula ni habilita desde este panel.
No equivale al registro global de exposición temporal del Laboratorio acreditado.

## Límites y contratos

La política `atlas-retrospective-eur-v1` de dev.6 permanece igual. Los horarios,
disponibilidad, ausencia de ajustes/eventos no acreditada y ejecución son supuestos;
no se convierten en evidencia validada al marcar una casilla. No se registran
candidatas ni operaciones en carteras.

Cuatro rutas POST locales `prepare`, `calculate`, `reopen` y `export`, bajo
`/api/lab/retrospective/`, comparten la capacidad de cálculo acotada y los controles
de origen/cabecera. Contratos OpenAPI regenerados. Sin servicios externos, cambios
de esquema, lectura/escritura de libros o archivos indicados dentro de un informe.

`retrospective_package.py` concentra el formato y la reproducción compartidos por
CLI/HTTP; el ejecutable conserva sus funciones públicas anteriores. Un informe de
otro código puede reabrirse en UI si todos sus resultados y su hash original
coinciden tras recálculo. Se avisa de la diferencia de código, conservando las
huellas originales. Eso no certifica igualdad del entorno ni autenticidad: un
hash sin firma no acredita al proveedor. La CLI `verify` conserva su comprobación
estricta de código original. No hay bandera para convertirlo en acreditado.

Se reprodujo el informe original de ZAL.DE dev.6 con el código nuevo, sin
reescribirlo: `437efdd47b1c944f4d0eb29f267ecc124233a488ec981f8e2bc6c57945ce2522`.

## Segundo caso observado: HelloFresh

Identidad HFG.DE, ISIN DE000A161408, EUR/Xetra, contrastada con el
[emisor](https://ir.hellofreshgroup.com/news/hellofresh-se-legt-angebotspreis-auf-eur-1025-pro-aktie-fest/85bc3aab-c993-4ed2-aa50-8b82a8aa9cc6)
y [Deutsche Börse](https://live.deutsche-boerse.com/equity/hellofresh-se/price-history/historical-prices-and-volumes).
Se eligió y fijó el protocolo antes de descargar/calcular, sin sustituir el activo
por su resultado. Comparte las fechas y parámetros fijados para ZAL.DE; no se
afirma independencia económica ni una muestra representativa de activos.

Descarga gratuita Yahoo/yfinance 1.7.0, 13/09/2026 16:24:47 UTC, TLS verificado,
sin ajuste automático, reparación o relleno. 762 filas coinciden con el calendario
Xetra 2023–2025 usado en [dev.6](v0_6_retrospectivo.md), sin huecos/extras.
Dividendos/splits cero y Adj Close igual a Close en la respuesta. El emisor sí
anuncia [recompras](https://ir.hellofreshgroup.com/share-buy-back-2025): no se afirma
ausencia de todo evento corporativo; no se modela su efecto fundamental.
El proveedor no acredita exhaustividad de eventos ni disponibilidad histórica.

Fuente capturada: DataFrame JSON, no respuesta HTTP cruda. SHA-256
`47e40c4877161d753d370c8ae7be7a91ae14ed413cdd2773b4b8204197dc4dc9`.
Normalización OHLC a 12 decimales HALF_EVEN, diferencia máxima 4,96e−13 EUR.
762 sesiones: 634 desarrollo (02/01/2023–30/06/2025) y 128 reservadas
(01/07/2025–30/12/2025). SMA20/50, 10.000 EUR, lote 1, peso/límite 1,
comisión 1 EUR + 5 pb, deslizamiento 5 pb; compra al siguiente open modelado.

| Referencia | NAV final EUR | Rentabilidad | Caída máxima | Ejecuciones | Comisiones EUR |
|---|---:|---:|---:|---:|---:|
| SMA20/50 | 8.413,39 | −15,8661 % | 57,3617 % | 10 | 62,86 |
| Comprar/mantener | 3.803,28 | −61,9672 % | 86,6829 % | 1 | 5,99 |
| Efectivo | 10.000,00 | 0 % | 0 % | 0 | 0 |

La estrategia pierde capital, supera a esta referencia y sufre una caída grande.
No acredita rentabilidad futura, superioridad general o permiso para operar.
No se han calculado robustez adicional o reserva a partir de este resultado.

Artefactos locales en `output/validation/v06-retrospective-hfg/`: receipt/audit,
provider-frame, prices.csv, calendar-dates.txt, request/frozen/report.json y
**atlas-hfg-desarrollo.zip**. ZIP verificado por recálculo, sin precios reservados.

- Protocolo: `430a5c8759fc1c6351a60cff60f22b39c7b8c9fc46f4b1a2cbc69be66c86c8c6`.
- Informe: `4b06777d73354bc5c87a9c773285794a36bf49d72568e02c818bf1195c856880`.
- Huella de filas de reserva: `62d7e945e341f45c38e618a08bc75458ba1da0df4def43841dff5c52fe1c06fe`.

Antes del cierre se retiró una línea vacía sobrante del módulo del paquete. Se
conservaron informe/ZIP anteriores con sufijo `before-format`, se regeneraron los
finales y se comprobó igualdad exacta de protocolo y resultados. Solo cambian la
huella de ese archivo de código y la del informe; el ZIP final vuelve a pasar verify.

## Estadística y LaTeX

[Revisión de dependencia](v0_6_dependencia_revision.md): identidad AR(1)
contrastada con matriz de covarianzas, protocolo de siguiente experimento fijado,
sin cambiar el bootstrap del producto ni escoger parámetros tras ver cobertura.
El experimento nuevo está definido, no ejecutado.

[Plantilla ATLAS](informes_latex_diseno.md): contenido, paleta, contrato de
generación propuesto, [fuente editable](templates/atlas-report-v1.tex) y
[maqueta HTML](templates/atlas-report-v1.html) con cinco puntos sintéticos.
Dos páginas HTML inspeccionadas y adaptación a 565 px sin desbordamiento; no es
un PDF generado por LaTeX. Compilador y generador pendientes; no se instalaron.

## Verificación de la entrega

1.124 Python + 91 subcasos, incluidos 20 nuevos casos HTTP; 336 frontend,
incluidos ocho nuevos; ocho pruebas de transporte Node. Contratos, TypeScript,
lint y build canónico correctos. API: origen, tamaño, alteraciones, límites de
cálculo, versión de código y base sin escrituras. UI: consentimiento/congelación,
respuesta tardía, revisión, archivos, errores y controles ocupados.

Primer pase E2E: 24 recorridos anteriores correctos; el nuevo falló en un selector
exacto de etiqueta que incluía el valor del textarea tras la carga. El contenido
sí estaba cargado. Se corrigió la búsqueda por nombre accesible, se limitó la
altura de los campos de archivos largos y el recorrido nuevo pasó en 4 s.
Incluye teclado, descarga JSON/ZIP, reapertura idéntica, contracción sin pérdida y
anchuras CSS 565/1366/3440. Esto no es una nueva comprobación física de DPI.
Evidencia dirigida `e2e-b3e4c281075c4a11b47bab595814f308`: 52 grupos, cero incidencias,
resultado 0 y ambos servidores salida 0. Regresión final completa
`e2e-8067445a9b4c451bb5cd1189375e342c`: **25/25 correctos en 111,42 s**, sin omitidos
o reintentos; resultado 0, servidores 0, puertos libres y base habitual intacta.
Captura: 1.886 grupos y 82 marcas de fallo/cancelación breves (≤167,705 ms), ninguna
espera de 1 s. No confundirlas con fallos de los recorridos ni con la causa histórica.

ATLAS habitual detenido y base conservada. Presupuesto cero, sin claves/proveedor
IA ni nueva dependencia. CSV acreditado e incidencia API histórica siguen abiertos;
PR #12, portátil, ensayo y movimientos personales siguen aplazados.
