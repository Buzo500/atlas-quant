# ATLAS Quant v0.1 · Entrega del 5 de septiembre de 2026

## Alcance real

Primera versión local funcional: cartera EUR, investigación con reglas sencillas, importación revisable, agente de investigación acotado, fuentes diarias y paper trading. El sistema no está conectado a cuentas de inversión y no puede enviar órdenes reales. La interfaz está preparada para pantallas pequeñas, pero su URL local no funciona desde otro dispositivo. El PDF del diseño mantiene su enlace privado independiente.

El backend es Python/FastAPI con SQLite en `var/atlas/atlas.sqlite3`. La interfaz React/TypeScript usa el scaffold Sites/Vinext y componentes Shadcn. El lanzador de v0.1 utiliza su servidor de desarrollo local, sin exposición de red. No se ha añadido infraestructura cloud, DuckDB, Parquet, un servicio Windows ni arranque automático al iniciar sesión. Cerrar el navegador no detiene el motor; cerrar el proceso, suspender el equipo o apagarlo sí.

## Cartera y convenciones financieras

- Importes contables calculados con Decimal; representación JSON numérica para mostrar resultados.
- Movimientos: depósitos, retiradas, compras, ventas, dividendos, comisiones y splits. EUR solamente; no cortos ni préstamos. El ratio de un split se indica como nuevas/antiguas.
- Libro mayor con identificadores estables. Reimportar un ID idéntico no duplica el movimiento; un ID con contenido distinto falla. La previsualización no modifica datos.
- P&L como patrimonio menos aportaciones netas. Coste medio de posiciones incluyendo comisiones y P&L no realizado.
- TWR diario con aproximación de flujos externos al final del día, declarada en resultados. No se calcula MWR/XIRR ni fiscalidad. La gráfica de patrimonio incluye aportaciones y no equivale a una curva de rentabilidad.
- No se admiten movimientos ni cotizaciones futuros. Las barras se validan, pero no se verifica de forma independiente cada sesión contra un calendario de bolsa.

## Investigación reproducible

Las estrategias disponibles en el núcleo son mantener, cruce SMA y momentum temporal de un único activo. La UI inicial compara mantener, SMA20/100 y SMA50/200. La IA puede proponer hasta ocho reglas mantener/SMA dentro del catálogo; no puede escribir ni ejecutar Python, instalar dependencias o modificar los límites.

La selección usa el primer 60% como historial de indicadores, 20% para elegir y el último 20% para probar al ganador. Las reglas no se entrenan mediante un modelo estadístico. El holdout se vuelve a simular con costes a 0,5×, 1× y 2× solo para ese ganador. El resultado sobre todo el historial se marca exploratorio. Crear otro experimento después de mirar el holdout puede introducir sesgo de selección humana: v0.1 lo advierte y registra, pero no impide reutilizarlo.

Señales basadas en cierres previos y ejecución en una apertura posterior, acciones enteras, volumen positivo, efectivo suficiente, comisiones fijas/proporcionales y deslizamiento. El peso máximo se aplica después de comisiones al precio de entrada. Estrategia, benchmark y paper comparten esa convención; la evolución del precio puede cambiar el peso después y no dispara rebalanceos. El efectivo no devenga interés.

Sharpe y volatilidad usan 252 sesiones y tipo libre de riesgo cero. Sharpe indefinido se muestra como no definido, no como cero. Drawdown se devuelve negativo; las políticas comparan su magnitud. No hay dividendos automáticos en backtesting, spread variable, impacto, libro de órdenes, profundidad ni ejecuciones parciales.

## Ciclo del agente

1. **Creación:** se guardan versión del conjunto, hash, hipótesis, política, costes, duración y presupuesto.
2. **Propuesta:** catálogo determinista sin coste, o una llamada a OpenAI/Anthropic. La respuesta debe superar un esquema y límites locales.
3. **Investigación:** candidatos comparados en validación; una estrategia congelada entra al holdout.
4. **Informe:** resumen del motor con cifras calculadas. Con IA, una segunda llamada puede explicar los resultados. Su texto es consultivo; cumplir JSON no garantiza que cada frase sea cierta. Las tablas del motor son la referencia numérica.
5. **Observación:** solo fechas posteriores al inicio y al último dato del experimento cuentan como sesiones nuevas. Se recalcula el resultado prospectivo de la regla congelada con efectivo inicial independiente. Releer el mismo fichero no suma sesiones.
6. **Cierre:** al alcanzar el plazo se guarda la conclusión. Sin evidencia suficiente no se ejecuta. No se amplía ni reoptimiza automáticamente el experimento.
7. **Simulación:** si pasan los criterios, existe autorización `auto_paper` y los límites globales lo permiten, comienza una cuenta virtual independiente desde ese momento. Se exige una sesión posterior para la primera señal y otra apertura posterior para el fill.

