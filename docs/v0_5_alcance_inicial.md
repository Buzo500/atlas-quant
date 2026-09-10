# v0.5 · Primer alcance propuesto: objetivos y diagnóstico de desviaciones

10/09/2026. Definición autorizada como punto 10; **no implementada**. No cambia la secuencia de la hoja de ruta ni autoriza iniciar v0.5. La versión completa conserva análisis, benchmarks, escenarios, agregación y propuestas; esta primera entrega es deliberadamente pequeña.

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

## Orden de trabajo cuando se autorice

1. Congelar contratos de objetivo/banda, instrumento frente a cotización y efectivo, con casos numéricos independientes.
2. Persistencia versionada y revisión/activación, aprovechando las transacciones del monolito modular.
3. Cálculo puro de pesos/desviaciones y comprobación de límites, consumiendo cortes D6 y sin recalcular otro libro.
4. Vista compacta en Cartera: tabla, contexto y explicación de conflictos; edición en Datos o sección desplegable de objetivos, sin sexta ventana principal.
5. Regresiones, concurrencia, restauración, anchos 390/1280/3440, presupuesto de carga y CI gratuita; publicación de desarrollo con límites explícitos.

Aceptación: ejemplo 60/20/20 contra 50/30/20 exacto; mismo instrumento con dos cotizaciones sin doble objetivo; saldo USD valorado con su FX; patrimonio cero/incompleto; bandas imposibles; dos activaciones simultáneas; cambio de precio/FX/libro tras previsualizar; recuperación exacta; políticas legacy intactas. No aprobar una propuesta que viole un límite aunque coincida con pesos deseados.

D7/D8 ya están publicados como desarrollo (`v0.4.0-dev.6`, PR #9); iniciar el código de esta primera entrega requiere nueva autorización. La incidencia del proxy sigue siendo un trabajo de fiabilidad separado antes de ampliar recorridos pesados. Ensayo de 48 horas y estabilidad no se dan por aceptados ni se reactivan.

Quedan para entregas siguientes de v0.5: reparto de aportaciones, cantidades y costes estimados, ventas/rebalanceo, redondeos/lotes, recursos comprometidos y objetivos de varias estrategias; luego benchmarks y escenarios. DSL y validación ampliada v0.6; bróker y paper externo v0.7; móvil, remoto, LaTeX y aprendizaje mantienen su ubicación vigente. Sin compras automáticas, IA de pago o microservicios.
