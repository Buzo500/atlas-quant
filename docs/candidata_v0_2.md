# Candidata v0.2 · Registro de preparación y evidencia

## Estado actual · 0.2.0-rc.2 en preparación

**Primera CI de rc.2 fallida; PR #2 abierta:** `dff5e24a0ebbce8a1cb0481fd64e47563794e433` está subido a `Buzo500/atlas-quant`. La [CI 34248790750](https://github.com/Buzo500/atlas-quant/actions/runs/34248790750) falló sobre ese SHA: 444 pruebas Python superadas, dos fallidas y 91 subtests en 21,99 s; 140 pruebas Vitest superadas. La [PR #2](https://github.com/Buzo500/atlas-quant/pull/2) sigue abierta. La fusión y la etiqueta `v0.2.0-rc.2` están autorizadas si pasa CI, pero no se han realizado. Código inicial: `e64351c0eb93ce2307be04ce31559c8aa9f3d24b`; documentación: `dff5e24`. El rechazo anterior de la revisión automática se conserva como antecedente, resuelto mediante autorización expresa.

**ATLAS está detenido antes de corregir el test.** La ejecución anterior `0e3cebcbaa5344b0ade7a17071b986bd` había verificado versión rc.2, salud, compilación y conservación de la base habitual; ese resultado se conserva como evidencia del arranque, no como estado activo actual. El escalado físico sigue pendiente y aplazado.

Los dos fallos remotos corresponden al test de aislamiento previo a colección, con y sin directorio heredado. Su comparación textual enfrentaba `store.path`, representado mediante el alias corto de Windows `RUNNER~1`, con la ruta resuelta bajo `runneradmin`: ambas identifican el mismo archivo. Se prepara una corrección exclusiva de la aserción de identidad del archivo, manteniendo la comprobación de aislamiento y sus dos variantes. Los logs y el fallo original no se eliminan. Este primer run no acredita E2E remoto; los cinco E2E superados de la tabla son locales. La repetición de CI se registrará con su nuevo SHA y resultado.

