# v0.5 · Primer alcance propuesto: objetivos y diagnóstico de desviaciones

10/09/2026. **Implementación autorizada posteriormente por «Vale, haz esas 5 tareas»**, junto con fiabilidad del transporte, comprobación Yahoo y recorrido EUR/USD. La versión completa conserva análisis, benchmarks, escenarios, agregación y propuestas; esta primera entrega se limita a objetivos y diagnóstico.

## Resultado visible

Sobre una cartera v2 y un corte EUR identificado, guardar una distribución objetivo manual por instrumento y efectivo; mostrar peso actual, peso objetivo, banda y diferencia en EUR. Ejemplo sintético: patrimonio 10.000 EUR, objetivo activo A 50 %, activo B 30 % y efectivo 20 %; actuales 60/20/20 → desviaciones +1.000/−1.000/0 EUR. Mostrar una explicación de concentración y del contexto de precios/FX utilizado.

**Primera entrega recomendada:** objetivos, bandas y diagnóstico, sin lista de órdenes o cantidades de compra. Permite comprobar contratos y riesgo antes de añadir el plan de aportación/rebalanceo en otra subentrega de v0.5.

## Límites y decisiones concretas

- Una cartera por evaluación; moneda base EUR y exposición EUR/USD de v0.4. Pesos por instrumento, sin duplicar sus distintas cotizaciones. Efectivo agregado con desglose por moneda; su peso no autoriza conversiones.
- Pesos no negativos y suma exacta 100 %, incluidos el efectivo objetivo y los instrumentos definidos. Bandas absolutas en puntos porcentuales, con mínimo/máximo dentro de 0–100; los límites de concentración prevalecen sobre el objetivo. Rechazar objetivos incoherentes con motivo.
- El usuario define los objetivos: no se sugieren pesos personalizados ni se optimiza rentabilidad. Un solo conjunto activo de objetivos por cartera; historial versionado y activación explícita. La edición genera borrador revisable.
- Solo un corte completo permite diagnóstico como definitivo. Un corte provisional puede consultarse como escenario provisional; incompleto no produce pesos totales. Sin inventar precio o FX, excluir una posición ni normalizar el resto a 100 % en silencio.
- Resultado inmutable enlazado con revisión de cartera, objetivos, políticas y fuentes; cambios lo marcan obsoleto. Guardado con previsualización, comprobación de contexto y auditoría atómica. Lectura/cálculo fuera de transacción escritora.
- Evaluación de límites como función pura reutilizable, separada de presentación y guardado. Define recurso disponible/comprometido como contrato para pasos posteriores; no crea reservas reales ficticias ni afirma que exista un OMS.

## Orden de trabajo autorizado

1. Congelar contratos de objetivo/banda, instrumento frente a cotización y efectivo, con casos numéricos independientes.
2. Persistencia versionada y revisión/activación, aprovechando las transacciones del monolito modular.
3. Cálculo puro de pesos/desviaciones y comprobación de límites, consumiendo cortes D6 y sin recalcular otro libro.
4. Vista compacta en Cartera: tabla, contexto y explicación de conflictos; edición en Datos o sección desplegable de objetivos, sin sexta ventana principal.
5. Regresiones, concurrencia, restauración, anchos 390/1280/3440, presupuesto de carga y CI gratuita; publicación de desarrollo con límites explícitos.

Aceptación: ejemplo 60/20/20 contra 50/30/20 exacto; mismo instrumento con dos cotizaciones sin doble objetivo; saldo USD valorado con su FX; patrimonio cero/incompleto; bandas imposibles; dos activaciones simultáneas; cambio de precio/FX/libro tras previsualizar; recuperación exacta; políticas legacy intactas. No aprobar una propuesta que viole un límite aunque coincida con pesos deseados.

D7/D8 ya están publicados como desarrollo (`v0.4.0-dev.6`, PR #9). La autorización de las cinco tareas permite iniciar esta entrega. La incidencia del proxy se atiende primero. Ensayo de 48 horas y estabilidad no se dan por aceptados ni se reactivan.

## Contratos de la primera entrega

- Porcentaje decimal de 0 a 100, hasta seis decimales; mínimo ≤ objetivo ≤ máximo ≤ límite de concentración. Efectivo obligatorio; un instrumento aparece una sola vez aunque tenga varias cotizaciones. La suma de objetivos es exactamente 100.
- Borradores inmutables numerados, revisión del conjunto y una activación vigente por cartera. Guardar borrador y activar son confirmaciones distintas, ambas previsualizadas. Un cambio concurrente rechaza la confirmación obsoleta; nunca activa parcialmente.
- Evaluar consume un **corte D6 guardado y vigente**, sin construir otro libro. Posiciones de distintas cotizaciones y derechos de dividendos se agregan por instrumento. Los derechos conservan identificación y no cuentan como efectivo disponible. Instrumentos sin objetivo se muestran, con objetivo cero y aviso explícito.
- El efectivo mantiene desglose EUR/USD del corte. Recursos comprometidos quedan **no disponibles**, porque todavía no existe OMS; no se inventan reservas cero ni autorizaciones de envío.
- Corte incompleto o patrimonio no positivo: sin pesos globales ni desviaciones EUR. Corte provisional: escenario provisional. Se conservan causas y subtotales. La disponibilidad histórica de las fuentes se muestra por separado de la calidad contable.
- Informes y borradores son registros analíticos nuevos sobre el almacén versionado existente; la clave primaria garantiza un estado de objetivos por cartera, y la comparación de revisión se ejecuta en la transacción escritora junto con auditoría. No cambia la semántica contable ni el esquema 5. El código anterior ignora estos registros; cualquier cambio de contexto invalida su vigencia al volver a esta entrega.

Quedan para entregas siguientes de v0.5: reparto de aportaciones, cantidades y costes estimados, ventas/rebalanceo, redondeos/lotes, recursos comprometidos y objetivos de varias estrategias; luego benchmarks y escenarios. DSL y validación ampliada v0.6; bróker y paper externo v0.7; móvil, remoto, LaTeX y aprendizaje mantienen su ubicación vigente. Sin compras automáticas, IA de pago o microservicios.
