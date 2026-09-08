# ATLAS Quant: continuidad entre equipos

Actualizado: 8 de septiembre de 2026. Este documento resume decisiones y estado para una conversación nueva de Codex; no contiene la transcripción completa del chat original.

## Estado actual: rc.2 con CI verificada

**CI de rc.2 superada:** [ejecución 34249730107](https://github.com/Buzo500/atlas-quant/actions/runs/34249730107), sobre `412918b5e9067e44f293b0633068ca932a472d64`. En Windows: **446 pruebas Python y 91 subtests** (22,13 s), **140 Vitest en 15 archivos** (43,86 s) y **5/5 E2E** (18,7 s); instalación limpia, build con manifiesto, contratos, TypeScript, lint, `pip check`, smoke, arranque y parada correctos. E2E remoto `e2e-ea578aac47f341ffac48cd6330edbb5a`: resultado 0, conservación de la base comprobada, integridad `ok` y puertos libres. Este SHA identifica fuentes, pruebas y workflow; el cierre posterior solo modifica documentación.

La integración mediante la [PR #2](https://github.com/Buzo500/atlas-quant/pull/2) y la etiqueta de entrega `v0.2.0-rc.2` siguen el procedimiento autorizado tras superar CI. Este registro no anticipa su fusión o publicación. Se conserva el rechazo previo de la revisión automática como antecedente, resuelto mediante autorización expresa; la validación se ha mantenido dentro de la cuota gratuita.

**ATLAS está arrancado para uso normal**, ejecución `7fa354c2b8d5425fa4818dab68acd8a0`, con salud rc.2 y la misma cartera: tres posiciones y NAV 25.118,66876 EUR. Conserva controles, parada global activada, ausencia de claves y presupuesto/gasto/reserva cero. Los registros del arranque anterior `0e3cebcbaa5344b0ade7a17071b986bd` y de conservación se mantienen como evidencia histórica.

**Motor e interfaz se identifican como `0.2.0-rc.2`, candidata con CI verificada, no v0.2 estable.** Rama de trabajo: `codex/v0.2.0-rc.2`, sobre la [PR #1](https://github.com/Buzo500/atlas-quant/pull/1) fusionada en `master` (`e1f6e020a1d75a81bff97eefcbebe726d47bcdb3`). La candidata rc.1 y sus resultados se conservan como historia.

**Intento remoto fallido conservado:** [CI 34248790750](https://github.com/Buzo500/atlas-quant/actions/runs/34248790750), sobre `dff5e24a0ebbce8a1cb0481fd64e47563794e433`: 444 pruebas Python superadas, dos fallidas y 91 subtests en 21,99 s; 140 Vitest superadas, sin E2E remoto acreditado en ese intento. Fallaban las dos variantes de aislamiento por comparar textualmente el alias Windows `RUNNER~1` y la ruta larga `runneradmin`. La aserción usa ahora `samefile`, conservando el aislamiento: reproducción con ruta corta, dos fallos antes y dos casos correctos después; también pasan las dos variantes con ruta larga. Logs y resultado original intactos.

**Validación local final del bloque:** 446 pruebas Python y 91 subtests en 38,34 s, con dos avisos previos; 140 pruebas Vitest en 15 archivos, en 13,34 s; cinco recorridos E2E en 9,6 s. TypeScript, contratos, lint, `pip check` y compilación con manifiesto correctos. Son resultados del sobremesa, no de CI de rc.2. La suite Python utiliza `ATLAS_DATA_DIR` explícito y, además, un `conftest.py` que aísla el directorio antes de recoger e importar módulos de prueba.

Están implementadas y comprobadas las correcciones de foco al importar datos, crear un experimento y confirmar movimientos; el mensaje de éxito del ledger sobrevive al refresco de versión. `QueryStatus` conserva la hora visible fuera de los anuncios accesibles y anuncia carga inicial, errores, recuperación y reintento sin repetir cada sondeo normal.

**E2E automatizado superado:** `var/validation/e2e-7e176e2037584e4983d8e2b53428724e`, cinco recorridos con interfaz compilada, API real y Chromium, sin respuestas simuladas. Ambos servidores terminaron con código 0, puertos libres, integridad `ok` y hashes de la base habitual conservados. El primer intento falló antes del navegador al comparar el PID del lanzador de Python con el del intérprete; ahora se comprueba pertenencia al Job Object específico del servidor. Se mantienen el resultado y los logs fallidos.

La base habitual tiene el mismo contenido completo, esquema, secuencias y 539 registros de auditoría que la copia `backups/atlas-20260908T151716582043Z-af195afe`, con integridad correcta. En copias aisladas se reprodujo que una apertura SQLite `mode=ro` puede crear WAL/SHM y una importación posterior de la aplicación puede retirarlos sin modificar los datos. Es una explicación compatible con la diferencia de hash del primer intento, **no una atribución concluyente**: aquel registro no conservaba los hashes individuales. El ejecutor registra ahora el inventario de hashes antes y después y rechaza cierres o comprobaciones de integridad incorrectos.

**Escalado físico 125 %/150 % no validado.** La herramienta de control de Windows bloqueó la operación al no poder identificar una URL de confianza; no se cambió la escala. Se observó una escala inicial del 100 %, monitor 1 de 2560 × 1440 y monitor 2 ultrapanorámico de 3440 píxeles de ancho. Las 35 comprobaciones anteriores de viewports CSS no sustituyen esta revisión. El entorno manual `e2e-0de1cebd856c4115984403a8086dc09e` terminó con resultado 0, base habitual intacta y puertos libres; **no se realizó ninguna interacción de UI manual** en él.

El ensayo sostenido de 48 horas y su seguimiento permanecen aplazados. El escalado físico pendiente y el ensayo impiden declarar v0.2 estable; la CI correcta no sustituye esas comprobaciones. Se mantiene presupuesto cero, sin claves ni llamadas pagadas.

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
