# Base de diseño del software quant

Estado: documento preliminar, anterior a las respuestas de alcance. Sustituido por [el diseño funcional y técnico completo](atlas_quant_diseno.md), que incorpora las decisiones del usuario. Se conserva como registro de la conversión inicial de los 16 criterios en requisitos verificables. No acredita una implementación ni una validación ya realizadas.

## 1. Propósito y decisiones abiertas

La amplitud de funciones se construirá por fases sobre un núcleo verificable. Cada mercado incorporado debe disponer de convenciones, datos, modelos de costes y pruebas adecuados; añadir su nombre a una lista de activos compatibles no demuestra soporte.

Decisiones pendientes del usuario:

1. Entrega: especificación funcional y técnica, o también desarrollo de una primera versión.
2. Trabajo principal: investigación de estrategias y carteras; microestructura y HFT; inversiones personales; o producto para terceros.
3. Operativa: análisis y simulación, paper trading, o envío de órdenes reales.
4. Mercado prioritario y horizonte de decisión; otros mercados posteriores.
5. Presupuesto de datos e infraestructura y plazo esperado.

El número de usuarios, el despliegue local o remoto, el hardware y los requisitos de disponibilidad se concretarán al conocer estas respuestas. El lenguaje, la base de datos y la interfaz se elegirán después de definir las cargas y los flujos de uso.

## 2. Componentes y responsabilidades

Estas son fronteras lógicas; no obligan a desplegar microservicios.

- **Instrumentos y convenciones:** identificadores estables, mercados, monedas, calendarios, zonas horarias, tamaños mínimos, multiplicadores y eventos contractuales.
- **Datos:** ingestión, conservación de originales, controles, versiones, historial de transformaciones y consultas con la información disponible en cada instante.
- **Cálculo y contabilidad:** rentabilidades, efectivo, inventario, valoración y atribución de pérdidas y ganancias; reglas específicas por instrumento.
- **Investigación:** hipótesis, variables, estrategias, estimación de modelos y comparación de experimentos.
- **Simulación:** reloj histórico, decisiones, órdenes, ejecuciones y costes compatibles con la resolución del dato.
- **Carteras y riesgo:** restricciones, construcción de posiciones, exposiciones, contribuciones al riesgo y escenarios.
- **Validación:** separación temporal, evaluación fuera de muestra, sensibilidad y comparación con alternativas sencillas.
- **Registro de resultados:** identificadores de ejecución, artefactos, estados de validación y exportación reproducible.
- **Interfaz y API:** configurar trabajos, inspeccionar resultados y errores, profundizar en una cifra y exportar evidencia.
- **Operativa, si entra en el alcance:** conectores de bróker, control de órdenes, límites previos al envío, conciliación, vigilancia y recuperación.

La interfaz consumirá los resultados del núcleo; no mantendrá una segunda implementación de las fórmulas. Compartir la lógica de estrategia entre simulación y operativa no implica que compartan el mismo modelo de ejecución.

## 3. Matriz de aceptación de los 16 requisitos

