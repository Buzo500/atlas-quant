# Contribución: contabilidad, análisis y decisiones de cartera personal

Diseño propuesto a 5 de septiembre de 2026. Alcance confirmado: acciones y ETF, varios mercados, informes en EUR, órdenes reales y automatización mediante reglas configurables. Este documento aporta decisiones funcionales y criterios de aceptación; no constituye una implementación ni recomienda una cartera concreta.

## 1. Decisión de producto

Recomiendo comenzar con posiciones largas, sin margen, sin ventas en corto y sin ETF apalancados o inversos. La cartera puede mantener efectivo en distintas divisas. Son restricciones iniciales deliberadas: permiten resolver aportaciones, diversificación, costes y disciplina de inversión sin incorporar deuda ni estrategias complejas. No implican ausencia de riesgo de mercado ni que cualquier ETF sea apropiado.

El primer valor del producto debe ser responder: cuánto tengo realmente, cuánto he aportado, cuánto he ganado o perdido, qué exposiciones concentro y qué operaciones acercan la cartera a mis objetivos con costes razonables. La automatización inicial debe ejecutar aportaciones y rebalanceos autorizados por reglas; no se presupone una estrategia de generación de alfa.

## 2. Libro contable y conciliación

- **Identidad del activo:** separar instrumento, clase de participación y cotización. Conservar identificador estable, ISIN cuando exista, mercado, divisa, unidad de precio —incluidos peniques frente a libras— y versión temporal de los símbolos. El ticker no es una clave global. Agrupar económicamente cotizaciones equivalentes sin mezclar sus restricciones de ejecución.
- **Registro inmutable:** movimientos originales del bróker, eventos normalizados y asientos derivados con referencias cruzadas. Correcciones mediante reversión y nuevo asiento; una importación duplicada no crea otra operación. Guardar cantidades e importes con precisión decimal explícita y redondear donde lo exige la operación, no repetidamente en cada cálculo.
- **Eventos mínimos:** aportación, retirada, transferencia de valores, compra, venta, comisión, conversión FX, interés, dividendo bruto, retención, split, fusión y reversión. Un evento corporativo no soportado queda pendiente de revisión: nunca se transforma silenciosamente en una rentabilidad extrema.
- **Fechas diferentes:** ejecución, liquidación, derecho económico del dividendo, pago, publicación y recepción. Reconocer posiciones por operaciones ejecutadas y representar cuentas a pagar/cobrar hasta su liquidación. No sumar simultáneamente una compra como posición y como efectivo disponible sin su contrapartida pendiente.
- **Saldos separados:** efectivo contable, liquidado, pendiente, reservado por órdenes y disponible para operar, por divisa. Una valoración total positiva en EUR no autoriza un saldo deudor USD. Las conversiones necesarias deben ser operaciones explícitas y cumplir la política de efectivo del bróker.
- **Dividendos:** reconocer el derecho a cobrar según el evento confirmado y sustituirlo por efectivo al pago, sin sumar el ingreso dos veces. Separar importe bruto, retención observada y neto. La reinversión son ingreso y compra; en un ETF de acumulación no se inventa un dividendo cobrado por el titular.
- **Lotes:** conservar lotes de adquisición, gastos y ajustes. Separar P&L económico del criterio fiscal; no presentar FIFO ni coste medio como regla legal universal. Una importación de posiciones sin su historia permite valorar hoy, pero no inventar coste fiscal ni rentabilidad histórica.
- **Conciliación:** cotejar efectivo por moneda, cantidades, operaciones, órdenes pendientes y eventos corporativos. El patrimonio puede diferir por precios o cortes temporales: explicar esa diferencia mediante un puente de valoración, no forzar los números para igualarlos. Las discrepancias de cantidades o movimientos bloquean las automatizaciones afectadas.

Valoración de control, para posiciones liquidadas y pendientes debidamente contabilizadas:

`NAV_EUR = suma(q_i × precio_i × factor_unidad_i × EUR_por_divisa_i) + efectivo_EUR + derechos_EUR − obligaciones_EUR`.

Los precios de valoración/ejecución son precios sin ajuste retrospectivo; cantidades y eventos corporativos explican sus cambios. Las series ajustadas sirven al análisis de retornos bajo una metodología identificada. No usar simultáneamente precio ajustado por dividendo y otro abono ficticio del mismo dividendo.

## 3. Rentabilidad y comparación