Los datos prospectivos importados se procesan después de recibirse. Son una reconstrucción determinista sobre barras diarias, no evidencia de que una orden hubiese llegado al mercado a tiempo. Las cuentas simuladas de distintos experimentos no comparten capital ni constituyen un riesgo agregado de cartera.

Política inicial: 48 horas de plazo, 126 observaciones OOS, 10 ejecuciones, Sharpe ≥0,5, drawdown máximo 15%, exceso de retorno ≥0 con costes normales y estresados, 20 sesiones posteriores como mínimo y resultado prospectivo válido. La fuente debe ser observada, reciente y sin incidencias de conciliación conocidas. Estos umbrales son configurables dentro de límites; no proporcionan una garantía estadística ni económica.

## IA y gasto

Las claves se leen de variables de entorno. `tools/run_atlas.py` carga opcionalmente `.env`, admitiendo exclusivamente `OPENAI_API_KEY` y `ANTHROPIC_API_KEY`. No las envía al proceso Node. No hay campos de claves en el navegador y no se registran respuestas crudas del proveedor. `.env` y `var/` quedan fuera de Git; el archivo local no está cifrado, por lo que requiere los permisos del usuario de Windows.

Endpoints oficiales fijos, sin URL de proveedor arbitraria, redirecciones, llamadas a herramientas ni reintentos automáticos. Límite de salida de 2.048 tokens por llamada, contenido acotado y presupuesto del experimento reservado **antes** de enviar la petición. Si el proceso muere con una llamada en curso, la reserva queda pendiente y el experimento pasa a interrumpido; no se repite la petición. Los costes comunicados por el proveedor no se truncan si exceden una estimación.

Precios de referencia, USD por millón de tokens, contrastados el 05/09/2026:

| Modelo | Entrada | Salida |
|---|---:|---:|
| OpenAI GPT-5.4 mini | 0,75 | 4,50 |
| Anthropic Claude Haiku 4.5 | 1,00 | 5,00 |

Ejemplo puramente aritmético: 8.000 tokens de entrada y 4.000 de salida sumados entre dos llamadas costarían unos 0,024 USD con GPT-5.4 mini según esos precios, antes de impuestos. No es una predicción del consumo de cada experimento. Presupuesto inicial del software: cero, hasta que el usuario configure uno. Los límites locales no sustituyen los límites de gasto de la cuenta del proveedor.

