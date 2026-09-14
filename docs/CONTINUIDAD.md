# ATLAS Quant: continuidad entre equipos

Actualizado: 13 de septiembre de 2026. Este documento resume decisiones y estado para una conversación nueva de Codex; no contiene la transcripción completa del chat original.

## Diagnóstico de CI dev.9 · 14/09

El usuario sube dev.9 y lanza CI `34821956088` sobre `12d262b`: fallan los E2E
(24/25), mientras Python (1.194 + 91 subcasos) y frontend (344) pasan. Smoke
posterior omitido. Autoriza las cinco tareas de reproducción/corrección/evidencia/
validación/publicación gratuita. [Diagnóstico](diagnostico_ci_20260914.md).
El test D2 mezclaba conservación de cartera con registro de instrumentos dentro
de 45 s; llega al tramo final aproximadamente a los 40 s. Se separa el registro
sin aumentar timeouts ni añadir reintentos y se conservan artefactos sintéticos
de fallos durante un día. La latencia intermitente sigue abierta: no se presenta
esta corrección de la prueba como arreglo del transporte. Validación/publicación
final se consignan en el diagnóstico. Motor y método estadístico intactos.
Las referencias siguientes a dev.9 sin subida/CI son antecedentes.

## Dev.9 local: cartera LaTeX, captura TCP y confirmación estadística

«Vale, haz los 5» autoriza las cinco propuestas del cierre dev.8. Completadas:
captura TCP automática, adaptador D7 guardado, descarga LaTeX en UI, experimento
aislado por grupos y ejecución principal/confirmación condicionada.
**0.6.0-dev.9 local**, `codex/v0.6-evaluador`, esquema 5; código `1881465`, cierre
documental posterior. [Uso y límites](v0_6_dev9_implementacion.md),
[validación local](v0_6_dev9_validacion.md) y
[evidencia compacta](evidence/dev9-validation.json).
No hay nueva subida, CI remota, PR, fusión o etiqueta. CI 34774872432 es dev.8.

Informes de cartera: `atlas-period-report-v1`/`atlas-period-latex-bundle-v1` sobre
el informe D7 almacenado, fuente original y JSON/CSV exactos. Descarga por IDs del
servidor con guardias locales, lectura coherente y vigencia separada del original;
sin recálculo contable ni escrituras. PDF opcional por CLI, misma estética aceptada.
Estados/posiciones/movimientos no conservados siguen ausentes con motivo explícito.
Detalle patrimonial verificable y subperiodo retrospectivo requieren la ampliación
definida en el contrato; no completar un histórico con el libro actual.

Tres PDF sintéticos compilados y todas sus páginas revisadas: caso base de
aportación/comisión (2), falta FX (2), tabla larga (5 páginas, 151 cortes completos).
En `output/pdf/dev9-cartera-entrega/`, con ZIP, fuentes y recibos. Exportación del
navegador verificada; revisión a 390/1.280/3.440 px sin desbordamiento de página.
No constituye una nueva aceptación del usuario o una prueba física de escalado.

[Experimento predeclarado](v0_6_dependencia_grupos_resultados.md): código/oráculos
congelados en `380e7375f86e09b8c5549c24591041b4f43158e7`. **q4 pasa todos los filtros
en las 15 celdas estacionarias de cada lote**: coberturas
93,8–95,7 % y 93,9–95,6 %, respectivamente. Cero intervalos inválidos; anchuras
dentro de los límites fijados. 18.000 historias por lote, semillas 20260916/17,
5.000 réplicas L10; q8 solo sensibilidad. Confirmación iniciada después de pasar
principal/reproducciones/auditoría, sin cambiar código o filtros. 36.000 fuentes
auditadas, 72 reproducciones exactas y comprobación aritmética independiente de
72.000 intervalos q4/q8. Ambos cálculos en menos de 26 min por lote, seis procesos.
Resumen completo versionado; fuentes conservadas bajo `var/validation/dependence-groups-*`.
Permite proponer una revisión versionada de método/contrato, **no integrar q4
automáticamente, declarar cobertura garantizada o validar una estrategia**.
La robustez del producto permanece exploratoria y los informes previos intactos.

Validación: suite completa 1.193 Python + 91 subcasos; nueve regresiones finales
de exportación y cinco de captura TCP correctas, incluido un caso adicional nuevo
(1.194 casos Python distintos comprobados, sin afirmar una segunda suite completa).
344 frontend, ocho Node, contratos/TypeScript/lint/build y **25/25 E2E** correctos.
Run `e2e-ad01b118a82c40a99b4f3f61fa65ea20`: arranque/parada 0/0, sin parada forzada,
base intacta y puertos liberados. Captura: 1.895 grupos, dos >=1 s, máximo
1.409,0049 ms, mientras corría Monte Carlo offline. TCP: 26 muestras, pico agregado
del equipo 1.679 sockets, sin eventos 4227/4231; no demuestra consumidor histórico
ni resuelve D4/API. Revisión final fija LF y límite estricto de 8 MB en la captura.

App habitual **detenida**, base SHA-256
`2791f15e1bb5be5833117810ce5de745e4dfb46817850c4d8d8cbc3cc2bc5549` conservado.
Gasto externo cero. Ensayo de 48 h, portátil, PR #12 y movimientos personales
siguen aplazados. Los archivos concurrentes de IA/riesgo se conservan en su estado,
sin incluirlos en este commit documental; su nota permanece como cambio local separado.

## Publicación dev.8, PDF aceptado y cinco tareas completadas

