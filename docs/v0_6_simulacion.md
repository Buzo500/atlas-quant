# v0.6 · Simulación económica EUR

Ampliación posterior: [Laboratorio temporal 0.6.0-dev.1](v0_6_laboratorio.md)
integra este motor con CSV nativo, HTTP, interfaz, informes persistidos y
benchmarks. El alcance sin API/UI de este documento describe el bloque original.

11/09/2026. «Ahora no puedo usar el portátil, sigue desarrollando lo siguiente» autoriza continuar el bloque siguiente del laboratorio. La revisión manual de v0.5 queda pendiente con sus comprobaciones ya recibidas conservadas; no se fusiona ni etiqueta por este aplazamiento.

## Alcance y criterios del bloque

Simulador offline de un instrumento EUR, utilizable desde Python/CLI, con el evaluador SMA compartido y el reductor `NativeBook` existente. Cuenta ficticia aislada: capital inicial, fracción del patrimonio asignada a la estrategia, límite de exposición, lote, comisión fija más proporcional y deslizamiento explícitos. Sin conexión a las carteras habituales, API nueva, UI, proveedor, bróker ni gasto. Las políticas y los resultados legacy se conservan.

- Las observaciones incluyen reloj y disponibilidad. Solo se simula en la siguiente apertura exacta declarada; una apertura ausente/tardía o una intención expirada no se recuperan con un precio posterior. No se deduce una secuencia intradía de OHLC.
- El objetivo lógico del evaluador se distingue de la cantidad efectivamente simulada. Una compra rechazada no se reintenta en las siguientes sesiones sin otra intención.
- La fracción asignada se mide sobre el patrimonio posterior a costes, valorando la posición al precio de apertura sin deslizamiento. Un objetivo superior al límite configurado se rechaza; no se rebaja silenciosamente. Son límites de esta cuenta ficticia, no controles de una cuenta externa ni reservas OMS.
- Cantidades en múltiplos enteros del lote; precios de ejecución con doce decimales y redondeo adverso; bruto liquidado a céntimos con HALF_EVEN, comisión fija + puntos básicos redondeada hacia arriba a céntimos. El informe separa comisión, deslizamiento y ajuste de liquidación. Sin cortos ni efectivo negativo, tampoco al vender con comisiones altas.
- Las operaciones se validan sobre una copia del reductor y se publican juntas con el consumo de la intención en el estado en memoria. No hay commit SQLite ni garantía de entrega a un bróker. Guardar un checkpoint conserva evidencia para reconstruir el ensayo offline.
- Un dato inválido no se rellena para valorar. La exposición se revisa con cada precio utilizable; los excesos posteriores se informan sin inventar una venta. Eventos corporativos conservan el bloqueo del evaluador.
- Replay e incremental usan el mismo coordinador. Checkpoints ligados a especificación, costes y eventos reconstruyen el libro con el mismo reductor, rechazando corrupción o cambios de contexto. El checksum no autentica datos hostiles.

Criterios: caso EUR calculado a mano, lotes y redondeos contrastados con un oráculo independiente, efectivo/posiciones/P&L conciliados con `NativeBook`, duplicados/conflictos sin doble efecto, ausencia de anticipación, caducidad, bloqueos, paridad con recuperación y límites de recursos. Referencia CLI reproducible con entradas completas y huellas; regresión Python y comprobación de la base habitual antes del arranque final.

Adaptador de datasets reales y contraste externo de su evidencia, persistencia/API/UI del laboratorio, protocolo temporal y registro de candidatas siguen pendientes. Los precios de referencia son ficticios y no acreditan disponibilidad histórica de un proveedor. Ensayo de 48 horas, movimientos personales, IA de pago, McClellan, móvil/remoto y LaTeX siguen aplazados.

## Implementación y uso

`simulation_contracts.py` contiene las hipótesis económicas estrictas. `strategy_simulation.py` aporta `SmaSimulation.process`, `simulate` y `restore_simulation`: el recorrido incremental y el replay comparten código. Se reutilizan `evaluate`/`opening_eligibility` y `NativeBook`, sin sustituir el Laboratorio anterior. Las funciones reciben especificación y observaciones validadas; no certifican la huella de un dataset real ni aceptan una fuente de proveedor automáticamente.

