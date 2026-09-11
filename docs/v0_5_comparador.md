# v0.5 · Fichas, comparación y correlaciones

11/09/2026. Autorizadas las cinco tareas propuestas: caso guiado de planificación, fichas/comparador, correlaciones, revisión de cierre v0.5 y definición inicial de v0.6. Rama `codex/v0.5-comparador`, identificación de desarrollo `0.5.0-dev.3`, esquema 5. Copia previa `backups/atlas-20260911T063013799897Z-4089e6f6`.

## Reglas del comparador

- Entre uno y doce activos/fuentes versionadas, nativas EUR/USD o conjuntos anteriores EUR. Identidad explícita del catálogo, sin unir instrumentos por su ticker. Rango de hasta 3.660 días, final anterior al día UTC en curso; moneda de comparación EUR. Límite de 200.000 barras de origen sumadas sin duplicar versiones compartidas. El selector consulta los últimos 500 conjuntos y las últimas 500 series FX; no descarga fuentes.
- Primera política `atlas-asset-analysis-v1`: **evolución de precios brutos**, sin dividendos, impuestos ni costes. No equivale a rentabilidad total ni a TWR de una cartera. Exige base bruta y calendario acreditados para las métricas; la ficha sigue identificando las fuentes que no cumplen los requisitos. No cambia las restricciones de investigación o valoración existentes.
- Conversión USD usando una versión FX explícita. Cada cierre necesita observación FX de esa misma fecha, disponible al final del día UTC; no arrastra otra fecha ni realiza conversiones de efectivo.
- Retorno simple entre sesiones consecutivas del calendario acreditado. Se descartan los intervalos con un extremo ausente o no disponible; nunca se salta sobre una sesión abierta sin precio. Los fines de semana/festivos solo se reconocen por el calendario suministrado.
- Comparación normalizada a 100 en fechas observadas comunes; se informa el periodo común efectivo. Las fichas muestran cobertura, variación de precio, volatilidad muestral por sesión y anualizada con la convención explícita de 252 sesiones, y caída máxima. Métricas completas solo con cobertura íntegra del periodo solicitado; sin sustituir una cifra no disponible por cero.
- Pearson sobre variaciones, no sobre niveles de precio; misma muestra de intervalos exactos para toda la matriz. Mínimo 20 intervalos comunes; una serie constante tiene correlación indefinida, incluida su diagonal. La muestra mínima es una decisión de producto, no garantía de robustez estadística. Una correlación histórica no determina causalidad ni persistencia futura.
- Splits conocidos sin ajustar que atraviesen el intervalo impiden métricas; los dividendos se identifican como excluidos de esta base. No se inventan eventos no registrados ni ajustes.
- Resultado inmutable con entradas, versiones, huellas, catálogo y revisión de eventos. Cálculo fuera del escritor, previsualización y confirmación atómica con contexto vigente. Guardar solo escribe informe/auditoría y no afecta a libros, objetivos o permisos operativos.

