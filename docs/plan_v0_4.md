# ATLAS Quant · Plan de v0.4: datos y contabilidad trazables

9 de septiembre de 2026. **Alcance aprobado: D1–D8, CSV propio y EUR/USD. D1 especificado, D2/D3 publicados y D4 desarrollado localmente en `codex/v0.4-d4`, `0.4.0-dev.3`. D5–D8 pendientes.** [D2](v0_4_d2.md), [D3](v0_4_d3.md) y [D4: CSV y conciliación EUR](v0_4_d4.md). D4 parte de la fusión de PR #5 y etiqueta `v0.4.0-dev.2`, `cdb59b1461d3d26ff88d6f7de90bdf4534ca5fe3`. Las carteras anteriores conservan su política EUR; el libro nuevo v2 incorpora saldos/coste sin NAV/TWR hasta D6/D7. USD sigue reservado a D6. Espera intermitente de API conservada como incidencia conocida abierta.

[D1: contratos y convenciones](v0_4_d1.md) fija orden, precisión, monedas, fechas, CSV, errores, capacidades, métricas y migración inicial. Incluye [12 casos numéricos](fixtures/v0_4_d1_referencias.json) comprobados mediante aritmética independiente; no son pruebas ejecutadas contra el motor nuevo.

La [arquitectura objetivo](arquitectura_objetivo.md), concretada el 09/09/2026, conserva D1–D8. El evaluador compartido, la construcción de posiciones objetivo, el riesgo continuo y el gestor de órdenes se desarrollarán en v0.5–v0.7 según la [hoja de ruta](hoja_de_ruta.md); no amplían esta entrega ni alteran los contratos heredados de v0.4.

## Objetivo y alcance

**Avance posterior · 09/09/2026:** D2 integrado en PR #4 y etiqueta `v0.4.0-dev.1`; el usuario autoriza concretar, preparar casos e implementar D3. [Contrato y evidencia D3](v0_4_d3.md), desarrollo local `0.4.0-dev.2`, `codex/v0.4-d3`. D4–D8 pendientes. Este avance sustituye los pendientes de D3 y autorización del registro inicial.

Poder explicar y reproducir el patrimonio, posiciones y rentabilidad de una cartera a partir de movimientos, instrumentos, precios, divisas y eventos identificados. Saber qué cifras están conciliadas, cuáles son provisionales y qué información falta. La prioridad es la corrección del núcleo; se conserva el monolito modular y la interfaz crema/cobre.

Alcance aprobado: identidad de instrumentos y cotizaciones, cartera independiente del conjunto de precios, importación y conciliación mediante CSV, cobertura/calendarios versionados, dividendos y splits ordinarios, efectivo multidivisa y valoración en EUR, y MWR/XIRR con convenciones explícitas. Primera aceptación multidivisa con **EUR y USD**; otras monedas requieren sus propios fixtures y cobertura, no solo habilitar un código de moneda.

Se mantienen ejecución local en Windows, un ejecutor por base, datos sintéticos para pruebas, ausencia de claves y presupuesto de API cero. CSV es el camino completo de aceptación sin depender de una descarga externa. No se promete acceso gratuito a calendarios, FX o eventos verificados: fuentes y permisos se contrastarán antes de incorporar cada adaptador.

## Auditoría del punto de partida

| Situación comprobada en v0.3 | Consecuencia para v0.4 |
|---|---|
| `analytics.py` usa Decimal, coste medio, compras/ventas, depósitos/retiradas, comisiones, dividendos y splits manuales; solo EUR. | Conservar lo existente y extender su semántica. No presentar dividendos/splits manuales como funciones nuevas. |
| `DatasetService` guarda el ledger bajo el ID del conjunto de precios. | Separar cartera/libro y conjunto antes de cambiar proveedores o combinar monedas. Cambiar precios no debe copiar movimientos. |
| Barras, posiciones y estrategias usan `symbol`; no existe catálogo persistente de identidad y cotizaciones. | El ticker pasa a ser un alias contextual. No fusionar activos de distintos mercados por coincidencia de texto. |
| Versiones de conjuntos inmutables y previsualización CSV vinculada al estado vigente dentro de `Store.atomic`. | Extender esas garantías a instrumentos, libro, acciones corporativas y FX. No perder el control de concurrencia. |
| El proveedor aporta acciones corporativas informativas y `applied_to_ledger=False`; una incidencia impide promoción. | Añadir conciliación verificable. Descargar un evento no es autorización para aplicarlo al libro. |
| TWR diario con flujos externos al cierre; puede usar último cierre conocido con advertencia. | Conservar la convención histórica y añadir calidad por fecha/posición. No cambiar resultados antiguos silenciosamente. |
| No hay MWR/XIRR, ledger multidivisa ni calendario de sesiones verificado. | Introducirlos después de la identidad, los movimientos y la valoración. |
| SQLite esquema 1; OpenAPI genera los tipos TypeScript. | Migración explícita, compatibilidad histórica y regeneración de contratos en cada entrega que los cambie. |