Límites: EUR, un instrumento, capital/lote/cantidad de hasta 10¹², comisiones y deslizamiento hasta 1.000 puntos básicos, pesos entre 0 y 1 (asignación positiva), 40.000 eventos y checkpoint de 32 MB. El libro conserva su límite monetario de 10¹⁸. La entrada se calcula por búsqueda de lotes frente al bruto/comisión realmente redondeados. La salida vende la posición íntegra o se rechaza si su comisión dejaría efectivo negativo. No hay intereses, dividendos, fiscalidad, impacto, parciales, liquidación diferida ni rebalanceo continuo.

Los informes incluyen fecha del reloj económico y del precio utilizado. Un cierre recibido tarde no sustituye una apertura más reciente ni fecha los saldos en el pasado. Si hay posición y el precio actual es desconocido, NAV es `null`, no cero. La exposición posterior puede superar el límite por movimiento del precio: queda registrada, sin una venta automática que la regla no ha emitido.

Referencia reproducible, con ATLAS detenido o arrancado; no usa su base:

```powershell
.\.venv\Scripts\python.exe tools\run_sma_simulation.py --output output\validation\mi-simulacion-sma.json
.\.venv\Scripts\python.exe tools\run_sma_simulation.py --reproduce output\validation\mi-simulacion-sma.json
```

El archivo de salida debe ser nuevo; la herramienta rechaza sobrescribirlo. Sin `--output` imprime el resumen. Se incluyen especificación, hipótesis, observaciones, libro, decisiones, resultados y huellas del código. `--reproduce` comprueba la huella y reconstruye los eventos; no confía en un saldo final editado. Los checkpoints son evidencia local para replay, no autorizaciones de ejecución ni documentos autenticados.

Referencia ficticia SMA20/50: 50 cierres a 100, luego 110, 90 y 80; entrada y salida en las siguientes aperturas declaradas a 100 y 80. Capital 1.000 EUR, lote 1, comisión fija 1 EUR, sin comisión proporcional ni deslizamiento. Compra 9 unidades, quedan 99 EUR; venta de 9 por 720 EUR menos 1 EUR. **Saldo final 818 EUR, P&L realizado −182 EUR, posición cero.** La última apertura permite completar la salida sin inventar otro cierre. Es un caso de contabilidad, no una estrategia rentable.

## Evidencia de cierre local

48 casos nuevos, más 53 del evaluador: **101 pruebas específicas correctas**. Regresión **909 Python y 91 subcasos**, 84,95 s; dos avisos de deprecación previos. Incluye oráculo exhaustivo independiente de lotes, conservación monetaria con costes/redondeo, comisión de salida insolvente, exceso de exposición, datos tardíos, atomicidad ante fallo del libro, duplicados/conflictos, recuperación en cada evento y CLI sin sobrescritura. El primer intento del test CLI no pudo crear el temporal predeterminado de pytest por permisos de Windows; repetición correcta con un `--basetemp` nuevo dentro del proyecto, sin cambiar la prueba para eludir el fallo.

Contratos OpenAPI/TypeScript y manifiesto de interfaz comprobados. No hay cambio HTTP/frontend/esquema ni una nueva etiqueta de aplicación: sigue identificada como dev.3. Esta validación es local y posterior a la CI de v0.5; no equivale a una CI remota del bloque v0.6.

Evidencia local: `output/validation/v06-economics-python.log`, `v06-sma-economics-reference.json` (generado y reproducido), `v06-economics-data-pre.json` y `v06-economics-data-online.json`. Copia previa `backups/atlas-20260911T094306917891Z-6b217137`; todas las tablas iguales a la copia tras las pruebas y tras el reinicio, integridad `ok`, esquema 5 y tres carteras intactas. Arranque dev.3 del sobremesa correcto, salud directa/proxy e interfaz HTTP comprobadas; parada global activa. Rama solo local; detalle operativo en continuidad. No se repite ni se atribuye una nueva comprobación del portátil.