El usuario acepta expresamente el PDF dev.8 y autoriza diagnóstico API, registrar
esa aceptación, subir/ejecutar CI gratuita y definir el siguiente experimento e
informes por fechas/cartera. [Cierre y evidencia](publicacion_v06_dev8.md).
**0.6.0-dev.8**, esquema 5, rama `codex/v0.6-evaluador` subida sobre código
`2091ea1c2557a9d067049e73673e26e14ded6c6c`, con cierre documental posterior.
[CI 34774872432 correcta](https://github.com/Buzo500/atlas-quant/actions/runs/34774872432):
**1.169 Python + 91 subcasos, 341 frontend, ocho Node y 25 E2E**;
contratos/TypeScript/lint/build, sonda 3.666 conexiones sin fallos y arranque/parada.
Cuota **531,7 → 555/2.000 minutos**, **0 USD facturables**, presupuesto cero y
bloqueo de pago comprobados. Sin PR, fusión o etiqueta nueva.

[Diagnóstico API](diagnostico_api_20260913.md): D3 local falla al descargar un
chunk JS con `net::ERR_NO_BUFFER_SPACE`, coincidente con evento Windows Tcpip
4231 por agotamiento de puertos efímeros. Identifica el recurso agotado, no el
proceso consumidor. D4 y las esperas históricas siguen abiertas. Captura ampliada
a estáticos con códigos canónicos, sin consultas/cuerpos ni cambios de transporte.
Cuatro regresiones nuevas. CI: 1.910 grupos/73 incidencias, 23 ≥1 s (8 API/15 estáticos),
máximo 1.547,308 ms; sin timeout de 10 s ni NO_BUFFER_SPACE. No declarar corregida
toda la API ni confundir esta evidencia con los reintentos JSON de dev.8.

[Nuevo experimento por grupos](v0_6_dependencia_grupos_plan.md): definido, **sin
implementar ni ejecutar**. q4 candidato, q8 sensibilidad, filtros previos y semilla
de confirmación solo si pasa; método exploratorio del producto conservado.
[Contrato de informes por periodo](informes_periodo_contrato.md): definido, **sin
implementar**. Primero exportar D7 guardado; no reconstruir sus posiciones históricas
desde el libro actual. Subperiodo retrospectivo hereda cuenta/estado de estrategia
y excluye reserva; exige una proyección futura compartida, no recalcular desde cero.
Aceptación visual registrada en la guía LaTeX, sin cambiar el PDF aceptado.

La carpeta habitual cambió a `master` durante la tarea. Se trabajó temporalmente
en un checkout aislado y, por respuesta explícita «Volver a dev.8», se restituyó
**`codex/v0.6-evaluador`**. Interfaz recompilada por el constructor canónico y
manifiesto verificado. Checkout temporal limpio y retirado; documentos posteriores
a `2091ea1` sin cambios de producto y subidos como cierre documental.
`output/analysis/` ajeno al cierre permanece sin seguimiento, sin modificarlo/publicarlo.
App habitual **detenida**, 3000/8000 libres, SHA-256 de la base
`2791f15e1bb5be5833117810ce5de745e4dfb46817850c4d8d8cbc3cc2bc5549` intacto.
No reactivar ensayo de 48 h, portátil, movimientos personales ni aceptación/fusión
PR #12. No nueva declaración de estabilidad ni llamadas IA/bróker.

## Antecedente local dev.8: LaTeX, dependencia y revisión Windows

El usuario acepta dev.7 («resulta claro») y autoriza las cinco propuestas.
[Plan previo](v0_6_dev8_plan.md). Rama `codex/v0.6-evaluador`, **0.6.0-dev.8 local**,
esquema 5. Dev.7 subida sobre `ab7764d`, [CI 34771575781 correcta](publicacion_v06_dev7.md):
1.124 Python + 91 subcasos, 336 frontend, ocho Node, 25 E2E y arranque/parada.
Cuota 510 → 531,7/2.000 minutos, 0 USD facturables, bloqueo de pago comprobado.
Esa CI no cubre los cambios locales de dev.8. Sin nueva PR/fusión/etiqueta.

[Generador LaTeX inicial](informes_latex_implementacion.md): desarrollo retrospectivo
completo verificado, botón de fuente editable en ZIP, contexto/métricas/curvas/todas
las operaciones y huellas originales. CLI opcional produce PDF/log/recibo local.
Sin compilador HTTP ni nuevas tablas/escrituras contables; ZIP JSON/CSV anterior
compatible, reserva sin precios ni cálculo. Paquete de 12 miembros con manifiesto,
verificador que reconstruye sin extraer y textos escapados/controlados.
LuaHBTeX 1.24.0 / TinyTeX v2026.09 portable bajo `var/tools`, sin PATH global;
2 GB/120 s/32 MB, dos pasadas, sockets/shell-escape desactivados. No es un sandbox
completo del SO. Versiones/licencias y límite de verificación GPG en la guía.

Maqueta de dos páginas compilada y revisada. HFG y ZAL: tres páginas cada uno;
prueba con 59 operaciones: cinco; sin operaciones y notas largas: cuatro.
Fuentes originales HFG/ZAL no se reescriben ni se calculan sus 128 sesiones reservadas.
PDF finales y ZIP: `output/pdf/atlas-dev8-entrega/`; maqueta en
`output/pdf/atlas-dev8/maqueta-atlas.pdf`. Artefactos excluidos de Git.

[Experimento de dependencia](v0_6_dependencia_resultados.md): 6.000 historias,
18.000 bootstrap y 4.000 oráculos; 5.000 réplicas por longitud, L10/20/40,
n504/1008 y seis procesos generadores, semilla 20260914. Ninguna longitud pasa
los filtros previos: AR(0,95), n504, L10 cubre 64,2 %, L40 76 %. No cambiar método
ni parámetros a posteriori; robustez sigue exploratoria. Semilla independiente
20260915 no ejecutada al no haber candidato que pase. Se verifican todos los hashes,
resúmenes/tablas y 12 reproducciones exactas. Resumen completo conservado en
`docs/evidence/dependence-study-v1-summary.json`, fuentes largas locales.

[Revisión Windows](diagnostico_windows_20260913.md): se reprodujo WinError 5 en
reemplazo atómico del monitor y lanzador. Ahora el mismo temporal se reintenta
solo para errores Windows 5/32/33, máximo seis intentos/310 ms acumulados; fallos
persistentes se propagan y conservan el JSON anterior. No reintenta acciones.
Seis regresiones nuevas, incluido handle real que impide reemplazar temporalmente.
Primera pasada Python usó por error el Node global antiguo: no confundir ese cierre
nativo con la entrega. Todas las comprobaciones finales usan Node 24.21.0.

Validación final: **1.168 Python + 91 subcasos**, 338 frontend, ocho Node;
contratos/TypeScript/lint/build correctos. 45 pruebas de LaTeX/HTTP después del
último ajuste de composición. Regresión E2E final
`e2e-d3b911045f3242c2b740cbce8503d05f`, **25/25 en 1,8 min**; resultado 0,
servidores 0/0, sin parada forzada/errores de limpieza, puertos libres e integridad OK.
Captura 1.884 grupos y 70 marcas de fallo/cancelación ≤169,68 ms, ninguna lenta.

La primera E2E sí tuvo dos timeouts de 10 s en recorridos antiguos (23/25):
síntoma observado, causa no confirmada; las capturas siguientes no lo reproducen.
**La incidencia API sigue abierta.** No presentar los reintentos acotados del JSON
como una corrección de la API ni el monitor sintético como un ensayo real.

ATLAS habitual **detenido** y base intacta, SHA-256
`2791f15e1bb5be5833117810ce5de745e4dfb46817850c4d8d8cbc3cc2bc5549`.
Sin llamadas IA/bróker/claves ni gasto facturable. No reactivar ensayo de 48 h,
portátil, movimientos personales o aceptación/fusión PR #12. La aceptación dev.7
no sustituye esas revisiones ni declara estable v0.2/v0.6.

## Continuación dev.7: interfaz retrospectiva y cinco tareas completadas

«Haz las 5 cosas» autoriza publicación dev.6, revisión estadística, interfaz
retrospectiva, segundo activo y definición LaTeX. [Plan previo](v0_6_dev7_plan.md)
y [guía/evidencia](v0_6_retrospectivo_interfaz.md). Rama `codex/v0.6-evaluador`,
**0.6.0-dev.7 local**, esquema 5. No nueva PR/fusión/etiqueta.

Dev.6 **subida sobre `27892a2`**, [CI 34768335375 correcta](https://github.com/Buzo500/atlas-quant/actions/runs/34768335375):
1.104 Python + 91 subcasos, 328 frontend, ocho Node, 24 E2E y arranque/parada.
Node 24.21.0, 3.685 conexiones sin fallos, contratos/build/TypeScript/lint.
Cuota 486,7 → 510/2.000 minutos, **0 USD facturables**, presupuesto cero con bloqueo
de pago comprobado antes del lanzamiento. [Publicación](publicacion_v06_dev6.md).
La CI no cubre los cambios posteriores de dev.7.

Dev.7 añade cuatro rutas HTTP locales acotadas y panel en Laboratorio para CSV y
calendario explícito, revisión del protocolo congelado antes de calcular, curvas,
descarga JSON/CSV/ZIP y reapertura verificada por recálculo. Contratos generados.
`retrospective_package.py` compartido con CLI, políticas acreditadas intactas,
sin nuevas tablas/libros/candidatas ni apertura de reserva. Conservación inicial
mediante archivos descargados; el borrador no sobrevive a recargas/cambios de
pestaña. Reabrir código anterior conserva informe/huellas originales, muestra la
diferencia y exige resultados idénticos; CLI verify conserva coincidencia estricta
de código. Reproducción del ZAL original comprobada, sin reescribirlo.

HFG.DE/HelloFresh, DE000A161408, EUR/Xetra: elegido y predeclarado antes de descarga
y cálculo. 762 fechas contrastadas con calendario 2023–2025, sin huecos y sin
dividendos/splits en la respuesta Yahoo gratuita/TLS verificado. Recompras del
emisor reconocidas; no se acredita ausencia exhaustiva de eventos o disponibilidad.
Mismo SMA20/50/capital 10.000/lote/pesos/costes que ZAL: desarrollo 634 sesiones,
NAV SMA **8.413,39 EUR**, BH **3.803,28 EUR**, efectivo 10.000 EUR. Pérdida y caída
SMA 57,36 % explícitas, sin promoción. Reserva 128 sesiones no calculada ni
exportada con precios. Informe `4b06777d73354bc5c87a9c773285794a36bf49d72568e02c818bf1195c856880`,
ZIP local `output/validation/v06-retrospective-hfg/atlas-hfg-desarrollo.zip`,
verificado por recálculo con el código dev.7.

[Revisión estadística](v0_6_dependencia_revision.md) con oráculo AR(1) frente a
matriz de covarianzas y nuevo experimento fijado. No cambia L=10 ni los informes;
el estudio nuevo aún no se ejecuta. [LaTeX definido](informes_latex_diseno.md),
fuente `.tex` y dos páginas HTML sintéticas inspeccionadas, sin compilador nuevo,
PDF o generador integrado. REPORT-001 conserva ampliaciones de cartera/fechas.

Dev.7 local: **1.124 Python + 91 subcasos**, 336 frontend, ocho Node, **25 E2E**
finales correctos; contratos, TypeScript, lint y build canónico. Recorrido nuevo
incluye teclado, descarga/reapertura exacta, reserva excluida y anchuras CSS
565/1366/3440, sin afirmar comprobación física de DPI.
Un selector de la prueba inicial falló tras llenar el textarea; corregido por
nombre accesible. Se acotó su altura para archivos largos. Pase dirigido 1/1
y regresión final completa `e2e-8067445a9b4c451bb5cd1189375e342c`, 25/25 en 111,42 s,
sin omitidos/reintentos. Resultado 0, ambos servidores salida 0, sin parada forzada,
limpieza correcta, puertos liberados e integridad OK.
Captura final 1.886 grupos, 82 marcas de fallo/cancelación ≤167,705 ms, ninguna
espera de 1 s. La CI dev.6 sí registra hasta 3.050,818 ms; ninguna captura demuestra
la causa de la incidencia histórica. No declararla resuelta.

ATLAS habitual **detenido**, build dev.7 listo para iniciar. SHA-256 de su base
conservado `2791f15e1bb5be5833117810ce5de745e4dfb46817850c4d8d8cbc3cc2bc5549`.
Sin proveedor IA/claves/dependencias nuevas/gasto. No reactivar portátil,
aceptación/fusión PR #12, ensayo de 48 h o movimientos personales. La fuente
acreditada sigue pendiente; retrospectivo no la sustituye.

## Antecedente dev.6: retrospectivo, caso observado y exportación local

«Vale, haz las 5 cosas» autoriza definir el modo retrospectivo, auditar una fuente
EUR, calcular el primer desarrollo con costes/reserva, ampliar cobertura y preparar
exportación reproducible. Completado como entrega inicial por CLI en la rama
`codex/v0.6-evaluador`, **0.6.0-dev.6 local**, esquema 5.
[Política, fuentes, resultados, comandos y limitaciones](v0_6_retrospectivo.md).

`atlas-retrospective-eur-v1` usa contratos independientes con indicadores de
acreditación falsos, calendario/horarios y ejecución supuestos. Comparte evaluador
SMA y NativeBook; la fábrica de especificaciones es un argumento interno, no una
opción HTTP. El Laboratorio acreditado conserva sus validaciones y contratos.
No hay nuevos endpoints, formularios, libros, candidatas ni permiso de órdenes.
Exporta desarrollo en JSON/CSV/ZIP determinista; valida entradas e integridad,
recalcula todos los resultados y no extrae archivos. LaTeX queda para otra entrega.

ZAL.DE (Zalando, DE000ZAL1111) descargado gratuitamente con yfinance 1.7.0 y TLS
verificado, sin dependencias nuevas. 762 fechas completas contrastadas con Xetra
2023–2025, sin eventos en la respuesta; la ausencia exhaustiva de eventos/base
point-in-time no está acreditada. Solo apta bajo la política retrospectiva.
SMA 20/50, 10.000 EUR, coste fijo 1 EUR + 5 pb y deslizamiento 5 pb, fijados antes
del cálculo: desarrollo 634 sesiones hasta 30/06/2025, NAV final 8.246,07 EUR;
BH 8.358,97 EUR. Reserva de 128 sesiones desde 01/07/2025 no calculada ni exportada
con precios. No acredita desconocimiento externo ni una reserva global de ATLAS.
Artefactos locales: `output/validation/v06-retrospective-zal/`; ZIP
`atlas-zal-desarrollo.zip`, verificado por recálculo con resultado idéntico.

Ampliación de cobertura: 100 historias por cada uno de seis escenarios, 5.000
réplicas y L=5/10/20. L=10 principal: 94/100 IID, 91/100 AR(1) phi=0,6,
73/100 AR(1) phi=0,9, 95/100 t(5), 94/100 cambio de varianza y 100/100 cambio de
media. Los cambios son estrés no estacionario, no prueba de validez.
Infracobertura explícita; no cambiar parámetros a posteriori ni promover
estrategias. Se verificaron hashes, 600 historias, 1.800 resultados y recuentos;
originales en `output/validation/robustness-coverage-v2/`. El experimento v1 queda conservado.

Validación local: **1.104 Python + 91 subcasos**, incluidos 40 nuevos y regresión
completa del motor; cuatro E2E v0.6 correctos (18,6 s: desarrollo/reserva,
walk-forward, sensibilidad/candidatas y robustez). Build canónico, contratos,
TypeScript y lint correctos. No se ha repetido toda la suite frontend/24 E2E;
las cifras 328/24 y CI 34760823911 de abajo son de dev.5.
E2E `e2e-03618c9f0ac045e9a7a9db09c0b5924d`: resultado 0, ambos servidores salida 0,
sin parada forzada ni error de limpieza, puertos liberados e integridad correcta.
Captura: 321 grupos correlacionados, un cierre incompleto/ECONNRESET de `/api/state`
a ~10 ms, ASGI completa en ~15 ms; no hay espera larga reproducida ni causa
histórica confirmada. No se cambia transporte ni se declara resuelta la incidencia.

ATLAS habitual continúa detenido. SHA-256 de su base conservado:
`2791f15e1bb5be5833117810ce5de745e4dfb46817850c4d8d8cbc3cc2bc5549`, igual al cierre
anterior y tras estas pruebas. Compilación dev.6 preparada para el próximo arranque.
Sin subida, CI remota, PR, fusión o etiqueta nuevas; ningún gasto ni proveedor IA.
No reactivar revisión pendiente v0.5/PR #12, portátil, ensayo o movimientos personales.
La fuente apta para el Laboratorio acreditado sigue pendiente; el caso retrospectivo
no la sustituye. Revisión dev.5 y contraste Windows–WSL anteriores ya completados.

## Continuación dev.5: historial corregido y segundo entorno comprobado

El usuario autoriza cinco tareas después de la revisión guiada. Corrección localizada
del historial y navegación compacta, comprobación responsiva/teclado, subida/CI
gratuita, contraste numérico entre entornos y búsqueda de datos observados.
[Detalle y evidencia](v0_6_historial_contraste.md). Dev.5 y esquema 5 conservados,
sin cambios estadísticos, contables ni en la reserva final.

Historial comprobado a 565/960/1366/3440 px CSS. 328 frontend, ocho Node, 24 E2E
locales, contratos, TypeScript, lint y build correctos. Seis resultados completos
exactamente iguales en Windows/Python 3.14.4 y Ubuntu/WSL/Python 3.12.3, NumPy
2.5.2 en ambos. No equivale a validar toda ATLAS en Linux o en otro ordenador.
La [fuente observada](v0_6_csv_observado.md) sigue pendiente tras revisar alternativas
primarias; no se inventa evidencia ni se fuerza una importación.

Rama `codex/v0.6-evaluador` subida sobre `2ee0dec`, CI gratuita
[34760823911](https://github.com/Buzo500/atlas-quant/actions/runs/34760823911) correcta:
1.064 Python + 91 subcasos, 328 frontend, ocho Node, 24 E2E, build/contratos/
TypeScript/lint y arranque/parada. Node 24.21.0, 3.683 conexiones de sonda sin
fallos; captura API con máximo 1.577,284 ms, sin confirmar la causa histórica.
Cuota mostrada 465 → 486,7/2.000 minutos, 0 USD facturables y bloqueo de pago
comprobado. Cierre posterior solo Markdown, subido sin repetir CI.
App habitual detenida, base intacta y pruebas aisladas cerradas con resultado 0,
puertos libres e integridad correcta. No hay nueva PR/fusión/etiqueta ni se reactivan
portátil, ensayo o movimientos personales.

## Antecedente: revisión guiada dev.5 completada, ajuste visual pendiente

El usuario ha completado cálculo, lectura de contexto/método, recuperación tras
recarga, reproducción estadística y muestra insuficiente. El agente comprobó
además que «No evaluable» se recupera tras recargar. [Registro y procedencia de
las comprobaciones](revision_guiada_v06_dev5.md). No repetir estos pasos como si
siguieran pendientes ni confundirlos con la aceptación de v0.5/PR #12.

Defecto visual confirmado, sin corregir: el botón «Consultar robustez…» tiene
`white-space: nowrap` y desborda un panel de 435,35 px en un viewport de 565 px;
el documento alcanza 629 px. Proponer ajuste localizado y verificación responsiva.
Recorrido funcional correcto; esto no declara estable toda v0.6.

Sesión `e2e-efa0141a11a04f01a1c94729b66e99f1` detenida de forma cooperativa:
resultado 0, servidores con salida 0, integridad correcta, sin errores de limpieza,
base habitual intacta y puertos liberados. Ambas sesiones de revisión están
cerradas; ATLAS queda detenido. Captura diagnóstica conservada, causa API aún
sin confirmar. Cierre solo documental local, sin subida/CI/PR/fusión/etiqueta.

### Antecedentes de la preparación y seguimiento de la revisión

Los pendientes y arranques de este apartado describen estados intermedios,
sustituidos por el cierre anterior.

Primer paso comprobado por el usuario mediante captura del informe calculado y
guardado a las 15:06:39 del 13/09: muestra completa, revisión 1, 504 intervalos
tras 3 sesiones de calentamiento, bloques 5/10/20 con 10 principal, estado
«Exploratorio» y acceso al informe en el historial. Media visible
−0,010393445904 pp diarios; los intervalos mostrados incluyen cero. Esto confirma
la presentación y el cálculo/guardado inicial. Muestra corta y aceptación
completa siguen pendientes. El usuario
confirma después haber realizado la revisión de «Contexto económico y ensayos
declarados» y «Método y reproducción» (comprobación comunicada por él, sin nueva
ejecución del agente). El usuario confirma recuperar el informe tras recargar y
que los valores coinciden. Lectura de la interfaz a las 15:13 confirma el informe
original de las 15:06:39, mismo motivo, 504 intervalos y resultados conservados.
Después de pulsar «Comprobar reproducción estadística», el usuario confirma que
aparece «Reproducción coincidente: instantánea y resultado conservados».
Reproducción manual comunicada por el usuario, sin ejecutar esa acción el agente.
Siguiente acción guiada: calcular robustez para «Revisión dev.5 · muestra corta»
y comprobar «No evaluable» por 4 intervalos frente al mínimo de 504.
La captura muestra
desplazamiento horizontal de la tabla y el botón de historial cortado a la derecha;
observación de presentación pendiente de valorar, sin modificar código.

Reapertura solicitada por el usuario el 13/09, sin haber podido comprobar el
primer paso. La sesión anterior terminó con resultado 0, ambos servidores con
salida 0, integridad correcta, puertos liberados y base habitual intacta. Al
retomar estaba abierto ATLAS habitual, run `f02eadac431b4a0ea5bf07cbdaee9097`, sin
experimentos activos; se detuvo mediante su lanzador antes de preparar la revisión.
Nueva sesión aislada `e2e-efa0141a11a04f01a1c94729b66e99f1`, abierta aproximadamente
a las 15:04, con el mismo límite de 1.200 segundos. Recibo y log excluidos:
`output/validation/dev5-manual-20260913-reapertura.json` y
`output/validation/dev5-manual-20260913-reapertura.log`. Casos sintéticos recreados
con nuevos identificadores; base habitual intacta durante la preparación. Formulario
de muestra completa abierto, informe aún sin calcular por el agente y aceptación
pendiente. Parada anticipada:
`.venv/Scripts/python.exe tools/run_e2e.py --stop-run e2e-efa0141a11a04f01a1c94729b66e99f1`.
Verificar vigencia y cierre de esta nueva sesión al continuar. Sin cambios de
código ni publicación; el registro siguiente describe la primera sesión.

El usuario autoriza la revisión guiada de dev.5. Se ha preparado una sesión
manual aislada, sin modificar código ni arrancar la base habitual:
`e2e-d8fc7ecf780a47c8bc9de48f8c3fa904`, iniciada el 13/09 a las 14:30
(Europe/Madrid), con límite de 1.200 segundos y parada automática. Antes de
continuar, comprobar si sigue activa; no dar por vigente este arranque después
del límite. Interfaz local: `http://127.0.0.1:3000/?tab=lab`.

Dos candidatas sintéticas: «Revisión dev.5 · muestra completa», con 504 intervalos
de desarrollo tras el calentamiento, y «Revisión dev.5 · muestra corta», con 4.
Se crearon sus protocolos y revisiones; todavía no se calculó ningún informe de
robustez. La interfaz queda abierta en el formulario de robustez de la muestra
completa para que lo utilice el usuario. Cinco comprobaciones pendientes de su
respuesta: cálculo, interpretación/contexto, conservación al recargar,
reproducción y rechazo de la muestra insuficiente. No confundir esta preparación
con aceptación manual ni con evidencia de mercado observado.

Recibo local excluido: `output/validation/dev5-manual-20260913.json`; log:
`output/validation/dev5-manual-20260913.log`. Base y procesos exclusivos bajo
`var/validation/e2e-d8fc7ecf780a47c8bc9de48f8c3fa904`. Las huellas de la base
habitual coinciden antes y después de preparar los casos; sin proveedores ni
presupuesto de IA. Para cerrar la sesión antes del límite:
`.venv/Scripts/python.exe tools/run_e2e.py --stop-run e2e-d8fc7ecf780a47c8bc9de48f8c3fa904`.
Después verificar el recibo de limpieza, puertos liberados e integridad; no
declarar aún comprobado ese cierre. PR #12, segundo entorno, fuente observada,
ensayo y demás aplazamientos conservan su estado. Sin nueva publicación o CI.

## Publicación dev.5 y CI gratuita correcta

«Haz el 2» autoriza subir la rama y ejecutar CI gratuita. Rama
`codex/v0.6-evaluador` subida y verificada sobre
`6dd01cec456793b506f7f6f44fb4700f60bed6ab`, **0.6.0-dev.5**, esquema 5.
[CI 34707688577](https://github.com/Buzo500/atlas-quant/actions/runs/34707688577)
**correcta**, job 103590615138, primer intento: **1.064 Python + 91 subcasos,
328 frontend, ocho Node, 24 E2E**, build/contratos/TypeScript/lint y arranque/parada.
[Registro de publicación y límites](publicacion_v06_dev5.md).

Node 24.21.0: 3.632 conexiones HTTP sin fallos. E2E
`e2e-0dbd4aeee0824238a9df110c5731543d`, 3,1 min, ambos servidores con salida 0,
integridad correcta, base habitual del runner intacta y puertos liberados.
Captura de 1.816 peticiones, seis grupos ≥1 s, máximo 1.333,30 ms; no reproduce
la espera histórica. Arranque posterior confirma dev.5/proxy/interfaz/gasto de IA 0
y parada limpia. Esta validación remota no es una nueva ejecución en este PC.

Cuota comprobada antes y después: **446,7 → 465 de 2.000 minutos**, 0/0,5 GB.
**0 USD facturables**, presupuesto Actions 0 USD con bloqueo de pago comprobado;
facturación intacta. Log local excluido `output/validation/ci-34707688577.log`.
Cierre posterior solo documental, subido en la misma rama sin otra CI.
App habitual sin arrancar ni modificar su base; sin nueva PR/fusión/etiqueta.
Revisión funcional dev.5, aceptación PR #12, segundo entorno numérico y fuente
observada suficiente siguen pendientes; API histórica abierta. Portátil, ensayo
y datos personales mantienen sus aplazamientos. Los estados siguientes son antecedentes.

## Cuatro últimos pasos · integración, fuente, captura y robustez local dev.5

«Haz los 4 últimos» acepta los puntos 2–5: decidir integración con PR #12,
obtener/auditar CSV observado suficiente, capturar la espera API si reaparece e
implementar el primer bloque estadístico. No realiza el punto 1 de revisión manual.
Rama `codex/v0.6-evaluador`, **0.6.0-dev.5**, esquema 5. Guía:
[robustez exploratoria](v0_6_robustez_implementacion.md); conserva el diseño previo.

Implementado: bootstrap estacionario pareado sobre NAV del desarrollo, con
calentamiento excluido, L=5/10/20, principal 10, 5.000 réplicas y NumPy 2.5.2/PCG64.
504–2.000 intervalos, máximo 30 millones de índices y semáforo compartido.
Informe independiente con candidata/revisión inmutable, ensayos declarados,
contexto económico, estado no evaluable, hashes y reproducción. Proyección SQL de
solo desarrollo: no entrega barras, aperturas ni resultados/calendario de la reserva
al módulo estadístico. Auditoría/guardado atómicos y ninguna escritura en libros.

Experimento de cobertura predeclarado: 180 históricos sintéticos, tres longitudes
por cada uno. L=10 cubre 57/60 IID y 53/60 AR(1); se documenta la infracobertura
sin reajustar parámetros. 95 % es nominal, sin significación confirmatoria,
probabilidad de éxito, promoción de candidatas ni permiso de órdenes.

Verificación local: **1.064 Python + 91 subcasos, 328 frontend, ocho Node, 24/24 E2E**,
contratos, TypeScript, lint y build canónico. E2E
`e2e-fcfb5be04b53451a976d6a77cd603e2c`, 102,58 s, recarga/reproducción y anchos CSS
960/1366/3440. No equivale a nueva comprobación física del portátil. Guardado
concurrente, conflictos, corrupción y rollback comprobados con datos aislados.

Puntos condicionados: [búsqueda de CSV](v0_6_csv_observado.md) ampliada con fuentes
primarias, **sin conseguir datos observados aptos**; no fabricar disponibilidad.
[Captura API](diagnostico_api_20260911.md): 1.840 peticiones, ningún grupo ≥1 s,
67 cierres/finalizaciones incompletas de captura por debajo del umbral, sin
reproducir la espera histórica. Ambas incidencias siguen abiertas.
[Integración](integracion_v06_pr12.md) definida: conservar v0.5 → v0.6 por separado;
PR #12 sigue abierta y requiere la aceptación funcional pendiente antes de fusionar.

App habitual ya detenida y conservada así; pruebas con motor/interfaz aislados,
salida 0 sin parada forzada, integridad correcta, base habitual intacta y puertos
liberados. Sin llamadas pagadas ni cambios de presupuesto. Trabajo local sobre
`3211b42`; no nueva subida/CI remota/PR/fusión/etiqueta. Segundo entorno numérico,
portátil, ensayo y datos personales pendientes/aplazados según corresponda.
Las entradas siguientes son antecedentes; la CI dev.4 no acredita dev.5.

## Diagnóstico y corrección del cierre de Node · CI final correcta

«Haz los 3 primeros pasos» autoriza diagnosticar el servidor E2E, corregir y volver
a ejecutar CI gratuita. [Evidencia y límites](diagnostico_ci_20260912.md).
Se reproduce un cierre nativo de Node 24.15.0 en una sonda HTTP local independiente
de ATLAS: `0xC0000409`, el mismo código del último frontend habitual. Node 24.21.0
se instala privadamente y se selecciona en lanzadores/build/E2E, con versión fijada
en Actions y regresión HTTP acotada. [Instalación](node_windows.md); Node global intacto.

Corrección local validada: **1.024 Python + 91 subcasos, 322 frontend, ocho Node y
23 E2E**, contratos, TypeScript, lint y build. La CI 34690769777 sobre `647be92`
pasó con Node 24.15.0 e instrumentación nueva (1.010 Python + 91, 322 frontend,
ocho Node, 23 E2E y arranque/parada). La corrección se sube en
`e1628b230a2f0e7b2630588361abe79fad21c108`: [CI 34691977950](https://github.com/Buzo500/atlas-quant/actions/runs/34691977950)
**correcta** con Node 24.21.0, 1.024 Python + 91 subcasos, 322 frontend, ocho Node,
23 E2E (2,9 min), build, contratos, TypeScript, lint y arranque/recorrido/parada.
Sonda HTTP: 3.659 conexiones sin errores. Servidores E2E con salida 0, sin parada
forzada, integridad correcta, base del runner intacta y puertos liberados.
El cierre posterior es solo documental; la CI acredita `e1628b2`.
Cuota comprobada tras las dos ejecuciones de este turno: **446,7/2.000 minutos**
(405 al comenzar y 426,7 tras la de diagnóstico); 0/0,5 GB, 2,68 USD brutos
cubiertos por descuentos y **0 USD facturables**. Presupuesto Actions 0 USD y
bloqueo de uso de pago verificados antes de cada CI, sin cambios de facturación.
La app habitual ya estaba detenida; no se arranca ni se modifica su base.
Versión 0.6.0-dev.4/esquema 5, sin PR/fusión/etiqueta nuevas. Portátil, PR #12,
ensayo y datos personales aplazados. La causa exacta del job antiguo no se prueba
sin su código de salida/dump; el timeout API histórico sigue abierto.

Las entradas siguientes describen estados anteriores a esta autorización.

## Publicación de dev.4 · CI remota fallida

El usuario autoriza **solo el punto 1: subir dev.4 y ejecutar CI gratuita**.
Rama `codex/v0.6-evaluador` subida y verificada contra origin sobre
`8dadb74de5ff65036a2d6d7236a3b694064036e6`, versión 0.6.0-dev.4 y esquema 5.
[CI 34610747174](https://github.com/Buzo500/atlas-quant/actions/runs/34610747174),
job 103300338249, `workflow_dispatch` sobre ese commit: **fallida**, sin reintento.

Pasan **1.004 Python + 91 subcasos, 322 frontend y ocho Node**, instalación/build,
TypeScript, contratos y lint. E2E `e2e-af41d2b021384cde87a63647412c930a` registra
14 recorridos correctos de 23 previstos y después aborta con «El puerto 3000 no
pertenece al proceso E2E frontend». No existe resultado completo de los nueve
restantes. Los pasos posteriores de arranque/recorrido sintético y parada se omiten.
El cierre del entorno aislado verifica integridad, puertos liberados y base habitual
del runner sin cambios; no es una comprobación de la base de este PC.

[Diagnóstico y límites](diagnostico_api_20260911.md): 740 peticiones correlacionadas,
12 grupos (nueve de error/cancelación y tres de al menos 1 s), sin truncamiento.
El log retenido no contiene la causa de la pérdida del servidor; no se identifica
con el timeout histórico ni se cambia el programa por conjetura. Siguiente paso
propuesto: conservar código de salida y cola acotada de logs de los servidores,
y reproducir el fallo antes de corregir/repetir CI. No está ejecutado por esta petición.

Facturación comprobada en la sesión de GitHub: antes 386,7/2.000 minutos y después
**405/2.000**, almacenamiento 0/0,5 GB; 2,43 USD brutos cubiertos por 2,43 USD de
descuentos, **0 USD facturables**. Presupuesto Actions 0 USD con `Stop usage: Yes`;
no se cambia la facturación. Log local excluido de Git:
`output/validation/dev4-ci-34610747174.log`; resumen `dev4-ci-publication.json`.

En este turno la lectura de salud de `127.0.0.1:8000` devuelve conexión rechazada.
No se ha arrancado/parado ATLAS ni modificado código o datos locales; la causa no
se ha diagnosticado. La comprobación correcta de salud/tablas de la entrada
siguiente pertenece al turno de implementación anterior. Cierre posterior solo
documental subido en la misma rama: la CI corresponde al código `8dadb74`, no al
commit documental posterior. Sin nueva PR, fusión o etiqueta; portátil, PR #12,
ensayo, movimientos personales y demás tareas mantienen sus aplazamientos.

## Antecedente local · cinco tareas de prevalidación y consulta v0.6 dev.4

Autorización «Vale, haz las 5»: buscar datos observados acreditados, prevalidar CSV
visualmente, capturar la próxima recurrencia API, buscar/comparar candidatas y
concretar el método estadístico antes de implementarlo. **0.6.0-dev.4**, rama
`codex/v0.6-evaluador`, esquema 5. [Guía de uso y verificación](v0_6_prevalidacion_consulta.md).

Implementado: prevalidación de versión nativa de solo lectura (sin acreditar ni
calcular), búsqueda literal Unicode en revisiones históricas y comparación de
dos a cuatro referencias inmutables. Mantener controles compartidos de identidad,
contexto económico explícito, evidencia capturada, libros/reserva intactos y ninguna
promoción automática. [Estadística](v0_6_robustez_estadistica.md) definida, **sin código**.

Puntos condicionados: **no se consiguió un dataset observado apto**, con fuentes
consultadas y límites en la [auditoría](v0_6_csv_observado.md); no completar
artificialmente `available_at` ni acreditar precios/eventos. La espera API original
no reapareció: [captura nueva](diagnostico_api_20260911.md), sin causa raíz confirmada.
El workflow local ahora usa `run_api_diagnostic.py` para retener trazas correlacionadas
en la próxima CI autorizada. No se ha lanzado CI remota ni un monitor/ensayo.

Validación: **1.004 Python + 91 subcasos, 322 frontend, ocho Node, 23/23 E2E**,
contratos, TypeScript, lint y build canónico correctos. E2E completo con diagnóstico
`e2e-48ea8fb5ecc84a728994ca1c2758ac45`, 1,7 min; 1.769 peticiones correlacionadas,
sin ninguna agrupación de al menos 1 s, base habitual intacta y limpieza correcta.
Regresiones dirigidas posteriores para los textos finales y captura visual en
`e2e-4932c0c8308141a0bfe0a92221ca82c6`, cerrado limpiamente. Anchos CSS 960/1366/3440;
no atribuir una nueva validación física al portátil. Las dos incidencias de UI
encontradas durante E2E y su corrección están registradas en la guía.

Copia previa `backups/atlas-20260911T130808392926Z-e4eca471`. ATLAS habitual
recompilado y arrancado como dev.4, run `94f976d38cc343e390bcfcb3343f2e6f`.
Comprobación de solo lectura: salud directa/proxy y HTML correctos, esquema 5,
tres carteras, todas las tablas iguales a la copia previa, parada global activa,
sin proveedores configurados ni protocolos ficticios añadidos a la base habitual.
Artefactos `output/validation/dev4-health.json`, `dev4-data-online.json` y capturas
`dev4-*.png`, todos locales y excluidos de Git.

**Entrega solo local, sin subir ni CI remota nueva, fusión o etiqueta.** La última
CI publicada 34600509327 pertenece a dev.3; no atribuirla a estos cambios. Portátil,
PR #12, ensayo de 48 horas, movimientos personales, llamadas pagadas y operaciones
externas conservan sus aplazamientos. No hay gasto nuevo ni dependencias instaladas.
Las siguientes entradas son antecedentes.

## Cinco tareas autorizadas · sensibilidad y candidatas v0.6

El usuario acepta «Venga, a hacer todos»: diagnóstico API, subir/CI gratuita,
contrastar CSV observado, sensibilidad y registro de candidatas. Esta autorización
sustituye el alcance anterior de solo walk-forward. **0.6.0-dev.3**, rama
`codex/v0.6-evaluador`, esquema 5; [guía y pruebas](v0_6_sensibilidad_candidatas.md).

Implementados escenarios de un factor cada vez declarados antes del cálculo,
reserva final intacta, informes reproducibles; candidatas con hipótesis, motivos,
estados de investigación/seguimiento/descarte y evidencia inmutable por revisión.
No existe promoción automática ni envío de órdenes. La [auditoría del CSV NVD](v0_6_csv_observado.md)
encuentra 175 filas válidas pero evidencia insuficiente y falta de sesión 07/09;
no importado ni acreditado como apto. El [diagnóstico API](diagnostico_api_20260911.md)
no reproduce la espera: 2 recorridos y 301 lecturas correctos, sin cerrar la incidencia.

Validación local: **990 Python + 91 subcasos, 317 frontend, ocho Node y 23 E2E**,
contratos/TypeScript/lint/build correctos. Tras la revisión visual se corrigió el
formato de fecha/hora de candidatas, con regresión dirigida y nueva compilación.
Capturas finales aisladas a 960/1366/3440 px, formulario y curvas revisadas.
La guía conserva fallos iniciales y sus límites. **Rama subida sobre `8e4d087dadc241ca9b79c56005f057e369ca5ce1`**;
[CI gratuita 34600509327](https://github.com/Buzo500/atlas-quant/actions/runs/34600509327) **correcta sobre ese commit**: 990 Python + 91 subcasos, 317 frontend, ocho Node, 23 E2E y arranque/parada. Todos los pasos correctos, 11 min 51 s en total; log `output/validation/v06-five-ci.log`. CI 34590252591 solo valida dev.1. Cuota previa 366,7/2.000 minutos, almacenamiento
0/0,5 GB, 0 USD facturables y presupuesto Actions 0 con bloqueo comprobados.
Tras CI: **386,7/2.000 minutos**, 0/0,5 GB; 2,32 USD brutos cubiertos íntegramente
por 2,32 USD de descuentos, **0 USD facturables**. No se cambió la facturación.

ATLAS detenido antes de editar, copia `backups/atlas-20260911T121035724463Z-d6011740`.
Los entornos aislados cerraron con integridad y base habitual intactas. ATLAS
habitual arrancado con run `a5975463f5ab4e7fbe2617595eddd5e1`: salud directa/proxy
0.6.0-dev.3, HTML 200, parada global activa, sin proveedores configurados. Tres
carteras y todas las tablas coinciden con la copia previa, esquema 5 e integridad
correctos. Evidencia `output/validation/v06-five-health.json` y
`v06-five-data-online.json`. Cierre posterior solo documental; rama subida, sin fusión ni etiqueta nuevas. PR #12 y revisión del portátil,
ensayo 48 h, datos personales, pago, bróker, móvil/remoto y LaTeX siguen aplazados.

## Primera tarea autorizada · Walk-forward fijo v0.6

El usuario indica «Vale, haz la primera»: implementar walk-forward, no los otros
cuatro pasos propuestos. Rama `codex/v0.6-evaluador`, **0.6.0-dev.2**, esquema 5.
Leer [v0_6_walk_forward.md](v0_6_walk_forward.md) para contrato, uso y verificación.
Configuración opcional congelada junto al protocolo: contexto 252/evaluación 63
sesiones por defecto; SMA fija, cuentas independientes y calentamiento previo
sin operaciones. Diagnósticos con datos ausentes explícitos, máximos de cálculo,
reproducción y publicación atómica. La prueba final no se abre por esta función.
Los protocolos sin walk-forward conservan su identidad y resultados anteriores.

ATLAS detenido antes de editar; copia previa
`backups/atlas-20260911T105820889993Z-c20a5e3b`. Estado operativo y pruebas finales
en la guía. Ampliación local: no se ha solicitado nueva publicación/CI, fusión ni
etiqueta. La CI 34590252591 de abajo valida dev.1 y no esta ampliación.
Sensibilidad, candidatas, datos observados contrastados, revisión del portátil,
PR #12, ensayo de 48 horas y movimientos personales mantienen sus pendientes.

Cierre: **961 Python + 91 subcasos, 300 frontend, ocho Node y 22 E2E** correctos;
contratos, TypeScript, lint y compilación canónica verificados. Confirmación E2E final
`e2e-7872a710e89941a6874c8ace34e1d4e2`. Una ejecución selectiva anterior agotó 10 s
en GET `/api/state` al preparar la demo, antes del gráfico; conservarla como
recurrencia de la incidencia de transporte, no declararla resuelta por el pase posterior.
ATLAS habitual arrancado con run `a2902c6436714915bc3ec7fa1255b5c7`, salud/UI correctas,
parada global activa, sin proveedores configurados, tres carteras y todas las tablas
iguales a la copia previa. Capturas, límites y registros detallados en la guía.

## Cuatro tareas autorizadas · Laboratorio v0.6

El usuario acepta los cuatro primeros pasos propuestos: subir/CI gratuita, CSV
propio con evidencia, API/UI de simulaciones y validación temporal con benchmarks.
Desarrollo **0.6.0-dev.1** en `codex/v0.6-evaluador`, esquema 5. Guía y registro en
[v0_6_laboratorio.md](v0_6_laboratorio.md), que prevalece sobre los pendientes del
antecedente de abajo. CI inicial **34588116355** correcta sobre `d7ea898`; CI final **34590252591** correcta sobre `e797ca3` (929 Python + 91 subcasos, 297 frontend, 8 Node, 21 E2E y arranque/parada), gasto 0 USD.

Se reutilizan series nativas, evaluador y economía del libro. Protocolos y resultados
se guardan sin tocar carteras. Reservas/exposición por instrumento y fechas impiden
reutilizar como prueba no vista un periodo calculado en este Laboratorio. Dos cuentas
independientes, calentamiento dentro de cada periodo y benchmarks con costes iguales.
No hay optimizador, validación estadística completa ni permisos para ejecución externa.

ATLAS se detuvo antes de editar y se creó
`backups/atlas-20260911T100806272408Z-ab4ac1f1`. ATLAS reiniciado en el sobremesa con run `41ea181bbe744aabbd6a34d20a0acdf2`,
versión `0.6.0-dev.1`, salud/UI correctas y todas las tablas iguales a la copia,
integridad `ok`, tres carteras. Ver la guía para la evidencia. Revisión manual del portátil, PR #12/fusión/etiqueta, ensayo
48 h y movimientos personales continúan pendientes. La CI del núcleo inicial es antecedente; el código API/UI lo valida la CI final.
Rama subida; cierre posterior solo documental, sin nueva etiqueta ni fusión PR #12.

## Ampliación v0.6 · simulación económica EUR offline

El usuario indica «Ahora no puedo usar el portátil, sigue desarrollando lo siguiente». Se aplaza el resto de su revisión manual y se desarrolla el siguiente bloque v0.6, conservando sus confirmaciones anteriores. No se fusiona/etiqueta dev.3 ni se atribuye aceptación global. Las comprobaciones manuales recibidas están conservadas por separado en el commit local `5479df3`.

**Implementado en `codex/v0.6-evaluador`:** `simulation_contracts.py`, `strategy_simulation.py` y `tools/run_sma_simulation.py`, política `sma-economics-eur-v1`. Un instrumento/cuenta ficticia EUR, lotes, costes, deslizamiento, siguiente apertura, límites explícitos y libro `NativeBook` compartido. Intención lógica y posición real de la simulación distintas; rechazos no reintentados, huecos sin valoraciones inventadas, eventos corporativos bloqueados y recuperación por replay del diario de observaciones. [Uso y límites](v0_6_simulacion.md).

**Validación local:** 48 pruebas nuevas, 101 con el evaluador; regresión **909 Python + 91 subcasos**, 84,95 s, dos avisos previos. Contratos HTTP/TypeScript y build con manifiesto correctos, sin cambio frontend/API/esquema. CLI generada y reproducida: capital 1.000 EUR, compra 9 a 100 EUR y venta a 80 EUR, comisión 1 EUR por lado; saldo final **818 EUR**, sin posición y con paridad exacta tras recuperar cada evento. Evidencia `output/validation/v06-economics-python.log` y `v06-sma-economics-reference.json`. Un primer intento del test CLI falló al acceder al temporal predeterminado de pytest; resuelto usando directorio de pruebas nuevo dentro del proyecto, sin cambiar lógica para omitir el test.

**Protección de datos y arranque final en el sobremesa:** parada cooperativa antes de editar, copia `backups/atlas-20260911T094306917891Z-6b217137`; todas las tablas coinciden con la copia tanto tras las pruebas como después del reinicio, integridad `ok`, esquema 5 y tres carteras. ATLAS arrancado con run `78f23e9ad14942d3918a5adbcb7125e8`, salud directa/proxy correcta, HTML de interfaz servido y parada global activa. Evidencia `output/validation/v06-economics-data-pre.json` y `v06-economics-data-online.json`. Sin llamadas pagadas ni datos personales añadidos. Código y documentación se conservan en la rama local, sin push/CI remota nuevos; la CI de dev.3 no valida este bloque posterior. La comprobación del sobremesa no sustituye la revisión aplazada del portátil.

Pendientes v0.6: datos reales con evidencia contrastada, caso de uso persistente/API/UI, protocolo temporal/benchmarks y registro de candidatas. No se conectan ni certifican automáticamente los datasets NVD o la demo legacy. La interfaz/API conservan `0.5.0-dev.3`. Ensayo de 48 horas, movimientos personales, IA de pago, bróker, McClellan, móvil/remoto y LaTeX siguen aplazados.

## Revisión manual en el portátil · operación, avisos y persistencia confirmados

El usuario indica que está en el portátil y confirma «Sí, funciona la comprobación» tras el recorrido guiado: abrir ATLAS, comprobar conexión/versión dev.3 y acceso al comparador, detener mediante `Detener-ATLAS.cmd` y volver a iniciar. **Arranque/parada/segundo arranque aceptados por comprobación manual del usuario en el portátil.** Es evidencia comunicada por el usuario; no una instalación o prueba remota ejecutada por el agente. No volver a pedir esta misma comprobación.

En el comparador aparecen `DEMO_WORLD`, `DEMO_EURO` y `DEMO_BOND`. Tras el recorrido para calcular y consultar el detalle, el usuario confirma «Sí, lo explica, funciona»: queda comprobada por él la presentación de los motivos de métricas no disponibles. La demostración estándar no aporta calendario/base de precios verificados para este comparador; esta confirmación no valida cifras ni correlaciones completas y no se modifica su evidencia para forzarlas.

Después de guardar la comparación, recargar con F5 y volver a consultarla desde «Comparaciones guardadas», el usuario confirma «Sí, aparece igual». Quedan comprobadas por él la persistencia y la reapertura de ese informe, con sus activos, fechas y explicaciones. No se le pide repetir el recorrido ni se atribuye una inspección del libro a esta respuesta.

Continúan pendientes revisar resultados numéricos con datos preparados, el caso guiado de planificación/guardado y la aceptación de los límites del alcance funcional. Las respuestas recibidas no declaran esos pasos completados ni autorizan atribuir una aceptación global. Para guiar planificación en el portátil, falta conocer si hay una cartera con libro v2: la demo legacy no muestra ese panel. Fusión y etiqueta dev.3 mantienen su autorización previa condicionada a cerrar esa revisión. La rama local, CI y estado del sobremesa del bloque siguiente no cambian; no se ha accedido a la base del portátil.

## Cinco pasos posteriores · revisión/CI de dev.3 e inicio SMA

**Estado final de esta tarea:** documentación de la PR #12 subida y verificada en `c3ec20c4e1c80c2fad4663121234d08f0b3ef4a4`; solo Markdown después de `ccb4b4a`, que pasó la CI. PR abierta, sin fusión ni etiqueta dev.3 porque la respuesta de revisión manual sigue pendiente. No repetir una petición genérica de permiso: esas acciones ya están autorizadas tras la aceptación. Portátil sin validación confirmada.

**Carpeta habitual en `codex/v0.6-evaluador`**, núcleo `2dbeb41` y documentación de dev.3 incorporada por merge `4d0fa3c`, más cierre local posterior. V0.6 se conserva en Git **solo localmente**, sin push/PR/CI remota nueva. [Guía del evaluador](v0_6_evaluador.md). No confundir esa conservación local con la rama dev.3 ya subida.

**Arranque final comprobado:** run `b51625396be8415892d759e72ab55899`; salud directa/proxy dev.3, esquema 5 e integridad correctos. Antes de arrancar, todos los registros coincidían exactamente con la copia previa; después siguen iguales las tablas históricas, registros, tres carteras y libros/respuestas EUR. No se introducen informes/operaciones sintéticos ni se cambian metadatos del feed en esta comprobación. Parada global activa, gasto/reserva cero y experimento previo completado. Evidencia `output/validation/v06-start-ordinary-pre.json` y `v06-start-ordinary-online.json`. Interfaz conectada; build anterior verificado, sin cambios de fuentes de frontend. La parada previa fue cooperativa, ambos procesos código 0. Inicio `Abrir-ATLAS.cmd`, parada `Detener-ATLAS.cmd`.

Autorización: «Vale, a por las 5 cosas» incluye revisión manual de v0.5/portátil, PR/CI gratuita, fusión/etiqueta dev.3 tras revisión, diagnóstico de NVIDIA y comenzar el primer evaluador SMA20/50. [Registro de entrega](v0_5_dev3_entrega.md). **Sustituye la restricción anterior de v0.6 solo definida**, sin ampliar a simulador económico, UI, bróker o IA de pago.

**PR #12 reutilizada y actualizada. CI gratuita [34578070191](https://github.com/Buzo500/atlas-quant/actions/runs/34578070191) correcta sobre `ccb4b4ad0883c09fc217307b2ffb8d46e79f8bd4`:** 808 Python + 91 subcasos, 294 frontend, ocho Node, instalación/build, tipos/lint/contratos, 20/20 E2E en 3,9 min y arranque/parada. Run remoto `e2e-f8a66515258a45df8a7d9bb8c48aac03`, base ordinaria intacta, integridad/limpieza correctas. Cierre posterior solo documental. Coste antes 310 y después 330/2.000 minutos, 0/0,5 GB y 0 USD facturables; presupuesto Actions 0 con bloqueo verificado. Logs `output/validation/v05-dev3-ci.log`.

**Revisión manual pendiente:** se ha pedido al usuario su resultado de arranque/parada del portátil y aceptación del alcance inicial/caso guiado. No atribuirle una aceptación no recibida. Fusión y etiqueta están autorizadas tras la revisión; la CI ya está correcta. No se ha declarado estable ni completado el ensayo de 48 horas.

**NVIDIA diagnosticada:** sonda aislada 08:12 UTC, TLS correcto, salida yfinance anterior al validador sin cierre para el 10/09. Rechazo correcto; no identifica si el origen interno es Yahoo o yfinance. Dos NVD.DE siguen en v2 hasta 09/09, 428 y 1.194 barras, versiones 1/2 conservadas. Calendario sin verificar, base desconocida y eventos pendientes; ver [diagnóstico y evidencia requerida](diagnostico_nvidia_20260911.md). Sin modificar el feed, precios ni libros.

**Primer bloque v0.6 local y separado:** `codex/v0.6-evaluador`, commit `2dbeb41`, sobre la cabeza de dev.3. `sma-cross-evaluator-v1`: contratos estrictos, comparación de medias exacta, reloj/datos explícitos, objetivo por presupuesto, replay e incremental compartidos, huecos/eventos, expiración de apertura y checkpoint. 53 pruebas nuevas; **861 Python y 91 subcasos** en 84,49 s, dos avisos previos; `output/validation/v06-python.log`. Referencia `tools/run_sma_reference.py` produce dos intenciones y paridad con recuperación en cada paso. Código/guía del evaluador viven en esa rama; no están incluidos en la PR/CI de dev.3. No modifica HTTP, UI, esquema 5 ni identificación de aplicación dev.3; la integración y simulación económica quedan pendientes.

ATLAS se detuvo cooperativamente antes de editar. Copia previa `backups/atlas-20260911T081309290792Z-36ef7a06`. Ensayo/monitor de 48 horas, movimientos personales, gasto API, bróker, móvil/remoto y LaTeX siguen aplazados. Estado final de arranque/base y publicación se registra al terminar.

## Antecedente · rama subida para instalar en el portátil

Autorización posterior: «sube la rama y dime pasos para instalar el software en mi portátil». **`codex/v0.5-comparador` subida y verificada en GitHub sobre `5482e3f19302bd871be700c1ad5abb97cbb4f369`**, con seguimiento `origin/codex/v0.5-comparador`. Se añade la [guía actual del portátil](instalacion_portatil.md) en un commit documental posterior de la misma rama. Código sin cambios; no se ha abierto PR, lanzado CI, fusionado ni etiquetado dev.3. El workflow no se dispara con este push de rama. No se ha instalado nada en el portátil ni transferido su base; las comprobaciones siguientes pertenecen al sobremesa. Para obtener dev.3 clonar esta rama, no `master`.

## Cinco tareas posteriores · v0.5.0-dev.3 local

«Vale, haz esas 5 cosas» autoriza caso guiado de planificación, fichas/comparador de activos, correlaciones, evaluar el cierre v0.5 y concretar la primera estrategia v0.6. Rama **`codex/v0.5-comparador`**, desde `524feac`, identificación `0.5.0-dev.3`, esquema 5. Copia previa `backups/atlas-20260911T063013799897Z-4089e6f6`. La publicación vigente continúa siendo dev.2/PR #11; no se ha ejecutado CI ni publicado/fusionado/etiquetado dev.3.

Implementados módulos `asset_analysis*` y panel en **Datos → Fichas y comparador de activos**. Una a doce fuentes con identidad/versión, bruto EUR y FX de la misma fecha, volatilidad muestral, drawdown, base 100 y Pearson con intervalos idénticos y mínimo 20 observaciones. Sin completar huecos ni tratar cifras ausentes como cero. Política `atlas-asset-analysis-v1`; precios brutos excluyen dividendos/costes. Informe inmutable, contexto coherente, límite compartido de cálculos, auditoría atómica e idempotencia; no escribe el libro ni activa objetivos. [Uso, reglas y evidencia](v0_5_comparador.md).

Validación: **808 Python + 91 subcasos**, **294 frontend**, ocho Node, contratos/tipos/lint/build correctos. E2E completo `e2e-fb3c520ba00b4cf489147f1c2b7c799a`, **20/20** en 1,4 min, integridad, base habitual y limpieza correctas. Carga `v05-asset-analysis-load-b1e8b6b3659e424cb1276f907594327b`: 10 fuentes, 100.000 precios, 10.000 FX y 10.000 movimientos; 3.660 sesiones, máximo 1,063 s, 136,22 MiB adicionales, controles por servicios p95 0,00197 s. No prueba nueva de escalado físico ni ensayo prolongado. Revisión ordinaria detecta dos fuentes NVD con etiquetas iguales: se distinguen por ID breve y se añade una regresión; recorrido específico repetido sobre el ajuste final, registrado en la guía.

[Caso guiado](v0_5_ejemplo_guiado.md) comprobado en base aislada: patrimonio 986,10 EUR, aportación hipotética 250 USD, compra simulada 0,6 unidades, comisión 1 USD, efectivo final 781 USD y patrimonio 1.222,65 EUR; libro intacto al guardar el informe. [Matriz de cierre v0.5](v0_5_cierre.md): candidata al cierre del alcance analítico inicial, **aceptación del usuario pendiente**. Se le ha presentado el caso y consultado sobre límites: costes simples, referencia por CSV y ausencia de OMS/reservas. No atribuir aceptación manual por las pruebas del agente.

[Primer alcance v0.6](v0_6_alcance_inicial.md) definido, sin implementar. SMA 20/50 propuesta provisional: 50 cierres de calentamiento, primera detección de cruce con 51, objetivo largo/efectivo por presupuesto, siguiente apertura y paridad replay/incremental. Se ha consultado SMA frente a McClellan; sin respuesta, no afirmar que haya elegido. McClellan mantiene sus datos de amplitud pendientes. Nueva autorización antes de implementar DSL/evaluador.

Operación: copia comparada antes de arrancar, todos los registros iguales. Primer run `33c16ce17b5346f1b824d2f4d71c0700`, salud dev.3, tres carteras/libros/respuestas EUR y todas las tablas históricas intactas, parada global activa y gasto/reserva cero. Parada cooperativa antes del ajuste final de etiquetas. Verificación final de arranque en la guía. Solo cambian metadatos operativos del feed: **Yahoo devuelve para el 10/09 una fila parcial sin cierre**, que ATLAS rechaza; ambos NVD permanecen en v2 hasta el 09/09. Esto no invalida la descarga correcta del día anterior ni acredita disponibilidad actual. No se rellena ni se elimina una fila parcial para continuar.

Ensayo/monitor de 48 horas, movimientos personales, gasto en API, bróker, móvil/remoto y LaTeX siguen aplazados. No se ha sembrado el caso nuevo en la base habitual. Inicio `Abrir-ATLAS.cmd`; parada `Detener-ATLAS.cmd`.

**Arranque final verificado:** run `a613d9c6f25e4a2ead2b4d0ea0c47063`, motor e interfaz conectados en dev.3, manifiesto correcto y tres carteras/libros intactos. Evidencia `output/validation/v05-comparator-ordinary-online.json`. Etiquetas de fuentes homónimas comprobadas en navegador; E2E final específico `e2e-c0a5b47cbf9742c197e53b2c9909b215` 1/1. ATLAS queda abierto en Datos con el comparador disponible. Trabajo conservado localmente; publicación/CI nuevas pendientes de decisión.

## Diez tareas autorizadas · ampliación v0.5.0-dev.2

**Entrega publicada:** PR #11 fusionada en `bde915bb775572eaaf18b2ef360df6dc8023ab39`, árbol idéntico al de `d139701`; etiqueta anotada `v0.5.0-dev.2` publicada y verificada, objeto `28e29be0dc86ae68022532534a292dfbc2f27042`. Carpeta habitual actualizada a `master`, build canónico con manifiesto. Run final `1288342934d740faa0bf40e892c8fa64`, versión `0.5.0-dev.2`, esquema 5/integridad correctos. Tres carteras/libros/respuestas EUR intactos, versiones históricas conservadas y únicamente las dos actualizaciones Yahoo descritas abajo. Parada previa de `d94de1b2fe5f4dff993a9179fd6e3d86`: ambos procesos código 0, sin forzar. Parada global activa y gasto/reserva cero; sin movimientos ni análisis ficticios añadidos. Evidencia final `output/validation/v05-expanded-yahoo-ordinary.json`. Inicio `Abrir-ATLAS.cmd`, parada `Detener-ATLAS.cmd`. Las diez tareas quedan atendidas en el alcance analítico acordado; toda v0.5 conserva los pendientes de su guía. Documentación de publicación posterior a la etiqueta; código sin cambios.

**CI final correcta:** [34525527095](https://github.com/Buzo500/atlas-quant/actions/runs/34525527095) sobre `e6f462568ee02614e756809e7fa2971fdfeb1caf`: 783 Python + 91 subcasos, 287 frontend, ocho Node, tipos/lint/contratos/build, 19/19 E2E en 4,0 min y arranque/parada correctos. Recorrido ampliado 38,5 s sin reintentos; entorno remoto `e2e-3bdfd91935c747618d3a7379ff4d394d`, integridad/base ordinaria/limpieza correctas. Las ejecuciones fallida/cancelada descritas debajo son antecedentes. [PR #11](https://github.com/Buzo500/atlas-quant/pull/11) fusionada y etiqueta `v0.5.0-dev.2` publicada. Este cierre documental posterior a CI solo cambia Markdown.

**Coste final:** 0 USD facturables, 310/2.000 minutos incluidos y 0/0,5 GB; consumo bruto 1,86 USD cubierto íntegramente por descuentos. Presupuesto Actions 0 USD con bloqueo conservado.

«Vale, pues a por las 10» autoriza revisión/publicación de dev.1, comprobación Yahoo, reglas y simulador de aportaciones, rebalanceo, agregación de estrategias, benchmark, escenarios y validación/publicación del bloque ampliado. Registro, reglas y límites en [v0_5_planificacion.md](v0_5_planificacion.md). No reactiva ensayo de 48 horas, movimientos personales, IA de pago ni bróker.

PR #10 fusionada por squash `e23f79fe390942abbb8366173aa11d840e55df30`; etiqueta anotada `v0.5.0-dev.1` publicada y árbol igual al de la PR con CI 34517010948 correcta. Revisión del agente en navegador: edición/previsualización sin guardar registros en la base habitual; no se atribuye aceptación manual al usuario.

Rama de implementación `codex/v0.5-planificacion`, identificada `0.5.0-dev.2`, esquema 5; integrada ahora en `master`. Copia previa `backups/atlas-20260910T191907486422Z-568bddf8`; ATLAS habitual detenido antes de editar. Nuevos módulos `planning*`: propuestas analíticas con lotes/costes, recursos nativos compartidos, presupuestos de objetivos, referencia total-return EUR por CSV y escenarios precio/FX. Reutilizan valoración/TWR/riesgo; informes con revisión y auditoría atómicas, sin escribir libro ni activar objetivos. Validación y publicación de esta ampliación cerradas; no confundir la CI de dev.1 con estas fuentes.

**Validación del bloque ampliado:** 783 Python + 91 subcasos, 287 frontend, ocho Node, contratos/tipos/lint/build correctos. Carga final 100.000 precios/10.000 movimientos: 0,575 s y 119,36 MiB adicionales; controles p95 0,0062 s por servicios. Recuperación exacta de los cuatro informes probada. Recorrido local completo `e2e-0acdf99b2f18441289070a08eed95f38`: 19/19, integridad, base ordinaria y limpieza correctas. CI 34523170223 cancelada para corregir un redondeo de comisiones con lotes pequeños; dos regresiones numéricas reproducen el exceso anterior y verifican la búsqueda acotada del mayor lote asequible. CI 34523956547 pasa motor/interfaz pero agota los 45 s totales del recorrido ampliado (18/19 E2E); solo ese recorrido dispone ahora de 120 s, manteniendo acciones/comprobaciones de 10 s y cero reintentos. La CI final correcta indicada al inicio sustituye esos intentos. Cuota previa 291,7/2.000 minutos, 0 USD facturables, presupuesto Actions 0 USD con bloqueo.

**Operación local posterior:** run `d94de1b2fe5f4dff993a9179fd6e3d86`, salud `0.5.0-dev.2`, esquema 5/integridad correctos, parada global activa y gasto/reserva cero. La parada previa de `67c1787e8792493fab7537a30d29f057` termina sin forzar y con ambos procesos código 0. Panel visible y conectado; la demo nativa continúa sin objetivos activos ni valoración válida, por lo que los cálculos nuevos quedan correctamente deshabilitados. No se siembra la base habitual para mostrar resultados. Informe posterior `output/validation/v05-expanded-yahoo-ordinary.json`.

Yahoo: **descarga real validada** el 10/09 a las 19:55:01 UTC mediante el adaptador habitual y TLS verificado. Los dos históricos NVD.DE avanzan v1→v2, 427→428 y 1.193→1.194 barras, añadiendo únicamente 09/09/2026; versiones y barras antiguas exactamente conservadas. Tres carteras/libros/respuestas EUR iguales a la copia previa, sin movimientos ni análisis ficticios añadidos. Evidencia `output/validation/v05-expanded-yahoo-ordinary.json`; identificadores, huellas y límites en la guía. La sonda directa anterior recibió 429 a las 19:27:27 UTC (`var/validation/yahoo-v05-expanded-6f178e5bee374334b987e37fd72bfce9/probe.json`); ese resultado no describe la descarga posterior. No se desactivó TLS ni se sustituyó el proveedor. No garantiza disponibilidad futura.

## Cierre anterior de las cinco tareas · v0.5.0-dev.1

El usuario autoriza «Vale, haz esas 5 tareas»: corregir transporte API, comprobar actualización Yahoo, revisar recorrido EUR/USD, aceptar el alcance inicial y **implementar objetivos/bandas/desviaciones v0.5**. Rama `codex/v0.5-objetivos`, desde `c7b22bf`. ATLAS detenido antes de editar; copia previa esquema 5 `backups/atlas-20260910T175658520867Z-0c63eb33`. Esta autorización sustituye las restricciones históricas de «v0.5 solo definida» que aparecen más abajo. No reactiva ensayo, monitor, movimientos personales ni bróker.

**Implementado localmente:** objetivos manuales/bandas/límites, versiones y activación revisadas, diagnóstico sobre cortes D6 guardados, agregado por instrumento/efectivo y derechos identificados; informes inmutables con vigencia, sin propuestas de operaciones. [Guía](v0_5_objetivos.md). Esquema 5 conservado. 739 Python + 91 subcasos, 283 frontend, ocho pruebas Node, tipos/lint/contratos/build correctos. Carga 200 objetivos sobre 100.000 barras/10.000 movimientos: 0,210 s y 3,19 MiB adicionales, controles ASGI p95 0,0043 s. Restauración de objetivos/diagnóstico exacta.

**Transporte corregido y validado localmente:** proxy Node con agente propio por petición, mantener upstream hasta consumir el cuerpo, cancelar y destruir al finalizar; sin reuso entre peticiones ni reenvío. Con `agent:false` se reprodujeron respuestas incompletas; no reintroducir cierre prematuro. Se conserva Proactor original. [Evidencia, hipótesis descartadas y límites](diagnostico_api_20260910.md). 19/19 E2E completos (`e2e-77fe4731a54d495d8249ed0b323f5189`), 727 respuestas API finalizadas máximo 134,674 ms, ninguna pendiente más de un segundo; integridad/base ordinaria/limpieza correctas. Recorrido CSV EUR/USD → patrimonio 986,10 EUR → periodo P&L 87,90 EUR → objetivos con desviaciones +23,56/−23,56 EUR, guardado/reapertura y anchos 390/1280/3440. Editor ampliado: `e2e-fe9b6e29f6e84d838c821dcb865be3f2`, 1/1. No equivale a escala física nueva o ensayo prolongado.

[PR #10](https://github.com/Buzo500/atlas-quant/pull/10) abierta sobre `1992eb5442dbed8e1abb33846901271114884e91`. [CI gratuita 34517010948](https://github.com/Buzo500/atlas-quant/actions/runs/34517010948) **correcta sobre ese commit**: instalación limpia, 739 Python + 91 subcasos, 283 frontend, ocho pruebas Node, contratos/tipos/lint/build, 19/19 E2E (3,2 min) y arranque/parada correctos. E2E remoto `e2e-770b95d971cc4cc9ba1d609635ab00af`, integridad/base ordinaria/limpieza correctas. PR lista para revisión; sin fusión ni etiqueta nueva. El cierre documental posterior solo cambia Markdown, no las fuentes validadas.

**Coste:** presupuesto Actions 0 USD con Stop usage Yes comprobado antes de ejecutar. Cuota previa 248,3/2.000 minutos; después 266,7/2.000, 0/0,5 GB y **0 USD facturables**. No hay ejecuciones automáticas por push ordinario ni se reactiva el ensayo.

**Operación habitual:** arranque, parada cooperativa (ambos procesos código 0) y nuevo arranque correctos. Run activo `f3bafd2d89e646eda41fe4193184aac2`, salud `0.5.0-dev.1`, esquema 5/integridad `ok`. Tres carteras y todos sus libros/respuestas EUR iguales a la copia previa; cero registros analíticos ficticios añadidos. Parada global activa, gasto/reserva cero y experimento previo completado. Interfaz conectada y panel nuevo visible en la demo nativa, sin objetivos activos ni corte de precios válido todavía. Evidencia `output/validation/v05-ordinary-online.json`. Inicio `Abrir-ATLAS.cmd`; parada `Detener-ATLAS.cmd`.

Yahoo: una consulta el 10/09 a las 18:01:53 UTC supera TLS y recibe HTTP 429, sin Retry-After. Evidencia `var/validation/yahoo-v05-1e562d3a12bf4c0c9edf7a663bc9eaba/probe.json`. No insistir ni desactivar certificados; actualización real todavía bloqueada externamente, precios habituales conservados.

## Cierre anterior: diez tareas completadas · v0.4.0-dev.6 publicada

D6 completo publicado en PR #8 / `v0.4.0-dev.5`; D7 y D8 publicados como desarrollo. PR #9 fusionada mediante squash `53cca20654c6c8a9bfc665e2b22f219f3ea85607`, etiqueta anotada `v0.4.0-dev.6` (objeto remoto `3ec9d901829afbcb284c6fe1ff34996d31d81086`). CI gratuita [34509155203](https://github.com/Buzo500/atlas-quant/actions/runs/34509155203) correcta sobre `211ca49f4427e2730dc326178fce7b845c9d2ca1`; árbol integrado idéntico. **709 Python + 91 subcasos, 278 frontend y 19/19 E2E**, instalación limpia, build, tipos, contratos, lint, arranque/proxy y parada correctos. E2E remoto `e2e-d99b1e9a5e4e4903bc7b1cc65e38cc3c`, 3,1 min; integridad/base ordinaria/limpieza correctas. Primer intento fallido y corrección por auditoría conservados más abajo. No se ha declarado estable.

Los diez puntos de [ejecución](ejecucion_diez_tareas_v0_4.md) están atendidos: D6.1–D6.6, diagnóstico, D7 especificado/implementado, D8 validado/publicado y primer alcance v0.5 definido. **v0.5 no está implementada ni autorizada todavía**; leer [alcance inicial](v0_5_alcance_inicial.md). Las incidencias de transporte/API y descarga Yahoo 429 siguen abiertas: continuar su diagnóstico no equivale a resolverlas.

**Coste:** antes de la segunda CI 231,7/2.000 minutos; después 248,3/2.000, 0/0,5 GB y 0 USD facturables. Presupuesto Actions 0 USD con Stop usage Yes. Sin nuevas ejecuciones por fusión o etiqueta de desarrollo; sin llamadas pagadas.

**Estado del sobremesa:** `master` actualizado a la entrega integrada, ATLAS compilado y arrancado, run `776831839dc2420bab76d7abc2265c5a`, salud `0.4.0-dev.6`, esquema 5, integridad `ok`. Tres carteras y libros/respuestas EUR idénticos a la copia previa; precios y resultados históricos conservados. Parada global activa, gasto/reserva cero, experimento previo completado. No se han importado movimientos personales ni datos USD en las carteras habituales. Evidencia `output/validation/d8-ordinary-online.json`. Compilación regenerada después del cambio a master con manifiesto verificado. Inicio `Abrir-ATLAS.cmd`; parada `Detener-ATLAS.cmd`.

**Operación:** copia previa de estas tareas `backups/atlas-20260910T152641167910Z-d35a888b` (esquema 5). Volver a D5 exige copia de esquema 4 y fuentes/build D5; copia `backups/atlas-20260910T142414461441Z-bc5cf98f`. Ensayo de 48 horas, monitor y movimientos personales siguen aplazados. No se inicia bróker, aprendizaje, móvil, remoto o LaTeX.

## Antecedente: ejecución de las diez tareas y cierre remoto

**Cierre D7/D8 en revisión tras primer intento remoto:** PR #9 abierta. CI 34506888529 sobre `78996cd` falla en E2E 17/19: `ECONNRESET` en D3 y confirmación D7 desaparecida; resto de fases previo a E2E correcto. Corregido localmente el remontaje por auditoría y las claves duplicadas de los paneles NAV/rentabilidad, con cuatro regresiones adicionales (278 frontend). Nuevas pruebas y CI condicionan la publicación; no fusionar el intento fallido. [Registro D8](v0_4_d8.md).

Tras la corrección: 278 frontend, tipos/lint/build y 19/19 E2E completos con sondas (`e2e-08ce8cbf7a7244b08809830f5119639f`, 1,2 min); integridad/base habitual/limpieza correctas. Solo cambia frontend y documentación; cálculo Python de D7 conserva su validación 709 + 91 subcasos. Se prepara segunda CI completa.

Arranque habitual intermedio `bdf8fad2193b41d0b8e960742f08a187`: salud dev.6, esquema 5/integridad correctos, tres carteras y libros/respuestas EUR idénticos a la copia previa de estas diez tareas; parada global activa, gasto/reserva cero. Interfaz conectada; demo D5 sin cotizaciones muestra NAV/rentabilidad no disponibles con causa explícita, costes conocidos 10 EUR. No se guardaron previews. Detenido de nuevo antes de corregir el código; evidencia `output/validation/d8-ordinary-online.json`.

El usuario ha autorizado «Vale, haz las 10», referidas a las dos listas consecutivas: [registro y orden de las diez tareas](ejecucion_diez_tareas_v0_4.md). Mantener este trabajo activo hasta completarlo; proponer siguientes pasos no sustituye esta autorización. Ensayo de 48 horas, movimientos personales, bróker, entrenamiento y servicios pagados siguen excluidos. No implementar v0.5: solo concretar su primer alcance.

**D6 publicado:** PR #8 fusionada mediante squash `a308f81d31212a6d03af37076fa152109b6d83c6`; etiqueta anotada `v0.4.0-dev.5`, objeto remoto `5a294a018b77ed61f6803f9b0df7bc09ea6fd435`. CI completa [34503177151](https://github.com/Buzo500/atlas-quant/actions/runs/34503177151) correcta sobre `a3561126fbda290524a1d742aef7ad470ee78bda`, árbol integrado idéntico. Cuota antes de lanzar: 198,3/2.000 minutos, 0 USD facturables, presupuesto 0 con bloqueo. CI previa parcial 34496563421 correcta. [D6 completo](v0_4_d6_cierre.md): 677 Python + 91 subcasos, 270 frontend y 19 E2E; recuperación y carga correctas.

**D7/D8 local listos para publicar:** rama `codex/v0.4-d7-d8`, `0.4.0-dev.6`, esquema 5 sin nuevo cambio. P&L, flujos/costes EUR, TWR por tramos y MWR/XIRR por fechas, restricciones de unicidad/dominio y calidad explícitas, UI e informes inmutables. Reutiliza el reductor del libro como cursor incremental. Máximo dos cálculos pesados; 503 sin bloquear controles. [D7](v0_4_d7.md), [D8](v0_4_d8.md). **709 Python + 91 subcasos, 274 frontend, 19/19 E2E**, tipos/lint/contratos/build correctos; `e2e-bed8fa18496a433383b025b279e501d5`, base habitual intacta, integridad y limpieza correctas. Capturas 390/1280/3440 revisadas en el recorrido D7 anterior, sin escala física nueva.

**Carga D8:** 100.000 barras, 10.000 movimientos, informe de 3.660 días: máximo NAV 0,724 s / informe 1,486 s; pico Python 142,62 / 148,15 MiB; 20 controles HTTP ASGI p95 0,3721 s (excluye Node/navegador). Recuperación exacta de NAV e informe. Informe `d8-delivery-1827e2e35e824ab6ac83a01ab5a44b90/report.json`. Migración 4→5 bajo código D7: `d6-migration-1242d205f0b74a0280050e407943ca7b/report.json`, tablas/respuestas EUR y copia fuente intactas.

**Punto 10 definido, sin implementar:** [primer alcance v0.5](v0_5_alcance_inicial.md), objetivos manuales, bandas y diagnóstico de desviaciones. No hay autorización para iniciar su código. Las diez tareas requieren aún publicar D7/D8 tras CI gratuita y registrar cierre operativo; continuar con ello sin pedir que se reautorice.

Diagnóstico API: el primer E2E `e2e-6df81e53a5f148e1a1ba9a1f36166d5b` reprodujo la espera real de 10 s en GET `/api/state`. Correlación `proxy-38548-52`: creación/envío de cabeceras upstream inmediato, `bodySent` a 10008,9 ms, aborto cliente a 10015 ms, `UND_ERR_SOCKET`; no entrada ASGI para esa correlación. Ocurre al reutilizar la conexión después de POST demo completado. Esto acota el fallo al envío/transporte previo al backend, **no identifica aún la causa ni la declara resuelta**. La siguiente suite pasó; otro error de socket a ~5 s está asociado a cancelación previa. Sonda ampliada con cabeceras de encuadre exclusivamente (sin credenciales/cuerpo), cork y cola del socket.

Yahoo: una única sonda posterior con bundle de certificados públicos de certifi y almacenes Windows autorizados para SERVER_AUTH supera TLS y devuelve HTTP 429. No desactivar verificación ni insistir ante el límite; todavía no hay descarga real validada ni modificación de cotizaciones habituales. Bundle diagnóstico en output ignorado. ATLAS habitual permanece detenido desde el inicio de estas diez tareas. Copia previa esquema 5: `backups/atlas-20260910T152641167910Z-d35a888b`.

## Antecedente: D6.1/D6.2 local y diagnósticos · cinco tareas

**Autorización posterior:** «a por las 5 tareas más»: diagnosticar Yahoo, dirigir la captura API al cuerpo/cancelación, publicar el plan anterior, implementar D6.1 y D6.2. Plan documental `8f33625` publicado mediante avance directo de `master`; el workflow no se activa por push ordinario y no se ha lanzado CI remota. Desarrollo local en `codex/v0.4-d6`, **`0.4.0-dev.5`, esquema 5**, sin publicación del código ni etiqueta nuevas. [Contratos, uso y límites de esta implementación](v0_4_d6_implementacion.md).

**Libro nativo EUR/USD por API `/api/v2`:** balances/posiciones/realizado con moneda explícita, conversiones de dos piernas y comisión atómicas, conciliación completa por moneda, correcciones con dependencias y dividendos/splits USD. Reutiliza servicios y transacciones D4/D5. API antigua conserva EUR y rechaza cortes/documentos con USD; `legacy-eur-v1` no cambia. Interfaz multidivisa D6.5, series/precios USD D6.3 y NAV D6.4 todavía pendientes. No se habilitan backtests/paper USD.

**Validación local:** 650 Python + 91 subtests, 266 frontend, tipos/lint, contratos regenerados y comprobados, build con manifiesto correctos. Suite final `d6-python-final.log`: 67,18 s, dos avisos de deprecación previos. Incluye regresión del documento con saldo EUR y fila USD en el extracto: API antigua devuelve 422 explícito. Referencias aritméticas 15/15 y 59 resultados exactos; no acreditan NAV futuro. Migración 4→5 sobre copia aislada, tablas/históricos y saldos EUR exactos, tablas nuevas vacías, reapertura y recuperación correctas: `var/validation/d6-migration-a7cd99985eed4a4e9f4703c67026dca5/report.json`. Navegador: **18/18 E2E** en 1,1 min, `e2e-aa269c16968c47c2b37c78e23289edff`, integridad correcta, base habitual intacta y puertos liberados. Sonda final: 3/3 D5 en 16,3 s (`e2e-268f9c4f9e6d4e779a24fd1a1ee53252`). No supone nueva aceptación visual física del escalado.

**Estado final:** ATLAS habitual arrancado y comprobado, run `f7ff0e7472b04d72af70e9721692613c`, interfaz compilada en `http://127.0.0.1:3000/`, salud `0.4.0-dev.5`, base migrada a esquema 5 e integridad `ok`. Tres carteras conservadas (dos legacy revisión 2, demo D5 revisión 5); tablas históricas, libros/contextos y respuestas EUR idénticos a la copia de esquema 4. Parada global activa; gasto/reserva IA cero. No se importó USD en estas carteras; la validación multidivisa usa fixtures aisladas. Evidencia `output/validation/d6-ordinary-start.json`.

**Operación:** se detuvo ATLAS antes de editar. Copia previa de esquema 4 `backups/atlas-20260910T142414461441Z-bc5cf98f`. D5 no abre esquema 5: retroceso con esta copia y fuentes/build `v0.4.0-dev.4`. No se importan movimientos personales ni nuevas operaciones de demostración en la base habitual durante este trabajo.

**Yahoo:** reproducida caché AppData inaccesible; corregida su ubicación a la carpeta de datos ATLAS y comprobada su apertura. La descarga real todavía falla por cadena TLS; una sonda separada con certificados de confianza del sistema obtuvo HTTP 429. No se deshabilita verificación ni se insiste tras el límite; precios anteriores conservados. El fallo de caché está corregido, la actualización diaria aún no validada. **API:** se amplía sonda optativa de cuerpo/aborto sobre bases E2E aisladas; la espera original sigue abierta. [Diagnóstico](diagnostico_api_20260910.md).

D6.3–D6.6, D7/D8, importaciones personales, monitor y ensayo de 48 horas siguen pendientes. Proponerlos no autoriza ejecutarlos. Inicio `Abrir-ATLAS.cmd`, parada `Detener-ATLAS.cmd`.

## Antecedente: diagnóstico, uso normal D5 y plan D6 · puntos 1–4

**Último alcance autorizado:** diagnosticar la API, comprobar D5 en la instalación habitual con demostración, concretar D6 y preparar referencias independientes. El usuario limita expresamente a «hasta el 4 incluido»: **no implementar D6**. Trabajo local en `codex/v0.4-d6-plan`, desde `a93bf8d` de `master`, sin nueva CI remota, subida, PR, fusión o etiqueta. La aplicación sigue en D5 publicado `0.4.0-dev.4`.

**[Diagnóstico API del 10/09](diagnostico_api_20260910.md):** 18/18 E2E con trazas, 1,1 min, `e2e-2df628fc57124fa1a4b6a9f8d09f92a7`, integridad `ok`, base habitual intacta y puertos liberados al cerrar el harness. ASGI completo máximo 127,273 ms; `/api/state` en proxy máximo 134,168 ms. Se correlacionan dos `UND_ERR_SOCKET` de ~5 s con lecturas cuyo cliente ya había cerrado en ~65/71 ms y ASGI terminó en ~68/87 ms; otros dos cierres de stream duran ~10 ms. **No reproduce ni resuelve la espera original de 10 s**; no se cambian aplicación, dependencias o tiempos. Incidencia abierta con siguiente captura dirigida documentada.

**[D5 habitual comprobado](comprobacion_d5_20260910.md):** ATLAS encendido en modo compilado, run `2c84f4b6c35c418dbb47905bead929ec`, base migrada **3→4** e integridad `ok`. Copia previa `backups/atlas-20260910T134952170690Z-55207169`; copia automática de arranque conservada. Dos carteras anteriores, libros, versiones de precios, vínculos y experimento preservados. El worker intentó refrescar Yahoo: ambas fuentes devolvieron `OperationalError`, cambiando solo `feed.last_attempt/error`; no actualizó cotizaciones. NVIDIA continúa hasta 08/09. Es una incidencia separada por diagnosticar, no una actualización diaria validada.

Demo nueva **«Demostración D5 · dividendos y split»**, cartera `72a9e51058004702a0ba44f352267aa7`, revisión 5, activo ficticio independiente. API ordinaria con previsualización/confirmación y revisión en navegador: depósito 10.000, compra 100 títulos por 100 EUR, derecho 50, cobro neto 40, split 2:1 → efectivo **9.940 EUR**, **200 títulos**, coste **100 EUR**, derecho cero. Corte 15/01: efectivo 9.900 y derecho 50. Sin precios vinculados, advertencia de base posterior sin acreditar correcta; no NAV nuevo. Datos de ejemplo explícitos, sin evidencia inventada para NVIDIA. Parada global activa, proveedores sin configurar, gasto/reserva cero y experimento anterior completado; sin nuevas investigaciones, importación personal, monitor o ensayo.

**[D6 especificado](v0_4_d6.md):** D6.1–D6.6 cubren contratos/migración, saldos/conversiones, CSV de precios USD y FX, NAV por corte, interfaz y validación. Comisiones explícitas, exposición por moneda, derecho/cobro USD con límites D5, temporalidad/calendarios, cortes inmutables y suma antes de redondear. TWR/XIRR siguen en D7; no se habilitan backtests/paper USD. [Referencias](fixtures/v0_4_d6_referencias.json): **15/15 casos aritméticos, 59 resultados exactos**, comprobador independiente `docs/fixtures/check_v0_4_d6.py`; **16 escenarios semánticos especificados**, sin pruebas contra un motor D6 que aún no existe. No cambio de versión, contratos físicos, esquema de aplicación ni build en este trabajo documental.

Inicio habitual `Abrir-ATLAS.cmd`; parada `Detener-ATLAS.cmd`. El estado «detenido/sin migrar» de los antecedentes inferiores es histórico. Volver a D4 exige copia de esquema 3 y fuentes/build compatibles. Próximas decisiones: incidencia de Yahoo/API, publicación del plan e inicio de D6.1; proponerlas no las autoriza. D7–D8, movimientos personales y ensayo de 48 horas siguen pendientes.

## Antecedente: D5 publicado · cinco pasos de cierre completados

**[PR #7](https://github.com/Buzo500/atlas-quant/pull/7) fusionada** mediante squash en `a91f077648f209e49dfba2c630fd2c6ccecfd1a0`. **[Etiqueta anotada `v0.4.0-dev.4`](https://github.com/Buzo500/atlas-quant/tree/v0.4.0-dev.4) publicada y verificada en remoto**, objeto `2161b14e3ddf088608c3e0688b65f14974c8fa20`. El árbol integrado coincide exactamente con la cabeza validada `5c3e8a7453418d2f5b7f6eb3feddefa44c28db92`. Copia local actualizada a `master`; el registro de cierre se publica después de la etiqueta mediante un cambio exclusivamente documental.

**[CI gratuita 34479828915](https://github.com/Buzo500/atlas-quant/actions/runs/34479828915) correcta**, job `102879544233`: **623 Python + 91 subtests** (48,60 s, dos avisos de deprecación previos), **266 frontend/28 archivos** (87,96 s) y **18/18 E2E** (2,5 min). Instalación limpia, compilación con manifiesto, TypeScript, contratos, lint, arranque/proxy y parada correctos. E2E `e2e-56ba51cbda5348e58f2e272337f72fa7`: integridad `ok`, base ordinaria del runner intacta y puertos liberados. El recorrido sintético del proxy devuelve salud `0.4.0-dev.4` y gasto IA cero. Evidencia local `output/validation/d5-ci-34479828915.log`.

Corrección de previsualización publicada: el formulario espera identidad/revisión coincidentes entre cartera y derechos antes de inicializarse. Las tres regresiones permanentes cubren ambos órdenes de respuesta y cambios de cartera sin aviso global; comprueban conservación del borrador y envío único con campos vigentes. Pasan también las ocho pruebas anteriores del panel. Revisión sin bloqueantes identificados; no había revisiones ni conversaciones de revisión pendientes en la PR. Los tres intentos remotos fallidos se conservan debajo. **La incidencia separada de latencia/502 de API sigue abierta**; esta CI correcta no demuestra su eliminación.

**Coste verificado:** antes 166,7/2.000 minutos; después 183,3/2.000 minutos, 0/0,5 GB y **0 USD facturables**. Presupuesto Actions 0 USD y Stop usage Yes comprobados antes de ejecutar; no se modificaron los controles. No se lanza otra CI por la fusión o la etiqueta de desarrollo.

**Operación y alcance:** ATLAS habitual continúa detenido, sin migrar su base ni importar movimientos personales. Copia pre-D5 de esquema 3 `backups/atlas-20260910T091254560815Z-782be607` conservada. El primer arranque D5 realizará la migración 3→4 ya validada en copias; volver a D4 exige copia compatible y fuentes/build D4. Inicio `Abrir-ATLAS.cmd`, parada `Detener-ATLAS.cmd`. D5 EUR publicado; el uso de USD, la valoración del libro exacto y su rentabilidad siguen pendientes de D6/D7. D6–D8, movimientos personales y ensayo de 48 horas no se inician. Se mantiene la condición de desarrollo y v0.2 candidata, sin declaración de estabilidad.

## Antecedente: D5 implementado · cierre de validación

El usuario acepta los cinco pasos D5.1–D5.5 y sus límites: contratos/eventos, dividendos, splits, interfaz/correcciones y validación/publicación de desarrollo tras CI gratuita. Rama `codex/v0.4-d5`, versión **`0.4.0-dev.4`**, esquema **4**; parte de D4 publicado y del plan documental `e59caf4`. [Uso, contratos físicos y límites](v0_4_d5.md). D6–D8 no iniciados.

Implementados eventos revisionados compartidos, derechos/cobros EUR separados, enlace sin doble abono, splits/reverse splits exactos y correcciones dependientes con confirmación atómica. El libro anterior `legacy-eur-v1` se conserva. Libro v2 sin NAV/TWR/XIRR todavía; EUR operativo, USD solo en catálogo. Conciliar una cartera no cambia restricciones de calidad globales. Sin evidencia inventada para NVIDIA, importación personal, nuevas claves o llamadas de pago.

**Cierre reanudado por autorización del usuario:** se añaden las pruebas permanentes de la corrección de previsualización, se revisan/suben los cambios y se ejecutará la CI gratuita; fusión de PR #7 y etiqueta `v0.4.0-dev.4` condicionadas al resultado correcto. `corporate-panel-refresh.test.tsx` cubre tres órdenes de actualización, el borrador durante/después del refresco y una única previsualización con fuente, cuenta y cantidad vigentes. Pasan las tres regresiones y ocho pruebas existentes, tipos y lint (`output/validation/d5-regression.log`). Cuota comprobada antes de preparar esta CI: 166,7/2.000 minutos, 0/0,5 GB y 0 USD facturables; presupuesto Actions 0 USD y Stop usage Yes. Los intentos anteriores y la corrección local se conservan abajo como historial. D6–D8, importación personal y ensayo siguen pendientes.

**Pruebas locales del sobremesa:** 623 Python + 91 subtests (60,29 s, dos avisos previos), 263 frontend/27 archivos (21,55 s), contratos, tipos, lint, dependencias y compilación con manifiesto correctos. **17/17 E2E completos** en 1,1 min (`e2e-57ae1577e6074637b345f34f04aed1c1`); tras ampliar al ancho completo los paneles contables, **4/4 recorridos afectados** repetidos en 20,4 s. Viewports CSS 3440/1280/390, integridad `ok`, base habitual intacta y procesos cerrados. Revisión visual de los paneles realizada. Publicación remota pendiente en este registro. Evidencia `output/validation/d5-python-full.log`, `d5-frontend-full.log`, `d5-build-final.log`, `d5-e2e-release.log`, `d5-e2e-layout.log`.

**Migración/recuperación:** copia pre-D5 `backups/atlas-20260910T091254560815Z-782be607`, esquema 3. `check_d5_migration.py` valida sobre copias aisladas: historial, ambas carteras, libros, vínculos y valoraciones conservados, cinco tablas nuevas vacías, reapertura idempotente e integridad `ok`. Informe `var/validation/d5-migration-61460f9c6c17493386af3c95f3e54bff/report.json`. Restaurar pausa las fuentes y activa la parada; no borra sus datos. La base habitual no se ha migrado ni se han usado movimientos personales como fixtures. No abrir esquema 4 con D4; recuperar copia y fuentes/build `v0.4.0-dev.3`.

**Operación:** ATLAS estaba detenido antes de editar. Los ensayos usan una base nueva aislada y paran sus procesos al acabar. El arranque ordinario realizará la migración ya comprobada en copia; abrir con `Abrir-ATLAS.cmd`, parar con `Detener-ATLAS.cmd`. El ensayo de 48 horas y su monitor siguen aplazados; no se declara v0.2 ni v0.4 estable.

**Intentos conservados:** dos E2E D5 iniciales correctos (`e2e-a138cc4a4cf3440d80df9d3d648122aa`). La primera suite conjunta conservó 14 recorridos previos correctos y falló en un supuesto del nuevo fixture: exigía un único conjunto tras las pruebas D2/D3. Se corrigió el fixture. El siguiente intento (`e2e-e4e76e996cb546dbad55b4c692b04707`) mostró el rechazo HTTP 409 correcto de la confirmación concurrente, pero el observador del test capturaba antes el 200 de previsualización; ahora identifica `commit=true`. En ese intento reapareció la espera intermitente de API: cuerpo de creación de cartera demoró ~9,9 s y la lectura de precios devolvió 502. Sigue abierta; no se ampliaron tiempos ni añadieron reintentos. El intento conjunto `e2e-acc5bc1b360e47dea360bed1510139c6` identificó otra carrera del fixture: leía el catálogo antes de terminar la confirmación; ahora espera su fila visible. Los tres recorridos D5 pasaron después (`e2e-39b01442214546edbff4408b47c2fb01`) antes de repetir la suite completa. No se atribuye a D5 una corrección de la incidencia de API ni una validación física nueva de escalado.

**Primer intento remoto D5:** [PR #7](https://github.com/Buzo500/atlas-quant/pull/7), head `465327d8319ab5bbd6bc6c1c5c9935fe9727f2b9`; [CI 34465823612](https://github.com/Buzo500/atlas-quant/actions/runs/34465823612), job `102834044383`. Pasan 623 Python + 91 subtests (57,01 s), 263 frontend (85,63 s), instalación/build, tipos, contratos y lint. E2E 16/17: los tres D5 correctos, pero el recorrido anterior de precios agota los 45 s globales mientras comprueba la ficha flotante. No se fusiona ni etiqueta ese resultado. Evidencia `output/validation/d5-ci-34465823612.log`; base ordinaria del runner intacta, integridad `ok`, puertos liberados.

Se separa el recorrido extenso en datos/agregación y adaptación visual, conservando todas sus verificaciones, cambios sucesivos de tamaño y límites (45 s por test, 10 s por comprobación, cero reintentos). Cada tamaño tiene un paso identificado. El primer intento local de esa separación (`e2e-03feb736d7a644938ab8da1caa539bc8`) detecta una omisión en su preparación: faltaba situar el deslizador al principio; corregida. También conserva otra aparición de la incidencia previa: `quality` 502 en 10,05 s, `prices` 200 en 10,05 s, controles tardíos en pantalla completa nativa. No se atribuye una corrección de API. Después pasan 5/5 recorridos afectados en 24,4 s (`e2e-91911ef5cfee4b949e36ea8450863be8`, `output/validation/d5-e2e-ci-fix2.log`). La suite pasa a 18 recorridos por la separación; su repetición completa y nueva CI condicionan el cierre.

**Validación tras el ajuste de E2E:** 18/18 recorridos completos en 1,1 min, `e2e-76ac4e298b984ecf8d3725d805908756`, evidencia `output/validation/d5-e2e-ci-ready.log`. Contratos de aplicación sin cambios; tipos, lint y build con manifiesto verificados. Integridad `ok`, base habitual intacta y procesos cerrados.

**Segundo intento remoto:** [CI 34467501259](https://github.com/Buzo500/atlas-quant/actions/runs/34467501259), head `02c53c77a02c88060243cb6c0b29ad04bc426f7c`, job `102839409924`. Pasan todas las fases previas a E2E y 17/18 recorridos en 1,7 min, incluidos ambos recorridos de precios separados. Falla un selector ambiguo del test D5 después de recargar y cambiar a Cartera: el saldo cero existe también en el panel Datos conservado en el DOM. Se acota al `tabpanel` Cartera y se comprueba antes el saldo recargado en Datos; sin cambiar el producto ni sus cálculos. Tres D5 locales pasan con el selector acotado (`e2e-d7a84c65a4b241b9888c0809fd06fcfe`, 16,2 s). Evidencia del intento remoto `output/validation/d5-ci-34467501259.log`; integridad `ok`, base habitual del runner intacta y puertos liberados. Publicación aún condicionada a CI completa correcta.

El recorrido final de dividendo comprueba ambos paneles tras recargar y pasa en 7,4 s (`e2e-1b95b42e3a3b4588aea62d092afc961f`, `output/validation/d5-e2e-ci-selector2.log`). Tipos/lint/build correctos. No se alteran timeouts, reintentos ni lógica del producto.

GitHub comprobado antes de preparar CI: 120/2.000 minutos, 0/0,5 GB, 0 USD facturables; presupuesto Actions 0 USD y Stop usage Yes. Tras el primer intento: 138,3/2.000 minutos; tras el segundo: 150/2.000 minutos, 0/0,5 GB y 0 USD facturables; bloqueo mantenido. Cierre remoto pendiente en este punto del registro.

**Tercer intento remoto y corrección local acotada:** [CI 34468459133](https://github.com/Buzo500/atlas-quant/actions/runs/34468459133), head `08fe4dffb9ed33170918b27bee73fb6c76c3fe79`, job `102842499767`. Pasan las fases previas y 17/18 E2E; el dividendo no muestra la segunda previsualización (efectivo esperado 9940,00 EUR) dentro de los 10 s. Evidencia `output/validation/d5-ci-34468459133.log`. No se fusiona ni etiqueta. La última instrucción del usuario limita el trabajo al **punto 1: diagnosticar y corregir localmente este fallo**; prueba permanente de regresión, nueva CI y publicación quedan pendientes de su elección.

Se reproduce de forma controlada una carrera compatible con ese fallo: la revisión nueva de la cartera remonta `CorporateApplicationForm` mientras `useRead` aún conserva los derechos anteriores. Los inicializadores de estado dejan fuente, cuenta y cantidad vacías aunque después lleguen los derechos nuevos; la validación HTML de campos obligatorios impide enviar la previsualización. `CorporatePanel` ahora espera identidad y revisión coincidentes antes de montar el formulario y vuelve a consultar los derechos cuando cambia la revisión de cartera. Refrescar la misma revisión conserva el borrador. Esto no atribuye una solución a la incidencia separada de latencia/502 de API; el log remoto por sí solo no permite demostrar el orden de sus respuestas.

**Verificación local de la corrección:** diagnóstico temporal con respuestas diferidas reproduce el fallo antes y pasa después en dos variantes, con/sin aviso global de actualización; comprueba campos, conservación del borrador y envío de previsualización. Ocho pruebas existentes del panel correctas, tipos/lint y build con manifiesto correctos. Un único E2E existente de dividendo pasa en 7,0 s (`e2e-98b070e8ea2e451a9a344dc37bbd5e9c`): derecho, cobro neto, corte, recarga e historial; integridad `ok`, base habitual intacta y puertos liberados. Evidencia `output/validation/d5-race-before.log`, `d5-race-after.log`, `d5-race-build.log`, `d5-race-e2e.log`; diagnóstico archivado fuera de la suite en `output/validation/d5-race-diagnostic.tsx`, sin test permanente añadido. Cambios locales sin commit/subida, sin nueva CI ni etiqueta. ATLAS habitual continúa detenido, base sin migrar; ensayo aplazado.

## Antecedente: D4 publicado y D5 especificado

El usuario autorizó los cinco pasos: revisar D4, subirlo/abrir PR, ejecutar CI gratuita, fusionar/etiquetar si pasa y concretar D5. **Completados**. [PR #6](https://github.com/Buzo500/atlas-quant/pull/6) fusionada mediante squash `39d922cf63a95c4f39fbe8f35e88047d86d2807f`; [etiqueta anotada `v0.4.0-dev.3`](https://github.com/Buzo500/atlas-quant/tree/v0.4.0-dev.3) verificada en remoto (objeto `98c362a171c273099fbdd5961b9908e22159bbae`). Árbol idéntico al head validado `aa7ad176b5d851ca093f05689386e2942d2bc935`. Revisión técnica sin bloqueantes identificados; no se atribuye al usuario una prueba manual nueva.

**[CI D4 34456773938](https://github.com/Buzo500/atlas-quant/actions/runs/34456773938) correcta al primer intento**, job `102804902070`: 570 Python + 91 subtests (42,42 s, dos avisos previos), 255 frontend y 14/14 E2E (1,9 min). Instalación limpia, build con manifiesto, tipos, contratos, lint, arranque/proxy y parada correctos. E2E `e2e-f6b76e352f3840ccae5fb33670d23eb1`: datos aislados, integridad `ok`, base ordinaria del runner intacta y puertos liberados. Evidencia `output/validation/d4-ci-34456773938.log`. Cuota/bloqueo comprobados antes: 105/2.000 minutos, 0/0,5 GB, 0 USD facturables y presupuesto Actions 0 USD con Stop usage Yes; después: 120/2.000 minutos, 0/0,5 GB y **0 USD facturables**. No se ejecutó otra CI al publicar la etiqueta de desarrollo.

**D5 especificado localmente**, [reglas y tareas D5.1–D5.5](v0_4_d5.md), [10 oráculos](fixtures/v0_4_d5_referencias.json) comprobados con Decimal/Fraction sin importar ATLAS ni abrir su base. Dividendos EUR con derechos/cobros separados, enlace sin doble abono, splits exactos y coste conservado, eventos revisionados y previsualizaciones atómicas. Primera propuesta: pago completo único, fracción conservada solo acreditada y exactamente representable; liquidaciones de fracciones y FX fuera del alcance inicial. Evidencia incompleta limita las capacidades, y conciliar una cartera no habilita investigación global. **No se implementó D5 ni se cambió el esquema/versionado de la aplicación.** Rama documental `codex/v0.4-d5-plan`, desde `origin/master` integrado; el código sigue siendo D4 publicado. Esta documentación de cierre y plan no forma parte de la etiqueta ya publicada; queda guardada localmente para revisión/publicación posterior.

**Estado operativo comprobado hoy:** `Status-Atlas.ps1` devuelve detenido, sin bloqueo, con la última ejecución registrada `312c4405e59040f1ad2669319ff5a26b`; puerto 3000 sin servicio. No se arrancó el programa ni se reconstruyó en este cierre documental. La evidencia de arranque del 09/09 siguiente es histórica. Inicio `Abrir-ATLAS.cmd`, parada `Detener-ATLAS.cmd`. Sin movimientos personales, claves nuevas, llamadas de pago ni ensayo/seguimiento reactivados. Esquema 3 y copia pre-D4 conservados; v0.2 sigue sin ser estable y la intermitencia histórica de API sigue abierta.

Próximo trabajo recomendado: revisar los límites D5 y autorizar D5.1 (contratos/identidad/migración con pruebas), antes de dividendos, splits, interfaz e integración. Proponerlo no autoriza ejecutarlo.

## Antecedente · 09/09/2026: cierre local D4

**Cierre local D4:** implementación guardada en `0eb5523`; ATLAS arrancado en modo compilado, ejecución `312c4405e59040f1ad2669319ff5a26b`. Motor/proxy responden `0.4.0-dev.3`; interfaz normal abierta con NVIDIA y «Libro y conciliación». Esquema 3, integridad `ok`; las diez tablas previas se conservan salvo la auditoría de arranque, y las tres nuevas están vacías. Demo: seis movimientos, tres posiciones y NAV 25.118,66876 EUR. «Cartera de pruebas»: revisión 2, cero movimientos y vínculo NVIDIA v1 intacto. Los tres conjuntos mantienen v1; proveedores sin configurar, presupuesto/gasto/reserva cero y parada global activa. Evidencia `output/validation/d4-normal-after.json`. Arranque habitual `Abrir-ATLAS.cmd`; parada `Detener-ATLAS.cmd`.

El usuario autoriza los cinco pasos: publicar D3 y arquitectura, ejecutar CI gratuita, fusionar/etiquetar si pasa, especificar D4 e implementarlo con pruebas. **D3 publicado** en [PR #5](https://github.com/Buzo500/atlas-quant/pull/5), squash `cdb59b1461d3d26ff88d6f7de90bdf4534ca5fe3`; etiqueta anotada `v0.4.0-dev.2` verificada en remoto. [CI 34376199945](https://github.com/Buzo500/atlas-quant/actions/runs/34376199945) correcta sobre `864097448b8200c8d9c8b0295598c84ba465fcf9`, árbol integrado idéntico: 523 Python + 91 subtests, 249 frontend y 13 E2E. Un único intento. Facturación posterior comprobada: 105/2.000 minutos, 0/0,5 GB, 0 USD facturables; presupuesto cero con bloqueo del uso de pago.

**D4 desarrollado localmente**, rama `codex/v0.4-d4` desde la etiqueta D3; versión `0.4.0-dev.3`, esquema 3. [Contrato, uso y evidencia D4](v0_4_d4.md). Libro nuevo `atlas-accounting-v2` EUR: CSV v2, efectivo/posiciones/coste sin precios, extractos completos, diferencias sin ajustes, revisiones/correcciones y evidencia inmutable. Formularios en Datos, saldos en Cartera, contexto y confirmación atómicos. API antigua sin política conserva `legacy-eur-v1`; carteras existentes y gráficos anteriores intactos. El libro v2 no tiene todavía NAV/TWR: corresponde a D6/D7. USD, dividendos/splits nuevos y D5–D8 pendientes. No ejecutar código D3 sobre una base de esquema 3.

**Pruebas:** regresión 569 Python + 91 subtests y prueba adicional heredada 1/1; 255 frontend y seis del panel repetidas tras el ajuste final; 14/14 E2E en 51,7 s (`e2e-90ffdf4e4e85464e9364e1f0acd201c5`). Tipos, lint, contratos, dependencias y build con manifiesto correctos. Integridad `ok`, base habitual intacta y procesos E2E cerrados. Se conserva la evidencia de intentos fallidos y no se declara resuelta la intermitencia de API ni validado un escalado físico nuevo.

**Migración/recuperación:** ATLAS detenido antes de editar; copia previa `backups/atlas-20260909T162440667503Z-1d55fabf`, esquema 2. Su migración y restauración aisladas conservan todas las tablas anteriores, ambas carteras, vínculos/versiones y valoraciones. Informe `var/validation/d4-migration-ee74166399194cc5aa23fee45795b74f/report.json`. Las tablas nuevas están vacías. Esa copia y fuentes/build D3 permiten retroceder al punto anterior; nunca reutilizar una base de esquema 3 con D3.

D4 todavía sin subida/PR/CI remota propia. Presupuesto cero, sin importación de movimientos personales, sin nuevos indicadores ni aprendizaje. La importación de «Cartera de pruebas» y el ensayo de 48 horas siguen aplazados; v0.2 no se declara estable. Los apartados inferiores son históricos y sus pendientes D3/D4 quedan sustituidos por este estado.

Preferencia de comunicación: al terminar cada proceso, presentar cinco siguientes pasos concretos, en orden de prioridad, con su utilidad, dependencias y una recomendación. El usuario elegirá; la lista no autoriza por sí misma esos pasos ni reactiva el ensayo aplazado.

## Última planificación: arquitectura y hoja de ruta · 09/09/2026

El usuario autoriza concretar los cinco trabajos de diseño tras proponer un esquema Research/Data/Backtest/Validation/Risk/Execution: [arquitectura objetivo](arquitectura_objetivo.md). Se documentan los dos recorridos, módulos y propietarios del estado, contratos lógicos con invariantes, promoción/suspensión/recuperación y escenarios de aceptación. IA investigadora con salidas restringidas; ejecución bajo mandato y controles independientes. Se mantienen monolito modular, un ejecutor por base y versiones/políticas históricas.

La [hoja de ruta](hoja_de_ruta.md) conserva numeración y orden. v0.4 mantiene D1–D8; v0.5 explicita construcción de cartera y riesgo reutilizable; v0.6 concreta DSL/evaluador, validación, registro de candidatas y memoria; v0.7 se desglosa en lectura/conciliación, paper supervisado, paper automático acotado y cierre de recuperación. v1.3 se identifica como automatización **real**. No se incorporan notebooks, feature store específico, datos alternativos, LLM local ni ML como requisitos obligatorios para el primer paper.

Entrega solo documental sobre el código `93c7f7d`. Sin cambios de código, contratos HTTP, esquema, versión, build, proceso o datos; no se necesitan pruebas del motor para estos documentos. Enlaces locales y diff revisados. No se realiza publicación ni CI remota. La implementación D3 y su validación son las del cierre inferior. D4–D8, la importación personal, el ensayo de 48 horas y desarrollos posteriores conservan su estado pendiente; los cinco trabajos autorizados aquí son de arquitectura y planificación.

## Estado actual: D2 integrado y D3 implementado y validado localmente

**Cinco pasos autorizados completados · 09/09/2026:** [PR #4](https://github.com/Buzo500/atlas-quant/pull/4) fusionada mediante squash en `77f8fa0a0056a94f65b257a05ff6f0a79b1d982e`; etiqueta anotada [v0.4.0-dev.1](https://github.com/Buzo500/atlas-quant/tree/v0.4.0-dev.1) publicada y comprobada en remoto sobre ese commit. Integración con contenido idéntico a la cabeza revisada de D2; su CI gratuita es la indicada en el registro inferior. No se ha ejecutado otra CI por la fusión.

Se concreta D3, se añaden siete oráculos independientes y se implementa en `codex/v0.4-d3`, **`0.4.0-dev.2`**, esquema SQLite 2, contabilidad `legacy-eur-v1`. [Contrato, uso, validación e intentos fallidos](v0_4_d3.md). Calidad por fecha y capacidad, calendario/base/disponibilidad documentados, revisiones explícitas del histórico con nueva versión y confirmación transaccional. Informes paginados; controles `quality-v1` para experimentos nuevos; resultados, políticas anteriores y vínculos de cartera preservados. D3 sigue **local, sin subida, PR ni CI remota propia**. D4–D8 requieren su siguiente autorización.

**Validación en este sobremesa:** **523 Python + 91 subtests** (51,36 s, dos avisos anteriores), **249 frontend/25 archivos**, tipos, lint, contratos, dependencias y build con manifiesto correctos. Tras corregir etiquetas duplicadas se repiten las tres pruebas del panel. **13/13 E2E** (48,3 s), ejecución `e2e-ba5f5d6bc8fa41d3bb4e6bbe6b9e12fa`: precios/evidencia/revisión y los doce recorridos anteriores, viewports CSS 3440/1280/390. Integridad `ok`, base habitual intacta y puertos liberados. No es una prueba física nueva de escalado. Un intento previo volvió a sufrir espera de API; sigue como incidencia conocida abierta, sin ampliar tiempos ni introducir reintentos. Evidencia local `output/validation/d3-python-release-final.log`, `d3-frontend-final.log`, `d3-e2e-final.log`.

**Instancia habitual al cierre:** ATLAS arrancado y saludable en `http://127.0.0.1:3000/`, ejecución `f76e0b99393343a48ba18ef93baa0395`, modo compilado, motor/proxy `0.4.0-dev.2`, cero fallos de salud. Copia manual previa `backups/atlas-20260909T145952367649Z-1a342031`; antes del arranque todas las tablas coinciden con ella. Después, registros, versiones, catálogo, carteras y movimientos conservados exactamente; integridad `ok`. Cartera demo: seis movimientos, tres posiciones, NAV **25.118,66876 EUR**. «Cartera de pruebas»: revisión 2, **cero movimientos**, vínculo NVIDIA v1 conservado. Los tres conjuntos continúan en v1. Evidencia `output/validation/d3-normal-before.json` y `d3-normal-after.json`.

La pestaña habitual muestra NVIDIA, su gráfico con 427 barras y «Calidad de precios». Calendario, base y disponibilidad no acreditados; seis eventos corporativos pendientes. D3 permite dibujar esa serie, pero bloquea nueva investigación y promoción hasta resolver las incompatibilidades: no se le ha asignado evidencia ficticia. Presupuesto cero, proveedores sin configurar, parada global activa. La importación de movimientos y el ensayo de 48 horas permanecen aplazados; v0.2 no se declara estable. Abrir con `Abrir-ATLAS.cmd`, detener con `Detener-ATLAS.cmd`.

Los registros siguientes son históricos: sus pendientes de fusión/etiqueta D2 y de implementación D3 quedan sustituidos por este cierre.

## Histórico: D2 publicado en PR y CI correcta

**Cierre de publicación · 09/09/2026:** [PR #4](https://github.com/Buzo500/atlas-quant/pull/4), rama `codex/v0.4-d2`; [CI 34365374994](https://github.com/Buzo500/atlas-quant/actions/runs/34365374994) correcta al primer intento sobre **`5e64dea4888df6a25b1d43533b333b5b3085cabf`**. **497 pruebas Python + 91 subtests** (dos avisos previos), **246 frontend/24 archivos** y **12/12 E2E**. Instalación limpia en runner Windows, compilación, tipos, contratos, lint, arranque/proxy y parada correctos. E2E `e2e-fc6835bf893d46ac9b625b6c210f1100`: base de control conservada, integridad `ok`, puertos liberados y resultado 0. El cierre posterior solo modifica documentación; el SHA identifica exactamente las fuentes, pruebas y workflow ejecutados. Evidencia local `output/validation/d2-ci-34365374994.json` y `d2-ci-34365374994-job.log`. **Sin fusión ni etiqueta.**

Cuota posterior comprobada en GitHub: **90/2.000 minutos**, almacenamiento **0/0,5 GB**, **0 USD facturables**; antes figuraban 78,3 minutos. Se conserva el presupuesto de 0 USD con bloqueo del uso de pago. Un único intento, runner estándar y sin artefactos remotos.

ATLAS habitual sigue arrancado, ejecución `f059c045db5448a1a71af06737978cf3`, interfaz compilada y cero fallos de salud. NVIDIA vinculada a «Cartera de pruebas», revisión 2 y **cero movimientos**; importación aplazada expresamente. D3–D8 pendientes, ensayo de 48 horas aplazado y v0.2 sin etiqueta estable. Recomendación siguiente: aceptar D2 e integrar la PR antes de concretar D3. Las afirmaciones de «solo local» o «CI pendiente» que siguen son registros anteriores sustituidos por este cierre.

**Revisión y publicación D2 autorizadas · 09/09/2026:** el usuario pide completar la comprobación de NVIDIA, selección de período, vinculación a cartera y publicación con CI gratuita. Decide expresamente **dejar la importación de movimientos pendiente**. Se comprueba el histórico completo de 427 sesiones (02/01/2025–08/09/2026), fechas y zoom, sin errores JavaScript en el recorrido automatizado; la pestaña de ATLAS queda también con las 427 barras visibles. «Cartera de pruebas» (`0be47fa66796432380c0f6d92f32a372`) pasa a revisión 2 al vincular expresamente la cotización `a1e27093eae847deb4d8311d8c001f42` al conjunto NVIDIA `4fc6914f5b944719a4901d8613d9968b`, versión 1. Conserva **cero movimientos**; la cartera demo no se modifica. Evidencia local `output/validation/nvidia-bindings.json` y `nvidia-full-period.json`. Existe otro conjunto NVIDIA creado por el usuario; no se fusiona ni elimina. GitHub muestra presupuesto de Actions **0 USD**, consumo **0 USD** y **Stop usage: Yes** antes de la ejecución. Se prepara la publicación en `codex/v0.4-d2`; CI remota aún pendiente. No se autoriza fusión ni etiqueta en este cierre. Los párrafos siguientes conservan los estados anteriores a esta vinculación y autorización.

**Fuente NVIDIA reparada · 09/09/2026:** el usuario no veía el gráfico porque Yahoo fallaba con curl 60/422. Emisor observado: raíz de inspección HTTPS de Avast ya confiada en Windows, ausente del bundle de certifi. [Diagnóstico y mantenimiento](diagnostico_yahoo_windows.md). Se añade `REQUESTS_CA_BUNDLE` a la lista explícita del lanzador y se configura localmente `.env` con `var/certificates/requests-ca.pem` (certifi + CA de Windows); verificación HTTPS activa, Avast y almacén del sistema sin cambios. **48 pruebas runtime/feed + 28 subtests correctos**, build verificado y gráfico real `NVD.DE` visible sin errores JavaScript. No se repitieron todas las suites D2.

Instancia actual `f059c045db5448a1a71af06737978cf3`, arrancada tras copia manual `backups/atlas-20260909T142248305429Z-eaa0545f`. Nuevo conjunto `4fc6914f5b944719a4901d8613d9968b`, versión 1, Yahoo `NVD.DE`, **427 sesiones EUR del 02/01/2025 al 08/09/2026**. Dos carteras previas conservadas exactamente; no se registran compras ni se cambian sus fuentes. Seis eventos corporativos de Yahoo conservados sin conciliar; siguen sus restricciones. [Abrir gráfico](http://127.0.0.1:3000/?tab=data&dataset=4fc6914f5b944719a4901d8613d9968b). Configuración/certificados/datos permanecen locales e ignorados por Git. Presupuesto cero, sin CI, publicación o ensayo sostenido. Este arranque sustituye al indicado en el cierre D2 inferior.

**Cinco puntos de D2 completados · 09/09/2026:** el usuario autoriza el diseño físico de migración, pruebas de identidad, catálogo, separación de cartera/precios con transacciones y validación aislada de migración/recuperación/regresión. Implementados en `codex/v0.4-d2`, creada desde la etiqueta publicada `v0.3.0-dev.1` (`2705ffe3cd2b7a7a75bb2fdcca7f2abf280a9819`). Versión local **`0.4.0-dev.1`**, esquema SQLite **2**. [Diseño, uso y límites de D2](v0_4_d2.md). Los cambios de planificación anteriores se conservan. Todo sigue local, sin commit, subida, nueva PR, CI remota, fusión ni etiqueta.

Catálogo con ID estable de instrumento/cotización, alias por proveedor/mercado/fecha y revisiones inmutables. Cartera independiente del conjunto de investigación, libro con IDs/importes originales y vínculos explícitos a versiones de precios. Previsualización y confirmación detectan contexto obsoleto y cambios concurrentes; errores revierten también auditoría. Interfaz en Datos para elegir/crear cartera, configurar fuentes y consultar movimientos/catálogo. Se mantiene `legacy-eur-v1`: EUR operativo, USD solo metadato del catálogo. D3–D8, CSV v2, FX y cálculo v2 siguen pendientes. El catálogo permite altas; no edición/fusión de identidades. Las correcciones de movimientos aún no están implementadas.

**Validación en este sobremesa:** 496 pruebas Python + 91 subtests (dos avisos previos), 246 pruebas frontend en 24 archivos, tipos, lint, contratos generados, dependencias y build con manifiesto correctos. **12/12 E2E en 43,4 s**, ejecución `e2e-a4f46b554c314540b2993115f971eb19`: diez recorridos anteriores, regresión del sondeo móvil y flujo D2 con 3.300 barras/cambio de fuente y ticker sin alterar libro ni corte histórico. Viewports CSS 3440/1280/390, sin nueva comprobación física del escalado de Windows. Servidores aislados cerrados 0/0, integridad `ok`, base habitual intacta durante los ensayos y puertos liberados. Logs `output/validation/d2-python-second.log`, `d2-frontend-poll-fix.log`, `d2-e2e-final.log`; intentos anteriores conservados.

Se corrigió una causa demostrada de desaparición de la ficha móvil: el texto del refresco de estado añadía una línea, desplazaba la página y cerraba la ficha. Se reprodujo esperando un sondeo real y se mantiene ahora la lectura anterior durante el refresco. **No es una corrección ni explicación del timeout histórico de API**, que conserva su estado de incidencia conocida aceptada.

**Migración y recuperación:** copia manual previa `backups/atlas-20260909T131226845071Z-9973d0f5` (esquema 1) conservada. `tools/check_d2_migration.py` verifica sobre copias aisladas migración 1→2, historial heredado exacto, valoración idéntica, reapertura idempotente y backup/restauración de esquema 2; informe `var/validation/d2-migration-27b6150a04d244bdb74dea96f03d5079/report.json`. No abrir el esquema 2 con código v0.3: una vuelta atrás requiere parar, restaurar la copia compatible y recuperar sus fuentes/build.

**Instancia habitual al cierre:** arrancada y saludable en [http://127.0.0.1:3000/](http://127.0.0.1:3000/), modo compilado, ejecución `5457ee2999154374b5f9338f25722ca3`, cero fallos de salud. Migración real a esquema 2 comprobada: registros/versiones/auditoría anteriores intactos, seis movimientos y tres posiciones; NAV **25.118,66876 EUR**, efectivo, curva y TWR conservados. Cartera `990037066e0a4268ad0caa51a84c0b78`, revisión 2, conjunto legado `a4eb0c17469145ab962f45156db83897`. Salud del motor/proxy `0.4.0-dev.1`, interfaz HTTP 200, parada global activada, sin proveedores configurados, presupuesto/gasto/reserva cero. Evidencia `output/validation/d2-normal-before.json` y `d2-normal-after.json`. Abrir con `Abrir-ATLAS.cmd`, detener con `Detener-ATLAS.cmd`.

Pendiente al terminar la implementación local (resuelto por el cierre superior): revisar D2 en la interfaz y preparar su PR/CI gratuita antes de integrar. D3 requiere concretar su diseño antes de desarrollarlo. El ensayo de 48 horas y su seguimiento siguen aplazados; v0.2 continúa sin etiqueta estable. Los estados inferiores son históricos y no sustituyen el estado actual superior.

## Histórico: alcance v0.4 y entrega de desarrollo v0.3 aceptada

**Alcance v0.4 aprobado y D1 concretado · 09/09/2026:** el usuario acepta D1–D8, CSV propio y EUR/USD y solicita concretar D1. [Especificación D1](v0_4_d1.md) fija contratos lógicos, precisión decimal, orden de movimientos, fechas/flujos, derechos de dividendos, FX, XIRR, capacidades, CSV v2, errores y diseño inicial de migración. [12 oráculos numéricos sintéticos](fixtures/v0_4_d1_referencias.json) comprobados con Decimal/fechas de biblioteca estándar, sin ejecutar ATLAS; no son pruebas de implementación v0.4. Las convenciones concretas de D1 prevalecen sobre las propuestas generales del plan. D2–D8 no implementados; ningún cambio de programa, base, esquema, versión o dependencias. Solo documentación y datos de referencia locales, sin commit/subida/CI. El siguiente trabajo es diseñar la migración física de D2 y convertir los casos pertinentes en pruebas de contrato. Los registros inferiores que describen el alcance como pendiente quedan sustituidos por esta aceptación.

**Plan de v0.4 definido · 09/09/2026:** el usuario solicita planificar la siguiente versión. [Plan v0.4](plan_v0_4.md): D1 contratos/fixtures; D2 identidad y cartera independiente de precios; D3 calidad/calendarios; D4 importación/conciliación CSV; D5 dividendos/splits conciliados; D6 FX EUR–USD; D7 MWR/XIRR; D8 integración/migración/CI. CSV propio y EUR–USD son propuestas iniciales del plan, no preferencias confirmadas por el usuario. **Sin implementación autorizada**, cambios de versión/esquema, instalación, pruebas nuevas ni publicación. Se preserva el monolito modular y el presupuesto cero. Primer desarrollo recomendado: D1 y después D2.

La PR #3 está fusionada y la etiqueta anotada `v0.3.0-dev.1` publicada sobre `2705ffe3cd2b7a7a75bb2fdcca7f2abf280a9819`, verificados en la tarea anterior. El checkout local seguía en `codex/v0.3-graficos`, `c110be8`, con el mismo contenido que la fusión; no asumir que ya existe una rama de v0.4. El plan se redacta localmente sobre esa base. El estado del proceso de ATLAS no se consulta ni modifica al planificar.

**Cierre G6 autorizado · 09/09/2026:** el usuario acepta expresamente el timeout como incidencia conocida de `0.3.0-dev.1`, cierra G6 y autoriza subir la documentación, actualizar y fusionar la PR #3 y publicar la etiqueta `v0.3.0-dev.1`. La causa de la incidencia sigue abierta; aceptación no equivale a corrección. Pantalla completa comprobada manualmente por el usuario en precios y cartera. CI vigente `34346311068` sobre `d5c3b09`: 482 Python + 91 subtests, 244 frontend, 10 E2E. Desde ese SHA solo cambian documentación e instrucciones del proyecto. [PR de integración](https://github.com/Buzo500/atlas-quant/pull/3) y [referencia de entrega](https://github.com/Buzo500/atlas-quant/tree/v0.3.0-dev.1) identifican su publicación cuando se complete. El ensayo de 48 horas sigue aplazado y v0.2 no es estable. No se autoriza iniciar v0.4 por este cierre.

Los siguientes registros conservan la secuencia previa: sus pendientes de G6, permisos y pantalla completa quedan sustituidos por este cierre.

**Pantalla completa confirmada manualmente por el usuario · 09/09/2026:** tras seguir el procedimiento en Datos/precios y Cartera, confirma «están perfectos, lo acabo de comprobar». Se da por completada la comprobación de ocultación de pestañas/barra de direcciones mediante el botón del gráfico y restauración con Escape. Es evidencia comunicada por el usuario, no una captura ni una ejecución automatizada. Sustituye el pendiente de pantalla completa de los registros anteriores. G6 queda pendiente únicamente de decidir la aceptación del timeout como incidencia conocida de la entrega de desarrollo. No se infiere autorización de fusión ni etiqueta. El estado detenido descrito a continuación corresponde al cierre anterior; después el usuario realizó su prueba manual y no se ha consultado aquí la salud de la instancia.

**Revisión de los tres siguientes pasos · 09/09/2026:** matriz G1–G6 y decisión de API documentadas en la [revisión final](revision_final_v0_3.md#revisión-de-los-tres-puntos-solicitados--09092026). Se recomienda conservar el timeout como incidencia conocida abierta sin repetir ensayos genéricos; aceptar esa limitación para la entrega de desarrollo requiere decisión del usuario. La comprobación del marco de Chrome volvió a quedar bloqueada: Computer Use detuvo la captura por no poder determinar la URL antes de cualquier entrada. Requiere observación manual, no otro intento idéntico automatizado. Entorno `e2e-1039ec2490db4b3497f7117acf70a17b` cerrado, resultado 0, servidores 0/0, integridad `ok`, hashes conservados y puertos libres. G6 abierto. Solo documentación local, sin cambios del programa, nueva CI, subida, fusión, etiqueta ni ensayo de 48 horas.

**Preparación final consolidada · 09/09/2026:** [revisión final de v0.3](revision_final_v0_3.md) es el índice vigente de evidencia y pendientes. Fuentes de gráficos `c8f4eb6`, CI correcta, escalado físico 125 %/150 % correcto y 100 % restaurado. La espera intermitente de API sigue sin causa demostrada; la ocultación del marco de Chrome mediante el botón del gráfico sigue sin certificar. El último intento nativo fue detenido por Computer Use al no poder identificar la URL, sin acreditar un defecto de ATLAS. No repetirlo como si hubiera pasado.

Herramientas de diagnóstico revisadas: protecciones de base/parada también con Python `-O`, identificación completa del entorno, comprobación HTTP/estado en los tres clientes y liberación de respuestas incluso ante fallos. **27 pruebas Python de diagnóstico/aislamiento correctas**, con tres pruebas Node incluidas; **301 lecturas reales correctas**, máximo 112,42 ms. Entorno `e2e-a9f9e2f0e3704ea09a0067c2246a4a66` cerrado, salidas 0/0, integridad `ok`, hashes habituales intactos y puertos libres. No confundir estas pruebas de herramientas con una corrección de la API ni con otra CI.

**Consolidación subida y CI final correcta:** [34346311068](https://github.com/Buzo500/atlas-quant/actions/runs/34346311068), fuentes `d5c3b0909be477a93f274d2c03f174abd232baf0`: **244 frontend, 482 Python + 91 subtests, 10/10 E2E**, instalación/build, tipos, contratos, lint, dependencias, arranque, proxy y parada correctos. Job 5 min 8 s; cuota posterior 78,3/2.000 minutos y 0 USD facturables. El E2E remoto conserva su base de control, integridad `ok` y puertos libres. La primera CI de esta consolidación (`34345374202`, fuentes `46df937`) falló con 243/244 frontend: el selector de la prueba CSV estaba cerrado. Se conserva su log; la prueba usa ahora teclado, espera la opción y comprueba el cambio de tipo sin aumentar tiempos ni reintentar. También se corrigió la protección del diagnóstico en un checkout sin `var/validation`, con 28 pruebas locales de diagnóstico/aislamiento. Detalles en la revisión final.

ATLAS normal está detenido. La consolidación modifica herramientas, pruebas y documentación; no cambia lógica del programa, contratos ni dependencias. Build local regenerado por la huella de los tests y verificado: `3e26de5d896d7ff6a9ae917bf709d47d9ba4b86818f869c5c1ab4e00e2494c5b`. El cierre tras `d5c3b09` solo documenta los resultados. PR #3 en borrador, sin fusión ni etiqueta. G6 abierto; ensayo de 48 horas y seguimiento aplazados. No iniciar nuevas funcionalidades por la aceptación de esta revisión.

## Histórico: diagnóstico y escalado del 09/09/2026

Los estados y pendientes de los párrafos siguientes corresponden a cada intento; para retomar prevalece el resumen anterior.

**Escalado de los controles actuales comprobado el 09/09/2026:** seis recorridos correctos sobre precios, cartera y backtest con Windows **125 % y 150 % físicos**, monitor 2 de **3440×1440**, Chrome visible sin emulación y zoom 100 %. Lupas, barra por teclado, fichas contrastadas con originales, arrastre/rueda en vista ampliada, Escape y foco correctos; sin desbordamiento global ni errores JavaScript. **100 % inicial restaurado y verificado**. [Procedimiento y límites](escalado_controles_20260909.md). Límite específico: la API de pantalla completa se activó, pero el navegador automatizado conservó el área de página y estado de ventana maximizada; no se certifica la ocultación del marco de Chrome en uso normal. Entorno `e2e-03515a1481ab4494a2b8461ef35d4155` cerrado, resultado 0, integridad `ok`, hashes habituales conservados y puertos libres. ATLAS normal detenido. Solo documentación y evidencia local nuevas; sin cambios del programa, CI, subida, fusión ni etiqueta. El diagnóstico de API permanece abierto y G6 no se da por cerrado. El intento del párrafo siguiente queda como antecedente.

**Intento de escalado físico de los controles actuales, 09/09/2026:** pendiente de abrir manualmente Configuración → Sistema → Pantalla. Computer Use enumera ventanas, pero lanzar `SystemSettings.exe` no expuso una ventana accesible; no se aplicó ningún porcentaje. Compilación verificada con `build_frontend.py --check`. Entorno aislado `e2e-eedf1ecbfc15482486a3a2abbdd85c57`: demo y comparación real de DEMO_WORLD correctas (220 observaciones fuera de muestra). Chrome temporal, sin emulación de viewport, observó otro monitor de 2560×1440 y DPR 1: esto **no valida** el ultrapanorámico ni 125 %/150 %. Cerrados Chrome temporal y ambos servidores; resultado 0, hashes habituales conservados, integridad `ok` y puertos libres. ATLAS normal sigue detenido. No se modificó código del programa ni la escala de Windows, no hubo subida, CI, fusión ni etiqueta. Al retomar, crear otro entorno aislado y observar la escala inicial antes de cambiarla.

**Diagnóstico de API del 09/09/2026:** completado sin reproducir la espera de 10 s; **la causa continúa pendiente**. Siete repeticiones del recorrido original, 300 lecturas concurrentes comparando motor/proxy/navegador y 32 lecturas con pausas cercanas al cierre de conexiones: todas correctas. Suite completa instrumentada **10/10 en 29,5 s**, `e2e-14667ae05ed848b5ad853e9835ef65ae`. Los nueve entornos cerraron con códigos 0/0, integridad `ok`, puertos libres y hashes habituales conservados. [Diagnóstico, medidas, comandos y límites](diagnostico_api_20260909.md); informe `output/validation/api-diagnostic-20260909.json`.

Se añaden herramientas **locales, sin commit ni subida**, en `tools/diagnostics/`: trazas optativas de entrada/salida HTTP, upstream de Node y ASGI, con identificador de petición y sin cuerpos ni claves. Reutilizan el aislamiento de `run_e2e.py`; no están activadas en el arranque normal. No cambian lógica del programa, frontend, contratos, dependencias, timeouts ni reintentos. ATLAS estaba y queda detenido. No se ha ejecutado otra CI ni alterado la PR; la CI del bloque siguiente sigue validando las fuentes `c8f4eb6`. La intermitencia permanece abierta: no aplicar una corrección especulativa ni atribuirle los rechazos de conexión rápidos de clientes ajenos al test durante arranque/cierre.

**Revisión subida y CI gratuita superada el 09/09/2026:** fuentes `c8f4eb615ca40993c7ad021fa195e60c62b61ed7`, rama `codex/v0.3-graficos`, [PR #3 en borrador](https://github.com/Buzo500/atlas-quant/pull/3). [CI 34340199451](https://github.com/Buzo500/atlas-quant/actions/runs/34340199451), job Windows 102428944334, correcto en 6 min 16 s: **244 pruebas frontend/23 archivos** (65,68 s), **477 Python y 91 subtests** (24,57 s, dos avisos previos), **10/10 E2E** (56,3 s). Instalación limpia, build, tipos, contratos, lint, dependencias, arranque, smoke y parada correctos. E2E remoto `e2e-5e7d502b8c0f4b24b06aa35c446551ef`, resultado 0, base de control del runner conservada, integridad `ok` y puertos libres. Evidencia local `output/validation/v03-ci-34340199451.json` y `v03-ci-34340199451-job.log`.

Cuota comprobada antes de ejecutar: **50/2.000 minutos, 0/0,5 GB y 0 USD facturables**; un único job estándar limitado a 20 minutos, sin artefactos remotos ni cambios de facturación. Solo se ha realizado un intento. La CI correcta no demuestra resuelta la causa de la espera intermitente de `/api/state` del ensayo local; se conserva el diagnóstico. La autorización del usuario cubre subida y CI, no fusión ni etiqueta. Este cierre posterior modifica únicamente documentación; el SHA anterior identifica exactamente fuentes, pruebas y workflow ejecutados.

**Estado local observado al cerrar la tarea de CI:** `Status-Atlas.ps1` devuelve `stopped` para `789e5676dfaf4d3aa8e721c21b0db8b0`, bloqueo liberado, última salud registrada `2026-09-09T10:21:29.448030+00:00` y cero fallos de salud acumulados. No se ha ejecutado una parada ni un reinicio local durante la publicación/CI; la causa del cierre no se determina aquí. El párrafo de arranque de la revisión conserva su evidencia anterior, no acredita que siga activo. Para abrirlo, `Abrir-ATLAS.cmd`.

**Revisión de gráficos completada el 09/09/2026:** se corrige la primera ficha que desaparecía al aumentar la altura de su lectura en una curva estrecha; ratón conserva su ancla y teclado se recoloca sobre el punto. Pasan **244/244 pruebas frontend**, TypeScript, lint, build con manifiesto y los cinco recorridos E2E de gráficos. La suite general queda en **9/10** por una lectura intermitente de 10 s en `/api/state`; causa no acreditada, sin reintentos ni aumento del límite. [Revisión, evidencias y límites](revision_graficos_20260909.md).

Nuevas medidas sobre las fuentes finales: 100.000 observaciones, precios 1,66 s y curva 1,98 s; barra, ficha, lupas, actualización de arrastre y rueda p95 inferior a 100 ms. Veinte ciclos de pantalla completa por escenario, nativa 3440×1440 y alternativa 390×844, sin aumento de nodos/listeners tras calentamiento. No confundir estos viewports CSS con escalado físico: Windows 125 %/150 % no se ha repetido sobre los controles actuales. Benchmark final `e2e-63895c0dbb8f4fd88f92b0cce5e445d1`, cerrado, base habitual intacta e integridad `ok`. E2E general `e2e-08bd90a1b5ac4b31b17bcdf153f93389`, con fallo conservado y cierre correcto.

**Arranque normal actual:** `789e5676dfaf4d3aa8e721c21b0db8b0`, modo compilado, salud `ok`, cero fallos de salud y huella de fuentes `03d013e3a2e4ed500adc2f18e1a081e10e84658cab920e5c38a0256d999547ed`. Conjunto `a4eb0c17469145ab962f45156db83897` v1, tres posiciones, NAV 25.118,66876 EUR, experimento completado, parada global activada y presupuesto/gasto/reserva cero conservados; sin proveedores configurados. Disponible en http://127.0.0.1:3000/; Ctrl+F5. Comparación anterior/posterior en `output/validation/v03-review-before-20260909.json` y `v03-review-normal-runtime-20260909.json`. Copia previa `backups/atlas-20260909T094122813887Z-4d19d0c4`.

Los ajustes de fichas, navegación y revisión están subidos en el SHA indicado arriba, versión `0.3.0-dev.1`; la CI sí repite las pruebas Python sobre esas fuentes. Motor/contratos/dependencias no cambian en este ajuste. G6 sigue abierto por el diagnóstico de la incidencia local de API y la comprobación física de los controles actuales. Ensayo de 48 horas y seguimiento aplazados; aprendizaje, indicadores, LaTeX, remoto, móvil y bróker siguen fuera del alcance actual. El trabajo de CI se ejecutó en GitHub; el estado local final es el indicado en la nota anterior.

## Histórico: ajustes de interacción del 08/09/2026

**Ajustes locales posteriores a la PR, 08/09/2026:** las barras de inspección se sustituyen por fichas junto al cursor. Después, por petición del usuario, los botones textuales de desplazamiento se sustituyen por una barra de navegación proporcional al tramo visible; se añaden lupas, restablecimiento y pantalla completa. En la vista ampliada se puede arrastrar con el ratón y hacer zoom con la rueda; Escape restaura vista, rango y foco. La pantalla completa nativa tiene alternativa dentro de la ventana. Se conservan teclado, lecturas originales, tablas y el límite de 1.000 velas. ATLAS se detuvo antes de editar; copia de este último ajuste `backups/atlas-20260908T203524852914Z-89ee4206`, anterior de las fichas `backups/atlas-20260908T200801426429Z-09337c0b`. Fuentes sin commit ni subida desde `0a5b813`; CI de v0.3 pendiente y ensayo de 48 horas aplazado. [Uso y validación actualizada](graficos_v0_3.md).

Validación actual: **241 pruebas frontend/23 archivos en 19,26 s**, TypeScript y lint correctos, build con manifiesto; **9/9 E2E en 27,1 s**, `e2e-94be132c780e4337a8e5e0ab818135cb`, integridad `ok`, hashes habituales conservados, ambos servidores cerrados con código 0 y puertos liberados. Pantalla completa nativa en Chromium 3440×1440 y alternativa 390×844, barra, lupas, arrastre, rueda hasta una observación y vuelta, fichas, Escape y foco comprobados. Huella `f2bc34d1dac0512a40af3dda92e2bdb4a7d515d190b698006056bec9cb510815`. Corregidos y probados el anclaje de las lupas a la observación seleccionada y el bloqueo por redondeo de la rueda entre una y dos observaciones. Evidencia `output/validation/v03-navigation-frontend-complete.json`; intentos previos conservados en la documentación de gráficos. Motor sin cambios; suite Python, benchmarks y escalado físico de Windows no repetidos para este ajuste.

**Arranque normal actual:** `83105b9cbc8744619ae828958d8d98cc`, interfaz compilada, salud `ok`, cero fallos de salud y manifiesto verificado. Conjunto habitual `a4eb0c17469145ab962f45156db83897` v1, tres posiciones y NAV 25.118,66876 EUR conservados; parada global activada, sin proveedores configurados y presupuesto/gasto/reserva cero. Disponible en http://127.0.0.1:3000/; recargar con Ctrl+F5 para recibir la interfaz nueva. Evidencia `output/validation/v03-navigation-normal-runtime.json`. Sustituye al arranque `b282…` de las fichas y al `3de2…` de la entrega inicial.

La validación anterior de las fichas pasó 214 pruebas frontend y 7/7 E2E (`e2e-d49a7fad535349bb8b56854448fc1611`). Se conserva su intento intermedio con una espera puntual de 10 s en `/api/state`, causa no determinada, para revisar si reaparece en CI/operación. Los resultados históricos de rendimiento y escalado físico corresponden a la interfaz inicial; no se atribuyen automáticamente a las fichas ni a la pantalla completa.

El usuario aplaza el ensayo de 48 horas y su seguimiento, y autoriza expresamente **empezar a implementar v0.3**. La rama es `codex/v0.3-graficos`, basada en `v0.2.0-rc.2` (`9aee422`). Motor e interfaz se identifican como **0.3.0-dev.1**. No se declara estable v0.2, no se reactiva el monitor y no se publican etiquetas estables nuevas.

Implementados: lectura de precios por versión inmutable; panel OHLCV en Datos con velas/línea/área/OHLC, volumen, intervalos diarios/semanales/mensuales, fechas, zoom, desplazamiento y originales paginados; inspección por ratón y teclado en precios, cartera y backtests; línea/área y TWR de cartera desde el origen. El SVG conserva observaciones originales para la lectura y limita explícitamente la ventana de velas a 1.000. [Uso y evidencia](graficos_v0_3.md); [alcance y criterios](plan_v0_3.md).

**Fuentes subidas en `abf908577c901372e0274aeb34ce95fe4bf1d68a`, [PR #3 en borrador](https://github.com/Buzo500/atlas-quant/pull/3).** Validación final local: 477 Python y 91 subtests (40,57 s, dos avisos previos), 201 Vitest en 20 archivos (20,58 s) y 7/7 E2E (18,0 s), además de contratos, TypeScript, lint, dependencias y build. E2E final `e2e-ff1a7f3c5a944c77af2ce68098d5d12b`, resultado 0, ambos servidores cerrados con código 0, puertos libres, integridad `ok` y hashes habituales intactos. La huella final de fuentes del frontend es `a77f6ea4e24bc08978d5ddf407412d7407ce40bba67d5e2aaafd44af21420063`.

**ATLAS vuelve a estar arrancado para uso normal en http://127.0.0.1:3000/**, ejecución `3de2afd2cc30422087368a73b5c43488`, modo compilado, salud `0.3.0-dev.1`. Conserva conjunto `a4eb0c17469145ab962f45156db83897` v1, tres posiciones, NAV 25.118,66876 EUR y experimento `488cdb4833af470c821417e3f2672312` completado. Parada global activada; claves ausentes; presupuesto, gasto y reserva cero. Comprobada también la lectura normal de las 1.100 barras de DEMO_WORLD. `Abrir-ATLAS.cmd` abre; `Detener-ATLAS.cmd` detiene motor e interfaz. Evidencia local `v03-normal-runtime.json` y `v03-preservation-final.json` en `output/validation/`.

Se detuvo ATLAS antes de editar y se creó `backups/atlas-20260908T172729906683Z-0db1c3ca`. La comprobación anterior a la validación conserva el contenido persistente y la auditoría de esa copia. Las pruebas con escritura se ejecutan exclusivamente en directorios `var/validation/e2e-*`, con datos sintéticos, sin claves y presupuesto cero. Los benchmarks generan fechas civiles artificiales desde 1750; no representan un histórico bursátil acreditado. Las funciones contables, ejecución simulada y controles no cambian por explorar un gráfico.

**Escalado físico de los gráficos nuevos comprobado** el 08/09/2026: monitor 2 de 3440 × 1440, Chrome visible y zoom 100 %, Windows 125 % y 150 %, sin emulación. Revisados precios, cartera y resultado real del Laboratorio en la base aislada; sin desbordamiento global, controles/teclado legibles, SVG sin escalado de tipografía. **100 % inicial restaurado y verificado**. Evidencia local `output/validation/v03-windows-scale/results.json` y siete capturas de la aplicación; las capturas nativas de Configuración están en la conversación. El ajuste posterior solo acota los decimales residuales del cambio calculado, conservando geometría y valores originales.

Rendimiento local con Chromium y API real: 100.000 observaciones, primera representación de precios **2,10 s**, curva **2,44 s**, p95 de inspección/zoom alrededor de **34 ms**, heap tras GC **31,4 MiB**; ocho cambios de pestaña sin aumento de nodos/listeners después del calentamiento. Prueba adicional de 1.000 velas: puntero p95 **33,8 ms**, zoom p95 **50,7 ms**, 4.025 nodos SVG y heap **25,2 MiB**. Son mediciones cortas, no el ensayo sostenido. Scripts reproducibles en `tools/benchmarks/`.

Los apartados siguientes son historia. Sus referencias a rc.2 o rc.1 y a instancias arrancadas describen aquellas entregas; para retomar prevalecen este bloque y el registro de v0.3. CI de v0.3 pendiente; no atribuirle los resultados de CI de rc.2. Aprendizaje, indicadores nuevos, LaTeX, remoto, móvil y bróker siguen fuera del desarrollo actual.

## Histórico: rc.2 con CI verificada

**CI de rc.2 superada:** [ejecución 34249730107](https://github.com/Buzo500/atlas-quant/actions/runs/34249730107), sobre `412918b5e9067e44f293b0633068ca932a472d64`. En Windows: **446 pruebas Python y 91 subtests** (22,13 s), **140 Vitest en 15 archivos** (43,86 s) y **5/5 E2E** (18,7 s); instalación limpia, build con manifiesto, contratos, TypeScript, lint, `pip check`, smoke, arranque y parada correctos. E2E remoto `e2e-ea578aac47f341ffac48cd6330edbb5a`: resultado 0, conservación de la base comprobada, integridad `ok` y puertos libres. Este SHA identifica fuentes, pruebas y workflow; el cierre posterior solo modifica documentación.

La [PR #2](https://github.com/Buzo500/atlas-quant/pull/2) está fusionada y la etiqueta [v0.2.0-rc.2](https://github.com/Buzo500/atlas-quant/tree/v0.2.0-rc.2) publicada sobre `9aee4224a12556e97cde16ed283854af10845bda`. La [CI de la etiqueta, 34251099444](https://github.com/Buzo500/atlas-quant/actions/runs/34251099444), también pasó sobre ese commit: 446 pruebas Python y 91 subtests, 140 de frontend y cinco E2E, dentro de la cuota gratuita. Se conserva el rechazo previo de la revisión automática como antecedente, resuelto mediante autorización expresa.

**ATLAS está arrancado para uso normal**, ejecución `7fa354c2b8d5425fa4818dab68acd8a0`, con salud rc.2 y la misma cartera: tres posiciones y NAV 25.118,66876 EUR. Conserva controles, parada global activada, ausencia de claves y presupuesto/gasto/reserva cero. Los registros del arranque anterior `0e3cebcbaa5344b0ade7a17071b986bd` y de conservación se mantienen como evidencia histórica.

**Motor e interfaz se identifican como `0.2.0-rc.2`, candidata con CI verificada, no v0.2 estable.** Rama de trabajo: `codex/v0.2.0-rc.2`, sobre la [PR #1](https://github.com/Buzo500/atlas-quant/pull/1) fusionada en `master` (`e1f6e020a1d75a81bff97eefcbebe726d47bcdb3`). La candidata rc.1 y sus resultados se conservan como historia.

**Intento remoto fallido conservado:** [CI 34248790750](https://github.com/Buzo500/atlas-quant/actions/runs/34248790750), sobre `dff5e24a0ebbce8a1cb0481fd64e47563794e433`: 444 pruebas Python superadas, dos fallidas y 91 subtests en 21,99 s; 140 Vitest superadas, sin E2E remoto acreditado en ese intento. Fallaban las dos variantes de aislamiento por comparar textualmente el alias Windows `RUNNER~1` y la ruta larga `runneradmin`. La aserción usa ahora `samefile`, conservando el aislamiento: reproducción con ruta corta, dos fallos antes y dos casos correctos después; también pasan las dos variantes con ruta larga. Logs y resultado original intactos.

**Validación local final del bloque:** 446 pruebas Python y 91 subtests en 38,34 s, con dos avisos previos; 140 pruebas Vitest en 15 archivos, en 13,34 s; cinco recorridos E2E en 9,6 s. TypeScript, contratos, lint, `pip check` y compilación con manifiesto correctos. Son resultados del sobremesa, no de CI de rc.2. La suite Python utiliza `ATLAS_DATA_DIR` explícito y, además, un `conftest.py` que aísla el directorio antes de recoger e importar módulos de prueba.

Están implementadas y comprobadas las correcciones de foco al importar datos, crear un experimento y confirmar movimientos; el mensaje de éxito del ledger sobrevive al refresco de versión. `QueryStatus` conserva la hora visible fuera de los anuncios accesibles y anuncia carga inicial, errores, recuperación y reintento sin repetir cada sondeo normal.

**E2E automatizado superado:** `var/validation/e2e-7e176e2037584e4983d8e2b53428724e`, cinco recorridos con interfaz compilada, API real y Chromium, sin respuestas simuladas. Ambos servidores terminaron con código 0, puertos libres, integridad `ok` y hashes de la base habitual conservados. El primer intento falló antes del navegador al comparar el PID del lanzador de Python con el del intérprete; ahora se comprueba pertenencia al Job Object específico del servidor. Se mantienen el resultado y los logs fallidos.

En la validación previa a la publicación, la base habitual tenía el mismo contenido completo, esquema, secuencias y 539 registros de auditoría que la copia `backups/atlas-20260908T151716582043Z-af195afe`, con integridad correcta. En copias aisladas se reprodujo que una apertura SQLite `mode=ro` puede crear WAL/SHM y una importación posterior de la aplicación puede retirarlos sin modificar los datos. Es una explicación compatible con la diferencia de hash del primer intento, **no una atribución concluyente**: aquel registro no conservaba los hashes individuales. El ejecutor registra ahora el inventario de hashes antes y después y rechaza cierres o comprobaciones de integridad incorrectos. La revisión posterior del escalado no repite esa comparación de hashes ni atribuye actividad de otros clientes.

**Escalado físico 125 %/150 % comprobado el 08/09/2026** en el monitor 2 de 3440 × 1440, aplicando ambos porcentajes en Configuración de Windows, con Chrome visible, zoom 100 % y sin emulación de viewport/DPI. Revisadas las cinco secciones, formularios y detalles existentes: sin desbordamiento global, superposiciones ni controles ilegibles; tablas con desplazamiento interno y foco/teclado comprobados. No se detectaron errores JavaScript ni peticiones de escritura a la API. Laboratorio se revisó solo en su formulario, sin otra ejecución. [Procedimiento, evidencia y límites](validacion_escalado_windows.md); registro local `output/validation/windows-scale-20260908/results.json` y capturas. **Restaurado y verificado el 100 % inicial**, cerrado el perfil temporal de Chrome y ATLAS normal sigue saludable con la cartera y controles indicados arriba.

El intento anterior quedó bloqueado por el control de Windows sin cambiar la escala; se conserva como antecedente. Las 35 comprobaciones de viewports CSS siguen siendo evidencia distinta. El entorno manual anterior `e2e-0de1cebd856c4115984403a8086dc09e` terminó con resultado 0, base habitual intacta y puertos libres; no tuvo interacciones de UI manual y no se reutilizó para acreditar el escalado actual.

El ensayo sostenido de 48 horas y su seguimiento permanecen aplazados. Sigue pendiente superar ese ensayo antes de declarar v0.2 estable; la CI y el escalado correctos no lo sustituyen. Se mantiene presupuesto cero, sin claves ni llamadas pagadas.

Los apartados siguientes conservan estados y validaciones históricos. Sus referencias a una aplicación arrancada o a rc.1 describen aquellas entregas; para el estado actual prevalece este apartado.

## Histórico · CI de la revisión anterior a rc.2

El usuario autorizó ejecutar la CI. **Completada el 08/09/2026** para `3f1d990ac15c391e638302828d1a720d99d78003`, en `codex/fix-local-health-resources`: [GitHub Actions, ejecución 34241300060](https://github.com/Buzo500/atlas-quant/actions/runs/34241300060). La rama está subida; se conservan `master` y la etiqueta original `v0.2.0-rc.1`. Los cambios posteriores que registran esta evidencia son exclusivamente documentales; el SHA citado identifica las fuentes, pruebas y workflow realmente ejecutados.

En el runner Windows de GitHub: **421 pruebas Python y 91 subtests** (19,01 s; dos avisos previos), **126 pruebas de interfaz en 14 archivos** (37,77 s), instalación desde checkout limpio, compilación con manifiesto, TypeScript, contratos, lint, arranque, recorrido sintético por proxy y parada correctos. El smoke confirma proveedor sin IA, gasto cero, HTML 200 y proxy correcto; no ejecuta interacciones de navegador. Estas últimas corresponden a la validación local del bloque siguiente.

El primer intento sobre `839f2d3` falló en tres tests de interfaz: dos recorridos excedieron 5 s y otro no encontró su selección. La corrección limita workers según CPU, acota consultas al contenedor de cada test y admite 15 s solo en los dos recorridos complejos; sin eliminar aserciones ni añadir reintentos. La contaminación del test siguiente por una continuación asíncrona era un riesgo compatible con el fallo, no una causa demostrada. También se evita ejecutar la parada de CI si no se intentó arrancar ATLAS. La suite completa corregida pasó localmente con afinidad de 2 CPU antes de repetir la CI. Detalle y primer run fallido en [candidata_v0_2.md](candidata_v0_2.md).

Cuota comprobada antes de ejecutar: 6,7/2.000 minutos y 0/0,5 GB utilizados, 0 USD facturables. Ambos intentos acotados a 20 minutos permanecen dentro de la cuota gratuita; sin cambios de facturación, claves nuevas, servicios de pago ni artefactos remotos.

ATLAS se detuvo antes de modificar pruebas/configuración y se reconstruyó con `tools/build_frontend.py`. **Vuelve a estar funcionando en http://127.0.0.1:3000/**, ejecución `a0e040c188c1410d93449bdf4367e97a`, con salud y manifiesto correctos. La base habitual mantiene integridad, huella persistente y prefijo de auditoría de la copia anterior; conjunto, experimento, controles y presupuesto/gasto/reserva cero conservados. No se sustituye ni restaura la base.

Evidencia local ignorada: `output/validation/github-ci-34241300060.json`, `github-run-34241300060.json`, `github-job-102111855928.log`, `frontend-hardening-preservation.json` y `ci_frontend_revision.json`. **No se ha repetido el ensayo de 48 horas ni reactivado su seguimiento**. H6 sigue pendiente, la versión sigue en `0.2.0-rc.1` y no se declara estable. Abrir: `Abrir-ATLAS.cmd`; detener ambos servidores: `Detener-ATLAS.cmd`.

## Consolidación del frontend previa a la CI

El usuario autorizó resolver, uno a uno, los nueve puntos de la revisión del frontend. **Implementados y validados el 08/09/2026**, manteniendo crema/marfil/cobre y el monolito modular. Detalles y límites en [frontend_consolidacion.md](frontend_consolidacion.md).

1. Confirmación de movimientos ligada a CSV, conjunto, versión, precios y ledger mediante token verificado dentro de la transacción.
2. Resultados del Laboratorio con contexto real e inmutable de ejecución y aviso cuando el borrador cambia.
3. Vitest/Testing Library y CI con pruebas de interfaz; lint incluye funcionalidades, componentes propios, compartidos y tests.
4. Consultas con descarte de respuestas y errores obsoletos, cancelación, última consulta y reintento. Ajustes envía solo el campo modificado: guardar peso desde un estado antiguo no desactiva una parada concurrente.
5. Borradores conservados al cambiar de pestaña; URL para sección/conjunto/experimento. Recargar conserva selecciones, no CSV, hipótesis ni autorización automática.
6. Pantallas separadas en `frontend/features/` y utilidades en `frontend/shared/`; el manifiesto de compilación incorpora estas carpetas y sus pruebas.
7. Formatos comunes EUR/USD/porcentajes/fechas con ausencia y valor inválido diferenciados; precio con fecha de sesión. Instantes en Europe/Madrid explícita.
8. Benchmark más contrastado, ejes explicados y tabla accesible de datos originales.
9. Medición de 100.000 observaciones y 1.000 registros; reducción solo visual por extremos y tablas de 50 filas, conservando todos los datos.

Pruebas finales de este sobremesa: **421 del motor + 91 subtests** (32,87 s, dos avisos previos de TestClient), **126 de interfaz** (12,49 s), TypeScript, contratos, lint y compilación con manifiesto correctos. **35 comprobaciones de tamaño** (cinco secciones por siete viewports, incluido 3440 × 1440), sin desbordamiento global ni paneles ocultos ocupando espacio. Consola sin errores. El escalado físico de Windows al 125 % y 150 % sigue pendiente: los anchos equivalentes no lo sustituyen.

ATLAS se detuvo antes de editar. Copia: `backups/atlas-20260908T131709657852Z-125c578f`. Pruebas con escritura en `var/validation/frontend-hardening-20260908/data`, con claves eliminadas del entorno y `run_worker=False`: demo, Laboratorio, revisión/edición/confirmación CSV y expediente desechable de una hora, pausado/reanudado/cancelado inmediatamente. No se ejecutó ese experimento ni se inició el ensayo de 48 horas. Ambos servidores de prueba terminaron con código 0.

**ATLAS queda arrancado para uso normal en http://127.0.0.1:3000/**, ejecución `b17661795e9c416c8a6ff0bb995b3e59`, con la base habitual. Integridad SQLite, huella persistente y prefijo de auditoría coinciden con la copia; se conservan NAV 25.118,66876 EUR, tres posiciones e IDs originales. Parada global activada, sin claves, presupuesto/gasto/reserva cero. Abrir con `Abrir-ATLAS.cmd`; detener con `Detener-ATLAS.cmd`.

Evidencia ignorada por Git: `output/validation/frontend-hardening.json`, `frontend-hardening-backend.xml`, `frontend-hardening-ui-tests.json`, `frontend-hardening-viewports.json`, `frontend-hardening-preservation.json` y `frontend_bench_final.json`. Este bloque recoge la entrega local anterior; su publicación y CI posterior están en el apartado vigente de arriba. Sigue **0.2.0-rc.1**, con ensayo y seguimiento aplazados. Sites, gráficos avanzados, aprendizaje, móvil, remoto e informes LaTeX no cambian.

## Implementación visual previa: frontend crema y cobre

El 08/09/2026 el usuario autorizó implementar la dirección visual de la maqueta en el programa local, con adaptación a pantallas ultrapanorámicas como **3440 × 1440**. Se aplica a las cinco secciones existentes: Cartera, Laboratorio, Agente IA, Datos y Ajustes. Fondo crema, superficies marfil, cobre, texto oscuro y cifras tabulares; tablas y formularios compactos y curva azul pizarra medida mediante `ResizeObserver`. Se conservan los endpoints, contratos y controles del motor. Detalle de implementación y validación en [frontend_crema_cobre.md](frontend_crema_cobre.md).

Se detuvo ATLAS antes de editar y se creó la copia `backups/atlas-20260908T124552339287Z-c00f74f9`. La base habitual conserva conjunto, versiones, ledger, investigación e IDs: su huella persistente y el prefijo de auditoría coinciden con la copia, con integridad SQLite correcta. Se validaron demo y Laboratorio en una base aislada y el expediente existente mediante consultas. Ninguna llamada pagada, clave añadida ni orden real. El arranque diario mantiene el manifiesto generado por `tools/build_frontend.py`. **ATLAS queda arrancado para uso normal en http://127.0.0.1:3000/**; abrir con `Abrir-ATLAS.cmd` y detener con `Detener-ATLAS.cmd`.

**394 pruebas y 91 subtests superados en este sobremesa**, con los dos avisos previos de TestClient; TypeScript, contratos y lint de aplicación y del componente de curva correctos. Se corrigió una prueba dependiente de la fecha real: ahora el generador de demo y su servicio comparten el reloj fijo del test de concurrencia, sin cambiar el código del motor. Evidencia local en `output/validation/frontend_crema_cobre_tests.xml` y `frontend_data_preservation.json`.

Los tamaños se comprueban como viewports CSS de navegador, no como medición física del monitor. Las tablas pueden desplazarse horizontalmente dentro de su panel. Queda pendiente una comprobación manual del escalado real de Windows al 125 % y 150 %. La creación de un nuevo experimento de 48 horas fue bloqueada por la revisión automática de aprobación; no se reintentó ni se inició el ensayo. Se verifican el informe existente y las condiciones de los controles mediante lectura y pruebas automatizadas del núcleo.

La [maqueta publicada en Sites](https://atlas-quant-interfaz.patosverdes098.chatgpt.site) permanece independiente, privada y sin cambios, con iframe aislado y CSP. Los informes LaTeX por fechas siguen en planificación como **REPORT-001**, propuestos para v0.6. No se implementan gráficos avanzados, aprendizaje, móvil ni acceso remoto. El ensayo sostenido sigue aplazado y su seguimiento pausado. La versión sigue siendo **0.2.0-rc.1**: estos cambios locales necesitan una candidata identificada, CI y el ensayo correspondiente antes de declarar estabilidad.

## Corrección anterior: fallo del ensayo y arranque habitual

El usuario pidió únicamente corregir el fallo del ensayo; su repetición queda aplazada. Se trabaja en `codex/fix-local-health-resources`, basada en la candidata `ef75b7be7afc2072142ace73bf0df166da245a55`. Al retomar, la carpeta estaba en `master` (`97520b8`) sin cambios locales; esa rama y la etiqueta `v0.2.0-rc.1` se conservan.

El ensayo del 6 de septiembre falló tras 3.900 segundos válidos: el supervisor agotó archivos abiertos al construir un cliente HTTP, y ambos servidores terminaron ordenadamente. Los datos y la auditoría se verificaron intactos. La evidencia original está en `output/validation/incident-rc1-20260906T185725Z/`; no se altera ni se convierte en un ensayo superado.

Las comprobaciones del supervisor y del monitor usan ahora `tools/local_http.py`: HTTP directo a `127.0.0.1`, sin crear contextos TLS ni consultar proxies, y cierre de respuesta y conexión incluso ante errores. Antes, cada `urllib.build_opener` creaba también un contexto TLS en Python 3.14 y abría el destino heredado de `SSLKEYLOGFILE`, aunque la petición fuese HTTP local. Los errores de construcción, protocolo y lectura de salud pasan por el control de fallos existente. No se modifica la configuración del antivirus ni las variables de entorno.

Validación de la corrección en este sobremesa: **85 pruebas focalizadas superadas en 16,51 segundos**, con datos aislados y conexiones simuladas. Incluyen 200 consultas repetidas sin TLS, cierre ante errores, agotamiento de descriptores, respuestas inválidas y regresiones del supervisor/monitor. No se han arrancado servidores de ATLAS. Evidencia local: `output/validation/local_http_fix_tests.xml` y `output/validation/local_http_fix.json`.

Al entregar la corrección, ATLAS quedó detenido y el seguimiento horario pausado. Esta corrección no publica otra candidata, no ejecuta CI ni reinicia la prueba de 48 horas. La CI superada corresponde al commit anterior; el ensayo largo de la corrección sigue pendiente.

Después, el usuario intentó abrir la aplicación y comunicó «La compilación está desactualizada». El cambio de rama había dejado las fuentes y el manifiesto de compilación con hashes distintos; Git comprueba texto normalizado, pero el manifiesto compara bytes, incluidos los finales de línea. Se regeneró la interfaz con `tools/build_frontend.py`, sin cambios de código ni dependencias, y se realizó el arranque habitual con `Start-Atlas.ps1 -OpenBrowser`. **ATLAS queda funcionando**, con motor, proxy, HTML y recursos compilados verificados, integridad SQLite correcta y contenido persistente/auditoría anterior conservados. Evidencia: `output/validation/startup_after_rebuild.json`. El ensayo de 48 horas sigue aplazado y el seguimiento permanece pausado. Los apartados siguientes conservan la evidencia histórica.

## Preparación anterior: cierre de v0.2

El usuario autorizó preparar y validar la candidata, ejecutar CI con coste cero y comenzar el ensayo sostenido. La versión de candidata es **0.2.0-rc.1**, aún sin calificar como estable. La suite previa al commit pasa con **368 pruebas y 91 subtests**, además de contratos, TypeScript, lint, dependencias y build. La evidencia viva del cierre se conserva en `output/validation/candidate_release.json`; leerla para saber el commit, CI y monitor realmente iniciados, no inferir su resultado de este plan. Ver [candidata_v0_2.md](candidata_v0_2.md) para el estado del cierre; los apartados siguientes conservan la evidencia histórica previa. La salida inesperada anterior sigue sin causa confirmada: ahora se archiva el diagnóstico por ejecución. No modificar código ni reconstruir mientras corre el ensayo. Los resultados del monitor se guardan en `output/validation/` y no van a Git.

## Consolidación del núcleo anterior

El usuario autorizó mantener el monolito modular y consolidar límites, contratos, transacciones, concurrencia, controles y pruebas. **Implementado y validado en este sobremesa**, con detalle en [consolidacion_core.md](consolidacion_core.md). La revisión previa [revision_core_arquitectura.md](revision_core_arquitectura.md) se conserva como diagnóstico histórico.

Se corrigieron CORE-001 (descargas frente a importaciones concurrentes), CORE-002 (pausa/cancelación durante cálculo y publicación tardía) y los contratos prioritarios de CORE-003. `DatasetService`, `controls.py` y las operaciones atómicas de Store separan responsabilidades y aseguran las escrituras. Riesgo y paper se confirman juntos; reanudar/desbloquear por peso no ejecuta sesiones recibidas durante la parada. Hay bloqueo explícito de un único ejecutor por base, también para servidores lanzados manualmente y restauraciones. No hay ejecución distribuida.

**Validación de esta consolidación: 328 pruebas y 91 subtests superados**, 74 pruebas nuevas; TypeScript, contratos generados, lint de aplicación, `pip check` y compilación con manifiesto correctos. Dos avisos previos de TestClient. Los controles durante CPU/IA se prueban por HTTP con eventos y proveedores simulados. Cartera verificada en navegador; API, proxy, detalle e informe correctos. Evidencia: `output/validation/core_hardening_desktop.json` (ignorado).

Copia anterior: `backups/atlas-20260906T163217941908Z-e705d40d`. Comparación realizada: conjunto completo, versión, ledger, investigación, resumen e IDs intactos; NAV 25.118,66876 EUR, tres posiciones, experimento `488cdb4833af470c821417e3f2672312` en observación. ATLAS arrancado con demo original, parada global activada, sin claves, presupuesto/gasto/reserva cero. La base no se ha sustituido ni restaurado.

En la primera ejecución de cierre se observó una salida no explicada de un servidor; el supervisor cerró ambos y se conservaron los datos. Se añadió diagnóstico de hijo/código de salida con cuatro pruebas, incluido en las 328. Consultar la incidencia y el ensayo posterior en `consolidacion_core.md`; no dar por diagnosticada su causa.

La v0.2 continúa en desarrollo y el motor en 0.1.0. Faltan CI en GitHub, ensayo de 48 horas y candidata identificada/publicada. La política compartida entre backtest/paper y la división adicional de paneles siguen como deuda concreta; no se afirma una arquitectura terminada. `pnpm lint` cubre aplicación mantenida; `pnpm lint:all` sigue mostrando diagnósticos de componentes/hooks base. No se han añadido gráficos, aprendizaje, móvil o red remota. Los cambios de esta sesión son locales; no se han subido a GitHub.

### Estrategia McClellan propuesta

El usuario pidió guardar una estrategia que utilizaba: cierre del McClellan Oscillator inferior a −100, seguido de dos cierres estrictamente entre −100 y 0, como señal de compra; también considerar el McClellan Summation Index. Registrada como **STRAT-001** en [backlog_planificacion.md](backlog_planificacion.md), solo candidata de investigación, sin implementación. Falta confirmar si los dos cierres son consecutivos/inmediatos, la serie/plataforma y variante, universo de amplitud, activo negociado, salidas y rearme. No suponer que se calcula sobre el precio del ETF ni imponer un filtro del Summation Index todavía. Encaje propuesto en v0.6, condicionado a disponer de datos adecuados con presupuesto cero. Se conserva la prioridad de fiabilidad del núcleo; guardar esta idea solo modifica documentación.

### Planificación remota y móvil anterior

El usuario añadió **solo a planificación**: enviar pruebas de estrategias desde el portátil al sobremesa para mantenerlas ejecutándose durante ausencias, y una app móvil para elegir/controlar estrategias y consultar resultados. Se registraron REMOTE-001 y MOBILE-001 en el backlog, con detalle en [ejecucion_remota_movil.md](ejecucion_remota_movil.md) y posiciones propuestas v0.8/v0.9. No se ha implementado ni configurado red, servicios, acceso móvil o GPU. Las órdenes reales conservan los requisitos futuros de v1.2/v1.3; «controlar un experimento» no equivale a enviar una orden de mercado.

### Trabajo operativo previo

Tras completar la instalación de v0.1 en el sobremesa, el usuario pidió profesionalizar el proyecto, enumerar versiones y comenzar los siguientes pasos. Confirmó que había subido los cambios anteriores a GitHub. El trabajo actual partió del commit `97520b8` (`traslado al sobremesa`) con el árbol limpio: se ha documentado la hoja de ruta y se están entregando las mejoras operativas de **v0.2 en desarrollo**. El motor y la interfaz siguen identificándose como 0.1.0/v0.1; no se ha etiquetado una v0.2 estable.

Prioridad vigente: [hoja de ruta](hoja_de_ruta.md), [plan de v0.2](plan_v0_2.md) y [auditoría y evidencia](auditoria_v0_2.md). Guía de uso actual: [operación en Windows](operacion_windows.md). Mantener presupuesto cero, sin claves, demo existente y ninguna mejora de gráficos/aprendizaje o conexión a bróker. Consultar Git antes de asumir qué cambios se han guardado o subido.

### Instalación inicial ya completada

El usuario retomó el proyecto en Windows nativo desde `C:\Users\lulae\Documents\Personal\Proyectos\atlas-quant`, con base nueva y datos de demostración, sin claves de API y presupuesto cero.

La instalación partió del commit `cdab38a`, con el árbol de trabajo limpio y sin `.venv`, `frontend/node_modules`, `.env` ni base local. La instalación y validación han terminado: funcionan el motor, el proxy y las interacciones principales de la interfaz; la parada cierra ambos puertos y el reinicio conserva la cartera, el conjunto y el experimento. ATLAS queda arrancado en segundo plano, con la demo y un experimento técnico sin IA en observación. Ambos proveedores siguen sin configurar, sin `.env`, con presupuesto, gasto y reserva cero.

La preparación anterior en el portátil solo añadió documentos, instrucciones y exclusiones de Git. La primera instalación del sobremesa no modificó el motor ni la interfaz, no migró la cartera del portátil y conservó los archivos de dependencias fijadas. Se añadió `.pnpm-store/` a las exclusiones de Git por la caché local de instalación. El trabajo posterior de v0.2 sí cambia los lanzadores, la ejecución compilada, el almacenamiento y sus pruebas.

## Objetivo y preferencias confirmadas

- Software para analizar inversiones y gestionar una cartera personal; acciones y ETF primero.
- Diseño funcional y técnico amplio, implementado por fases; recursos gratuitos al principio y costes justificados antes de contratar.
- El usuario quiere órdenes reales y automatización configurable como objetivo futuro. La v0.1 no puede enviar órdenes a un bróker. IBKR es candidato, sin conexión ni cuenta comprobadas aquí.
- OpenAI y Anthropic seleccionables; configurar integración antes de decidir presupuesto. Presupuesto inicial cero.
- La IA debe acumular experiencia sobre estrategias y condiciones de mercado, no limitarse a responder preguntas aisladas. Sigue pendiente elegir e implementar la arquitectura de aprendizaje.
- El usuario probó v0.1 y confirmó que funciona y le gusta su aspecto.
- Comunicación en español, concreta, realista y sin dar por buena cualquier propuesta.

## Equipos

El portátil original usa Windows. Una inspección anterior identificó Intel Core Ultra 9 185H, 32 GiB de RAM instalada y NVIDIA RTX 2000 Ada Generation Laptop GPU, con 8.188 MiB de VRAM. No se ejecutó un benchmark de IA local.

En el sobremesa se han comprobado Windows 11 Home x64, versión `10.0.26200`, Intel Core i7-10700K, 31,9 GiB de RAM y NVIDIA RTX 3080 con 10.240 MiB de VRAM y controlador `616.64`. El usuario declara WSL2 instalado; no se ha utilizado ni comprobado su distribución o acceso a CUDA.

La v0.1 se ha instalado en Windows nativo. WSL2 queda para un posible piloto posterior de IA local. El software actual no usa CUDA ni un modelo local; la GPU no acelera automáticamente los backtests.

## Lo que existe

- Backend Python/FastAPI en `backend/atlas_quant/`, con SQLite WAL en `var/atlas/atlas.sqlite3`.
- Interfaz React/TypeScript, Vinext y Shadcn en `frontend/`. El nuevo arranque habitual usa el servidor Node compilado, con proxy local y manifiesto verificado; el servidor de desarrollo queda para desarrollo. Sin despliegue compartido.
- Cartera EUR: movimientos, comisiones, dividendos/splits contables, posiciones, P&L y TWR diario con aproximación de flujos al final del día. Sin FX, fiscalidad ni XIRR.
- Importación CSV con validación, versiones inmutables y previsualización de movimientos. Demo con tres símbolos ficticios.
- Backtests long-only: mantener, SMA y momentum en el núcleo; ejecución posterior a la señal, costes y límites de posición compartidos con el benchmark.
- Investigación con división cronológica 60/20/20, selección en validación, ganador congelado y sensibilidad a costes.
- Experimentos persistidos: propuesta, backtest, informe y observación de nuevas sesiones. Máximo ocho candidatos y dos llamadas LLM por experimento. Sin código arbitrario generado por el modelo.
- Adaptadores OpenAI y Anthropic con claves locales y reservas de presupuesto previas al envío. Sin llamadas de IA al arrancar. Catálogo determinista disponible sin proveedor.
- Simulación paper condicionada a datos, evidencia, autorización y límites; parada global activada inicialmente. Los datos sintéticos no habilitan promoción.
- Fuente opcional Yahoo/yfinance diaria en EUR. Datos parciales o problemas corporativos conocidos bloquean promoción; no hay reconciliación completa de dividendos/splits en backtesting.
- Historial y auditoría en la base local. Copias consistentes manuales, antes de instalar y automáticas al arrancar/cada 24 horas; retención de siete automáticas. Restauración con estado operativo pausado y copia del destino. Esquema SQLite explícito con adopción desde v0.1. No hay sincronización de bases, aprendizaje acumulativo ni servicio del sistema con reinicio automático.

Los umbrales temporales y numéricos no garantizan rentabilidad. Dos días de ejecución son una prueba operativa, no validación estadística de una estrategia. Cada experimento paper tiene capital independiente; falta riesgo agregado entre ellos.

## Instalación y ejecución

Guía paso a paso: `docs/traslado_sobremesa.md`.

Versiones observadas en el portátil el 06/09/2026: Python 3.12.14, Node 24.19.0 y pnpm 11.19.0. Son referencias históricas. El instalador actual valida Python 3.12+, Node 22.13+ y pnpm exactamente 11.19.0; instala dependencias fijadas y compila bajo el mismo bloqueo usado por la ejecución. Si existe una base, crea una copia previa.

En este sobremesa se usa Python 3.14.4 x64 del sistema (`C:\Python314`), con `.venv` creada localmente; Node 24.15.0 del sistema y pnpm 11.19.0 instalado en el perfil del usuario. Su directorio global se ha añadido al PATH del usuario: abrir una ventana nueva de PowerShell para recoger el cambio. Se han instalado `requirements.txt` y `frontend/pnpm-lock.yaml` sin modificarlos; `pip check` no detecta incompatibilidades.

La descarga con npm/pnpm necesitó `NODE_OPTIONS=--use-system-ca` en la sesión de instalación para usar los certificados del sistema. No se desactivó la verificación TLS ni se hizo permanente esa variable. No se han configurado claves ni presupuesto de pago para probar la aplicación.

Desde PowerShell en la raíz, después de instalar dependencias:

```powershell
.\.venv\Scripts\python.exe tools\run_atlas.py --open
```

Interfaz: `http://127.0.0.1:3000/`. Backend: puerto 8000. Ambos son exclusivamente locales. Mantener el proceso y el equipo activos para observar experimentos. El supervisor detecta la salida de un servidor o tres fallos de salud y detiene la instancia completa; no reinicia trabajos automáticamente. Para parar: Ctrl+C en el lanzador en primer plano o `Stop-Atlas.ps1`.

`Start-Atlas.ps1 -OpenBrowser` arranca en segundo plano y confirma la salud antes de devolver éxito. `Status-Atlas.ps1` consulta estado y `Stop-Atlas.ps1` espera el cierre. Los accesos `Abrir-ATLAS.cmd` y `Detener-ATLAS.cmd` permiten hacerlo con doble clic. Registros: `var/logs/`; último estado: `var/runtime.json`. Las claves opcionales se configuran en `.env`; no son necesarias para instalar ni probar la demo.

Desde una nueva ventana de PowerShell en este PC:

```powershell
cd C:\Users\lulae\Documents\Personal\Proyectos\atlas-quant
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-Atlas.ps1 -OpenBrowser
```

Para solicitar la parada desde esa carpeta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-Atlas.ps1
```

`ExecutionPolicy Bypass` se aplica únicamente al proceso que ejecuta el script. Se han comprobado el arranque en segundo plano, la parada efectiva de los puertos 3000/8000 y la persistencia tras reiniciar. Cerrar la pestaña no detiene ATLAS. No hay arranque automático al encender el PC.

## Código, datos y conversación se trasladan por vías distintas

GitHub conserva código, documentación y pruebas. `.venv` y `frontend/node_modules` se reconstruyen en cada equipo. `.env` y `var/` están excluidos. Con un clon nuevo se empieza sin los experimentos ni la cartera del portátil.

Para mover estado existente hay que detener y comprobar el fin del motor, preparar una copia coherente y guardar respaldo del destino. No copiar una base SQLite activa aislada de sus archivos WAL. No fusionar dos bases ni arrancar los mismos experimentos activos en ambos equipos. Un estado `running` interrumpido se marca `interrupted` al recuperarse; no se repite automáticamente una llamada al proveedor.

Propuesta de operación entre equipos: sobremesa como dueño de las ejecuciones prolongadas; portátil con datos de desarrollo independientes. Descargar cambios antes de trabajar, guardar/subir al terminar y actualizar la versión de ejecución entre experimentos. No editar en caliente la versión con la que se está evaluando una estrategia.

Este documento y `AGENTS.md` permiten reanudar el trabajo en un chat nuevo con contexto explícito. Clonar Git no copia la transcripción de Codex ni sus credenciales. Las funciones de conexión remota y handoff son alternativas que requieren configuración y disponibilidad; no se han configurado durante el traslado.

## Backlog pendiente

Fuente detallada: `docs/backlog_planificacion.md`.

1. Cursor sobre gráficos con fecha, hora cuando exista, apertura/máximo/mínimo/cierre y volumen. No inventar información intradía en datos diarios ni OHLC de mercado en una curva de patrimonio.
2. Velas japonesas, barras OHLC, línea/área, zoom y desplazamiento; después otros tipos si aportan utilidad. Los precios sintéticos de gráficos transformados no deben usarse para simular ejecuciones.
3. Memoria consultable de investigaciones: conservar también fallos y variantes rechazadas, datos y versiones, costes y conclusiones verificables.
4. Modelo cuantitativo pequeño que aprenda relaciones entre variables observables y resultados posteriores, con evaluación temporal y comparación con alternativas fijas.
5. Comparar un LLM por API con uno local; ajustar adaptadores solo si una tarea concreta lo justifica. La recomendación de memoria y modelos numéricos locales con LLM intercambiable es una propuesta, no una arquitectura ya aprobada o construida.
6. REMOTE-001: crear experimentos desde el portátil y mantenerlos en el sobremesa, con datos/versiones, acceso autenticado, recuperación y prevención de duplicados. La RTX 3080 no acelera los backtests actuales de CPU.
7. MOBILE-001: panel móvil para estrategias, controles y métricas actualizadas; PWA como propuesta inicial. No existe esa app en la versión actual; `pdf-mobile/` solo publica el diseño.
8. UI-001: implementar el futuro frontend crema/marfil y cobre con distribución adaptable, incluyendo 3440 × 1440 y escalado de Windows/navegador. Requisito pendiente de implementación y validación; la maqueta no sustituye a la aplicación.
9. REPORT-001: informes LaTeX editables con plantilla propia, recursos y fechas seleccionables para cartera y backtests; métricas del período y datos/versiones identificados. Encaje propuesto en v0.6, sin generar documentos ni instalar herramientas ahora.

El usuario pidió expresamente mantener estas mejoras en planificación. No retomarlas automáticamente al instalar la aplicación en otro ordenador.

## Evidencia y límites de la entrega anterior

La documentación de v0.1 registra 167 pruebas y 91 subtests superados, compilación y TypeScript comprobados, prueba del proxy local y recuperación del estado tras reinicio. Hubo dos avisos de deprecación de TestClient. Son resultados de la entrega en el portátil, no pruebas nuevas realizadas en el sobremesa.

En aquella entrega no se validaron interacciones automatizadas en navegador, ejecución continua de 48 horas, llamadas de pago, conexión IBKR ni inferencia/entrenamiento local. El usuario sí verificó personalmente que la interfaz funciona. Las comprobaciones nuevas del sobremesa se detallan a continuación; las demás limitaciones siguen vigentes.

## Validación en el sobremesa · 06/09/2026

- Python: 167 pruebas y 91 subtests superados, con dos avisos de deprecación de TestClient. Se usó `ATLAS_DATA_DIR=var/test-data` para aislar la base creada al importar la app y `--basetemp var/pytest-<guid>` porque el sandbox denegaba el directorio Temp. Los proveedores de IA y Yahoo están simulados en estas pruebas.
- TypeScript: pasó `node frontend/node_modules/typescript/bin/tsc --noEmit --project frontend/tsconfig.json`, ejecutado desde la raíz. También pasó `pnpm.cmd --dir frontend exec tsc --noEmit` usando el pnpm instalado y el PATH normal del usuario fuera del sandbox. Compilación: pasó `node node_modules/vinext/dist/cli.js build`, ejecutado desde `frontend`.
- Arranque: backend `http://127.0.0.1:8000/api/health` y proxy `http://127.0.0.1:3000/api/health` respondieron `status: ok`, `mode: local` y `live_available: false`. La página principal devolvió HTTP 200.
- Navegador: carga de demostración comprobada, tres posiciones ficticias y patrimonio de 25.118,66876 EUR. En Laboratorio se ejecutó la comparación de `DEMO_BOND`, con tres candidatos y sensibilidad a costes de 0,5×, 1× y 2×.
- Motor persistente: `tools/smoke_local.py` creó el experimento técnico sin IA (`provider: none`, presupuesto 0), que llegó a `observing`, con 220 observaciones fuera de muestra, promoción rechazada y `paper_account: null`. El informe se abrió en la interfaz y mostró gasto y reserva de API en cero. La prueba dejó ese experimento de demostración en la base nueva; su resultado local está en `output/validation/runtime_v01.json`.
- Estado final: ambos proveedores sin configurar, `.env` ausente, un único conjunto sintético sin fuentes automáticas y un único experimento con presupuesto/gasto/reserva cero, `auto_paper: false` y sin cuenta paper. Parada global activada, modo paper y capacidad real deshabilitada.
- Parada y reinicio: `Stop-Atlas.ps1` cerró los puertos 3000 y 8000; `Start-Atlas.ps1` volvió a abrirlos exclusivamente en `127.0.0.1`. Se conservaron los IDs del conjunto y experimento, las tres posiciones, el patrimonio, los límites y el estado `observing`. `PRAGMA integrity_check` devolvió `ok`. Tras recargar el navegador, la interfaz volvió a mostrar «Motor conectado» y la cartera conservada.
- Evidencia local adicional: `output/validation/desktop_windows.json`, excluido de Git, registra el entorno y estas comprobaciones. El campo `browser_interactions: not_tested` del informe original de smoke solo describe lo que hace ese script; las interacciones posteriores sí se verificaron en esta sesión.

No se han realizado pruebas sostenidas de 48 horas, llamadas de pago, descarga de mercado en este equipo, conexión con IBKR ni inferencia local. Las pruebas de instalación no equivalen a validar una estrategia de inversión.

Comprobaciones para cambios de código cuando correspondan:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
pnpm --dir frontend exec tsc --noEmit
.\.venv\Scripts\python.exe tools\build_frontend.py
```

`tools/smoke_local.py` modifica el estado de la instalación con datos/experimentos de prueba. No ejecutarlo sobre una cartera de uso sin valorar esa modificación.

## Avance de v0.2 en el sobremesa · 06/09/2026

- **254 pruebas y 91 subtests superados**, con los dos avisos de deprecación ya conocidos; TypeScript y compilación verificada correctos. Se añadieron pruebas de copias, restauración, retención, migraciones, bloqueo y propiedad de procesos, además de la salida de instaladores sin consola.
- Instalación principal actualizada con `Install-Atlas.ps1`, que creó una copia previa y terminó correctamente. La base pasó de esquema 0 a 1 sin cambios en el contenido del conjunto, versiones, ID/estado del experimento, proveedor ni importes de presupuesto. Se comparó con el snapshot anterior y ambas bases superan `integrity_check`.
- Instalación limpia desde una copia de las fuentes en `var/validation/clean install 37e86b7d`, sin entorno ni datos previos: instalación, build, inicio, demo, experimento sin IA, doble arranque, backup, verificación, parada, restauración y reinicio correctos. Cartera e IDs idénticos tras restaurar; experimento pausado y controles seguros. Una segunda actualización de esa copia conservó incluso el hash de la base durante la instalación. La copia de validación queda detenida.
- Navegador comprobado con interfaz compilada: cartera principal, comparación del Laboratorio y expediente del experimento existentes. En la instalación aislada se verificaron assets sin HMR y rechazos HTTP 403 para mutaciones sin cabecera o de origen ajeno.
- **Estado al entregar:** ATLAS principal arrancado con `Start-Atlas.ps1` invocado desde otra carpeta, salud correcta, interfaz compilada en `http://127.0.0.1:3000/`, una demo y un experimento técnico sin IA en `observing`. NAV 25.118,66876 EUR, tres posiciones, parada global activada, sin cuenta paper ni fuentes automáticas, presupuesto/gasto/reserva cero y `.env` ausente. Cerrar el navegador no lo detiene; usar `Detener-ATLAS.cmd` o `Stop-Atlas.ps1`.
- Evidencia local excluida de Git: `output/validation/runtime_v02_desktop.json`, `migration_v02_desktop.json` y `clean_v02.json`. Detalles en [auditoria_v0_2.md](auditoria_v0_2.md). La copia aislada se instaló desde archivos fuente de trabajo; no fue un clon del commit final ni una prueba en Windows recién instalado.

Pendientes para cerrar la versión: guardar una candidata identificable, ejecutar su CI remota tras comprobar los límites de GitHub Actions y completar la prueba sostenida de 48 horas. El workflow está preparado solo para ejecución manual; esta sesión no lo ha subido, disparado ni registrado como superado. Tampoco se ha programado una tarea de seguimiento de 48 horas. El código y documentos de esta consolidación permanecen como cambios locales pendientes de guardar/subir; comprobar Git antes de continuar.

## Documentos y publicación

- `README.md`: uso y arranque.
- `docs/hoja_de_ruta.md`: versiones previstas y orden vigente.
- `docs/plan_v0_2.md` y `docs/auditoria_v0_2.md`: alcance, criterios y evidencia de consolidación.
- `docs/operacion_windows.md`: instalar, actualizar, iniciar, detener y recuperar.
- `docs/ejecucion_remota_movil.md`: viabilidad y alcance propuesto de REMOTE-001/MOBILE-001, todavía sin implementar.
- `CHANGELOG.md`: cambios sin publicar y entregas anteriores.
- `docs/version_0_1.md`: alcance implementado y limitaciones.
- `docs/atlas_quant_diseno.md`: especificación objetivo completa, 20 secciones.
- `output/pdf/atlas_quant_diseno.pdf`: diseño en PDF, 22 páginas; no es la especificación del alcance ya implementado.
- `docs/backlog_planificacion.md`: gráficos y aprendizaje pendientes.
- `docs/insumos_*` y `docs/base_diseno_quant.md`: material preparatorio, no reemplaza el diseño definitivo.

El PDF móvil se publicó en un sitio privado independiente, enlazado desde README. `pdf-mobile/` es otro repositorio Git y no forma parte del clon principal. El archivo local `frontend/.openai/hosting.json` sí es necesario: contiene valores nulos de configuración y lo importa Vite. No eliminarlo por confundirlo con la publicación del PDF.

El generador `tools/render_design_pdf.py` necesita ReportLab/pypdf y fuentes de Windows que no forman parte de la instalación del motor. Leer el PDF existente no requiere regenerarlo.
