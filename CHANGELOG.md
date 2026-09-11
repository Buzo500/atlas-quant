# Cambios de ATLAS Quant

## 0.6.0-dev.3 · Sensibilidad y candidatas · 2026-09-11

- Sensibilidad opcional congelada con el protocolo: una media o los costes cada vez, máximo ocho casos; mismo motor, cuentas independientes y prueba final cerrada.
- Métricas, curvas, motivos, huellas y reproducción; no optimiza parámetros ni aprueba estrategias. Límites combinados de cálculo con walk-forward.
- Registro de hipótesis, seguimiento y descartes, hasta 20 protocolos y 100 revisiones. Evidencia capturada por revisión, vínculos acumulativos, control optimista y auditoría atómica.
- API local y contratos TypeScript regenerados; interfaz con protección de borradores/concurrencia y fechas con zona. Esquema 5, libros e identidades previas conservados.
- [Guía y validación](docs/v0_6_sensibilidad_candidatas.md): 990 Python + 91 subcasos, 317 frontend, ocho Node y 23 E2E locales. Publicación/CI final según continuidad.
- Rama subida sobre `8e4d087`, [CI gratuita 34600509327 correcta](https://github.com/Buzo500/atlas-quant/actions/runs/34600509327) con las mismas 990+91/317/8/23 pruebas y arranque/parada; 0 USD facturables. ATLAS habitual arrancado y todas las tablas conservadas. Cierre posterior solo documental; sin fusión/etiqueta.
- [CSV observado](docs/v0_6_csv_observado.md) auditado y no apto por falta de evidencia. [API](docs/diagnostico_api_20260911.md) no reproduce la espera en 301 lecturas; incidencia abierta, sin cambios especulativos de transporte.

## 0.6.0-dev.2 · Walk-forward con parámetros fijos · 2026-09-11

- Ventanas móviles de contexto/evaluación dentro del desarrollo, con configuración y criterios congelados antes del cálculo; reserva final intacta.
- Calentamiento SMA con cierres anteriores y cuenta nueva por evaluación; sin operaciones durante el calentamiento ni posiciones heredadas. Reutiliza evaluador, política económica y libro nativo.
- Informe por ventana con contexto, curvas, operaciones, benchmarks, motivos y diagnóstico agregado. Los datos ausentes y las ventanas incompletas se muestran explícitamente; no capitaliza cuentas independientes ni autoriza estrategias.
- Publicación atómica junto al protocolo y auditoría, reproducción y contratos API regenerados. Protocolos previos mantienen identidad y resultados. [Uso, límites y pruebas locales](docs/v0_6_walk_forward.md). Sin nueva CI remota, fusión ni etiqueta.

## 0.6.0-dev.1 · Laboratorio temporal · 2026-09-11

- CSV nativo EUR y evidencia explícita de aperturas, calendario, disponibilidad y ausencia de eventos corporativos.
- Protocolos SMA congelados, historial paginado, reproducción y guardado con auditoría atómica.
- Desarrollo y prueba final separados, reserva explícita y exposición persistida por instrumento/fechas.
- Efectivo y comprar/mantener con costes, lotes y límites compartidos; NAV, rentabilidad, caída máxima y operaciones simuladas.
- Interfaz en Laboratorio, contratos HTTP/TypeScript, esquema 5 y libros anteriores conservados. [Guía y validación](docs/v0_6_laboratorio.md).
- Rama subida; CI final 34590252591 correcta sobre e797ca3: 929 Python + 91 subcasos, 297 frontend, ocho Node y 21 E2E, instalación/arranque/parada y gasto 0 USD. No fusiona PR #12 ni publica etiqueta.

## v0.6 · Simulación económica local, sin etiqueta de aplicación · 2026-09-11

- Simulador EUR offline sobre el evaluador SMA compartido y `NativeBook`: lotes, comisiones fijas/proporcionales, deslizamiento, siguiente apertura estricta y consumo en memoria sin efectos duplicados.
- Límites de efectivo y exposición, caducidad y ausencia de datos explícitas; objetivo lógico separado de posición simulada. Correcciones y fallos no publican un libro parcial.
- CLI `tools/run_sma_simulation.py`, informe con entradas/código/costes y reconstrucción verificable. Referencia ficticia 1.000 → 818 EUR; no escribe carteras habituales ni envía órdenes.
- 48 pruebas nuevas; regresión 909 Python + 91 subcasos. Contratos HTTP/build coherentes, esquema 5 y UI/API dev.3 conservados. [Uso, pruebas y pendientes](docs/v0_6_simulacion.md).
- Rama solo local, sin nueva CI remota, push ni etiqueta. Revisión manual del portátil aplazada por el usuario; PR #12 continúa pendiente de aceptación.

## v0.6 · Primer bloque local, sin etiqueta de aplicación · 2026-09-11

- Contrato restringido y evaluador puro SMA20/50, política `sma-cross-evaluator-v1`, calendario/datos explícitos, objetivos por presupuesto y comparación exacta.
- Replay e incremental comparten transición; checkpoints, duplicados, huecos, eventos corporativos y expiración temporal comprobados. No produce órdenes ni fills.
- Referencia sintética ejecutable con `tools/run_sma_reference.py`; 53 casos nuevos y regresión total 861 Python + 91 subcasos. [Uso y límites](docs/v0_6_evaluador.md).
- Rama `codex/v0.6-evaluador` solo local; UI/API permanecen en dev.3, esquema 5. La integración con datasets y la simulación económica quedan pendientes.

## v0.5.0-dev.3 · PR y CI correctas · 2026-09-11

- Fichas y comparador de activos en Datos: identidad/versiones, precio EUR, cobertura, volatilidad y caída máxima, comparación normalizada sobre fechas comunes.
- Pearson de variaciones simples EUR con la misma muestra de intervalos para todas las celdas; ausencia/constancia explícitas, sin interpolación.
- Informes revisados e inmutables, historial y recuperación, sin escribir libros ni activar objetivos. Política `atlas-asset-analysis-v1`, esquema 5.
- Caso guiado de planificación, matriz de cierre funcional v0.5 y primer contrato SMA 20/50 de v0.6, todavía sin implementar.
- 808 Python + 91 subcasos, 294 frontend, ocho Node y 20 E2E, también en CI gratuita 34578070191 sobre `ccb4b4a`; tipos/lint/contratos/build y arranque/parada correctos. PR #12; revisión manual/fusión/etiqueta según [registro de entrega](docs/v0_5_dev3_entrega.md). Gasto facturable 0 USD.

## v0.5.0-dev.2 · Publicado · 2026-09-10

[PR #11](https://github.com/Buzo500/atlas-quant/pull/11) fusionada mediante squash `bde915bb775572eaaf18b2ef360df6dc8023ab39`; etiqueta anotada `v0.5.0-dev.2` verificada en remoto. [CI gratuita 34525527095](https://github.com/Buzo500/atlas-quant/actions/runs/34525527095) correcta sobre `e6f462568ee02614e756809e7fa2971fdfeb1caf`: 783 Python + 91 subcasos, 287 frontend, ocho Node, 19 E2E y arranque/parada. Fuentes integradas iguales a las validadas; cierre documental posterior. 0 USD facturables.

- Simulador de aportaciones y rebalanceo: lotes, comisiones, prioridad determinista, caja EUR/USD separada, remanentes y límites posteriores. Sin órdenes ni escrituras contables.
- Objetivos combinados por presupuestos de estrategias manuales, sin doble asignación ni relajación de los límites globales.
- Referencia total-return en EUR por CSV, fechas exactas y TWR acumulado; escenarios de precio/FX con efecto sobre cartera, efectivo y derechos.
- Informes inmutables, entradas/fuentes y contexto, previsualización/confirmación, historial y restauración. Esquema 5.
- Nuevo panel analítico en Cartera; regresiones, carga y recorrido aislado. Un test previo de cobros ahora espera a que aparezca la opción del selector, evitando una carrera en la propia prueba.
- [Guía y límites](docs/v0_5_planificacion.md). Descarga Yahoo real validada: dos históricos NVD.DE actualizados hasta el 09/09, versiones anteriores intactas y TLS verificado. Ensayo y movimientos personales aplazados.

## v0.5.0-dev.1 · Publicado · 2026-09-10

[PR #10](https://github.com/Buzo500/atlas-quant/pull/10), [CI gratuita 34517010948](https://github.com/Buzo500/atlas-quant/actions/runs/34517010948) correcta sobre `1992eb5442dbed8e1abb33846901271114884e91`: 739 Python + 91 subcasos, 283 frontend, ocho pruebas Node y 19 E2E; arranque/parada correctos. 0 USD facturables. Cierre documental posterior. PR #10 fusionada en e23f79f y etiqueta v0.5.0-dev.1 publicada.

- Objetivos manuales por instrumento/efectivo, bandas y límites; borradores inmutables y activación explícita con revisión concurrente.
- Diagnóstico de pesos y desviaciones EUR sobre cortes D6; cotizaciones/derechos agregados, calidad y contexto históricos. Sin cálculos de compras, órdenes ni reservas ficticias.
- Tabla y editor en Cartera, anchos 390/1280/3440; API tipada, auditoría atómica y restauración sobre esquema 5.
- Transporte Node mantenido: conexión upstream propia hasta recibir el cuerpo, cierre/cancelación explícitos, bytes conservados y operaciones sin reenvío automático. Se conserva el bucle Python original.
- [Guía, pruebas y rendimiento](docs/v0_5_objetivos.md), [diagnóstico del transporte](docs/diagnostico_api_20260910.md). Yahoo 429 sigue pendiente externamente; ensayo y movimientos personales aplazados.

## v0.4.0-dev.6 · D7/D8 · Publicado · 2026-09-10

PR #9 fusionada mediante squash `53cca20654c6c8a9bfc665e2b22f219f3ea85607`, etiqueta anotada `v0.4.0-dev.6` (objeto remoto `3ec9d901829afbcb284c6fe1ff34996d31d81086`). CI gratuita [34509155203](https://github.com/Buzo500/atlas-quant/actions/runs/34509155203) correcta sobre `211ca49f4427e2730dc326178fce7b845c9d2ca1`; árbol integrado idéntico. Coste final 0 USD facturables. Registro documental posterior a la etiqueta.

- P&L, flujos/costes, TWR diario por tramos y MWR/XIRR anual por periodo, con calidad, convenciones y motivos de indisponibilidad.
- Informes inmutables, revisión/confirmación y contexto versionado; historial, curva existente y tablas paginadas en Cartera.
- Reductor único del libro con avance incremental, máximo dos cálculos pesados y controles disponibles; esquema 5 conservado.
- 709 Python + 91 subcasos, 278 frontend y 19 E2E; migración, recuperación y carga de 100.000 barras/10.000 movimientos correctas. [Evidencia D8](docs/v0_4_d8.md).
- Primer alcance v0.5 definido, sin implementar. API intermitente y descarga Yahoo siguen con límites documentados; ensayo y datos personales aplazados.

## v0.4.0-dev.5 · D6 completo · Publicado · 2026-09-10

PR #8, squash `a308f81`, CI gratuita 34503177151 correcta sobre `a356112`; árboles iguales y etiqueta anotada publicada.

- Esquema 5 aditivo, API versionada para saldos y documentos EUR/USD; compatibilidad EUR conservada.
- Conversiones con importes reales/comisión, conciliación por moneda, correcciones atómicas y dividendos/splits USD.
- CSV de precios EUR/USD y FX versionados, evidencia/calendarios explícitos, vínculos y cortes de patrimonio EUR inmutables. Formularios multidivisa y detalle de procedencia.
- Lecturas SQLite coherentes de solo lectura y verificación breve antes de publicar; rendimiento y recuperación dentro del objetivo D6. [Uso y evidencia](docs/v0_4_d6_cierre.md).
- Caché Yahoo dentro de los datos ATLAS; diagnóstico TLS/429 y latencia API todavía abiertos.
- 677 Python + 91 subcasos, 270 frontend y 19 E2E correctos.

## v0.4.0-dev.4 · D5 · Publicado · 2026-09-10

[PR #7](https://github.com/Buzo500/atlas-quant/pull/7) fusionada mediante squash en `a91f077648f209e49dfba2c630fd2c6ccecfd1a0`; etiqueta anotada verificada en remoto. [CI 34479828915](https://github.com/Buzo500/atlas-quant/actions/runs/34479828915) correcta sobre `5c3e8a7453418d2f5b7f6eb3feddefa44c28db92`, con árbol integrado idéntico: 623 Python + 91 subtests, 266 frontend y 18 E2E. Instalación limpia, build, contratos, tipos, lint, arranque/proxy y parada correctos; 0 USD facturables. Este registro documental es posterior a la etiqueta.

- Eventos corporativos EUR con identidad compartida, fuentes explícitas, propuestas, revisiones y cancelaciones inmutables.
- Derechos de dividendo separados del efectivo; elegibilidad acreditada a exfecha, bruto/retención/comisión explícitos, enlace de cobro existente sin doble abono y un pago completo por derecho.
- Splits y reverse splits exactos, coste total conservado y validación de operaciones posteriores. Fracciones solo acreditadas y representables con hasta 12 decimales. Compatibilidad de precios separada del efecto contable; no habilita investigación global.
- Previsualización y confirmación atómicas con auditoría, revisión conjunta de dependencias, historial/cortes y evidencia JSON. Formularios en Datos, derechos en Cartera y CSV propios sin nuevas dependencias.
- Corregida la inicialización del formulario con derechos de una revisión anterior a la cartera; tres regresiones permanentes cubren el orden de respuestas y la conservación del borrador, sin aumentar tiempos ni introducir reintentos.
- Migración aditiva 3→4 y recuperación aislada; carteras/políticas antiguas intactas. D6–D8, movimientos personales y ensayo sostenido pendientes. [Contrato, límites y pruebas](docs/v0_4_d5.md); [cierre local/remoto](docs/CONTINUIDAD.md).


## v0.4.0-dev.3 · D4 · Publicado · 2026-09-10

[PR #6](https://github.com/Buzo500/atlas-quant/pull/6) fusionada mediante squash en `39d922cf63a95c4f39fbe8f35e88047d86d2807f`; etiqueta anotada verificada en remoto. [CI 34456773938](https://github.com/Buzo500/atlas-quant/actions/runs/34456773938) correcta al primer intento sobre `aa7ad176b5d851ca093f05689386e2942d2bc935`, árbol integrado idéntico: 570 Python + 91 subtests, 255 frontend y 14 E2E. Instalación, build, contratos, tipos, lint, arranque/proxy y parada correctos. La especificación posterior de D5 no forma parte del código de esta etiqueta.

- Libro exacto EUR optativo al crear cartera: CSV v2 para depósitos, retiradas, compras, ventas y comisiones, costes y cantidades decimales sin precios. Carteras y resultados anteriores preservados; NAV/TWR v2 pendientes de D6/D7.
- Extractos completos EUR: saldos de referencia, diferencias explícitas e historial consultable; guardar un informe no ajusta el libro. Reimportación por identidad externa, conflictos visibles y bruto declarado revisado.
- Anulación/sustitución con motivo y versiones enlazadas, previsualización, validación de historia posterior y confirmación atómica con auditoría. Consultas por corte/revisión y respuestas paginadas.
- Migración aditiva 2→3 y backup/restauración; diagnóstico de persistencia ampliado. Interfaz en Datos/Cartera, plantillas y evidencia JSON. [Contrato, uso y pruebas](docs/v0_4_d4.md).

## v0.4.0-dev.2 · D3 · Publicado · 2026-09-09

PR #5 fusionada mediante squash en `cdb59b1461d3d26ff88d6f7de90bdf4534ca5fe3`; etiqueta anotada publicada. CI [34376199945](https://github.com/Buzo500/atlas-quant/actions/runs/34376199945) correcta sobre `864097448b8200c8d9c8b0295598c84ba465fcf9`; árbol integrado idéntico. Incluye arquitectura documental y hoja de ruta, sin implementar sus módulos futuros.

- Calidad por serie/fecha: calendario explícito versionado, cobertura, antigüedad y disponibilidad histórica. Estados separados para dibujo, valoración de precios, investigación exploratoria, investigación acreditada al cierre y promoción paper.
- Calendario y evidencia CSV previsualizados; confirmación protegida frente a cambios concurrentes. No deduce festivos ni disponibilidad desde descargas. Informes paginados fuera de `/api/state`.
- Revisión expresa de precios históricos con motivo, nueva versión, evidencia afectada invalidada y feed pausado. Versiones anteriores y vínculos de cartera intactos; una revisión posterior detiene el seguimiento de experimentos congelados conservando sus resultados.
- Los experimentos nuevos usan `quality-v1` y exigen calidad antes de promoción; cuentas anteriores mantienen su política. La cartera identifica calidad de fuentes sobre sus cifras heredadas, sin cambiar contabilidad ni conciliar eventos automáticamente.
- Interfaz crema/cobre conservada, formularios revisables, tabla por fecha y pruebas de concurrencia, recuperación, controles y navegador. [Reglas y evidencia](docs/v0_4_d3.md).

## v0.4.0-dev.1 · D2 · Publicado · 2026-09-09

PR #4 fusionada y etiqueta anotada sobre `77f8fa0a0056a94f65b257a05ff6f0a79b1d982e`. CI [34365374994](https://github.com/Buzo500/atlas-quant/actions/runs/34365374994) correcta sobre las fuentes D2; integración con contenido idéntico. Entrega de desarrollo, sin ensayo de 48 horas ni declaración de estabilidad.

- El lanzador permite configurar `REQUESTS_CA_BUNDLE` desde `.env`, manteniendo precedencia del entorno y verificación HTTPS. Resuelve en este PC la confianza de la raíz de inspección de Avast mediante un bundle local. 48 pruebas runtime/feed y 28 subtests, descarga y gráfico NVIDIA comprobados; detalle en `docs/diagnostico_yahoo_windows.md`.

- Catálogo con IDs estables para instrumento/cotización, mercado y moneda declarados, códigos externos y alias por proveedor/periodo. Altas revisionadas; ninguna fusión por ticker o ISIN.
- Carteras/libros separados de los conjuntos. Fuentes de precios explícitas y fijadas por versión, previsualización y confirmación protegidas frente a cambios concurrentes. Lectura de cortes históricos y movimientos originales.
- Migración transaccional SQLite 1 → 2, archivo legado intacto y un único libro activo. Copias/restauración compatibles con ambos esquemas; bloqueo de migración ante otro ejecutor. La comprobación de persistencia operativa incluye las nuevas tablas, sin reactivar el ensayo aplazado.
- Datos incorpora catálogo y configuración de cartera; Cartera mantiene su selección aunque cambie el conjunto de investigación. Importación CSV v1 existente dirigida a la cartera elegida. Editor CSV acotado con desplazamiento interno y corrector ortográfico desactivado.
- El sondeo del estado mantiene estable el texto de la última consulta cuando hay datos, evitando saltos de altura que cerraban la ficha de precios en pantallas estrechas. Carga inicial y errores siguen visibles; regresión con sondeo real en navegador.
- Conserva contabilidad EUR heredada, controles y resultados de investigación. USD solo en el catálogo; D3–D8, LaTeX, aprendizaje, remoto y móvil pendientes. [Evidencia y límites D2](docs/v0_4_d2.md).

## v0.3.0-dev.1 · Gráficos interactivos · 2026-09-08

Cierre de desarrollo aceptado el **09/09/2026**: G1–G6 cerradas por decisión expresa del usuario. Pantalla completa verificada manualmente en precios y cartera; escalado físico Windows 125 %/150 % correcto. CI final [34346311068](https://github.com/Buzo500/atlas-quant/actions/runs/34346311068), fuentes `d5c3b09`: **482 Python + 91 subtests, 244 frontend y 10/10 E2E**, instalación/build, contratos, tipos, lint, dependencias, arranque/proxy/parada correctos. El cierre posterior solo modifica documentación e instrucciones. El timeout histórico se acepta como incidencia conocida abierta, sin atribuirle una corrección. La integración por PR #3 y etiqueta `v0.3.0-dev.1` sigue la autorización del usuario. Los pendientes de los registros anteriores quedan sustituidos por este cierre.

Entrega de desarrollo basada en `v0.2.0-rc.2`. El ensayo sostenido y su seguimiento siguen aplazados; no se publica una versión estable por omitirlos.

- Fuentes revisadas `c8f4eb6` subidas y [CI gratuita de Windows superada el 09/09](https://github.com/Buzo500/atlas-quant/actions/runs/34340199451): 477 Python y 91 subtests, 244 frontend y 10/10 E2E, instalación, compilación, contratos, lint, arranque y parada correctos. Se conserva la incidencia intermitente del intento local; PR en borrador y escalado físico de los controles actuales pendiente.
- Consulta de precios por conjunto, versión inmutable, activo y fechas inclusivas, con procedencia, advertencias y cierre anterior. Lectura local sin descargas ni mutaciones de dominio.
- Panel de precios en Datos con velas, línea, área, OHLC y volumen; intervalos diarios, semanales y mensuales calculados sobre las sesiones elegidas, con cobertura parcial explícita.
- Cursor y teclado, fechas, zoom, desplazamiento y tabla diaria original. Ventana explícita de hasta 1.000 barras dibujadas, sin eliminar datos de origen.
- Curvas de cartera y backtest con inspección de observaciones originales, línea/área y navegación temporal. TWR de cartera calculado desde su origen, sin convertir métricas globales en métricas del tramo visible.
- Fichas de datos junto al puntero en precios, cartera y resultados; sustituyen los deslizadores de inspección. Se ajustan a los bordes de la pantalla y mantienen inspección por teclado, lecturas de referencia y tablas originales.
- Barra para desplazar el intervalo visible y herramientas de lupa, restablecimiento y pantalla completa. La vista ampliada permite arrastrar la serie y hacer zoom con la rueda, conservando datos, selección y límites del histórico.
- Revisión del 09/09: la primera ficha de una curva estrecha ya no desaparece cuando su lectura ocupa otra línea y cambia la altura del gráfico; la ficha de teclado se recoloca junto al punto. Regresiones de ratón/teclado y mediciones repetidas de navegación, con [resultados y una incidencia de API pendiente](docs/revision_graficos_20260909.md).
- Contratos regenerados, pruebas de lectura inmutable y agregación, y recorridos de navegador con la API real. [Uso, evidencia y límites](docs/graficos_v0_3.md).

## v0.2.0-rc.2 · Candidata con CI verificada · 2026-09-08

Candidata desarrollada en `codex/v0.2.0-rc.2`, sobre la [PR #1](https://github.com/Buzo500/atlas-quant/pull/1) fusionada en `master` (`e1f6e020a1d75a81bff97eefcbebe726d47bcdb3`). La [CI 34249730107](https://github.com/Buzo500/atlas-quant/actions/runs/34249730107) verifica las fuentes, pruebas y workflow de `412918b5e9067e44f293b0633068ca932a472d64`; el cierre posterior solo modifica documentación. La integración por la [PR #2](https://github.com/Buzo500/atlas-quant/pull/2) y la etiqueta `v0.2.0-rc.2` siguen el procedimiento autorizado. No es estable: escalado físico pendiente, ensayo de 48 horas y seguimiento aplazados. [Evidencia de candidata](docs/candidata_v0_2.md).

- Conserva el monolito modular, las transacciones, los controles de simulación y la operación Windows incorporados en rc.1.
- Corrige el agotamiento de archivos del supervisor: comprobaciones HTTP locales sin crear contextos TLS ni consultar proxies, con cierre explícito de respuesta y conexión. La corrección no convierte el ensayo fallido de rc.1 en uno superado.
- Interfaz crema, marfil y cobre para las cinco secciones, adaptada a escritorio y pantallas ultrapanorámicas.
- Confirmación de movimientos vinculada al CSV, conjunto, versión, barras y ledger revisados, con comprobación del token dentro de la transacción.
- Comparaciones del Laboratorio con identidad de ejecución, datos y costes utilizados; aviso cuando el borrador deja de coincidir con el resultado.
- Consultas que descartan respuestas obsoletas, distinguen carga/error/datos conservados y permiten reintentar lecturas; ajustes parciales que no sobrescriben una parada concurrente al guardar un peso.
- Borradores conservados entre pestañas y selecciones recuperables desde la URL; la recarga no conserva una autorización de simulación automática.
- Paneles separados por funcionalidad, formatos comunes EUR/USD/fechas, tabla accesible de las curvas y paginación de 50 filas. La reducción del SVG conserva los datos completos.
- Pruebas de comportamiento con Vitest/Testing Library y CI ampliada. **Antecedente validado:** `3f1d990ac15c391e638302828d1a720d99d78003` superó [CI de Windows](https://github.com/Buzo500/atlas-quant/actions/runs/34241300060) con 421 pruebas Python, 91 subtests y 126 pruebas de interfaz; esa ejecución no valida cambios posteriores de rc.2.
- Recorridos E2E con interfaz compilada, API real y Chromium sobre una base nueva por ejecución; presupuesto cero y cierre comprobado de los procesos propios. El PID del intérprete se verifica mediante su pertenencia al grupo del servidor; una integridad o cierre incorrectos impiden dar la prueba por superada.
- Foco persistente al importar datos, crear un experimento y confirmar CSV, respetando cambios de campo o sección durante la espera. El mensaje de importación permanece tras actualizar la versión del conjunto.
- Hora de consulta visible fuera de los anuncios accesibles; carga inicial, errores, recuperación y reintentos anunciados sin repetir sondeos normales.
- Aislamiento de pytest antes de recoger e importar módulos, evitando abrir la base habitual al construir la aplicación global.
- Identidad de archivos del test de aislamiento mediante `samefile`, compatible con alias Windows 8.3 y rutas largas. Se conserva la primera CI fallida y la reproducción que confirmó la corrección.
- CI de Windows superada: **446 pruebas Python + 91 subtests** (22,13 s), **140 Vitest en 15 archivos** (43,86 s), **5/5 E2E** (18,7 s), instalación limpia, build, contratos, tipos, lint, dependencias, smoke, arranque y parada correctos.
- Validación local: **446 pruebas Python y 91 subtests** (38,34 s, dos avisos previos), **140 pruebas Vitest en 15 archivos** (13,34 s), **5/5 E2E** (9,6 s), TypeScript, contratos, lint, `pip check` y compilación correctos. Conservación del contenido de la base habitual verificada frente a su copia; resultados fallidos anteriores preservados.
- Escalado físico de Windows al 125 % y 150 % pendiente: la herramienta de control bloqueó la operación y no se modificó la escala. Los tamaños CSS comprobados anteriormente no sustituyen esta validación.

No incorpora gráficos avanzados del backlog, aprendizaje, acceso remoto, móvil, conexión a bróker ni órdenes reales. Se mantiene el recorrido sintético sin claves y con presupuesto cero.

## v0.2.0-rc.1 · Candidata · 2026-09-06

Candidata histórica: motor, OpenAPI, salud e interfaz se identificaron como 0.2.0-rc.1. No es una etiqueta estable: su CI, recorridos del commit y ensayo interrumpido se conservan en [cierre de candidata](docs/candidata_v0_2.md).

- Arranque con instancia única, verificación de dependencias, puertos, página y API; estado consultable y parada cooperativa. Los fallos de un servidor detienen ambos sin repetir trabajos.
- Propiedad de procesos mediante Windows Job Objects, incluyendo descendientes. La parada no utiliza un PID guardado para terminar procesos ajenos.
- Interfaz compilada en Node, proxy local al motor y manifiesto que detecta fuentes o artefactos alterados. La ejecución habitual deja de usar el servidor de desarrollo.
- Copias coherentes de SQLite con manifiesto e integridad comprobada; automáticas al iniciar y cada 24 horas, con retención de siete; copias manuales y antes de actualizar.
- Restauración con respaldo del destino, experimentos activos pausados, parada global activada, fuentes automáticas desconectadas y reservas de API conservadas.
- Esquema SQLite versionado; adopción transaccional desde v0.1 sin modificar registros financieros y rechazo de esquemas incompatibles.
- Instalador bloqueado durante la ejecución, dependencias fijadas, compilación verificada, accesos de inicio/parada y guía de actualización/recuperación.
- Pruebas operativas adicionales, workflow manual de validación Windows y hoja de ruta por versiones.
- Datos, ledger, demo y controles extraídos a casos de uso con transacciones sobre el estado vigente; descargas tardías e importaciones concurrentes ya no pierden actualizaciones.
- Pausa/cancelación durante investigación, interrupción cooperativa de cálculo, resultados protegidos y reservas de IA liquidadas sin reactivar trabajos ni repetir fases completadas.
- Riesgo, órdenes y auditoría atómicos; reanudar o desbloquear por peso no ejecuta retrospectivamente sesiones recibidas durante una parada.
- Exclusión explícita de ejecutores y restauraciones sobre la misma base; limpieza de propietarios de ejecución al recuperar/restaurar.
- Contratos Pydantic/OpenAPI, tipos TypeScript generados y cliente extraído; controles de interfaz coherentes con la operación en curso y sondeo protegido frente a respuestas antiguas.
- 74 regresiones nuevas: total 328 pruebas y 91 subtests superados. Contratos y lint de aplicación añadidos al workflow manual. [Evidencia y límites](docs/consolidacion_core.md).

- Diagnóstico archivado por ejecución con identificador, horas y códigos de salida; se conserva tras reiniciar.
- Herramientas reproducibles de validación de candidata y ensayo de 48 horas con evidencia local y detección de interrupciones.

No incorpora cambios de gráficos, aprendizaje, integración con bróker ni operativa real. Continúa disponible el recorrido sintético sin claves y presupuesto cero.

## v0.1 · Base local

Alcance y limitaciones en [version_0_1.md](docs/version_0_1.md). La instalación original del portátil y la posterior validación del sobremesa se registran por separado en [CONTINUIDAD.md](docs/CONTINUIDAD.md).
