# D6 completo: libro multidivisa y patrimonio trazable

10/09/2026. Implementación `0.4.0-dev.5`, esquema 5, PR #8. La autorización posterior de las diez tareas amplía D6.1/D6.2 a D6.3–D6.6. Esta es una entrega de desarrollo; D7 y D8 continúan después. El ensayo de 48 horas permanece aplazado.

## Uso

En **Datos → Precios y tipos de cambio**, importar CSV propio de precios EUR/USD o FX expresado en EUR por USD. Seleccionar la cotización del catálogo, identificar la fuente y declarar solo la evidencia que se pueda acreditar. Las plantillas indican columnas, moneda y disponibilidad. Previsualizar y confirmar son acciones distintas. Una revisión histórica exige motivo; las versiones anteriores se conservan. Los gráficos reutilizan los controles existentes.

Vincular explícitamente la versión de precios a la cotización y la versión FX a la cartera. El libro muestra saldos y posiciones por moneda, conversiones, conciliación y eventos corporativos con los mismos controles de D4/D5. No hay conversión implícita del efectivo ni financiación entre monedas.

En **Cartera → Patrimonio en EUR**, elegir fecha y calcular. Revisar efectivo, posiciones, derechos pendientes, precio/FX aplicado y motivos de calidad. Guardar conserva un corte inmutable: un cambio posterior de libro, fuente o evidencia lo identifica como histórico, sin sobrescribir sus cifras. Los importes nulos no se convierten en cero y el subtotal conocido no se presenta como patrimonio completo.

## Contratos y límites

Se añaden `/api/v2/market`, importaciones `/market/{prices|fx}/imports`, lectura `/market/{prices|fx}/{id}/versions/{version}`, vínculos `/portfolios/{id}/fx-binding` y cortes `/portfolios/{id}/valuations`. Consultar OpenAPI para las rutas exactas de plantillas e historial. Magnitudes económicas como textos decimales, respuestas tipadas y contratos TypeScript generados. Las escrituras requieren guardia local, previsualización y contexto vigente; publicación y auditoría son atómicas.

Precios: una cotización/moneda por serie, OHLC exacto con hasta 12 decimales. FX: USD→EUR, hasta 18 decimales, sin inversión automática. Máximo 100.000 observaciones por serie y 8 millones de caracteres CSV. Disponibilidad desconocida permanece desconocida. Revisar historia crea versión, no reescribe resultados. La identidad nativa no puede ser ocupada por el importador legado y las series nativas no habilitan investigación/paper USD.

NAV: efectivo + posiciones a precio bruto acreditado + derechos pendientes, convertido a EUR con la versión FX elegida. Selección de última marca no posterior al corte. Calendario acreditado con cobertura y última sesión correcta permite cierre completo; sin esa evidencia, marca de hasta 7 días provisional y más antigua incompleta. Base incompatible, evento sin resolver o marca ausente bloquean el total. Disponibilidad para una decisión histórica se informa aparte de la reconstrucción contable. Redondeo del total una sola vez a céntimos, Decimal 64/HALF_EVEN; diferencia frente a filas redondeadas explícita. Falta de FX de una aportación antigua no invalida automáticamente el NAV actual.

Lecturas pesadas usan una instantánea SQLite WAL de solo lectura. Antes de guardar se comprueban referencias a revisiones inmutables en una transacción breve; no se reescribe un estado anterior después de una espera. El motor, políticas legacy, datos habituales y esquema 5 se conservan. D5 requiere restaurar su copia compatible para retroceder.

## Evidencia local

Navegador: 19/19 recorridos en `e2e-72c2b7425cbb4fa083222032ef47fa2a`, incluidos CSV USD/FX, vínculos, NAV 986,10 EUR y guardado. Capturas revisadas a 390/1280/3440 píxeles CSS; no representa una nueva prueba física de escala Windows. Base habitual intacta, integridad correcta y puertos liberados. Suite y CI definitivas se registran en continuidad.

Benchmark reproducible `tools/benchmarks/benchmark_d6_valuation.py`: 10 cotizaciones, 100.000 barras, 10.000 observaciones FX y 10.000 movimientos sintéticos. Windows, Python 3.14.4, este sobremesa. Cinco cálculos más serialización tras calentamiento: 0,694–0,729 s; pico de asignaciones Python medido con tracemalloc: 143,26 MiB. Veinte controles de aplicación con otro Store durante valoración: p95 0,0649 s. Estos controles miden la frontera de servicios, no la latencia HTTP del proxy. Copia y restauración del corte exactas. Informe `var/validation/d6-benchmark-ea7147756cc34a959d8d4e2f879661c1/report.json`. La primera medición detectó 326,82 MiB y p95 1,96 s; la separación de lectura y verificación corrigió esos límites.

## Yahoo y API

La caché Yahoo permanece en datos ATLAS. En Windows se compone un bundle local con certifi y certificados públicos ya confiados para servidor por Windows; se respeta una ruta CA configurada explícitamente. No se desactiva TLS, instala confianza ni lee claves privadas. Pruebas sin red verifican selección y escritura atómica. Una sonda pública con esa confianza superó TLS y recibió HTTP 429: la descarga real continúa sin validarse y no se insiste ante el límite.

La espera original de API se reprodujo antes de la entrada ASGI; [evidencia y límites](diagnostico_api_20260910.md). La suite posterior correcta no acredita que esté reparada. No se han aumentado tiempos ni añadido reintentos de escrituras. Sin claves, gasto API, datos personales ni conexión a bróker.
