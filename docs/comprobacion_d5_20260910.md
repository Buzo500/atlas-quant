# D5 en la instalación habitual · 10/09/2026

**Arranque de D5 y recorrido contable correctos en el sobremesa.** Se ha creado una demostración independiente de los datos de NVIDIA y de las carteras anteriores. La valoración del libro v2 sigue pendiente de D6; mostrar saldos no la acredita.

## Arranque y conservación

Antes de iniciar: copia coherente `backups/atlas-20260910T134952170690Z-55207169`, esquema 3. Se conserva también la copia pre-D5 anterior `backups/atlas-20260910T091254560815Z-782be607`.

Arranque habitual mediante `Start-Atlas.ps1`, ejecución `2c84f4b6c35c418dbb47905bead929ec`, iniciada a las 13:50:24 UTC, modo compilado. El lanzador genera además la copia automática `backups/automatic/atlas-20260910T135025474278Z-8388a116`. Salud mediante proxy: `0.4.0-dev.4`, motor conectado, modo local, sin bróker; base migrada **3→4**, integridad `ok`. Las cinco tablas D5 estaban vacías tras migrar, antes de crear la demo.

Comparación contra la copia previa: las dos carteras anteriores, sus cuatro revisiones, seis movimientos antiguos, identidades/alias, tres versiones de datos e historial previo permanecen iguales. Las altas de la demostración añaden filas; no sustituyen las anteriores. Registros de demo, ledger y experimento anterior idénticos. No se importaron movimientos personales ni se modificó el vínculo a NVIDIA.

**Incidencia separada de descarga:** el worker intentó actualizar las dos fuentes Yahoo existentes al arrancar. Ambas devolvieron `Yahoo/yfinance no pudo completar la descarga (OperationalError)`. Solo cambiaron `feed.last_attempt` y `feed.error`; no cambiaron barras, versiones, vínculos ni resultados. NVIDIA conserva las cotizaciones anteriores, hasta 08/09/2026. No se inventaron precios ni se diagnosticó aquí la causa de ese `OperationalError`; requiere comprobación propia antes de dar la actualización diaria por operativa.

Parada de ejecución global activa, OpenAI/Anthropic sin configurar, único experimento anterior completado con proveedor `none`, presupuesto/gasto/reserva cero y `auto_paper=false`. No se inició experimento nuevo, seguimiento ni ensayo de 48 horas. La actualización gratuita configurada de Yahoo es distinta de una llamada a proveedor IA.

## Ejemplo reproducible en la aplicación

Nombre: **Demostración D5 · dividendos y split**, cartera `72a9e51058004702a0ba44f352267aa7`, libro v2, revisión final 5. Cotización ficticia independiente `5d96e69508984e8b921ef885c700e4b6`, nombre «Activo ficticio D5 · sin datos de mercado», sin mercado/identidad acreditados ni precios vinculados. No representa NVIDIA ni otra empresa real.

Fuente/cuenta: `Demostración sintética D5` / `DEMO-D5-20260910`. Evidencia de eventos declarada expresamente como comprobación del guion ficticio, sin evidencia de mercado ni disponibilidad histórica inventadas. Las altas y aplicaciones usan la API local ordinaria con previsualización, revisión y confirmación; no escrituras directas a SQLite. La inspección posterior se hace en la interfaz habitual.

| Fecha / operación | Efectivo EUR | Cantidad | Coste EUR | Derecho pendiente EUR |
|---|---:|---:|---:|---:|
| 05/01: depósito 10.000; compra 100 a 1 EUR | 9.900 | 100 | 100 | 0 |
| 10/01: derecho confirmado 0,50 EUR/título | 9.900 | 100 | 100 | 50 |
| 20/01: cobro bruto 50, retención declarada 9,50 y comisión 0,50 | 9.940 | 100 | 100 | 0 |
| 01/02: split 2:1 | 9.940 | 200 | 100 | 0 |

Aportaciones netas: 10.000 EUR. Cuatro movimientos de libro y tres documentos de aplicación corporativa. El derecho no duplica el ingreso; el split conserva el coste. No se presenta el resultado de ventas de cero como rentabilidad total.

Verificado por API en los cortes 15/01, 20/01 y 01/02. Verificado en navegador: motor conectado, efectivo/cantidad/coste actuales, estados «Cobro conciliado» y «Split aplicado», consulta al 15/01 con 50 EUR pendientes y 9.900 EUR de efectivo. La advertencia «falta una marca posterior con base bruta acreditada» aparece correctamente: el ejemplo no tiene precios para valorar. Revisión visual en panel local; no nueva prueba física de Windows/3440.

Para consultarlo, abrir ATLAS → Datos → Cartera activa → **Demostración D5 · dividendos y split**. En «Dividendos y splits», corte `2026-01-15` muestra el derecho antes de cobrarse; `2026-02-01` muestra ambos eventos aplicados. En Cartera se ven los saldos actuales.

## Estado y evidencia

Al cerrar este trabajo documental se deja ATLAS habitual encendido para consultar la demostración, con ejecución global detenida. Inicio habitual `Abrir-ATLAS.cmd`; parada de motor/interfaz `Detener-ATLAS.cmd`. El ensayo prolongado sigue aplazado. Volver a D4 exige parar y restaurar una copia de esquema 3 junto con fuentes/build D4; no abrir el esquema 4 con D4.

Evidencia local excluida de Git: `output/validation/d5-normal-{before,started}-20260910.json`, `d5-normal-preservation-20260910.json`, `d5-normal-{right,payment,split,cuts}.json` y contexto del ejemplo. Logs del lanzador en `var/logs/launcher-2c84f4b6c35c418dbb47905bead929ec.log`. La comparación distingue cambios de metadatos de Yahoo de modificaciones de cotizaciones/libros; no afirma una base completa idéntica después de arrancar y añadir la demo.
