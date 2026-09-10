# D6.1 y D6.2 · contratos y libro EUR/USD

**Actualización posterior:** las diez tareas autorizadas amplían este trabajo a D6 completo. Este documento conserva la evidencia inicial D6.1/D6.2; consultar [D6.3–D6.6, uso y cierre](v0_4_d6_cierre.md) y [continuidad](CONTINUIDAD.md) para el estado vigente.

10/09/2026. Desarrollo local `codex/v0.4-d6`, **`0.4.0-dev.5`, esquema 5**. El usuario autoriza las cinco tareas posteriores al plan: diagnóstico de Yahoo, sonda dirigida de API, publicar la documentación anterior e implementar D6.1 y D6.2. El plan anterior se publicó en `master` mediante `8f33625`; este código no está publicado ni ha pasado una nueva CI remota.

## Disponible y pendiente

El mismo cálculo contable reconstruye efectivo, aportaciones y resultado realizado por moneda, y posiciones/coste en la moneda de cotización. EUR no financia automáticamente una compra USD. El CSV permite conversiones explícitas en ambos sentidos con importes efectivos y comisión en una de las dos monedas. Ambas piernas y la comisión se confirman juntas, con saldos no negativos por moneda.

Dividendos y splits USD conservan los límites D5: derecho separado, un pago completo, retenciones/comisiones en la moneda del pago, evidencia y versión explícitas, sin doble abono, split exacto y coste nativo conservado. La revisión de movimientos valida también las operaciones posteriores y sus aplicaciones corporativas. La conciliación exige efectivo de cada moneda utilizada, incluso con saldo cero; no suma EUR y USD.

**Todavía no hay formularios multidivisa ni patrimonio EUR nuevo.** La interfaz actual continúa usando el contrato EUR; un libro con USD devuelve un rechazo explícito a ese cliente. Para probar D6.2 debe usarse la API `/api/v2` con una cartera de demostración separada. D6.3 añadirá precios USD y series FX; D6.4, NAV; D6.5, interfaz. Las cuatro tablas nuevas de FX/cortes están vacías tras migrar: no representan casos de uso disponibles. Backtests/paper USD, TWR/XIRR, conexión al bróker, D7/D8, movimientos personales y ensayo de 48 horas siguen pendientes.

## Contratos disponibles

Las rutas siguientes comparten servicios, transacciones, límites, guardia local de escritura y auditoría con D4/D5. No hay un segundo motor ni escritor.

| Ruta | Operación |
|---|---|
| `GET /api/v2/portfolios/{id}/book` | Saldo nativo y movimientos paginados; admite fecha y revisión histórica. |
| `POST /api/v2/portfolios/{id}/imports` | CSV `atlas-ledger-v2`, previsualización y confirmación. |
| `POST /api/v2/portfolios/{id}/reconciliations` | Extracto completo `atlas-statement-v2`, diferencia por moneda/cotización. |
| `POST /api/v2/portfolios/{id}/corrections` | Sustituir/anular sin borrar historial y revisar dependencias. |
| `GET /api/v2/portfolios/{id}/book-documents[/{document_id}]` | Resumen paginado y documento de la revisión. |
| `GET /api/v2/corporate-events[/{id}/versions/{revision}]` | Catálogo EUR/USD y versión de evento. |
| `POST /api/v2/corporate-events/imports`, `/revisions` | Importación y revisión del evento con previsualización. |
| `GET/POST /api/v2/portfolios/{id}/corporate-actions` | Derechos, pagos, splits y su aplicación revisada. |
| `GET /api/v2/portfolios/{id}/corporate-documents[/{document_id}]` | Evidencia y contexto de aplicaciones. |

Solicitudes POST: formatos de entrada D4/D5 y cabecera local `X-Atlas-Client: local-v1`; siguen requiriendo los controles de origen. Se obtiene primero `preview_token` sin escribir, después se reenvía la misma entrada con `commit=true` y ese token. Contexto cambiado → 409; entrada o moneda incompatible → 422; escritura sin guardia → 403. No confirmar automáticamente una nueva previsualización tras un conflicto.

`NativeBalance` devuelve `as_of_date`, `balances: [{currency, cash, net_contributions, realized_pnl}]`, `positions: [{listing_id, currency, quantity, cost_basis}]` y `warnings`. Todas las magnitudes económicas son textos decimales. `pending_receivables_by_currency` contiene pares `{currency, amount}`. No existe un `cash` ni un derecho pendiente escalar que mezcle monedas. No se calcula ganancia por conversión FX sin una política de valoración: `realized_pnl` sigue siendo resultado de ventas en la moneda de la cotización.

Los contratos EUR anteriores conservan forma e importes para carteras/documentos EUR. El catálogo corporativo antiguo lista solo eventos EUR y mantiene la revisión global para detectar conflictos. El acceso EUR a un corte/documento con USD se rechaza, incluso si USD solo aparece en el extracto y está a cero; no oculta ese saldo ni lo rotula EUR. `legacy-eur-v1` mantiene su política y solo admite conciliación EUR, también mediante el adaptador nuevo.

## CSV de conversión