Referencia de la biblioteca estándar para desviación muestral y Pearson: [documentación de statistics](https://docs.python.org/3/library/statistics.html). Los importes/conversiones usan Decimal; las estadísticas se serializan con precisión explícita.

## Aceptación

Casos independientes: precios 100→110 y FX 0,90→0,95 producen variación EUR 16,111… %; precio constante en USD con FX variable tiene variación EUR; Pearson +1/−1 y serie constante; muestras/fechas distintas, huecos y FX ausente sin interpolación; eventos/splits y base no acreditada; revisión de fuente durante el cálculo; rollback, idempotencia, recuperación y ausencia de escrituras contables. Interfaz, estados vacíos y anchos 390/1280/3440. El caso guiado es sintético; la valoración personal y el ensayo de 48 horas siguen aplazados.

La revisión con el usuario se registra separada de las pruebas del agente. [Caso guiado](v0_5_ejemplo_guiado.md), [matriz de cierre v0.5](v0_5_cierre.md) y [primer contrato v0.6](v0_6_alcance_inicial.md); no se implementa aún el evaluador DSL.

## Uso

En **Datos → Fichas y comparador de activos → Abrir comparador**, añade las fuentes y elige inicio/fin. Para USD, selecciona una serie EUR por USD explícita. Calcula, revisa las fichas, las fechas efectivas y la matriz; guarda para conservar las cifras/versiones. Puedes reabrirlas en Comparaciones guardadas. Si una fuente cambia, selecciona la versión actual para calcular de nuevo; los informes anteriores mantienen sus cifras y señalan el cambio de contexto.

Las fuentes Yahoo/legacy sin evidencia acreditada conservan su ficha y último precio recibido, pero no reciben métricas supuestamente verificadas. No inventar calendarios ni ajustes para forzar un resultado. Para un cálculo contrastado hay que importar/declarar esa evidencia con el flujo de calidad existente. Las tablas se desplazan horizontalmente cuando hace falta; no desbordan la página en pantallas estrechas.

Rutas tipadas `/api/v2/asset-analysis/sources` y `/api/v2/asset-analysis/reports` (previsualización/confirmación, historial paginado, informe por ID). Política Decimal con 12 decimales para estadísticas; presentación de hasta cuatro decimales. Una cifra mostrada redondeada no altera los cálculos ni las fuentes. Esquema 5, registros de informe y resumen nuevos; el libro no cambia.

## Validación local del 11/09

808 Python + 91 subcasos (25 pruebas específicas nuevas), 294 frontend (siete nuevas), ocho Node, contratos/tipos/lint y compilación canónica correctos. Pruebas nuevas de recuperación, auditoría fallida, confirmaciones concurrentes, revisión durante cálculo, legado, límites de tamaño/fecha, calendarios diferentes, retorno constante y huecos sin interpolar. Dos ajustes del propio arnés —fecha sintética del día UTC en curso y selector ambiguo de avisos— quedaron resueltos antes de la batería final.

E2E completo `e2e-fb3c520ba00b4cf489147f1c2b7c799a`: **20/20**, 1,4 min, sin reintentos, integridad y limpieza correctas, base habitual exactamente intacta. El recorrido nuevo añade EUR/USD, 24 intervalos comunes, guardado y reapertura; capturas revisadas a 390/1280/3440. Recorrido individual previo `e2e-603df8f091494742afbd188753a44099`: 1/1. No equivale a una nueva validación de escala física de Windows ni al ensayo aplazado.

CI/publicación de dev.3 todavía no ejecutadas. La entrega publicada sigue siendo dev.2; sus cifras de CI no certifican estos cambios locales.

Carga con `tools/benchmarks/benchmark_v05_asset_analysis.py`: 10 fuentes, 100.000 precios, 10.000 cambios FX y 10.000 movimientos; análisis de 3.660 sesiones en 1,010–1,063 s, pico adicional 136,22 MiB. Controles por servicios con Store independiente, p95 0,00197 s mientras se calculaba. Límites de aceptación (<5 s, <256 MiB, controles <1 s) cumplidos; no es una medición de latencia de red ni de equipos distintos.

Revisión final con datos habituales: los dos históricos NVD.DE tenían el mismo nombre en el selector. Se añade ID breve a precios y FX para distinguir fuentes homónimas, con séptima regresión de interfaz. Batería frontend final 294/294, tipos/lint correctos, build canónico renovado; recorrido específico `e2e-c0a5b47cbf9742c197e53b2c9909b215` 1/1, integridad/base habitual/limpieza correctas. La batería completa 20/20 anterior cubre el resto; el ajuste posterior es solo de etiquetas y su prueba.

Operación final: run `a613d9c6f25e4a2ead2b4d0ea0c47063`, salud `0.5.0-dev.3`, esquema 5 e integridad correctos. Las tres carteras, sus libros/respuestas EUR y las tablas históricas coinciden con la copia previa. Sin informes ficticios en la base habitual, parada global activa, gasto/reserva cero. Evidencia `output/validation/v05-comparator-ordinary-online.json`. Interfaz conectada y fuentes NVD distinguidas visualmente por `689ac9b5` / `4fc6914f`. La parada del run anterior fue cooperativa y liberó ambos procesos.

La consulta automática Yahoo al arrancar recibió una fila parcial del 10/09 sin cierre. Se rechazó conservando ambos históricos en v2 hasta el 09/09; solo cambian metadatos operativos del feed. No se relajó la validación. El éxito de la descarga del 10/09 a las 19:55 UTC, descrito en dev.2, sigue siendo antecedente válido, no una garantía de datos completos hoy.

Arrancar en este equipo: `Abrir-ATLAS.cmd`. Detener: `Detener-ATLAS.cmd`. ATLAS queda iniciado con la compilación final; para editar/reconstruir, detenerlo antes. El caso guiado y el cierre funcional siguen pendientes de la respuesta del usuario; no se ejecutó CI remota ni se publicó una nueva etiqueta.
