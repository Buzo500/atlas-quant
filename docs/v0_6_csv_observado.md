# v0.6 · auditoría de un CSV observado NVD.DE

Actualización 13/09/2026: [primer caso ZAL.DE calculado bajo una política
retrospectiva explícita](v0_6_retrospectivo.md), sin acreditar disponibilidad/base
históricas. No cambia el diagnóstico de NVIDIA ni consigue una fuente apta para
el Laboratorio acreditado. La adquisición pendiente de abajo se refiere a ese
estándar de evidencia, no a ausencia de cualquier histórico observado.

**Resultado: formato válido, evidencia insuficiente para el Laboratorio.**
Se contrastó el histórico ya descargado de NVD.DE, sin cambiar sus versiones,
importarlo en la base habitual ni completar artificialmente su evidencia.
Es una comprobación del 11/09/2026 sobre datos anteriores, no una descarga nueva.

## Fuente y transformación explícita

### Búsqueda adicional · 12/09/2026

La adquisición sigue **pendiente**. Se revisan alternativas primarias sin comprar
datos, solicitar claves ni modificar series habituales. La página actual de
[Deutsche Börse](https://www.cashmarket.deutsche-boerse.com/cash-en/Data-Tech/statistics/market-data)
remite a Data Shop y A7 para históricos; no acredita aquí una exportación gratuita
con todos los campos exigidos por ATLAS.

La [especificación pública NextHistory de Euronext, versión 2.1.2 de 2020](https://connect2.euronext.com/sites/default/files/documentation/data/NextHistory%20Cash%20Client%20Specification%20V2.1.2_20.10.2020.pdf)
describe datos posteriores a compensación, ficheros de calendario, instrumentos,
dividendos, ajustes y precios dentro de sus suscripciones (páginas 5–7). En la
sección 3.2, página 9, indica que la disponibilidad del fichero no tiene una hora
fija y varía cada día. Es una especificación histórica, no una garantía comercial
actual ni un fichero adquirido.

Consecuencia para esta auditoría: una hora de operación o un OHLC oficial no basta
para reconstruir `available_at`. No asignar una hora constante a los ficheros ni
usar su hora de descarga actual como disponibilidad histórica. No se ha conseguido
un CSV observado que supere todos los controles; esto no demuestra que no exista
ninguna fuente gratuita apta. Tampoco se relajan controles para forzar la prueba.

El ensayo estadístico de dev.5 usa exclusivamente escenarios sintéticos declarados:
verifica el cálculo, no valida una estrategia con datos de mercado.

### Búsqueda adicional de fuente gratuita · 11/09/2026

Se buscó una alternativa primaria para completar OHLC, disponibilidad y eventos.
El registro oficial de AWS marca el antiguo dataset público Deutsche Börse como
retirado y sin mantenimiento. El enlace a su repositorio oficial devuelve 404
en la consulta web. [Registro oficial](https://github.com/awslabs/open-data-registry/blob/main/datasets/deutsche-boerse-pds.yaml).

El servicio actual de Deutsche Börse ofrece datos con 15 minutos de retraso,
actualización por minuto y conservación hasta la medianoche del siguiente día
hábil. Sirve para observaciones recientes, pero esa ventana no recupera el
histórico requerido. La hora de una operación o la de un agregado no acredita
cuándo estaba disponible el dato en un sistema histórico.
[Descripción oficial](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/Delayed-data).

Las sondas HTTPS locales al antiguo repositorio y al bucket público fallan en la
validación del certificado de este entorno (Python: CA sin Basic Constraints
critical; PowerShell: fallo SSL). No se desactiva TLS ni se deduce de ello que el
bucket responde 404. Artefactos locales `output/validation/source-availability-dev4.json`
y `source-bucket-dev4.json`. La página de ficheros diferidos pudo consultarse por
la herramienta web; no se contrató ni descargó un producto comercial.

**Resultado del punto de adquisición: pendiente, no acreditado.** Tener OHLC
descargados no satisface por sí solo `available_at`, aperturas, calendario y ausencia
de eventos. Un periodo sin dividendos conocidos tampoco prueba su ausencia. La
fuente gratuita revisada no resuelve todos esos requisitos; esto no afirma que
ninguna fuente gratuita pueda hacerlo. Los datos NVD anteriores siguen intactos.

Ruta concreta para desbloquearlo: exportación histórica autorizada que conserve
identidad, precios brutos y disponibilidad documentada, contrastada con calendario
y avisos corporativos del mercado/emisor. Si solo hay OHLC retrospectivos, valorar
por separado una política futura de supuestos explícitos de ejecución; **no
reclasificar esos supuestos como evidencia** ni relajar la política actual de forma
silenciosa. Comprar datos no garantiza que contengan estos campos.

### Búsqueda adicional de fuente gratuita · 13/09/2026

Se revisaron alternativas primarias sin claves, compras ni cambios en la política:

| Fuente consultada | Qué aporta | Carencia para el Laboratorio actual |
| --- | --- | --- |
| [Nasdaq, datos diferidos MiFID II](https://www.nasdaq.com/market-regulation/nordic/mifid-ii) | Ficheros gratuitos diferidos, con actualización frecuente | La retención descrita de 24 horas no recupera los 504 intervalos de desarrollo más calentamiento y reserva necesarios. |
| [Nasdaq Baltic, ficha NTU1L](https://nasdaqbaltic.com/statistics/en/instrument/LT0000131872/trading) | Identidad LT0000131872, EUR y operaciones recientes | No se obtuvo el histórico completo ni evidencia de publicación histórica y ausencia de eventos. El enlace histórico falló en la herramienta web; no se interpreta como inexistencia del servicio. |
| [Euronext Web Services](https://www.euronext.com/en/data/how-access-market-data/web-services) | Oferta de acceso a datos históricos | La página comercial no acredita una descarga gratuita accesible con todos los campos requeridos. No se solicitó contrato ni se contactó a terceros. |
| [BCE, tipos de referencia](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) | Histórico descargable de tipos FX | Son tipos de referencia, no OHLC ejecutables de un activo EUR. No sustituyen la fuente exigida para SMA. |

La [estructura de sesión de Nasdaq Baltic](https://nasdaqbaltic.com/market-information/trading-day/)
describe una subasta de apertura con instante aleatorio dentro de cinco segundos
y una de cierre dentro de treinta segundos. Inferencia para esta auditoría: el
horario general del mercado no acredita la hora efectiva de cada apertura ni la
disponibilidad histórica del dato. Tampoco «sin dividendos próximos» en una ficha
actual demuestra ausencia de eventos en un periodo histórico.

**Resultado: fuente observada apta todavía pendiente.** No se genera un CSV con
horas inventadas, no se acredita el NVD anterior y no se abre una reserva final.
La próxima decisión útil es aportar una exportación con evidencia suficiente o
definir explícitamente, como trabajo nuevo, un modo exploratorio retrospectivo
con supuestos y restricciones propios. Este último no equivaldría a evidencia
point-in-time ni habilitaría paper externo. No se ha implementado en este turno.

### CSV ya auditado

Dataset `4fc6914f5b944719a4901d8613d9968b`, versión 2, en EUR; tramo
01/01/2026–09/09/2026. La identidad de NVIDIA (ISIN US67066G1040, símbolo NVD)
se contrastó con la [ficha oficial de Deutsche Börse](https://live.deutsche-boerse.com/equity/nvidia-corp/price-history/tick-data).
Esta ficha no acredita todos los OHLC históricos de Yahoo.

Lectura SQLite `mode=ro`. Se conserva el JSON de origen y se deriva un CSV nativo
con `listing_ref=NVD.DE`; no se presenta como el CSV original del proveedor.
Los precios binarios del JSON se convierten a un máximo de 12 decimales con
`ROUND_HALF_EVEN`, explícitamente para el contrato nativo. Diferencia máxima
numérica: `5E-13` EUR. `available_at` permanece vacío: la hora de descarga no
acredita disponibilidad histórica de un cierre o una apertura.

- SHA-256 JSON: `a173fe678b8b9ffb6b243c304b9f899ec30bdbb4e8c6dec143a818c0f2fb04af`.
- SHA-256 CSV derivado: `514c606950eade9946380eeb12087cd393384f12ed6fdb0f6bef33914327711f`.
- Artefactos locales: `output/validation/v06-observed-nvidia/`, excluidos de Git.

## Comprobaciones

El CSV pasa `MarketImport` y el analizador real de precios nativos. Tiene 175
filas entre 02/01 y 09/09, fechas ordenadas, ningún duplicado y OHLC coherentes
internamente. Esa coherencia no acredita que el precio sea correcto frente a una
fuente independiente ni que su base sea bruta.

Se compararon las fechas con el [calendario oficial 2026 de Xetra/Frankfurt](https://www.cashmarket.deutsche-boerse.com/resource/blob/4481276/760a75c511e33638c89f940d398373c7/data/xetra-trading-calendar-2026.pdf):
176 sesiones esperadas, ninguna fecha extra y **falta el 07/09/2026**. Es una
comparación de fechas del mercado, no evidencia de horas efectivas de subasta o
de una posible suspensión particular de este valor.

Faltan las horas históricas de los 175 cierres y las aperturas acreditadas. Base
raw, calendario completo con horas y contraste independiente permanecen sin
verificar. El origen declara además dividendos el 11/03 y 04/06; sus datos no
se certifican mediante esta auditoría. El tramo completo tampoco satisface la
restricción inicial del simulador de ausencia de eventos corporativos.

## Decisión y siguiente evidencia necesaria

**No marcar este CSV como apto ni activar las casillas de evidencia para forzar
un resultado.** Antes de usar datos observados se necesita:

1. Acreditar base y OHLC, y explicar el hueco con la fuente/mercado.
2. Aportar calendario con horas y disponibilidad histórica de cierres/aperturas.
3. Contrastar eventos y escoger un periodo permitido por el motor actual.

El trabajo autorizado de contraste se ha realizado y el resultado es negativo.
Queda pendiente conseguir una fuente suficiente; el ejemplo sintético reproducible
continúa disponible para verificar el software, sin presentarlo como validación
de una estrategia sobre mercado real. No se compran datos ni se cambia el presupuesto.