Fuentes: [Structured Outputs OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs), [modelo OpenAI](https://developers.openai.com/api/docs/models/gpt-5.4-mini), [Structured Outputs Anthropic](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [precios Anthropic](https://platform.claude.com/docs/en/about-claude/pricing).

## Datos y ejecución diaria

CSV: máximo 8 MB de entrada y 100.000 barras por conjunto. Moneda EUR por defecto documentada en las plantillas. Se conservan versiones completas, fecha, fuente declarada y SHA256. Las actualizaciones solo pueden añadir fechas posteriores para cada activo; revisiones o inserciones históricas requieren crear otro conjunto. La procedencia declarada de un CSV no verifica su exactitud.

Yahoo/yfinance es opcional, gratuito y orientado a investigación personal según sus condiciones. Confirma moneda e instrumento mediante metadata y descarga OHLC sin autoajuste ni reparación. Consulta cada seis horas con el ordenador activo; las consultas manuales se espacian al menos un minuto. No es un feed en tiempo real. Los días de la fecha UTC actual se excluyen deliberadamente.

Las filas sin ningún OHLC, volumen cero y sin cotización útil pueden excluirse con advertencias y fechas registradas, conservando acciones corporativas. Las filas parciales o incoherentes provocan un error. No se completan precios. El campo «Fin inicial» permite pedir un corte histórico de manera explícita; las siguientes actualizaciones intentan obtener todos los días cerrados. Un fallo conserva la versión anterior y bloquea su promoción automática.

Si Yahoo comunica dividendos, splits o ganancias distribuidas sin tratar, se bloquea la promoción. En v0.1 no existe todavía un flujo de conciliación corporativa que elimine ese bloqueo. Tampoco puede detectar todos los ajustes omitidos por el proveedor o por un CSV. [Documentación de yfinance](https://github.com/ranaroussi/yfinance).

## Persistencia y controles

SQLite usa transacciones y WAL, con versiones inmutables de datos, estados de experimentos, cuentas paper y registro de acciones. Las claves no se guardan en SQLite. No hay backup automático ni cifrado de la base; para copiarla de forma consistente, detén ATLAS y copia la carpeta `var/atlas` completa.

El kill switch es persistente y empieza activado. Cancela las órdenes paper pendientes y bloquea nuevas entradas/salidas; no liquida posiciones. Rearmar o reanudar consume las sesiones recibidas durante la parada sin crear operaciones retrospectivas. Una posición existente puede perder valor mientras la ejecución está parada. Los errores de datos o criterios bloquean nuevas órdenes; no sustituyen la gestión de una cuenta real.

HTTP solo en loopback; Host validado, origen autorizado y cabecera local obligatoria en mutaciones. No hay autenticación multiusuario: otro proceso que se ejecute con acceso al ordenador puede llamar a la API local. No expongas estos puertos a internet. El servidor de desarrollo de la interfaz es deliberado en esta entrega y deberá sustituirse antes de un despliegue compartido.

## Cobertura de los 16 requisitos originales

| Requisito | Evidencia en v0.1 | Pendiente relevante |
|---|---|---|
| Matemática y finanzas | Decimal, P&L, TWR y pruebas analíticas | MWR, FX, valoración de otros productos |
| Datos | CSV, validación, hashes y versiones | Calendarios y acciones corporativas completas |
| Modelos | Reglas limitadas y explicables | Modelos estadísticos avanzados |
| Validación temporal | Separación cronológica y forward congelado | Walk-forward múltiple, PBO/DSR y prevención sistemática de reutilización |
| Costes | Comisión, mínimo, deslizamiento y estrés | Spread, impacto y liquidez |
| Riesgo | Límites de peso, drawdown y kill switch | Riesgo agregado, VaR/ES y límites del bróker |
| Benchmark | Mismo símbolo, costes y exposición | Benchmark total return y atribución |
| Robustez | Sensibilidad de costes | Regímenes, parámetros y stress histórico amplio |
| Reproducibilidad | Versiones, política congelada y dependencias fijadas | Artefactos completos de entorno y backups |
| Tests | Motor, API, IA mock, datos, paper y recuperación | Soak 48h, cuenta paper externa, pruebas de navegador |
| Fiabilidad | Worker persistido, reservas y estados interrumpidos | Servicio del sistema y recuperación de fallos de infraestructura |
| Seguridad | Loopback, claves fuera del cliente, límites IA | Vault, cifrado, autenticación y despliegue remoto |
| Incertidumbre | Advertencias, NaN rechazado y narrativa consultiva | Intervalos y análisis estadístico de significación |
| Arquitectura | Módulos y adaptadores independientes | Adaptador IBKR y almacenamiento histórico especializado |
| Rendimiento | Trabajo acotado, un worker, límites de tamaño | Benchmarks de carga y grandes universos |
| Utilidad/coste | Cartera, laboratorio, CSV y demo sin API de pago | Operativa real y fiscalidad |

## Siguiente hito vigente

La prioridad aprobada el 06/09/2026 es **v0.2: fiabilidad y distribución local**, seguida de gráficos, datos/contabilidad, análisis y laboratorio. Consultar la [hoja de ruta](hoja_de_ruta.md) y el [plan de v0.2](plan_v0_2.md). Sus mejoras de arranque, compilación y copias se documentan en la [guía operativa](operacion_windows.md); las descripciones anteriores de servidor de desarrollo y ausencia de copias automáticas corresponden a la entrega original v0.1.

### Intención histórica de integración con bróker

Conectar IBKR primero en lectura y cuenta paper, identificar contratos con IDs del bróker, importar posiciones/efectivo/ejecuciones y conciliar antes de enviar órdenes. Después: máquina de estados durable de órdenes, idempotencia, comprobación de sesión y saldo, límites agregados, recuperación de desconexiones y mandato explícito por cuenta. Solo tras esas comprobaciones tendrá sentido habilitar dinero real y automatización. Esta v0.1 no se debe promocionar a real cambiando un booleano.