Se mantienen las 18 columnas de `atlas-ledger-v2`. Ejemplo sintético; no representa operaciones del usuario:

```csv
external_id,date,day_sequence,kind,listing_ref,quantity,unit_price,gross_amount,currency,fee_amount,fee_currency,tax_amount,tax_currency,fx_to_amount,fx_to_currency,ratio_numerator,ratio_denominator,corporate_event_ref
demo-deposit,2026-01-05,1,deposit,,,,1000.00,EUR,0.00,EUR,0.00,EUR,,,,,
demo-exchange,2026-01-05,2,fx_exchange,,,,400.00,EUR,2.00,EUR,,,440.00,USD,,,
```

Resultado: 598,00 EUR y 440,00 USD; aportaciones 1.000,00 EUR y 0,00 USD. Si la comisión se declara USD: 600,00 EUR y 438,00 USD. `gross_amount/currency` es lo entregado; `fx_to_amount/fx_to_currency`, lo recibido. La serie FX de valoración no determina ninguno de esos importes.

La conversión requiere monedas distintas EUR/USD, ambos importes positivos y comisión explícita a 2 decimales. Cotización, cantidad, precio, retención, ratio y evento deben estar vacíos. Los movimientos ordinarios mantienen comisión/retención en la misma moneda del movimiento; un cargo independiente en otra moneda se registra como `fee`. Precisión interna Decimal 64/HALF_EVEN, coste repartido a 12 decimales y residuo absorbido por la última venta.

## Migración y recuperación

Antes de editar se detuvo ATLAS y se guardó la copia de esquema 4 `backups/atlas-20260910T142414461441Z-bc5cf98f`. Esquema 5 añade `fx_series`, `fx_versions`, `portfolio_fx_versions` y `valuation_cuts`, con claves/referencias y validación de estructura. No reescribe libros, IDs, resultados, políticas ni documentos anteriores.

```powershell
.\.venv\Scripts\python.exe tools/check_d6_migration.py backups/atlas-20260910T142414461441Z-bc5cf98f
```

Comprobación sobre copias aisladas correcta: tablas antiguas idénticas, libros EUR y adaptados idénticos antes/después, aplicaciones D5 conservadas, tablas nuevas vacías, reapertura idempotente, copia/restauración e integridad correctas. Informe `var/validation/d6-migration-a7cd99985eed4a4e9f4703c67026dca5/report.json`; la copia de entrada permanece intacta. Restaurar pausa las fuentes y activa la parada global.

**D5 rechaza esquema 5.** Para retroceder, detener ATLAS y recuperar una copia de esquema 4 con fuentes y compilación `v0.4.0-dev.4`. No rebajar manualmente `user_version` ni abrir la base nueva con código antiguo. Las operaciones registradas después de aquella copia no estarán en ella.

## Verificación

Pruebas permanentes en `backend/tests/test_multicurrency_d6.py`: ejemplos numéricos independientes, compras/ventas con residuo, monedas y campos inválidos, insuficiencia en cualquiera de las piernas, conciliación completa, adaptador heredado, corrección dependiente, rollback antes de auditoría, doble confirmación concurrente, dividendos/splits USD, contratos HTTP y migración. Se amplían las fixtures de migraciones anteriores para representar sus esquemas reales.

Resultado local: **650 Python + 91 subtests, 266 frontend y 18 E2E correctos**, tipos/lint, contratos regenerados y `--check`, compilación con manifiesto. Sonda final: 3/3 D5 correctos. ATLAS habitual vuelve a estar arrancado en esquema 5; tres carteras y sus libros/contextos EUR conservados, parada global activa y gasto/reserva IA cero. Evidencia y límites en [continuidad](CONTINUIDAD.md). Las referencias de NAV/temporalidad del [plan D6](v0_4_d6.md) todavía son criterios de D6.3/D6.4, no capacidades validadas por estas pruebas del libro.

## Yahoo y API

Se reprodujo `OperationalError` al abrir la caché SQLite predeterminada de yfinance en AppData. Ahora se configura una sola vez por proceso dentro de `ATLAS_DATA_DIR/cache/yfinance`, antes de crear el primer Ticker, siguiendo la [configuración oficial de caché](https://ranaroussi.github.io/yfinance/advanced/caching.html). La apertura y la regresión local pasan.

La descarga real sigue sin quedar validada: después de corregir la caché aparece un fallo de cadena TLS, también fuera del sandbox. Una comprobación separada con certificados públicos de confianza del sistema y certifi mantuvo verificación TLS y recibió HTTP 429 de Yahoo. No se añadió esa configuración experimental a la aplicación, no se desactivó TLS y no se insistió tras el límite. Los precios anteriores se conservan; no afirmar que Yahoo ya actualiza correctamente.

La sonda optativa de API se amplía a aborto del cliente y consumo/cancelación de cuerpo. Sigue limitada a bases E2E aisladas, sin contenidos ni secretos, sin leer por adelantado y sin cambiar plazos/reintentos de la aplicación. [Resultados y límites de la captura](diagnostico_api_20260910.md). La espera original de diez segundos continúa abierta.