Lecturas de referencia: `backend/atlas_quant/{analytics,data,datasets,contracts,store,feed,prices,gates}.py`. Es una auditoría de código para planificar, no una nueva validación del motor.

## Entregas y dependencias

Los códigos D1–D8 son bloques de trabajo, no ocho versiones comerciales. Cada bloque se revisa antes de ampliar el siguiente y debe dejar recorridos utilizables o estados explícitos de función todavía no disponible. No se comprometen fechas.

| Bloque | Resultado concreto | Dependencia | Criterio para aceptarlo |
|---|---|---|---|
| **D1 · Contratos y casos de referencia** | Especificación de identidad, libro, valoración, orden de eventos y fixtures con resultados independientes. | v0.3 aceptada | Ejemplos calculables a mano, invariantes y política de errores; plan de migración y matriz de capacidades aprobados antes de cambiar persistencia. |
| **D2 · Instrumentos y cartera independiente** | Registro de instrumentos/cotizaciones y alias; cartera/libro separados de conjuntos, con revisiones coherentes. | D1 | Dos mercados con el mismo ticker no se mezclan; cambio de ticker conserva identidad; cambiar conjunto conserva movimientos; migración de v0.3 sin pérdida ni cambios contables. |
| **D3 · Calidad, calendario y versiones** | Informe por serie/fecha de cobertura, antigüedad, base de precio y aptitud para valorar/investigar/simular. | D2 | Festivo conocido, sesión ausente y calendario desconocido se distinguen; revisiones históricas crean versión; ningún dato futuro o incompatible pasa por válido. |
| **D4 · Importación y conciliación de extractos** | CSV normalizado de movimientos y saldos/posiciones de referencia; previsualización, diferencias y confirmación. Primera entrega EUR. | D2–D3 | Reimportación idempotente; discrepancias visibles; confirmación obsoleta rechazada; importación y auditoría atómicas; nunca crear ajustes ocultos para cuadrar. |
| **D5 · Dividendos y splits conciliados** | Vincular eventos del proveedor y movimientos existentes o propuestas revisadas; tratar bases de precios de forma coherente. | D3–D4 | Sin doble dividendo ni doble split; cantidades, coste y efectivo correctos; mismo tratamiento económico para estrategia y benchmark cuando el modo sea compatible. |
| **D6 · Divisas y valoración EUR** | Efectivo por moneda, cambios explícitos, series FX versionadas y valoración trazable en EUR. Extensión CSV/conciliación EUR–USD. | D4–D5 | Casos de referencia con comisiones y FX; sin doble aportación por conversión; FX ausente/obsoleto identificado; sin usar tipos posteriores a la valoración. |
| **D7 · Rentabilidad y explicación contable** | MWR/XIRR por periodo y desglose coherente de flujos, costes y patrimonio; TWR con convención identificada. | D5–D6 | Casos con fechas irregulares, flujos intermedios, patrimonio inicial, raíz ausente/ambigua y datos insuficientes; no convertir fallos en 0 %. |
| **D8 · Integración y entrega** | Migración/recuperación, contratos, pruebas de navegador, rendimiento, documentación y CI gratuita. | D1–D7 | Todos los casos aceptados; una lectura identifica el mismo corte de libro/precios/FX/eventos; datos habituales conservados; límites publicados y sin regresiones de v0.3. |

**Secuencia actual: revisar y publicar D4; después concretar D5.** D2/D3 están integrados. D6 no debe empezar como una ampliación de `Literal["EUR"]`: admitir una moneda en un formulario antes de resolver efectivo, FX y valoración produciría capacidades aparentes sin soporte contable.

## Decisiones de arquitectura propuestas

### Identidad y libro

