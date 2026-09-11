# v0.6 · auditoría de un CSV observado NVD.DE

**Resultado: formato válido, evidencia insuficiente para el Laboratorio.**
Se contrastó el histórico ya descargado de NVD.DE, sin cambiar sus versiones,
importarlo en la base habitual ni completar artificialmente su evidencia.
Es una comprobación del 11/09/2026 sobre datos anteriores, no una descarga nueva.

## Fuente y transformación explícita

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