**Panel principal:** patrimonio, aportaciones netas, beneficio económico absoluto, TWR del periodo, XIRR desde inicio, costes, efectivo disponible y fecha/calidad de la valoración. El beneficio absoluto del periodo es `NAV_final − NAV_inicial − aportaciones + retiradas`, incluyendo transferencias externas de valores a valor razonable. Aportaciones no son ganancias; operaciones y dividendos dentro del perímetro de cartera no son aportaciones.

**TWR:** encadenar geométricamente los retornos de subperiodos separados por flujos externos. La valoración inmediatamente anterior a cada flujo permite neutralizarlo; con cierres diarios y flujos intradía se adopta una convención documentada y se identifica la aproximación. Sirve para comparar la evolución de la cartera sin premiar el momento de las aportaciones. Usar estas referencias matemáticas no acredita cumplimiento GIPS. [CFA Institute, GIPS Handbook](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/).

**MWR/XIRR:** resolver `suma(CF_j / (1+r)^((fecha_j−fecha_0)/365)) = 0`, con aportaciones negativas desde la perspectiva del inversor, retiradas positivas y valor final positivo. Para un intervalo que empieza con patrimonio, incluir su valor como desembolso inicial, no su coste de compra original. Registrar convención ACT/365, residual y convergencia; si no se encuentra una raíz válida o aparecen varias soluciones, mostrarlo expresamente. XIRR pondera importes y fechas, por lo que no debe reemplazar TWR ni compararse directamente con el CAGR de un índice. [Portfolio Performance, método MWR](https://help.portfolio-performance.info/en/concepts/performance/money-weighted/).

**Anualización:** aplicar `(1 + TWR_acumulado)^(365/días) − 1` únicamente donde esté definida y etiquetarla como TWR anualizado. No calcular CAGR a partir de patrimonio inicial/final cuando existen aportaciones. El retorno acumulado será la presentación principal para periodos inferiores a un año; XIRR se identificará siempre como tasa anualizada.

**Benchmark:** elegir de forma explícita moneda EUR y variante de retorno total, distinguiendo dividendos brutos y netos. Un índice de precio omite los dividendos y no es una comparación equivalente. Mantener referencia, versión, costes supuestos y calendario estables durante cada experimento. [MSCI, metodología de índices](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Index_Calculation_Methodology_Feb2026.pdf).

Además del índice, comparar con una cartera sencilla o mantener las posiciones iniciales. Para comparar patrimonio alcanzado, simular las mismas aportaciones y retiradas en las mismas fechas; para comparar gestión, comparar TWR. Si se utiliza un ETF como sustituto gratuito de un índice, etiquetar que incluye su propia implementación y costes. No descontar otra vez el TER a una rentabilidad observada del ETF: su efecto ya se refleja en el valor del fondo. Comisiones de cuenta, compraventa y FX sí se registran separadamente. [BlackRock, guía de ETF](https://www.blackrock.com/gls-download/literature/investor-guide/etf-guide-for-institutional-investors.pdf).

**Divisas:** distinguir cotización, moneda base del fondo, exposiciones de los activos subyacentes y cobertura de la clase. Comprar en EUR un ETF internacional no elimina por sí mismo el riesgo de divisa. La descomposición EUR/precio local mide traducción contable, no toda la sensibilidad económica de las empresas. Las exposiciones obtenidas de participaciones publicadas del ETF deben indicar fecha, cobertura y proporción desconocida. [Xtrackers/DWS, preguntas sobre ETF y divisas](https://etf.dws.com/en-gb/knowledge/faq-etfs/).

Los tipos BCE pueden servir para valoración histórica de referencia bajo un corte coherente. No son precios ejecutables ni sustituyen el cambio efectivo de una conversión del bróker. [BCE, tipos de cambio de referencia](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).

## 4. Riesgo y construcción de cartera

Orden recomendado de desarrollo:

1. Pesos actuales y objetivo, efectivo, concentración por activo y emisor, solapamiento entre ETF y exposición sectorial/geográfica disponible. Distinguir información conocida, parcial y desconocida; no rellenar componentes faltantes con ceros.
2. Caída máxima sobre un índice de riqueza obtenido del TWR, no sobre patrimonio contaminado por aportaciones; volatilidad sobre retornos coherentes, correlaciones y escenarios de caída. Mostrar horizonte, frecuencia, muestra y cobertura. El uso de `sqrt(252)` es una convención para determinada serie diaria, no una ley universal ni una predicción.
3. Escenarios editables: por ejemplo, renta variable −20 %/−40 %, EUR fortaleciéndose frente a USD, y shocks conjuntos. Son hipótesis transparentes sin probabilidad implícita. Revaluar las exposiciones que el modelo represente realmente y marcar el resto como no modelado.
4. Riesgo marginal y contribución: con pesos `w`, covarianza `Σ` y volatilidad `σ = sqrt(w'Σw)`, contribución del activo `i = w_i(Σw)_i/σ`. Las contribuciones suman `σ` bajo este modelo y pueden ser negativas. El caso `σ=0` debe tratarse expresamente. No extrapolar esa identidad a contribuciones de drawdown o riesgo extremo.
5. VaR/ES históricos como módulo secundario, con horizonte, confianza, observaciones y número efectivo de pérdidas de cola. No presentar VaR como pérdida máxima: con 250 observaciones, un cuantil del 99 % se apoya aproximadamente en 2–3 observaciones de cola. Sharpe requiere una referencia sin riesgo coherente en moneda y frecuencia; si falta, no inventar un 0 %.

Antes de buscar pesos «óptimos», incorporar rebalanceo hacia objetivos elegidos por el usuario y preferencia por usar nuevas aportaciones. Considerar coste mínimo por orden, FX, tamaño mínimo, fracciones permitidas, liquidez, restricciones de venta y efectivo reservado. Un periodo sin operar es un resultado válido.

La optimización avanzada puede minimizar riesgo y desviación de los objetivos penalizando costes y rotación, con pesos no negativos, efectivo no negativo por moneda y límites configurables. Conviene usar estimaciones regularizadas de covarianza y comparar contra pesos iguales/objetivos fijos. Evitar inicialmente maximizar Sharpe con medias históricas como si fueran rentabilidades futuras conocidas. Una solución inviable, un solver sin convergencia o la falta de datos deben producir un diagnóstico; no relajar límites a escondidas. Las restricciones se vuelven a comprobar tras convertir pesos en cantidades ejecutables. [Cvxportfolio, restricciones de cartera](https://www.cvxportfolio.com/en/1.5.0/constraints.html).

## 5. Flujo del inversor y automatización

`Importar/conectar → conciliar → entender cartera → fijar política → comparar propuesta → ejecutar → conciliar → revisar resultado`.

La política guarda universo permitido, objetivos, calendario o bandas de rebalanceo, presupuesto, efectivo mínimo, límites de concentración, ventas permitidas, máximo por orden/día y costes aceptables. Las reglas se versionan y tienen fecha de activación. Un ejemplo ilustrativo puede usar una revisión mensual y bandas de 5 puntos porcentuales; son parámetros que el usuario decide, no valores óptimos ni recomendaciones universales.

Cada propuesta explica cantidades, motivo, pesos y efectivo antes/después, cambios de exposición, costes, datos utilizados y órdenes pendientes consideradas. Debe permitir comparar ejecutar ahora, usar próximas aportaciones o no operar. Mostrar coste relativo: una comisión de 1 EUR sobre una compra de 100 EUR consume un 1 % antes del spread; esperar a acumular fondos puede ser preferible.

La primera fase puede pedir aprobación de cada propuesta. La fase automática autoriza una política concreta y ejecuta las operaciones que cumplan sus límites sin repetir esa aprobación. Un cambio de política se aplica como nueva versión. La disponibilidad de datos de cierre gratis sirve para investigar y planificar; la ejecución automática exige datos y estado de cuenta suficientemente actuales para sus controles.

Si faltan datos, existe una discrepancia o se desconoce el estado de una orden, pausar nuevas decisiones afectadas y reconciliar. Detener el motor no implica vender toda la cartera. La acción ante una infracción sobrevenida por movimientos de mercado debe configurarse: alertar, bloquear compras o generar una propuesta; no asumir liquidación automática por defecto.

## 6. Casos de aceptación financiera

Estos ejemplos son construidos para validación; no utilizan cotizaciones reales.

| Caso | Resultado exigido |
|---|---|
| 1.000 EUR iniciales, aportación de 1.000 EUR al inicio del periodo, cierre de 2.200 EUR | Beneficio 200 EUR; TWR 10 %, no 120 %. |
| 1.000 EUR iniciales, valor antes de aportación 1.100 EUR, aportación final de 1.000 EUR | Cierre 2.100 EUR; beneficio 100 EUR y TWR 10 %. |
| Aportaciones de 1.000 EUR al inicio y exactamente 365 días después; 2.310 EUR finales a los 730 días | XIRR 10 % anual, bajo ACT/365. No deducir una TWR sin valoraciones intermedias. |
| Compra de 10 acciones a 100 EUR, comisión 5 EUR; venta de 4 a 110 EUR, comisión 2 EUR; precio final 110 EUR | Con coste contable que incorpora compra: realizado 36 EUR, no realizado 57 EUR, P&L total 93 EUR. Patrimonio final 1.098 EUR frente a 1.005 EUR aportados. No duplicar las comisiones. |
| Split 2:1 sobre 10 acciones a 100 EUR | 20 acciones a 50 EUR; valor y coste agregado constantes, sin beneficio artificial. |
| 10 acciones a 100 EUR; dividendo bruto de 2 EUR/acción, retención total 3 EUR; precio exdividendo supuesto 98 EUR | Valor 980 EUR y derecho neto 17 EUR: patrimonio 997 EUR; efecto neto −3 EUR. El pago posterior cambia derecho por efectivo, sin otro ingreso. |
| Posición constante de 100 USD; cambio de 1,25 a 1,00 USD por EUR | Valor de 80 a 100 EUR; +25 % EUR y 0 % USD. No interpretar el movimiento como subida de precio en USD. |
| Transferencia entre dos cuentas incluidas en el mismo informe | Flujo externo agregado cero; en el informe de una sola cuenta sí cruza el perímetro. |
| Compra ejecutada pendiente de liquidación | Posición y obligación presentes; NAV sin creación de dinero; disponible reducido según reservas y reglas del bróker. |
| Efectivo EUR suficiente y USD insuficiente, conversión automática no autorizada | La compra USD no puede generar deuda accidental aunque el NAV consolidado sea positivo. |
| Misma operación importada dos veces o replay tras reinicio | Mismas cantidades, efectivo y P&L; cero duplicación. |
| ETF con historial observado y TER conocido | El cálculo no resta de nuevo el TER al historial; distingue coste informativo y cargo real de cuenta. |
| Precios ausentes o posiciones importadas sin coste de origen | Resultado parcial/estimado o métrica no disponible; nunca cero coste inventado ni rentabilidad presentada como completa. |
| Rebalanceo factible en pesos pero inviable con mínimos y comisiones | Mantener límites y reportar la desviación o inviabilidad; no exceder presupuesto ni usar margen. |

Para estos casos pequeños: igualdad de cantidades al incremento permitido, asientos monetarios al redondeo de la moneda y tolerancia analítica de `1e-10` en retornos calculados con entradas exactas. La tolerancia numérica no mide precisión de datos de mercado. En conciliación real, registrar tolerancia y residuo por concepto; las divergencias no explicadas no se aceptan porque el total esté cerca.

## 7. Entregas por fase

- **Fase financiera inicial:** importación, identidad de instrumentos, eventos comunes, libro multimoneda, conciliación, valoración, TWR/XIRR, benchmarks y exportación auditable. Datos diarios y operaciones reales importadas son suficientes para iniciar este bloque.
- **Fase de decisiones:** objetivos, exposiciones y solapamientos, escenarios, rebalanceo por aportaciones y simulación de costes; todas las propuestas se pueden reconstruir.
- **Fase de órdenes:** integrar la máquina de estados del bróker, reservas y controles previos; ensayar y conciliar el ciclo completo antes de habilitar real.
- **Fase automática:** ejecutar políticas de aportación/rebalanceo versionadas y ensayadas, con pausa, límites y manejo de incidencias. La automatización no presupone mejor rentabilidad.
- **Fase avanzada opcional:** covarianzas regularizadas, optimización con restricciones, atribución, VaR/ES y datos históricos más ricos. Justificar cada coste de datos por una capacidad concreta; no bloquear la utilidad inicial por no disponer de terminales profesionales.

No prometer cumplimiento fiscal, GIPS, exactitud absoluta del riesgo ni rentabilidad superior. Lo comprobable es que el software aplica convenciones declaradas, conserva evidencia, supera casos de aceptación y expone dónde no sabe calcular o ejecutar con suficiente fiabilidad.