| ID | Requisito | Condición de diseño y evidencia exigida |
|---|---|---|
| Q01 | Corrección matemática y financiera | Documentar fórmula, dominio, unidades, convención, calendario y precisión de cada cálculo central. Contrastar casos analíticos y referencias independientes. Ejemplo: una inversión sin flujos que pasa de 100 a 110 y después a 99 produce −1 % acumulado; sumar 10 % y −10 % sería incorrecto. Fijar tolerancias por cálculo y escala. |
| Q02 | Calidad y procedencia de datos | Cada conjunto tendrá proveedor, cobertura, fechas, esquema, versión, licencia y controles de calidad. Conservar originales y separar observado, ajustado, estimado y simulado. Probar duplicados, ausencias, revisiones, dividendos, splits y desaparición de instrumentos cuando corresponda. La ausencia de un universo histórico adecuado limita las conclusiones y debe quedar visible. |
| Q03 | Adecuación de modelos | Cada modelo tendrá hipótesis, finalidad, datos necesarios, supuestos, dominio de uso y alternativa sencilla. Incorporarlo exigirá una justificación; conservarlo exigirá evidencia pertinente a su uso. Un modelo fuera de su dominio debe advertir o rechazar el cálculo según la gravedad. |
| Q04 | Validación y sesgos | El acceso histórico a datos respetará su disponibilidad efectiva. Ajustar transformaciones y seleccionar modelos usando exclusivamente los tramos permitidos. Definir entrenamiento, validación y prueba antes de evaluar. Tratar el solapamiento de etiquetas y el historial de múltiples experimentos cuando aplique. Una prueba reservada utilizada para elegir modelos deja de ser una evaluación independiente. |
| Q05 | Realismo económico | Desglosar comisiones, spread, deslizamiento, impacto, financiación, préstamo y costes específicos relevantes, evitando doble contabilización. Probar órdenes parciales, rechazos y límites de volumen cuando el dato permita representarlos. Una señal calculada con el cierre completo no puede asumir automáticamente una ejecución a ese mismo cierre. Los supuestos de ejecución siempre acompañarán al resultado. |
| Q06 | Riesgo | Mostrar pérdidas, drawdown, exposiciones, concentración, apalancamiento y escenarios apropiados. Incorporar riesgo marginal o contribuciones cuando exista cartera. Las medidas estadísticas identificarán horizonte, método, ventana y supuestos. VaR y escenarios no se presentarán como pérdidas máximas garantizadas. Las medidas para opciones u otros instrumentos no lineales deberán reflejar su naturaleza. |
| Q07 | Comparación relevante | Comparar con benchmark, alternativa sencilla y mantener posiciones o efectivo cuando tenga sentido. Alinear fechas, moneda, flujos, costes, dividendos y riesgo comparable. Separar cualquier diferencia de exposición que explique la rentabilidad. Un ranking no deberá mezclar resultados calculados bajo convenciones incompatibles. |
| Q08 | Robustez | Ejecutar variaciones de parámetros, costes, periodos, liquidez y semillas cuando corresponda. Mostrar distribuciones y configuraciones que fallan, además de la mejor. Definir perturbaciones relevantes para el uso; no imponer un rango porcentual universal. Comprobar regímenes y dependencia de instrumentos o episodios concretos. |
| Q09 | Reproducibilidad | Guardar versiones o huellas de datos, código, configuración, dependencias, modelos y semillas. Para código sin commit, conservar el estado o parche necesario. Recrear una ejecución en un entorno limpio y comparar dentro de tolerancias documentadas. Registrar diferencias esperables entre plataformas y bibliotecas numéricas. |
| Q10 | Pruebas del software | Incluir pruebas unitarias del núcleo, propiedades financieras, integración y regresión con datos de referencia. Cubrir cartera vacía, posiciones cortas, flujos, datos inválidos, matrices singulares y fallos de proveedores. La evidencia de aceptación incluirá los resultados ejecutados y sus versiones; una lista de pruebas previstas no equivale a pruebas superadas. |
| Q11 | Fiabilidad y recuperación | Cada trabajo tendrá estados persistentes y errores distinguibles. Simular interrupciones y reanudar sin publicar resultados incompletos como finales. Conservar la última versión íntegra del dato. Fijar antigüedad admisible, tiempo de recuperación y pérdida de trabajo aceptable según el caso. Si el estado de una orden es incierto, reconciliar antes de decidir si se reenvía. |
| Q12 | Seguridad y dinero | Mantener credenciales fuera del código y de los registros; minimizar permisos y controlar dependencias. Si hay ejecución, separar cuentas y entornos, aplicar límites antes de enviar, identificar órdenes de forma persistente y verificar respuestas del bróker. Probar parada de nuevas órdenes, cancelación y recuperación. Cancelar o liquidar son acciones distintas y requieren políticas explícitas. |
| Q13 | Transparencia e incertidumbre | Cada cifra mostrará unidad, instante, origen, convención y condición de cálculo o estimación. Un resultado no calculable será ausente con motivo, nunca cero por defecto. Si se incorpora IA, sus cifras deberán proceder de resultados identificables del núcleo y sus afirmaciones tener respaldo verificable. Un texto generado no aprobará por sí mismo un modelo ni una operación. |
| Q14 | Arquitectura y mantenimiento | Definir contratos entre datos, cálculos, estrategia, simulación, riesgo e interfaz. Versionar esquemas y migraciones. Demostrar la incorporación de un segundo proveedor mediante su adaptador y pruebas de contrato, sin modificar la lógica de estrategia por diferencias de formato. Las diferencias económicas reales entre mercados sí pueden exigir nuevos modelos. |
| Q15 | Rendimiento | Definir conjuntos y cargas de referencia: instrumentos, eventos, años, experimentos concurrentes, hardware y almacenamiento. Medir duración, memoria y distribución de latencias pertinente al uso. Fijar objetivos numéricos después de concretar el producto; no prometer latencia HFT desde un benchmark de cálculo local. |
| Q16 | Utilidad y coste total | Verificar un flujo completo: importar o seleccionar datos, configurar una hipótesis, ejecutar, comparar, investigar una cifra y exportar. Registrar tiempos y obstáculos con tareas representativas. Presupuestar datos, licencias, almacenamiento, cómputo, copias, observabilidad y mantenimiento. El acceso gratuito a una API no demuestra permiso de redistribución. |

