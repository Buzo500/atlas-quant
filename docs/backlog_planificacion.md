# ATLAS · Cambios solicitados y plan de aprendizaje

Fecha: 6 de septiembre de 2026. Estado: planificación, sin implementación autorizada en este turno.

El usuario solicita guardar tres mejoras para futuras versiones: información al pasar el ratón por los gráficos, velas y otros tipos de gráfico, y una IA que acumule experiencia y aprenda de sus investigaciones. Pide estudiar si conviene entrenarla en local. La elección de arquitectura que aparece aquí es una recomendación del asistente, todavía no una decisión adoptada por el usuario.

Se mantienen las preferencias ya confirmadas: OpenAI y Anthropic seleccionables desde la app, presupuesto inicial cero y presupuesto decidido antes de cualquier consumo de IA; primero en el PC. No se han instalado modelos, lanzado entrenamientos, realizado llamadas pagadas ni modificado el motor o la base SQLite durante esta planificación.

## Pendientes de gráficos

### GRAPH-001 · Inspección del punto bajo el cursor

Solicitud del usuario: al pasar el ratón, mostrar máximos, mínimos, horas y la información habitual de una plataforma de inversión.

Alcance propuesto:

- Cursor en cruz, selección de la barra real más cercana y tarjeta o leyenda con apertura, máximo, mínimo, cierre y volumen (OHLCV).
- Fecha, hora y zona horaria cuando existan en la fuente; temporalidad, símbolo, moneda, origen y tipo de ajuste identificables. Con los datos diarios de v0.1, mostrar fecha/sesión; no inventar una hora intradía.
- Cambio absoluto y porcentual respecto al cierre anterior, con el criterio de ajuste visible.
- Leyenda coordinada con indicadores y operaciones si esas series están presentes.
- En la curva de patrimonio o de resultados, mostrar patrimonio/rentabilidad, benchmark y flujos relevantes. Un punto de NAV diario no tiene máximos y mínimos intradía disponibles: no fabricar OHLC para esa curva.
- Acceso equivalente mediante teclado y selección táctil para futuras pantallas pequeñas. Comportamiento explícito cuando falta un dato.

Criterio de aceptación: cada cifra del cursor coincide con el registro de origen de esa barra, incluyendo extremos del gráfico, huecos, redimensionado y zoom; las series sintéticas y las fechas sin hora no se presentan como ticks de mercado.

### GRAPH-002 · Tipos de gráfico

Solicitud del usuario: velas japonesas y otras visualizaciones habituales.

Orden recomendado:

1. Línea, área, velas japonesas y barras OHLC en gráficos de precios, con volumen, zoom y desplazamiento.
2. Temporalidades semanal/mensual agregadas a partir de OHLCV diario: primera apertura, máximo de máximos, mínimo de mínimos, último cierre y suma de volumen; señalar periodos incompletos. Esto no crea información intradía.
3. Heikin-Ashi, si aporta utilidad demostrable, como transformación visual claramente indicada. Renko, Kagi, Point & Figure y otros tipos quedan como opciones posteriores, sujetas a datos adecuados y a una necesidad concreta.