- `instrument_id` identifica el instrumento/clase; `listing_id` su cotización con mercado y moneda. ISIN y otros códigos son atributos contrastados, no una razón para fusionar automáticamente registros. Alias de ticker y proveedor con vigencia y fuente. No inventar mercado/ISIN para la demo o CSV antiguos.
- `portfolio_id` y un libro revisionado se independizan del conjunto. Mantener una cuenta local inicial de uso sencillo; un identificador de cuenta de origen sirve para conciliación, sin construir todavía un producto de consolidación multibróker.
- Migración conservadora: una cartera por ledger antiguo y asociaciones explícitas a su conjunto. Identidades antiguas quedan locales/no verificadas, sin deduplicación global por ticker. Preservar IDs, orden de movimientos y snapshots de investigaciones históricas.
- Movimientos nuevos con moneda, origen, ID externo cuando exista, orden intradía explícito si se conoce y vínculo a correcciones. No reordenar movimientos de igual fecha por un UUID ni inventar horas; una secuencia ambigua que afecte saldo o derechos bloquea confirmación hasta resolverla.
- Correcciones contables auditables mediante revisión/anulación y sustitución enlazadas; no borrar el original. Separar estado efectivo del historial de cambios. Decimal en el núcleo y representación decimal canónica en persistencia/importaciones; redondeo explícito por concepto y moneda. Los floats de presentación no son la fuente de conciliación.

### Versiones y transacciones

- Conservar el acceso a SQLite detrás de Store; casos de uso coordinan validación y confirmación, y funciones puras calculan valoración/conciliación. Extraer módulos de identidad, contabilidad y calidad según estos límites; no añadir microservicios, colas distribuidas ni otro ejecutor.
- Una valoración identifica cartera, revisión de libro, mapa de instrumentos, versiones de precios/FX/eventos, política y fecha de corte. Leer el contexto coherente en una transacción; calcular fuera de ella cuando sea costoso. Un resultado persistido conserva sus versiones y no se publica como estado vigente si estas cambiaron.
- Descargar y analizar fuera de la transacción de escritura. Al confirmar, releer y contrastar revisiones; commit de movimientos, vínculos de conciliación y auditoría juntos. Nunca escribir un snapshot antiguo después de un `await`.
- Extender el token de previsualización para cubrir archivo, mapeo, cuenta, libro, precios, FX, eventos y políticas utilizados. Un cambio material invalida la confirmación aunque el CSV sea idéntico.
- Mantener respuestas históricas legibles. Adaptadores para formatos antiguos, nuevas respuestas versionadas cuando proceda y tipos regenerados con `tools/export_contracts.py`; no cambios silenciosos del significado de campos existentes.

### Calidad y disponibilidad temporal

- Estados por capacidad, no una única casilla «datos buenos»: inválido, incompleto, provisional, conciliado y desconocido con códigos de motivo. Una falta de FX puede impedir NAV sin impedir leer movimientos; una sesión ausente puede impedir investigar sin invalidar un saldo conciliado.
- Mostrar último precio/FX usado y antigüedad. Se permite consulta provisional identificada bajo una política concreta; faltantes críticos o base incompatible bloquean valoración definitiva y promoción de simulación. Ni rellenar barras ni eliminar incidencias por abrir la pantalla.
- Calendarios como referencias versionadas con mercado, zona, periodo cubierto, fuente y estado de verificación. Los fixtures usan calendarios sintéticos explícitos. Fuera de cobertura: desconocido, no «sesión completa». Mantener fechas de sesión separadas de timestamps UTC.
- Distinguir fecha efectiva, disponibilidad conocida y recepción. Si se desconoce la disponibilidad histórica, no afirmar que un backtest pudo usar esa información entonces. Los datos descargados hoy no reconstruyen automáticamente lo sabido en el pasado.
- Revisiones de precios/eventos/FX generan nueva evidencia y versión; no sobrescriben la serie usada por un resultado previo. Revisar el impacto antes de activar una corrección sobre una cartera.

## Semántica contable que debe fijar D1

**Importación:** CSV propio versionado como formato inicial de intercambio, con plantilla y mapeo revisable; no parser universal de extractos. El archivo de saldos/posiciones de referencia contrasta el libro a la misma fecha y moneda. IDs de movimientos acotados por fuente/cuenta; archivos solapados sin IDs fiables generan candidatos a duplicado, no eliminaciones automáticas. Dos ingresos iguales pueden ser movimientos distintos. Los adaptadores de un bróker concreto se elegirán cuando exista un ejemplo anonimizado y necesidad real; PDF/OCR y conexión al bróker quedan fuera.

