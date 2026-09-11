# NVIDIA · diagnóstico del 11 de septiembre de 2026

## Resultado

La cadena Yahoo/yfinance sigue entregando una fila parcial para la sesión local **10/09/2026** de `NVD.DE`. La validación de ATLAS la rechaza antes de guardar precios. No corresponde sustituir el cierre, eliminar la fila para seguir ni marcar el conjunto como verificado.

Sonda aislada a las **08:12:11 UTC**: mismo adaptador `yfinance 1.7.0`, TLS verificado, rango 07/09 inclusivo a 11/09 exclusivo, caché fuera de la base habitual. Se guarda la tabla recibida y se pasa **esa misma respuesta** al validador, sin una segunda descarga para validar.

- Metadata: `EUR`, `EQUITY`, `GER`, `Europe/Berlin`.
- Tres filas recibidas. La última tiene apertura 189,479995…, máximo 189,520004…, mínimo 189,139999…, **cierre ausente**, volumen 8.367 y dividendo declarado por el proveedor 0,2154. Son valores diagnósticos del proveedor, no cotizaciones/eventos acreditados ni instrucciones para el libro.
- El índice serializado `2026-09-09T22:00:00Z` representa la medianoche del 10/09 en Berlín. ATLAS conserva correctamente la fecha de sesión del índice local.
- Error: `Cotización incompleta para 2026-09-10: faltan close`. La anterior respuesta del arranque también carecía de cierre, con otro volumen. La variación confirma que las respuestas no son idénticas; no determina por sí sola la causa interna en Yahoo/yfinance.
- Evidencia local ignorada por Git: `var/validation/nvidia-dev3-2e36532f1dce4ced9d31cf872e358838/report.json` y `provider-frame.json`; huella de la tabla `36b1092ed303c88aaa0323a430c18d97213a13a9f21b49918330cbe49876cedc`.

La sonda captura la salida de yfinance anterior a la normalización de ATLAS; **no distingue todavía** un dato parcial original de Yahoo de una transformación interna de yfinance. Sí permite descartar que el cierre desaparezca en el gráfico o en el guardado de ATLAS. No se cambia el código del feed, se desactiva TLS ni se insiste con reintentos.

## Datos habituales conservados

Lectura SQLite en modo de solo lectura, tras detener ATLAS. Ambos mantienen las versiones 1 y 2 y terminan el 09/09/2026:

| Conjunto | Barras v2 | Inicio | Evidencia actual |
| --- | ---: | --- | --- |
| `4fc6914f5b944719a4901d8613d9968b` | 428 | 02/01/2025 | Calendario sin verificar; base desconocida; seis eventos corporativos |
| `689ac9b5170445649605a0abd743b142` | 1.194 | 03/01/2022 | Calendario sin verificar; base desconocida; 19 eventos corporativos |

El informe `quality-v1` permite dibujar ambos conjuntos, pero bloquea valoración, investigación exploratoria/acreditada y paper en este corte. Hay eventos corporativos sin resolver, además de la evidencia ausente. Inventario local: `output/validation/nvidia-dev3-inventory.json`.

La descarga válida del 10/09 a las 19:55 UTC sigue siendo evidencia histórica válida. Entonces se excluyó explícitamente el 07/09, que llegó sin ningún OHLC y con volumen cero. Esa exclusión deja un hueco: no acredita un festivo ni justifica excluir una fila **parcial** como la del 10/09.

## Evidencia necesaria para usar un tramo real

1. **Identidad y mercado:** verificar que el instrumento y su cotización corresponden al centro de negociación elegido. `GER` y el sufijo de Yahoo no bastan para certificar toda la identidad financiera. Mantener separadas las dos fuentes existentes y sus vínculos de cartera.
2. **Calendario:** escoger el periodo y aportar el CSV D3 `date,status,close_at`, con todos los días civiles, fuente, mercado y zona. Contrastar festivos y horarios especiales con la [fuente oficial de Deutsche Börse](https://www.cashmarket.deutsche-boerse.com/cash-en/trading/trading-calendar-and-trading-hours); sus calendarios distinguen Xetra y Frankfurt y remiten a horarios de subastas. El evaluador v0.6 también necesitará aperturas explícitas. No convertir la ausencia del 07/09 en día cerrado sin evidencia.
3. **Base de precios y eventos:** contrastar qué ajustes contiene realmente la serie y revisar splits/dividendos del tramo. La [documentación de yfinance](https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html) distingue autoajuste, back-adjust, reparación y conservación de NaN. ATLAS usa `auto_adjust=False`, `back_adjust=False`, `repair=False`, `keepna=True`; estas opciones no certifican precios de mercado brutos ni integridad de eventos. Resolverlos en una cartera tampoco resuelve automáticamente la evidencia global de investigación.
4. **Disponibilidad histórica:** aportar `date,available_at` y su procedencia. La hora de descarga actual no prueba cuándo estuvo disponible cada cierre en el pasado. Para v0.6, la siguiente apertura debe ser posterior a la decisión; un dato tardío no genera una ejecución retrospectiva.
5. **Revisión versionada:** cuando exista un CSV contrastado o una respuesta completa, previsualizar cobertura y cambios. Confirmar solo sobre la versión vigente; conservar históricos, resultados y libros. Una revisión histórica del feed debe pasar por el flujo D3, que pausa su actualización automática.

Para empezar v0.6 basta la referencia sintética. La elección del CSV real y la acreditación anterior continúan pendientes; no se declara esta serie apta para una estrategia automática.