Estado del 8 de septiembre de 2026. Motor e interfaz locales usan **`0.2.0-rc.2`**, en la rama `codex/v0.2.0-rc.2`; **no se declara v0.2 estable**. La [PR #1](https://github.com/Buzo500/atlas-quant/pull/1) está fusionada en `master`, commit `e1f6e020a1d75a81bff97eefcbebe726d47bcdb3`. Se conserva la candidata rc.1 y la trazabilidad de sus resultados. La CI histórica no se atribuye a las fuentes nuevas de rc.2; la nueva etiqueta queda condicionada a superar su CI.

| Comprobación | Estado de este punto |
|---|---|
| Pruebas locales | **446 pruebas Python + 91 subtests** en 38,34 s, dos avisos previos; **140 pruebas Vitest en 15 archivos** en 13,34 s. TypeScript, contratos, lint, `pip check` y compilación con manifiesto correctos. Son resultados locales, no de CI de rc.2. |
| Teclado, foco y anuncios | Correcciones implementadas y cubiertas por pruebas de componentes: destinos de foco persistentes tras importar datos, crear experimentos y confirmar movimientos; respeto al cambio de campo o sección durante una espera; mensaje de éxito del ledger conservado al refrescar la versión. `QueryStatus` mantiene las horas fuera de la región viva y evita anunciar sondeos normales. El E2E automatizado comprueba navegación por teclado y foco visible; no equivale a una auditoría con lector de pantalla. |
| Integración/E2E | **5/5 recorridos superados en 9,6 s**, ejecución `e2e-7e176e2037584e4983d8e2b53428724e`: interfaz compilada, API real y Chromium; salidas de ambos servidores 0, puertos libres, hashes habituales intactos e integridad `ok`. Primer intento fallido antes del navegador conservado; corregida la identificación del intérprete por pertenencia al grupo de procesos propio. |
| Aislamiento de pytest | `conftest.py` fija una base temporal antes de recoger los módulos; dos regresiones verifican la colección con y sin `ATLAS_DATA_DIR` heredado. La suite final usa además un directorio explícito. |
| Conservación de la base habitual | Integridad y contenido completo, esquema, secuencias y 539 eventos de auditoría iguales a `backups/atlas-20260908T151716582043Z-af195afe`. El run E2E correcto registra igualdad de hashes antes/después. La diferencia de archivos WAL/SHM del primer intento tiene una reproducción compatible en copias, sin atribución concluyente de su causa original. |
| Windows 125 % y 150 % | **No validado.** El control de Windows bloqueó la operación porque no pudo identificar una URL de confianza; no se cambió la escala inicial del 100 %. Monitor 1: 2560 × 1440; monitor 2: ultrapanorámico de 3440 píxeles de ancho. Las 35 comprobaciones históricas de viewports CSS no sustituyen el escalado físico. |
| Entorno manual | `e2e-0de1cebd856c4115984403a8086dc09e` detenido con resultado 0, base habitual intacta y puertos libres. No se realizó ninguna interacción de UI manual. |
| CI de rc.2 | [Ejecución 34248790750](https://github.com/Buzo500/atlas-quant/actions/runs/34248790750), **fallida** sobre `dff5e24a0ebbce8a1cb0481fd64e47563794e433`: 444 Python superadas, 2 fallidas y 91 subtests (21,99 s); 140 Vitest superadas. Corrección del test y nueva CI pendientes; E2E remoto no acreditado por este run. |
| H6 / ensayo sostenido | Ensayo de 48 horas y seguimiento aplazados; este bloque no los reinicia. |

Se mantiene presupuesto cero, sin claves ni llamadas de pago. Los registros E2E están en `var/validation/`; se conservan también los intentos fallidos. La apertura SQLite con `mode=ro` creó WAL/SHM en copias y una importación posterior de la aplicación los retiró sin cambiar el contenido. El primer intento no conservó hashes individuales: esta reproducción es compatible con aquella diferencia, pero no demuestra su causa. El cierre actual registra cada hash y falla ante integridad, salidas de servidores o liberación de puertos incorrectas.

## Histórico · Candidata v0.2.0-rc.1

Los apartados siguientes describen la preparación y los resultados anteriores a rc.2. Las versiones, ramas, arranques y CI citados pertenecen a esos momentos; el estado vigente figura arriba.

Preparación autorizada el 6 de septiembre de 2026. **No fue una entrega estable.** El código de motor, OpenAPI, salud e interfaz de esa candidata usaba `0.2.0-rc.1`; su etiqueta identifica el commit validado. No confundir esa etiqueta con `v0.2.0`, que requiere cerrar H5/H6.

**Actualización del 8 de septiembre:** la CI de `ef75b7b` pasó, pero el ensayo falló tras 3.900 segundos válidos por agotamiento de archivos abiertos en el supervisor. Se corrigen las conexiones de comprobación HTTP en `codex/fix-local-health-resources`; la etiqueta original permanece intacta. El usuario ha aplazado expresamente el siguiente ensayo y el seguimiento sigue pausado. Posteriormente se recompiló la interfaz y arrancó ATLAS para uso normal. Detalle vigente en [CONTINUIDAD.md](CONTINUIDAD.md).

**Frontend del 08/09/2026:** aplicado el rediseño crema y cobre con autorización del usuario. Las comprobaciones locales de [frontend_crema_cobre.md](frontend_crema_cobre.md) corresponden al árbol modificado, no al SHA de la CI anterior. Identificar y validar de nuevo la candidata que incluya estos cambios antes de repetir el ensayo. No se ha iniciado otro seguimiento ni publicado una versión estable.

## Histórico · Recorrido de cierre de rc.1 y revisión posterior

**CI histórica superada, previa a rc.2:** `3f1d990ac15c391e638302828d1a720d99d78003`, rama `codex/fix-local-health-resources`, [ejecución 34241300060](https://github.com/Buzo500/atlas-quant/actions/runs/34241300060), del 08/09/2026. El checkout y el resultado del workflow corresponden a ese SHA: 421 pruebas Python y 91 subtests (19,01 s), 126 pruebas de interfaz (37,77 s), instalación limpia, build con manifiesto, TypeScript, contratos, lint, arranque, smoke sintético y parada correctos. No se cambia la etiqueta original. Los commits posteriores que solo registraban esta evidencia no modificaban las fuentes de aquella validación.

La consolidación posterior del frontend añadió pruebas y modificó los contratos de movimientos, investigación manual y ajustes. Su [validación local](frontend_consolidacion.md) incluyó revisión de navegador y conservación de la base del sobremesa; aquella CI comprobó el recorrido HTTP, sin automatizar navegador. H5 disponía de CI para esa revisión; **H6 y el ensayo de 48 horas continuaban aplazados**. El recorrido original de preparación se conserva a continuación como referencia histórica; no autoriza iniciar ahora el ensayo.

1. Guardar y revisar las fuentes en la rama `codex/v0.2.0-rc.1`, conservando `master` y el punto anterior `97520b8`.
2. Ejecutar pruebas, contratos, TypeScript, lint de aplicación y compilación verificada. La suite incluye las regresiones de concurrencia y recuperación, y comprueba que las versiones publicadas por backend e interfaz coinciden.
3. Ejecutar `tools/validate_candidate.py` contra el commit: crea un clon local limpio en una ruta con espacios, instala dependencias fijadas y prueba demo, Laboratorio, controles, proxy y recursos compilados; copias/restauración segura y actualización desde un snapshot histórico de esquema 0. Los datos y logs son independientes y quedan en `var/validation/`.
4. Subir la rama y publicar expresamente `v0.2.0-rc.1`, lo que dispara la CI de Windows. El workflow también permite ejecución manual cuando esté incorporado a la rama por defecto. No se activa con cada push normal ni usa secretos, artefactos de pago, caché remota o proveedores externos.
5. Arrancar la candidata principal y ejecutar el monitor de 48 horas descrito en [ensayo_v0_2.md](ensayo_v0_2.md), con demo, proveedor `none` y gasto cero. El monitor registra el commit y el `run_id`; una caída, suspensión, cambio de fuentes o alteración de invariantes invalida el ensayo.
6. Tras las 48 horas, comprobar parada/reinicio, persistencia y copia final. Revisar la evidencia y los defectos antes de preparar `v0.2.0` y su entrega. No convertir automáticamente un estado del monitor en una publicación estable.

La copia principal no se sustituye ni restaura para validar. Mientras el monitor esté activo, no modificar código, reconstruir, cambiar de rama, importar datos ni operar sobre la demo de prueba. Cerrar la pestaña no interrumpe el ensayo; suspender, apagar o detener ATLAS sí lo invalida. No se modifica el plan de energía ni se instala un servicio Windows.

## CI y presupuesto cero

**Revisión del frontend, 08/09/2026:** el usuario autorizó subir y validar `codex/fix-local-health-resources`, conservando `master` y la etiqueta original. La primera [ejecución de esta revisión](https://github.com/Buzo500/atlas-quant/actions/runs/34240011639), sobre `839f2d3e84b82891bbd062412d7eb69620957491`, falló en tres pruebas de interfaz: dos recorridos excedieron cinco segundos y otro no encontró su selección. Pasaron las otras 123. La parada añadió un error al no existir todavía la instalación. Se conserva este resultado como fallo; la segunda ejecución sobre `3f1d990` valida la corrección y pasa completa. No se ha ejecutado el ensayo sostenido.

La corrección acota las consultas de las pruebas a su propio contenedor y limita workers según CPU disponible. Solo los dos recorridos que caducaron disponen de 15 segundos; no se eliminan aserciones, pruebas ni aislamiento, ni se añaden reintentos. La limpieza de CI se ejecuta cuando se intentó arrancar ATLAS, incluso si ese paso falla o se cancela. No intenta detener una instalación que nunca llegó a arrancar.

Antes de ese run, la página de consumo de Actions mostraba **6,7 de 2.000 minutos usados**, **0 de 0,5 GB de almacenamiento** y **0 USD facturables**. Cuota suficiente para el runner estándar acotado a 20 minutos, sin publicar artefactos ni añadir llamadas pagadas. No se han modificado las opciones de facturación.

Comprobado en la cuenta del propietario antes de la ejecución original del 6 de septiembre: repositorio privado, GitHub Free, **0 de 2.000 minutos** de Actions consumidos, **0 de 0,5 GB** de almacenamiento utilizado y sin método de pago configurado. No se han cambiado datos de facturación, presupuestos ni suscripciones. Según la [documentación de GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-actions), sin método de pago válido el uso se bloquea al agotar la cuota. Esta comprobación no debe asumirse vigente para futuras ejecuciones si cambia la cuenta.

La CI usa un runner estándar `windows-latest` con límite de 20 minutos. Sus resultados deben asociarse a la etiqueta y SHA concretos, sin sustituirlos por los resultados de este PC.

## Incidencia previa

La salida de un servidor registrada durante la consolidación anterior sigue sin causa demostrada. Se revisaron supervisor, bloqueos y propiedad de procesos Windows; no se reprodujeron procesos huérfanos ni se encontró un defecto que permita atribuirla retrospectivamente. Ahora cada arranque marca los logs con `run_id`/hora y conserva su resultado final en `var/logs/runtime-<run_id>.json`, incluso tras otro reinicio.

Cualquier recurrencia invalida el ensayo y requiere conservar ese diagnóstico, resolver el fallo y repetir lo afectado. Un ensayo correcto aporta evidencia operativa, pero no identifica por sí mismo la causa histórica.

## Evidencia

En el sobremesa, antes de fijar el commit: **368 pruebas y 91 subtests superados**, con los dos avisos anteriores de TestClient; contratos, TypeScript, lint de aplicación, `pip check` y compilación con manifiesto correctos. Son 40 regresiones nuevas respecto al bloque de 328: versión coherente, archivo del diagnóstico, validador de recorridos y monitor. No equivalen a una CI remota o a 48 horas transcurridas.

Los resultados detallados quedan fuera de Git en `output/validation/` y `var/validation/`. El registro local `output/validation/candidate_release.json` enlaza commit, pruebas, recorrido independiente, CI y carpeta del monitor. El estado de las 48 horas se consulta mediante `tools/soak_atlas.py status --output RUTA_DEL_ENSAYO`. La ausencia de un resultado o un estado pendiente no cuenta como superado.

La preparación de esta candidata no incorpora McClellan, gráficos nuevos, aprendizaje, acceso remoto, móvil, bróker ni órdenes reales. La deuda de arquitectura documentada se mantiene fuera de este cierre salvo que revele un defecto funcional bloqueante.