**Eventos corporativos:** solo dividendos ordinarios en efectivo y splits/reverse splits. El hecho comunicado, el derecho económico y el cobro son registros relacionados distintos. Separar exfecha, fecha de pago y retención declarada; no deducir esas fechas de un campo ambiguo del proveedor. Cuando se modele un derecho a cobrar, reconocerlo una vez y cancelar ese derecho al cobrar, sin sumar dos veces el efectivo. No calcular fiscalidad: retenciones solo importadas/declaradas y mostradas como tales. Derechos/fracciones inciertos o compensaciones en efectivo sin importe confirmado quedan pendientes. Fusiones, escisiones, amortizaciones y otras acciones complejas se detectan y bloquean donde afecten al resultado; no se simulan como un split genérico.

**Base de precios y simulación:** separar observado, ajustado por split, ajustado por dividendos/retorno total y desconocido; cada transformación conserva su método y versiones. No aplicar simultáneamente un evento y el mismo ajuste incorporado al precio. La aptitud para dibujar no implica aptitud para fills. D5 debe fijar la matriz de compatibilidad de investigación/paper de un activo y sus benchmarks; el modo sin soporte se rechaza explícitamente. D6 habilita cartera EUR–USD, no autoriza por sí mismo backtests o paper multidivisa. Los experimentos antiguos conservan el modelo anterior y sus limitaciones; no se recalculan automáticamente.

**FX:** proponer inicialmente `EUR por unidad de moneda origen` para valoración; importaciones identifican orientación y toda inversión de tipo es explícita. El cambio de efectivo guarda ambos importes y comisión real: no se reconstruye desde el tipo de valoración. No crear saldo negativo en una moneda porque haya saldo positivo en otra; la conversión es un movimiento. La cuenta sigue expresada en moneda base EUR. Política diaria de selección as-of, calendario y antigüedad documentada; ausencia de cotización adecuada produce estado incompleto. La atribución separada de rendimiento de activo y divisa puede aplazarse, pero debe seguir siendo posible reproducir el valor EUR y el FX usado.

**MWR/XIRR:** fechas civiles, base anual días reales/365 como convención propuesta del producto. Perspectiva del inversor: valor inicial y aportaciones negativos; retiradas y valor final positivos. Compras/ventas, dividendos retenidos en la cuenta y conversiones internas no son aportaciones externas. Definir corte de apertura/cierre y flujos de los extremos para no duplicarlos. Conservar el TWR diario actual y su aproximación de flujos al cierre; no presentarlo como TWR intradía exacto. Solver con tolerancia, dominio, límite de iteraciones y estados de no convergencia/ambigüedad explícitos; encontrar una raíz no demuestra unicidad. Para patrones no convencionales sin unicidad acreditada, devolver indeterminado con motivo. El horizonte de backtest y los gráficos existentes no se reinterpretan como rentabilidad personal MWR.

## Casos de referencia mínimos

Fixtures nuevos, sintéticos y pequeños, con cálculo esperado independiente del código bajo prueba. Estos ejemplos fijan expectativas, no son resultados ya ejecutados.

| Caso | Resultado esperado |
|---|---|
| Depósito 1.000 EUR; compra 4 títulos a 100 EUR con comisión 2 EUR; cierre 110 EUR | Efectivo 598, posición 440, NAV 1.038, aportación 1.000, P&L 38, coste de la posición 402. |
| 10 títulos con coste total 1.000 EUR; split 2:1; nuevo cierre 50 EUR | 20 títulos, mismo coste total, valor 1.000 EUR; sin beneficio artificial por el split. |
| Dividendo bruto 20 EUR y retención declarada 3 EUR | Cobro neto 17; conciliación con evento existente no suma otro cobro; el derecho previo se cancela cuando corresponda. |
| Cambio de 100 EUR por 110 USD, sin comisión | Movimiento interno, no aportación; conserva ambos importes. Con marca 1/1,1 EUR por USD vale 100 EUR antes de redondeo. |
| Activo de 100 USD, FX 0,90 EUR por USD | Valor 90 EUR; FX futuro rechazado y ausencia de FX produce valoración incompleta, nunca 100 EUR por omisión. |
| Inversión inicial 1.000 y valor final 1.100 exactamente 365 días después, sin otros flujos | MWR anual 10 % dentro de la tolerancia especificada. |
| Aportaciones/retiradas irregulares y valor inicial previo al rango | NAV/P&L/TWR/MWR contrastados con cálculo independiente; sin duplicar flujos en los extremos. |
| Mismo ticker en dos mercados; cambio de ticker; CSV duplicado/conflictivo | Identidades separadas o alias de la misma cotización según evidencia; cero duplicados contables; conflicto visible. |
| Festivo, sesión ausente, precio viejo, calendario desconocido, split sin nuevo precio compatible | Motivos distintos, con capacidades permitidas/bloqueadas según política. |
| Confirmación concurrente, caída durante commit, migración y restauración | Ningún commit parcial; estado revisado obsoleto rechazado; rollback y auditoría verificables. |