## 4. Contratos mínimos de trazabilidad

Un conjunto de datos identificará el instrumento y mercado, el tiempo del hecho, el tiempo de publicación cuando exista, su disponibilidad en la fuente y su ingestión. No se inventarán fechas desconocidas: si se aproximan, se conservará la regla y su limitación. Los datos brutos y los ajustados tendrán usos diferenciados; el histórico ajustado no sustituye sin más a los precios de ejecución.

Un resultado tendrá `run_id`, versiones de entradas y código, configuración, entorno, inicio y fin, estado del trabajo, advertencias y referencias a artefactos. Cada métrica añadirá método, unidad, horizonte, moneda si corresponde y tratamiento de datos ausentes.

Separar dos estados:

- **Ejecución:** pendiente, en curso, completada, cancelada o fallida.
- **Evaluación:** no revisada, exploratoria, evaluada con limitaciones o aceptada para un uso y versión concretos.

Completar un cálculo no equivale a validar su interpretación económica. Un cambio material en datos, modelo, convenciones o mercado exige revisar la evaluación previa.

Cuando exista operativa, efectivo, posiciones, órdenes y ejecuciones tendrán un registro duradero de eventos y un proceso de conciliación. Un timeout de envío no implica que la orden haya sido rechazada. La parada de emergencia bloqueará nuevas acciones según la política; no prometerá eliminar instantáneamente órdenes remotas ni posiciones.

## 5. Ejemplos de pruebas de aceptación del núcleo

1. **Rentabilidad compuesta:** 100 → 110 → 99, sin flujos ni costes: −1 %.
2. **Contabilidad de una compra:** comprar 10 acciones a 100, con comisión de 1, reduce el efectivo en 1.001; valoradas inmediatamente a 100, el patrimonio cae en 1 si no hay otras diferencias de valoración. La comisión no se restará otra vez al calcular el patrimonio desde efectivo y posiciones.
3. **Split 2:1:** 10 acciones a 100 pasan a 20 a 50, conservando valor 1.000 en el caso controlado sin otras variaciones ni costes.
4. **Cronología:** modificar exclusivamente un dato que se publica después de una decisión no puede alterar esa decisión histórica en una ejecución determinista.
5. **Fallo explícito:** un precio obligatorio ausente debe invalidar o limitar la valoración con una causa visible; no puede transformarse silenciosamente en un precio cero ni ejecutarse una orden con él.
6. **Reconstrucción:** el registro de operaciones y flujos debe permitir reconstruir el efectivo y las posiciones del resultado; las diferencias de redondeo se documentarán.
7. **Reinicio:** interrumpir un trabajo durante la escritura no dejará un artefacto parcial marcado como completado. Si hay órdenes, reiniciar no volverá a enviar una orden sin conocer o reconciliar su estado.

Estos son casos iniciales, no una batería completa para todos los activos.

## 6. Secuencia de implementación propuesta

1. Concretar producto, mercados, flujo principal y criterios medibles de la primera versión.
2. Construir contratos de datos, convenciones y núcleo de cálculo con casos de referencia.
3. Entregar un flujo completo y verificable de investigación o análisis para el mercado prioritario.
4. Añadir sensibilidad, evaluación fuera de muestra, riesgo y exportaciones según ese flujo.
5. Incorporar nuevos instrumentos y modelos solo con su evidencia de aceptación.
6. Si se solicita operativa, añadir primero simulación en directo y pruebas de recuperación; el uso real tendrá límites, conciliación y evaluación específicos.

No se fija todavía un plazo ni un coste: faltan datos sobre alcance, recursos y disponibilidad de proveedores. El resultado perseguido es un software comprobable para usos definidos, sin promesas de rentabilidad ni de ausencia absoluta de errores.

## 7. Referencias concretas consultadas

- [scikit-learn: Common pitfalls — Data leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage). Fundamenta separar entrenamiento y prueba antes de ajustar transformaciones y evitar que la selección de modelos utilice el conjunto de prueba.
- [QuantConnect: Trade fills — Key concepts](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/trade-fills/key-concepts). Distingue el modelado de precios y cantidades ejecutadas, spread y deslizamiento.
- [Federal Reserve Bank of St. Louis: FRED API — Real-Time Periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html). Explica la consulta de información económica tal como era conocida en periodos históricos y sus revisiones.

Estas fuentes respaldan conceptos concretos; no certifican el diseño ni sustituyen su validación. Las menciones genéricas a instituciones en el texto de partida no se interpretan como estándares cumplidos.
