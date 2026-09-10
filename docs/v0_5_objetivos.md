# v0.5.0-dev.1 · Objetivos manuales y diagnóstico

Primera entrega autorizada de v0.5. Monolito modular, esquema SQLite 5 y libro contable v2 de v0.4 conservados. No es una versión estable. Estado de publicación y operación en [continuidad](CONTINUIDAD.md).

Publicada en PR #10, squash `e23f79f`, etiqueta `v0.5.0-dev.1`. La ampliación posterior de propuestas, agregación, referencia y escenarios se documenta aparte en [v0_5_planificacion.md](v0_5_planificacion.md); los límites «sin propuestas» de esta guía describen exclusivamente dev.1.

## Uso

1. En **Cartera**, selecciona una cartera nativa v2. En **Patrimonio en EUR**, calcula una fecha de cierre y guarda el corte tras revisar sus fuentes y calidad.
2. Abre **Objetivos y desviaciones → Consultar y editar objetivos**. Crea un borrador con nombre, porcentajes por instrumento y efectivo, bandas mínimas/máximas y límite de concentración. Todas las entradas son manuales; la suma objetivo debe ser exactamente 100 %.
3. Revisa y guarda el borrador. En **Versiones y activación**, revisa la versión y confirma su activación. Guardar un borrador por sí solo no lo activa. Puedes copiar los objetivos activos a un borrador nuevo.
4. Selecciona el corte guardado y calcula las desviaciones. Un exceso aparece positivo; un déficit, negativo. Revisa los avisos de banda/concentración y después guarda el diagnóstico.
5. Consulta los diagnósticos guardados. Si cambian el libro, las fuentes, el catálogo, los eventos o los objetivos activos, conservan sus cifras originales y se muestran como históricos. Para un diagnóstico nuevo hace falta un corte vigente.

No se calcula una propuesta de compras, cantidades, conversiones ni envíos. Los importes son diferencias frente a tus objetivos, no recomendaciones de asignación.

## Convenciones

- Una fila por instrumento, agregando sus cotizaciones EUR/USD y sus derechos pendientes de dividendos. Efectivo agregado con desglose nativo y EUR. Los derechos no son efectivo disponible.
- Porcentajes entre 0 y 100 con hasta seis decimales. Mínimo ≤ objetivo ≤ máximo ≤ límite de concentración. Se rechazan duplicados, instrumentos inexistentes, límites incompatibles y sumas inexactas.
- Denominador: patrimonio exacto del corte, antes de redondear. Desviación EUR = valor actual − patrimonio × peso objetivo / 100. La interfaz redondea la presentación; el resultado decimal completo permanece guardado.
- Incompleto o patrimonio no positivo: sin pesos globales ni desviaciones; no se omiten faltantes ni se renormaliza el resto. Provisional: escenario provisional. La acreditación de disponibilidad histórica se consulta en el corte.
- Instrumentos mantenidos sin objetivo: aparecen con objetivo cero y aviso «Sin objetivo definido». No se inventa un límite para ellos.
- Recursos comprometidos: no disponibles, porque no existe OMS. No se crean reservas ficticias.

## Diseño y contratos

`targets.py` calcula exclusivamente sobre un corte D6 guardado. `limits` es pura y no tiene autoridad de ejecución. `targets_service.py` lee una instantánea coherente, calcula fuera de la escritura, compara revisiones y publica con auditoría atómica. Comparte el límite de cálculos pesados. No hay otro reductor contable ni instantáneas viejas escritas tras un `await`.

El almacén usa registros analíticos nuevos: `target_set`, `targets_head`, `target_report` y `target_report_summary`. La clave primaria identifica un único estado por cartera; la transacción compara su revisión antes de activarlo. Borradores e informes inmutables, historial paginado. El libro y sus políticas no cambian, por lo que se conserva esquema 5. El código anterior ignora estos registros y sus cambios contables invalidan la vigencia al volver a v0.5.

API bajo `/api/v2/portfolios/{id}`: `targets` (historial y borrador), `targets/activate` (revisión/activación), `target-reports` (historial y cálculo/guardado), `target-reports/{report_id}` (consulta). Mutaciones requieren el mismo control local y previsualización que los servicios anteriores; confirmaciones obsoletas devuelven 409 y no se reintentan automáticamente. Tipos TypeScript generados desde OpenAPI.

## Validación local

- 739 pruebas Python y 91 subcasos; 29 pruebas específicas nuevas. Aritmética independiente 60/20/20 frente a 50/30/20, dos cotizaciones por instrumento, USD/FX, derechos, patrimonio incompleto/no positivo, conflictos concurrentes, auditoría y restauración exacta. `output/validation/v05-python-delivery.log`.
- 283 pruebas frontend; cinco nuevas sobre borrador, edición, cancelación de revisiones, activación explícita y conservación ante sondeos. `output/validation/v05-ui-full.log`.
- Carga con 100.000 barras, 10.000 movimientos y 200 objetivos: máximo 0,210 s, pico adicional Python 3,19 MiB. Controles ASGI p95 0,0043 s, sin incluir navegador/proxy. `var/validation/v05-load-8dd37ed969ce48fe87a7c38d4f3afb3e/report.json`.
- Recorrido de navegador EUR/USD desde CSV hasta informe por fechas, objetivos y recuperación del diagnóstico, con capturas 390/1280/3440. 19/19 recorridos completos; editor y diagnóstico revisados en los tres anchos. Ocho pruebas Node de transporte y 40 respuestas reales de Uvicorn de 2,1 MB. El cierre remoto se registra en continuidad; no equivale a aceptación física nueva de la escala de Windows.

Yahoo devolvió 429 en la comprobación del 10/09 a las 18:01:53 UTC con TLS verificado. La actualización real sigue condicionada al proveedor. Ensayo de 48 horas, movimientos personales, bróker y presupuesto pagado siguen aplazados.

## Cierre remoto y operación

[PR #10](https://github.com/Buzo500/atlas-quant/pull/10) lista para revisión. [CI gratuita 34517010948](https://github.com/Buzo500/atlas-quant/actions/runs/34517010948) correcta sobre `1992eb5442dbed8e1abb33846901271114884e91`, con los mismos recuentos locales y 19 E2E en 3,2 min. Instalación, arranque/proxy y parada correctos; 0 USD facturables. Documentación de cierre posterior sin cambios de código; sin fusión ni etiqueta nueva.

ATLAS habitual arrancado en Windows con esta entrega. Tres carteras, libros e históricos iguales a la copia previa; esquema 5/integridad correctos, parada global activa y gasto cero. No se han añadido operaciones, objetivos o fuentes ficticias a las carteras habituales. Para iniciar, `Abrir-ATLAS.cmd`; para detener, `Detener-ATLAS.cmd`.