D1 ampliará estos ejemplos con fracciones, venta parcial, devolución/corrección, cuenta vacía, NAV cero y patrones XIRR sin raíz/ambiguos. Las tolerancias se fijan antes de implementar: importes/posiciones exactos según política decimal, métricas numéricas con error absoluto y relativo documentados.

## Interfaz y recorrido de aceptación

Conservar las cinco secciones. En **Datos**, identidad y procedencia, cobertura e incidencias, importación revisable y conciliación. En **Cartera**, saldo por moneda, valor EUR con fecha/FX, movimientos y diferencias de conciliación; MWR junto a TWR con sus periodos y motivos de indisponibilidad. En **Laboratorio/Agente IA**, capacidad del conjunto para el modo solicitado y bloqueo explicado. Los cambios de mapeo o fuente no confirman ni ejecutan operaciones.

Recorrido sintético final: crear/importar cartera → resolver identidades → cargar versiones de precios/calendario/FX → revisar extracto → detectar discrepancia y corregirla de forma trazable → conciliar dividendo/split sin duplicación → comprobar valores y métricas → recargar y recuperar el mismo corte. Probar teclado, errores, cambios concurrentes y pantallas de escritorio/ultrapanorámica. No rediseñar de nuevo los gráficos ni añadir ventanas sin necesidad del flujo.

## Migración, verificación y salida

- Antes de implementar: rama nueva desde la entrega aceptada, ATLAS detenido para código/build, copia coherente y fixtures aislados. La planificación actual no requiere detener el programa ni tocar su base.
- Migraciones nuevas y explícitas, transaccionales y probadas desde bases vacías y v0.3 con libros, conjuntos/versiones y experimentos. No basta aumentar `user_version`: verificar estructura y formato de registros. Conservar snapshots/IDs históricos y comparar totales antes/después.
- No prometer downgrade sobre la base migrada. Vuelta atrás mediante binario anterior y copia compatible, probada en aislamiento; explicar qué cambios posteriores no están en esa copia. Respaldos nunca van a Git.
- Regresiones de precios/gráficos y controles de v0.3, casos contables independientes, concurrencia con barreras, contratos, TypeScript, lint, build con manifiesto, arranque/parada y E2E reales. Las pruebas de proveedores usan fixtures, sin llamadas pagadas.
- Medir lectura/valoración, serialización y concurrencia de controles con cargas documentadas. No subir el límite actual de 100.000 barras por conjunto como efecto lateral de v0.4. Presupuestos de rendimiento del modelo nuevo se fijan en D1 y se contrastan en D8.
- Publicación de desarrollo solo tras CI gratuita sobre fuentes identificadas y aceptación de límites. El ensayo de 48 horas permanece aplazado: no se elude presentando v0.4 como estable. La incidencia de API conserva su seguimiento por evidencia; una recurrencia relevante exige reevaluar la entrega afectada.

## Fuera de alcance y decisiones pendientes

Fuera: bróker/órdenes reales, cortos/préstamos, derivados, fiscalidad declarativa, consolidación multibróker avanzada, liquidación intradía exacta, importación universal PDF/OCR, acciones corporativas complejas, backtests de cartera/multidivisa, nuevos indicadores/McClellan, aprendizaje, móvil/remoto e informes LaTeX. Mantienen su planificación en la hoja de ruta.

Decisiones de alcance aprobadas: formato CSV propio primero, EUR–USD como primer conjunto de monedas y evolución incremental D1–D8. Se mantiene la cartera inicial sencilla definida en D1. Calendarios/proveedores reales, primer formato de extracto externo y tratamiento de casos de liquidación no cubiertos se concretan cuando se disponga de evidencia; no bloquean los fixtures sintéticos ni justifican contratar servicios. Para convenciones técnicas concretas prevalece D1 sobre las formulaciones preliminares del plan.

La aprobación del plan no autoriza automáticamente cada implementación o publicación. Los cinco pasos posteriores autorizan publicar D3, ejecutar su CI gratuita, fusionar/etiquetar si pasa, concretar D4 e implementarlo con pruebas. D3 está publicado; D4 sigue local, pendiente de revisión y CI remota propias. La arquitectura futura no habilita un bróker ni inicia D5–D8. La importación de movimientos del usuario queda pendiente por decisión expresa.
