# Arquitectura y operativa propuestas

Diseño para una persona, acciones y ETF, análisis diario y operativa de baja frecuencia. España y EUR son supuestos pendientes de confirmar. Interactive Brokers es el candidato principal; tener cuenta, permisos y datos suficientes debe comprobarse durante el alta. Esta propuesta no acredita un sistema listo para operar.

## Arquitectura y concurrencia

Monolito modular Python con API FastAPI, interfaz React/TypeScript y un único servicio local. Separar módulos de instrumentos, datos, contabilidad, análisis, investigación, riesgo, órdenes, conectores y auditoría. Los cálculos financieros serán funciones independientes de la interfaz y del bróker. Un trabajador de cálculo ejecutará tareas pesadas sobre instantáneas inmutables; no recibirá credenciales ni autorización de ejecución.

SQLite almacenará cuentas, movimientos, órdenes, mandatos, trabajos y auditoría. Un coordinador serializará escrituras y decisiones de ejecución, con transacciones breves, restricciones únicas y control de versión. Activar WAL, claves foráneas y sincronización duradera para el registro operativo; comprobar su funcionamiento. WAL permite lectores junto al escritor, pero mantiene un escritor simultáneo y requiere almacenamiento local adecuado. [SQLite: WAL](https://www.sqlite.org/wal.html).

Parquet conservará históricos y revisiones; DuckDB consultará esos archivos, preferentemente con conexiones independientes en memoria. No será otra fuente de verdad para dinero u órdenes. Su modalidad integrada tiene restricciones de concurrencia entre procesos; aquí no hace falta introducir un servidor analítico. [DuckDB: concurrencia](https://duckdb.org/docs/current/connect/concurrency).

El adaptador IBKR utilizará la API Python oficial mediante TWS o IB Gateway. El dominio verá operaciones como resolver instrumento, consultar cuenta, enviar, cancelar y reconciliar. La API TWS se conecta por socket a esas aplicaciones; una conexión abierta no basta para declarar lista la cuenta. [IBKR: TWS API](https://www.interactivebrokers.com/docs/tws-api/doc/introduction).

## Contratos mínimos

| Entidad | Campos y reglas esenciales |
|---|---|
| Instrumento/cotización | ID interno estable, ISIN cuando exista, ticker con vigencia, mercado, divisa, calendario, identificador del bróker. Separar instrumento de sus distintas cotizaciones. |
| Observación | Instrumento, valor, unidad, divisa, instante económico, publicación conocida, recepción, proveedor, revisión y calidad. Un histórico retrospectivo no garantiza conocimiento disponible entonces. |
| Precio | OHLCV o bid/ask, sesión, zona horaria, ajuste aplicado y condición real/retrasado/congelado/estimado. Precios ajustados no se envían al bróker. |
| Movimiento | Cuenta, tipo, fecha operación/liquidación, cantidad, importe, divisa, comisión, retención, referencia externa y corrección vinculada. |
| Orden | ID local, cuenta y entorno, instrumento, lado, cantidad, límite, vigencia, política aprobada, identificadores del bróker, versión y estado. |
| Ejecución | ID externo único dentro de su ámbito, orden, cantidad, precio, instante y comisiones; admite correcciones identificadas. |
| Resultado | Datos y código utilizados, parámetros, semillas, convenciones, advertencias y manifiesto de reproducción. |

Usar decimales para dinero y cantidades; serializarlos como cadenas. Reservar coma flotante para estadística con tolerancias explícitas. El libro de movimientos es persistente; posiciones y saldos son vistas reconstruibles, contrastadas con el bróker. Diferenciar efectivo liquidado, pendiente y disponible para operar. Las correcciones añaden registros trazables.

## Contrato de API

Todas las rutas irán bajo `/api/v1`. Consultas de cartera, riesgo y precios devolverán fecha de referencia, procedencia y advertencias. Importaciones y backtests devolverán `202` con identificador de trabajo y progreso persistente.

`POST /orders/preview` calculará costes estimados, exposición y bloqueos. `POST /orders` recibirá intención y autorización manual o mandato automatizado vigente. Exigirá `Idempotency-Key`; repetir clave y contenido devuelve la misma orden, mientras que cambiar el contenido produce conflicto. `POST /orders/{id}/cancel`, `/reconciliation` y `/execution/halt` serán comandos auditados. Ningún GET modificará posiciones ni enviará órdenes.

## Estados y prevención de duplicados

Flujo local: `DRAFT → VALIDATED → AUTHORIZED → QUEUED → SUBMITTING`. Después pueden observarse `ACKNOWLEDGED`, `PARTIALLY_FILLED`, `FILLED`, `REJECTED`, `CANCEL_PENDING`, `CANCELLED` o `EXPIRED`. Preservar también el estado original del bróker y una condición independiente de certeza: `CONFIRMED` o `UNKNOWN`.

Antes del envío, guardar atómicamente intención, evaluación de riesgo y comando pendiente. Mantener un único emisor activo por cuenta y una asignación persistente de identificadores compatible con IBKR. Tras un timeout no generar otra identidad ni reenviar ciegamente: marcar incertidumbre y consultar órdenes abiertas, completadas y ejecuciones. La base local y el bróker no comparten transacción; no se promete ejecución exactamente una vez.

Procesar eventos repetidos sin contabilizarlos de nuevo y tolerar llegada desordenada. Los informes de ejecución determinan cantidades operadas; una cancelación puede afectar solo al remanente. IBKR especifica que pueden llegar ejecuciones mientras la cancelación está pendiente. [IBKR: estados de órdenes](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/order-status/understanding-order-status-message).

## Riesgo y automatización

La primera automatización será aportación/rebalanceo mediante mandatos versionados: universo permitido, calendario, presupuesto, pesos objetivo, bandas, máximo por orden y día, vigencia y reglas de suspensión. Empezar con efectivo, posiciones largas y órdenes limitadas en sesión regular. Un mandato no se modifica durante una ejecución.

Antes de cada envío, recalcular efectivo, posiciones y órdenes pendientes. Reservar recursos para compras abiertas sin presuponer ventas futuras; comprobar divisa, permisos, incremento de precio/cantidad, concentración y antigüedad de datos. Los límites de ETF diversificados y acciones individuales deben poder diferir. El presupuesto disponible es el mínimo entre política local y restricciones de cuenta aplicables.

El precio diario sirve para análisis; la ejecución automática requiere una referencia aceptable según la política del instrumento. Una cotización ausente o insuficiente bloquea el envío. Si cambia el estado desde la previsualización, repetir validaciones.

## Parada, seguridad y recuperación

La parada persistirá un bloqueo de nuevos envíos y solicitará cancelar órdenes abiertas gestionadas por la aplicación. Mostrará cuántas cancelaciones están confirmadas, pendientes o son desconocidas. No liquida automáticamente ni revierte operaciones ejecutadas. Existe una carrera inevitable con solicitudes ya enviadas; resolverla exige reconciliación. Si la aplicación falla, el usuario debe poder intervenir directamente en el bróker.

Separar físicamente bases, configuración y credenciales de simulación y real. Escuchar solo en loopback; exigir sesión autenticada y proteger comandos frente a solicitudes de otros orígenes. Guardar secretos en el almacén del sistema, aplicar mínimos permisos y excluirlos de logs y repositorio. Una máquina comprometida sigue siendo un riesgo. [OWASP: gestión de secretos](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html).

Después de reiniciar, iniciar bloqueado, recuperar registros y reconciliar cuenta completa, incluidas operaciones manuales externas. No reanudar hasta explicar discrepancias. Crear copias consistentes mediante la API de respaldo y verificar restauraciones; copiar únicamente un archivo SQLite activo puede ser insuficiente. [SQLite: respaldo](https://www.sqlite.org/backup.html).

Antes de dinero real, probar caídas antes/después de enviar, doble clic, ejecuciones parciales, cancelación concurrente, disco lleno, datos obsoletos y reinicio durante rebalanceo. La aprobación exige evidencia de esos escenarios, cuentas conciliadas y un ensayo de recuperación; una demostración visual o unos días rentables no bastan.
