# ATLAS Quant · Plan de v0.3: gráficos interactivos

Actualizado: 8 de septiembre de 2026. **Implementación autorizada y en curso.** Este documento fija el alcance y los criterios; no acredita por sí mismo que las funciones estén terminadas. El punto de partida es `v0.2.0-rc.2` (`9aee4224a12556e97cde16ed283854af10845bda`). La evidencia de cada entrega debe registrar el código realmente probado.

**Estado de entrega:** G1–G5 implementadas en `0.3.0-dev.1`; G6 cuenta con validación local, E2E, rendimiento y escalado físico completados. CI de la rama pendiente. La [guía de gráficos](graficos_v0_3.md) registra cifras, scripts, recorridos y limitaciones; no se etiqueta estable.

El usuario mantiene aplazado el ensayo de 48 horas y su seguimiento. Desarrollar v0.3 no lo ejecuta ni convierte v0.2 en estable: se conserva la candidata publicada y el criterio operativo pendiente. No se comprometen fechas de entrega.

Referencias: [hoja de ruta](hoja_de_ruta.md), [GRAPH-001 y GRAPH-002](backlog_planificacion.md#pendientes-de-gráficos), [consolidación del núcleo](consolidacion_core.md) y [consolidación del frontend](frontend_consolidacion.md).

## Resultado esperado

Leer una observación concreta, explorar un intervalo y cambiar su representación sin alterar los datos ni el cálculo financiero. La interfaz conserva crema, marfil, cobre y azul pizarra; cifras tabulares, controles compactos, leyendas claras y tablas accesibles. Los gráficos aprovechan el ancho disponible en 3440 × 1440 y se adaptan a ventanas menores.

Se mantienen las cinco secciones actuales. **Datos** será el primer lugar para inspeccionar precios de un activo del conjunto seleccionado. **Cartera** y **Laboratorio** incorporarán interacción a sus curvas existentes; los resultados mostrados en Agente IA reutilizarán esa presentación cuando ya dispongan de esas curvas. No se añade un panel de negociación ni un nuevo mecanismo de órdenes.

| Serie | Representaciones previstas | Lectura de una observación |
|---|---|---|
| Precio diario de un activo | Línea de cierre, área de cierre, velas japonesas y barras OHLC; volumen separado | Sesión, apertura, máximo, mínimo, cierre, volumen y cambio respecto al cierre anterior cuando exista |
| Patrimonio de cartera | Línea o área de NAV; vista de rentabilidad a partir del índice TWR existente | Sesión, patrimonio y TWR identificado como acumulado o referido al intervalo, según la vista |
| Resultado de backtest | Línea o área de patrimonio de estrategia y benchmark | Sesión y valores originales de ambas series, con el contexto de la ejecución |

NAV y patrimonio de un backtest son observaciones diarias, sin OHLC intradía. No se transforman en velas. Los máximos y mínimos del intervalo, si se muestran, se refieren a las observaciones disponibles.

## Auditoría del punto de partida

La inspección corresponde a rc.2; las siguientes carencias son trabajo de v0.3, no capacidades disponibles en esa candidata.

| Componente existente | Capacidad comprobada en código | Trabajo necesario |
|---|---|---|
| `components/atlas/curve.tsx` | SVG medido con `ResizeObserver`, eje por observaciones, NAV o equity/benchmark, extremos preservados al reducir el dibujo, tabla original de 50 filas | Cursor, selección por teclado, rangos, zoom/desplazamiento y modo TWR; conservar precisión y estados vacíos/inválidos |
| `DatasetResponse` y `/api/state` | Identidad, versión, manifiesto y metadatos opcionales; las barras se excluyen deliberadamente | Lectura específica y tipada de precios, sin añadir el historial al sondeo general |
| `Store.get_dataset_version` | Lectura interna de versiones inmutables que ya contienen las barras | Exponer una lectura acotada de una versión, con identidad verificable y errores explícitos |
| `PortfolioPoint` | `date`, `nav`, `twr_index` | Adaptar la presentación; no hacen falta velas ni recalcular la contabilidad para inspeccionar estos campos |
| `PortfolioResponse` | Curva y totales, sin identidad/versionado de ledger en la respuesta | Mantener coherencia de la lectura; no atribuir metadatos obtenidos en otro instante ni inventar flujos por punto |
| `BacktestPoint` / `ResearchExecution` | `date`, `equity`, `benchmark`; contexto inmutable para investigaciones manuales nuevas | Mantener la identidad original al navegar; los resultados antiguos sin contexto no reciben metadatos supuestos |
| Validaciones de precios | CSV completo OHLCV, EUR, orden por fecha/símbolo, duplicados e incoherencias rechazados; volumen cero permitido | La nueva lectura debe validar su frontera: no reutilizar una normalización interna que complete volumen ausente con cero |
| Pruebas y mediciones | Vitest, contratos Python, E2E con API real; benchmark SSR con 1.000/10.000/100.000 observaciones | Casos de interacción, agregación y concurrencia; medir también el navegador real |

El límite HTTP de importación es **100.000 barras por conjunto** y un CSV de hasta **8.000.000 caracteres**. El parser admite hasta un millón de filas, pero eso no amplía el límite de esa ruta. Yahoo diario limita cada consulta a diez años y no certifica el calendario ni el historial completo de acciones corporativas. Estos límites no se elevan como parte de v0.3.

`recharts` 3.8.0 figura ya en las dependencias y existe una primitiva `components/ui/chart.tsx`; la curva de ATLAS utiliza su propio SVG. No se presupone que la primitiva resuelva velas, accesibilidad y rendimiento. La elección de renderizado se justifica con el prototipo y las mediciones, no con la presencia de un paquete.

## Contrato de lectura y límites del módulo

La nueva consulta de precios será una operación de lectura sobre los datos locales. Debe seleccionar conjunto, **versión inmutable**, activo y, cuando corresponda, fechas. Su respuesta identificará versión, huella, moneda, periodicidad diaria, origen sintético/observado, intervalo solicitado y cobertura devuelta. La ruta y los nombres definitivos se fijan en OpenAPI durante la implementación; este plan no documenta un endpoint existente.

- Leer barras y metadatos de la misma versión. Una ampliación concurrente del conjunto no modifica la respuesta ni mezcla páginas de versiones distintas. Una versión inexistente se rechaza; no se sustituye silenciosamente por la actual.
- Limitar respuesta y memoria. Si se introduce paginación, todas las páginas quedan ligadas a la misma versión y se informa de continuación y recuentos. Si se entrega una serie acotada completa, el límite se valida y cualquier exceso se rechaza; nunca recortar en silencio ni presentar una descarga parcial como historia completa.
- Evitar una petición por cada movimiento del cursor. La inspección trabaja con los datos ya recibidos; se cancelan o descartan respuestas de selecciones anteriores mediante las garantías de `useRead`.
- El módulo de datos valida y obtiene el snapshot; funciones puras preparan las series y agregaciones; el componente se ocupa de interacción y dibujo. No se consulta SQLite desde el frontend ni se añade otro ejecutor.
- La reducción visual es distinta de la agregación temporal y del cálculo financiero. Ninguna escribe precios, ledger, estrategia o resultados. Cambiar rango o estilo no vuelve a ejecutar un backtest.
- Los contratos públicos se definen en `backend/atlas_quant/contracts.py`. Regenerar `frontend/lib/api-types.ts` con `tools/export_contracts.py` y comprobar `--check`; no editar esos tipos manualmente.

Los flujos de efectivo por sesión no están en `PortfolioPoint`; los totales de `PortfolioResponse` no permiten reconstruirlos. No se añaden al cursor hasta disponer de un contrato coherente. Las acciones corporativas, cuando existan, se presentan como información de fuente: no como movimientos ya reconciliados ni ajustes calculados por el gráfico.

## Convenciones que debe cumplir la implementación

### Fechas, datos ausentes y acciones corporativas

1. `YYYY-MM-DD` es fecha de sesión, sin conversión de zona. La hora de descarga o de creación del manifiesto no es hora de cotización. Mostrar zona del mercado solo si existe; no inferir una hora intradía.
2. Mantener el eje por observaciones con su convención visible. Un espacio entre sesiones no permite decidir si hubo festivo, suspensión o dato omitido. No interpolar OHLCV ni inventar barras para días ausentes. Los huecos conocidos de la fuente y su incertidumbre permanecen identificables.
3. Precio, cero y ausencia son estados distintos. El volumen cero se muestra como cero; ausencia o dato inválido se indica y no se sustituye por cero. No dibujar una vela parcial como completa. El comportamiento inicial preferido ante un contrato inválido es un error explícito que conserve, cuando proceda, la última lectura válida del mismo recurso.
4. El manifiesto de CSV puede declarar `price_basis: unspecified` y `calendar: provided_rows_only`. Mostrar esa falta de verificación. Yahoo utiliza OHLC del proveedor con `auto_adjust=False`, `back_adjust=False` y `repair=False`: no equivale a una certificación de precios brutos de bolsa.
5. Dividendos, splits y plusvalías comunicados por la fuente no se aplican automáticamente. Un salto compatible con un split sigue siendo un cambio del precio recibido; no se anuncia como rentabilidad total. Ajuste verificado, calendarios y conciliación permanecen en v0.4.
6. El cambio absoluto/porcentual se calcula contra el cierre anterior de la misma serie y base de precio. Si no está disponible, mostrar ausencia; la primera observación visible no equivale a cambio cero. Al ampliar la lectura para obtener un predecesor, identificarlo como contexto y no introducirlo en el rango solicitado.

### Agregación semanal y mensual

- Agrupar sesiones del mismo activo, moneda, versión y base de precio. Semana civil de lunes a domingo y mes civil, con límites indicados; no reconstruir un calendario bursátil que no existe.
- Apertura = primera apertura disponible; máximo = máximo de máximos; mínimo = mínimo de mínimos; cierre = último cierre disponible; volumen = suma de los volúmenes presentes y válidos. No promediar precios para construir una vela.
- Conservar primer/último día observado, número de sesiones y límites del periodo. Una selección que corta una semana o un mes debe indicar esa parcialidad. La cobertura de un periodo no se certifica contando cinco días ni viendo una barra el viernes.
- Definir un solo orden: seleccionar las sesiones dentro del intervalo solicitado y agregarlas. Si el filtro corta un periodo, su vela representa únicamente esas sesiones y queda marcada. No incluir datos fuera de las fechas elegidas sin advertirlo.
- Si el conjunto termina antes del cierre civil del periodo, indicarlo como periodo abierto o cobertura truncada según el contexto. Los huecos desconocidos mantienen la advertencia de calendario/cobertura no verificada.
- Mostrar el periodo y sus valores agregados en la lectura del gráfico; la tabla conserva los diarios originales con un rótulo explícito. No se añade una segunda tabla de agregados. El volumen agregado no se da por completo cuando alguno de sus registros es ausente.
- Las curvas de NAV/TWR no utilizan esta fórmula OHLCV. Una eventual menor densidad de dibujo conserva inspección de sus observaciones originales; no crea una rentabilidad semanal sumando porcentajes diarios.

### Cursor, teclado y rangos

- Seleccionar la observación real más cercana en el eje horizontal; resolver empates de forma determinista. Conservar un índice o fecha de origen aunque el dibujo haya reducido puntos.
- Sincronizar precio y volumen de la misma barra. Estrategia y benchmark se leen en la misma fecha y con valores originales, no con una interpolación de las líneas dibujadas.
- Ofrecer entrada al gráfico por teclado, flechas para observaciones anterior/siguiente, Inicio/Fin para los extremos y Escape para salir de la selección fijada. Los controles de zoom, desplazamiento y restablecimiento tienen nombre visible y foco reconocible; no requieren arrastrar ni disponer de rueda.
- Mantener una leyenda visible y una alternativa tabular. Limitar anuncios accesibles a cambios accionados por la persona; el sondeo normal y cada píxel del ratón no deben inundar al lector de pantalla.
- Añadir intervalos explícitos y selección de fechas con extremos inclusivos para la vista. Mostrar sesiones efectivas y un estado vacío cuando no existan; no cambiar fechas silenciosamente para conseguir una curva.
- El zoom modifica el intervalo visible y el eje vertical se calcula sobre ese intervalo. Definir límites para una sola observación y las series constantes. El desplazamiento no rebasa los datos disponibles y restablecer recupera la vista completa.
- Conservar la selección por fecha al redimensionar o cambiar estilo. Un cambio de activo, versión o serie invalida cualquier selección que ya no corresponda; no mostrar bajo un nombre nuevo la leyenda anterior.
- En cartera, el índice TWR ya disponible permite mostrar acumulado como `(índice - 1) × 100`. Si se ofrece rentabilidad desde el inicio visible, usar una base explícita y distinta; una base cero o inválida no produce un porcentaje inventado. Recortar una curva no convierte las métricas globales de cartera o backtest en métricas del tramo.

## Entregas pequeñas y criterios de aceptación

| Entrega | Trabajo acotado | Evidencia necesaria para cerrarla |
|---|---|---|
| **G1 · Lectura de series** | Contrato de precios, consulta de snapshot inmutable y adaptadores de presentación | Barras y metadatos de la versión solicitada; errores de id/versión/activo/rango; límites y ausencia de mutaciones; actualización concurrente sin mezcla; contratos generados al día |
| **G2 · Inspección de curvas** | Cursor y teclado sobre NAV/equity/benchmark existentes, leyenda y tabla originales | Coincidencia con la fuente en extremos, huecos, un punto, ceros/negativos, resize y reducción visual; sin robo de foco ni errores obsoletos |
| **G3 · Precios diarios** | Inspección en Datos, línea/área/velas/OHLC y panel de volumen | OHLC exacto en velas alcistas, bajistas y sin cambio; cero volumen visible; metadatos y errores claros; cambiar estilo no modifica la serie ni dispara cálculos financieros |
| **G4 · Navegación temporal** | Fechas, rangos, zoom, desplazamiento y restablecimiento; presentación TWR de cartera | Selección consistente por ratón/teclado, intervalos vacíos y mínimos, límites correctos y métricas globales sin atribución al tramo |
| **G5 · Semana y mes** | Agregación pura y trazable, coberturas parciales | Casos calculados a mano con cambio de año, febrero bisiesto, huecos, extremos de rango, un punto, cero volumen y acciones corporativas informativas; mismos resultados en gráfico y tabla |
| **G6 · Integración y entrega** | Recorridos reales, rendimiento, diseño adaptable, versión y documentación | API real en base aislada, no regresiones de controles/importaciones, medidas reproducibles y evidencia asociada al commit; instalación/build/arranque/parada correctos |

G1 y G2 pueden avanzar por separado. G3 depende de G1; G4 se prueba sobre curvas y precios antes de G5; G6 integra el resultado. Cada bloque conserva pruebas existentes y añade las que verifican su comportamiento, sin dar por terminado el conjunto porque funcione un prototipo.

## Rendimiento y elección de renderizado

La línea base disponible mide serialización SSR de 1.000, 10.000 y 100.000 observaciones, no fluidez de navegador. Las tablas paginan 50 filas y el SVG reduce puntos conservando extremos; las series completas siguen en memoria. No convertir esas cifras en una promesa de latencia.

Para G2/G3 se compara primero ampliar el SVG propio con utilizar la dependencia gráfica existente. Separar antes el modelo de interacción de la representación. Una biblioteca nueva solo se incorporará si una carencia medida lo justifica, tras revisar documentación oficial, licencia, mantenimiento, compatibilidad React/compilación local y coste. No se introduce una suscripción, CDN o servicio de datos.

La evaluación debe registrar equipo, navegador, commit, tamaño/huella del fixture y viewport. Medir carga y primera representación, latencia de selección y zoom, tareas largas, nodos dibujados y memoria tras cambiar repetidamente de activo/rango. Probar 1.000, 10.000 y 100.000 observaciones sintéticas; esta última cifra es una carga técnica, no 100.000 sesiones bursátiles acreditadas.

Como objetivo inicial sujeto a medición: selección y navegación habituales con percentil 95 inferior a 100 ms en el sobremesa, sin crecimiento sostenido de listeners/nodos al repetir interacciones. Fijar un presupuesto de carga/memoria a partir del primer prototipo y documentarlo antes de aceptar G6. Si no se cumple, reducir trabajo de representación, limitar la ventana o cambiar el renderizado; no reducir la precisión de la leyenda ni omitir barras sin indicarlo. Las velas muy densas necesitan un tratamiento explícito: agregación temporal elegida, vista limitada o representación declarada; no desechar máximos/mínimos como si la serie siguiera íntegra.

## Pruebas y operación

- Funciones puras: selección, rangos, dominios numéricos, agregación y cambio frente al anterior. Fixtures pequeños con valores esperados independientes del algoritmo, más casos grandes para límites.
- Backend: lectura de versiones, aislamiento, límite de respuesta, validación de barras/metadatos y ausencia de escritura; preservar controles y transacciones existentes.
- Componentes: foco, teclado, leyenda, sincronización, vacío/error/recuperación y respuesta tardía tras cambiar contexto. Conservar la tabla de valores originales y su paginación.
- Navegador real: cargar demo, inspeccionar un precio conocido, cambiar estilo/temporalidad/rango, usar teclado y explorar una curva de cartera y otra de backtest. API real, base de pruebas aislada, sin claves, proveedor `none` y presupuesto cero.
- Diseño: 1366 × 768, 1920 × 1080 y 3440 × 1440, además de ventana estrecha; sin desbordamiento global ni leyendas/controles recortados. Repetir la comprobación física de Windows 125 %/150 % cuando cambien los gráficos: la evidencia de rc.2 no valida automáticamente el diseño nuevo. Restaurar la configuración inicial.
- Verificar contratos, TypeScript, lint, pruebas pertinentes y compilación con manifiesto. Detener ATLAS antes de modificar código o reconstruir; comprobar los datos habituales antes de devolverlo al uso normal. No ejecutar fixtures ni restauraciones destructivas sobre la cartera habitual.
- La CI usa exclusivamente la cuota gratuita comprobada; no se lanza un ensayo prolongado ni un monitor por aprobar estos bloques. La entrega registra lo comprobado y los límites pendientes, sin declarar estable una versión por omitir el criterio de 48 horas.

## Fuera de alcance

Intradiario y tiempo real; indicadores nuevos o señales de inversión; Heikin-Ashi, Renko, Kagi y otros precios transformados; reconciliación de splits/dividendos y FX; recálculo financiero arbitrario por rangos; aprendizaje, modelos locales o GPU; informes LaTeX; ejecución remota, móvil/PWA y bróker. Se conservan en sus versiones del backlog. No se necesitan claves ni llamadas pagadas para desarrollar y validar este alcance.