Cambiar el aspecto del gráfico no cambia los precios usados para fills ni la contabilidad. Heikin-Ashi/Renko y otras transformaciones pueden contener precios sintéticos; las pruebas de ejecución deben seguir usando precios de mercado observados con resolución suficiente. No se promete reconstruir la secuencia intradía de una vela diaria. [Advertencia técnica de TradingView sobre gráficos no estándar](https://in.tradingview.com/support/solutions/43000481029-strategy-produces-unrealistic-results-on-non-standard-chart-types-heikin-ashi-renko-etc/).

No se elige todavía biblioteca de gráficos. Se evaluarán cobertura, rendimiento, accesibilidad, licencia y coste de mantenimiento al implementar; no hace falta construir muchos estilos antes de resolver bien velas e inspección.

## AI-001 · Aprendizaje acumulativo: precisar qué debe aprender

El objetivo del usuario va más allá de consultas puntuales: quiere que ATLAS recuerde investigaciones, detecte patrones y mejore su criterio sobre qué estrategias funcionan en determinadas condiciones. Es un objetivo del sistema; no exige que todo ocurra dentro de los pesos de un modelo de lenguaje.

La v0.1 ya guarda experimentos y resultados. Aún no tiene un proceso de recuperación de esa experiencia para cada nueva investigación, ni modelos cuantitativos que se reentrenen con datos nuevos. Usar una API o un modelo local para generar respuestas no modifica automáticamente sus parámetros.

Se distinguen tres mecanismos:

| Mecanismo | Qué cambia con el tiempo | Uso propuesto |
|---|---|---|
| Memoria de investigación consultable | Base de datos de resultados y evidencias; contexto recuperado | Recordar pruebas, evitar duplicados, encontrar fallos y contradicciones |
| Modelo cuantitativo entrenable | Parámetros de una función numérica sobre datos y objetivos definidos | Estimar volatilidad/riesgo o estudiar si el contexto permite elegir mejor entre reglas |
| Ajuste de un LLM | Adaptadores o pesos de un modelo de lenguaje | Mejorar tareas concretas de especificación, clasificación o explicación, si se demuestra que compensa |

Entrenar un LLM con informes favorables no equivale a enseñarle una ventaja de inversión. Tampoco es necesario tenerlo en local para conservar la experiencia: una base local puede recuperar evidencia y pasar solo el contexto necesario a OpenAI o Anthropic. La documentación de OpenAI muestra la separación entre búsqueda de documentos y generación de respuestas; no obliga a alojar nuestra memoria en su servicio. [Retrieval](https://developers.openai.com/api/docs/guides/retrieval).

## Arquitectura recomendada: datos, memoria y modelos numéricos locales; LLM intercambiable

```text
Precios y acciones corporativas validados
                 ↓
Motor de backtests y decisiones registradas antes del resultado
                 ↓
Registro local completo: aciertos, fallos, costes y versiones
          ↙                                      ↘
Recuperación de evidencias                  Dataset cuantitativo
          ↓                                      ↓
OpenAI / Anthropic / futuro LLM local       Entrenamiento controlado
          ↓                                      ↓
Hipótesis y explicación consultiva         Evaluación temporal posterior
          ↘                                      ↙
         Candidatos versionados y comparación con alternativas fijas
                              ↓
               Reglas independientes de riesgo y ejecución
```

Es un esquema propuesto. No se han añadido estos componentes en el código.

### AI-002 · Memoria estructurada de investigación

Registrar familia de estrategia, variantes, hipótesis, universo y periodo, datos/versiones, código, costes, presupuesto de búsqueda y criterios decididos previamente. Conservar curvas y operaciones, además de métricas; incluir pruebas fallidas, errores, estrategias descartadas y razones de descarte.

Separar resultados de desarrollo, validación y evaluación posterior. Relacionar variantes que reutilizan la misma información para que no aparenten ser experimentos independientes. Marcar cada conclusión como hipótesis, evidencia observada, contradicha o pendiente de revisar, con enlaces a sus pruebas.

Antes de proponer una nueva prueba, recuperar evidencia relevante por estrategia, contexto y fecha. Empezar con filtros estructurados y búsqueda de texto; añadir búsqueda semántica si mejora la recuperación medida. No hace falta una base vectorial por costumbre.

Cuando se simule una decisión histórica, la memoria también debe respetar el corte temporal: excluir informes, resultados y noticias que aún no existían entonces. Un LLM moderno podría haber aprendido acontecimientos posteriores durante su preentrenamiento; por ello, sus interpretaciones históricas son material exploratorio y no una prueba limpia de capacidad prospectiva. La evaluación decisiva de ese componente tendrá que registrar recomendaciones antes de conocer nuevos resultados.

Criterios de utilidad: referencias correctas a experimentos, capacidad de recuperar también fracasos comparables, menor repetición de pruebas equivalentes y ausencia de cifras inventadas. La calidad narrativa no sustituye la calidad financiera.

### AI-003 · Modelo cuantitativo sobre contextos observables

Definir una pregunta medible antes de entrenar. Ejemplo de investigación: con volatilidad de las últimas sesiones, tendencia y liquidez conocidas en la fecha t, estimar el riesgo o el resultado neto de una regla durante un horizonte posterior. Alternativas iniciales: regresión regularizada y árboles pequeños; la selección concreta dependerá del objetivo y de los datos.

Cada ejemplo tendría fecha, activo, variables disponibles entonces, versión de regla y resultado futuro. El resultado solo se incorpora al entrenamiento cuando ya ha ocurrido. Las variables, escalados, umbrales de régimen y selección de características se estiman dentro del entrenamiento; no usando toda la serie.

No utilizar etiquetas retrospectivas como «antes de la crisis» para simular una decisión que no podía conocer esa crisis. Las series macro o fundamentales, si se añaden, necesitan fecha de publicación y revisiones conocidas en cada momento. No considerar cientos de ETF correlacionados como cientos de mercados independientes.

Comprobar si el selector añade valor a una regla fija o a una combinación estática con exposición comparable, después de costes. Si no la mejora de manera defendible, conservar la alternativa fija es un resultado correcto. Empezar con pocas familias de reglas mantiene el problema interpretable; no representa un umbral estadístico.

### AI-004 · Entrenar y evaluar sin contaminar el resultado

- Separación cronológica, evaluaciones en ventanas posteriores y datos reservados que no se usen para corregir repetidamente el modelo.
- Evitar que etiquetas cuyos horizontes se solapan atraviesen fronteras de entrenamiento/prueba; aplicar separaciones temporales según el objetivo, no un porcentaje universal.
- Registrar todas las variantes examinadas. Muchas búsquedas sobre la misma historia aumentan el riesgo de encontrar un ganador por azar.
- Evaluar también estabilidad, rotación, costes, riesgo y calibración si se producen probabilidades. La incertidumbre debe considerar dependencia temporal y entre activos; no se asume independencia de todas las filas.
- Fijar una revisión inicial, por ejemplo mensual, condicionada a disponer de etiquetas nuevas y datos suficientes. No reentrenar solo porque haya pasado una fecha ni promocionar automáticamente cada nueva versión.
- Mantener un modelo vigente y un candidato, guardar artefactos/versiones y permitir volver al anterior. Una versión nueva solo sustituye a la anterior cuando pasa la evaluación predefinida.
- Separar aprendizaje, propuesta, aprobación estadística y autorización de riesgo. No permitir que el modelo cambie por sí mismo sus límites de pérdida o la política de ejecución.

Seis meses aportarían aproximadamente 120–130 sesiones nuevas, según calendario; no 120–130 por cada backtest sobre la misma historia. Una prueba operativa de meses puede encontrar errores de funcionamiento sin demostrar rentabilidad. No existe un número fijo de backtests que garantice una ventaja.

El problema de búsqueda repetida y sobreajuste está formalizado por [White, 2000](https://users.ssc.wisc.edu/~behansen/718/White2000.pdf) y [Bailey et al., The Probability of Backtest Overfitting](https://carmamaths.org/resources/jon/backtest2.pdf). Registrar predicciones antes de resultados sigue el enfoque de evaluación secuencial de [Dawid, 1984](https://people.csail.mit.edu/jrennie/trg/papers/dawid-prequential-84.pdf).

## API frente a un LLM local

| Opción | Ventajas para ATLAS | Costes y límites | Recomendación |
|---|---|---|---|
| API + memoria y ML locales | Conserva conocimiento entre proveedores; evita servir un LLM; permite comparar OpenAI/Anthropic sobre las mismas tareas | Consumo por uso, internet y envío del contexto seleccionado; calidad por medir | Primera opción propuesta |
| LLM local + memoria y ML locales | Mayor control del modelo y posibilidad de no enviar contexto a un proveedor | Memoria gráfica, energía, mantenimiento, calidad/latencia por medir | Piloto opcional posterior |
| Ajuste de un LLM local | Adaptación de tareas estrechas con ejemplos revisados | Preparar dataset y evaluación, memoria adicional, riesgo de sobreajuste | Solo si un caso concreto supera al modelo sin ajustar |
| Entrenar un LLM desde cero | Control completo en teoría | Necesidades desproporcionadas de datos y cómputo para este proyecto | Descartado como recomendación inicial |

La comparación no es «una IA con memoria» frente a «una IA sin memoria»: ambas ubicaciones pueden usar el mismo registro de investigación. Tampoco equivale local a gratuito: no tiene facturación de inferencia de un proveedor, pero usa electricidad, equipo y mantenimiento.

La documentación oficial de OpenAI consultada el 06/09/2026 indica que está retirando su plataforma de fine-tuning: no admite nuevos usuarios y distingue la continuidad temporal para usuarios existentes. No se debe basar esta arquitectura en que podamos ajustar por API los modelos elegidos en v0.1. Esto no es una retirada de la API normal de inferencia. [Estado del fine-tuning de OpenAI](https://developers.openai.com/api/docs/guides/supervised-fine-tuning).

Los datos de la API de OpenAI no se usan por defecto para entrenar sus modelos salvo participación explícita; esto es distinto de la retención de datos y de nuestro propio aprendizaje local. No se presupone que las políticas de todos los proveedores sean idénticas. [Controles de datos](https://developers.openai.com/api/docs/guides/your-data).

## Viabilidad en el PC actual

Consulta local de hardware, sin ejecutar modelos: Intel Core Ultra 9 185H, 32 GiB de RAM instalada y NVIDIA RTX 2000 Ada Generation Laptop GPU. `nvidia-smi` informa 8.188 MiB de memoria gráfica total, aproximadamente 8 GiB. La comparación oficial de NVIDIA también especifica 8 GB para el modelo portátil; no confundirlo con tarjetas de escritorio de nombre parecido. [NVIDIA](https://www.nvidia.com/en-gb/products/workstations/professional-laptops/compare/).

Estimación de viabilidad, no benchmark de este portátil:

- Modelos cuantitativos pequeños: equipo adecuado para un piloto con pocos activos y variables; medir RAM, duración y calidad antes de ampliar.
- Inferencia de un LLM local: comenzar con 1–4 mil millones de parámetros cuantizados; 7–8 mil millones a 4 bits podrían probarse con contexto moderado y poca concurrencia. No se promete una velocidad concreta.
- Como referencias de tamaño, los repositorios oficiales de Qwen3 publican archivos Q4_K_M de aproximadamente 2,50 GB para 4B y 5,03 GB para 8B. El archivo no es la memoria total: faltan caché del contexto, buffers y otros usos de la GPU. Son ejemplos de candidatos de evaluación, no una recomendación de que sean los mejores modelos disponibles. [Qwen 4B](https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/main), [Qwen 8B](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/main), [caché de contexto](https://huggingface.co/docs/transformers/main/en/kv_cache).
- Un ajuste ligero de adaptadores mediante QLoRA podría estudiarse en modelos pequeños, con secuencias/lotes limitados. QLoRA congela el modelo base cuantizado y entrena adaptadores: no implica que quepa el entrenamiento completo de cualquier modelo en 8 GB. [Artículo original](https://arxiv.org/abs/2305.14314), [documentación PEFT](https://huggingface.co/docs/peft/developer_guides/quantization).

No se recomienda comprar otra GPU ni migrar de sistema operativo para este paso. Si se decide probar entrenamiento local, se validarán entonces las herramientas y su compatibilidad en Windows/WSL/Linux; no se ha instalado ni probado ese entorno.

## Orden de trabajo propuesto cuando se retome la implementación

| Etapa | Entrega concreta | Condición para avanzar |
|---|---|---|
| A | Inspección interactiva, velas y tipos básicos | Fidelidad al OHLCV, lectura correcta de fechas, ausencia de datos inventados |
| B | Tratamiento de datos pendiente y memoria estructurada de investigaciones | Experimentos reproducibles y recuperación verificable de evidencia; los datos defectuosos no pasan al aprendizaje |
| C | Primer modelo numérico pequeño y evaluación temporal | Objetivo definido, etiquetas maduras, comparaciones fijas y resultados posteriores defendibles |
| D | Comparativa del LLM actual por API con un candidato local | Medir calidad en español, especificaciones válidas, recuperación fiel, latencia, memoria y coste |
| E | Posible ajuste de adaptadores de lenguaje | Fallo concreto no resuelto por contexto/prompts y mejora demostrada en evaluación separada |

Las etapas no tienen fecha de inicio aprobada. La planificación no inicia trabajos en segundo plano ni experimentos pagados. Las horas de desarrollo y costes se estimarán al acotar cada etapa; no se fija ahora un calendario de meses que presuponga que el mercado ofrecerá suficiente evidencia.
