# Candidata v0.2.0-rc.1

Preparación autorizada el 6 de septiembre de 2026. **No es una entrega estable.** El código de motor, OpenAPI, salud e interfaz usa `0.2.0-rc.1`; la etiqueta de candidata identifica el commit que se valida. No confundir esta etiqueta con `v0.2.0`, que requiere cerrar H5/H6.

**Actualización del 8 de septiembre:** la CI de `ef75b7b` pasó, pero el ensayo falló tras 3.900 segundos válidos por agotamiento de archivos abiertos en el supervisor. Se corrigen las conexiones de comprobación HTTP en `codex/fix-local-health-resources`; la etiqueta original permanece intacta. El usuario ha aplazado expresamente el siguiente ensayo y el seguimiento sigue pausado. Posteriormente se recompiló la interfaz y arrancó ATLAS para uso normal. Detalle vigente en [CONTINUIDAD.md](CONTINUIDAD.md).

**Frontend del 08/09/2026:** aplicado el rediseño crema y cobre con autorización del usuario. Las comprobaciones locales de [frontend_crema_cobre.md](frontend_crema_cobre.md) corresponden al árbol modificado, no al SHA de la CI anterior. Identificar y validar de nuevo la candidata que incluya estos cambios antes de repetir el ensayo. No se ha iniciado otro seguimiento ni publicado una versión estable.

## Recorrido de cierre

**CI vigente superada:** `3f1d990ac15c391e638302828d1a720d99d78003`, rama `codex/fix-local-health-resources`, [ejecución 34241300060](https://github.com/Buzo500/atlas-quant/actions/runs/34241300060), del 08/09/2026. El checkout y el resultado del workflow corresponden a ese SHA: 421 pruebas Python y 91 subtests (19,01 s), 126 pruebas de interfaz (37,77 s), instalación limpia, build con manifiesto, TypeScript, contratos, lint, arranque, smoke sintético y parada correctos. No se cambia la etiqueta original. Los commits posteriores que solo registran esta evidencia no modifican las fuentes validadas.

La consolidación posterior del frontend añade pruebas y modifica los contratos de movimientos, investigación manual y ajustes. Su [validación local](frontend_consolidacion.md) incluye revisión de navegador y conservación de la base del sobremesa; la CI comprueba el recorrido HTTP, sin automatizar navegador. H5 dispone de CI para la revisión actual; **H6 y el ensayo de 48 horas continúan aplazados**. El recorrido original de preparación se conserva a continuación como referencia; no autoriza iniciar ahora el ensayo.

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
