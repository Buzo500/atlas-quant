# Candidata v0.2.0-rc.1

Preparación autorizada el 6 de septiembre de 2026. **No es una entrega estable.** El código de motor, OpenAPI, salud e interfaz usa `0.2.0-rc.1`; la etiqueta de candidata identifica el commit que se valida. No confundir esta etiqueta con `v0.2.0`, que requiere cerrar H5/H6.

## Recorrido de cierre

1. Guardar y revisar las fuentes en la rama `codex/v0.2.0-rc.1`, conservando `master` y el punto anterior `97520b8`.
2. Ejecutar pruebas, contratos, TypeScript, lint de aplicación y compilación verificada. La suite incluye las regresiones de concurrencia y recuperación, y comprueba que las versiones publicadas por backend e interfaz coinciden.
3. Ejecutar `tools/validate_candidate.py` contra el commit: crea un clon local limpio en una ruta con espacios, instala dependencias fijadas y prueba demo, Laboratorio, controles, proxy y recursos compilados; copias/restauración segura y actualización desde un snapshot histórico de esquema 0. Los datos y logs son independientes y quedan en `var/validation/`.
4. Subir la rama y publicar expresamente `v0.2.0-rc.1`, lo que dispara la CI de Windows. El workflow también permite ejecución manual cuando esté incorporado a la rama por defecto. No se activa con cada push normal ni usa secretos, artefactos de pago, caché remota o proveedores externos.
5. Arrancar la candidata principal y ejecutar el monitor de 48 horas descrito en [ensayo_v0_2.md](ensayo_v0_2.md), con demo, proveedor `none` y gasto cero. El monitor registra el commit y el `run_id`; una caída, suspensión, cambio de fuentes o alteración de invariantes invalida el ensayo.
6. Tras las 48 horas, comprobar parada/reinicio, persistencia y copia final. Revisar la evidencia y los defectos antes de preparar `v0.2.0` y su entrega. No convertir automáticamente un estado del monitor en una publicación estable.

La copia principal no se sustituye ni restaura para validar. Mientras el monitor esté activo, no modificar código, reconstruir, cambiar de rama, importar datos ni operar sobre la demo de prueba. Cerrar la pestaña no interrumpe el ensayo; suspender, apagar o detener ATLAS sí lo invalida. No se modifica el plan de energía ni se instala un servicio Windows.

## CI y presupuesto cero

Comprobado en la cuenta del propietario antes de la primera ejecución: repositorio privado, GitHub Free, **0 de 2.000 minutos** de Actions consumidos, **0 de 0,5 GB** de almacenamiento utilizado y sin método de pago configurado. No se han cambiado datos de facturación, presupuestos ni suscripciones. Según la [documentación de GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-actions), sin método de pago válido el uso se bloquea al agotar la cuota. Esta comprobación no debe asumirse vigente para futuras ejecuciones si cambia la cuenta.

La CI usa un runner estándar `windows-latest` con límite de 20 minutos. Sus resultados deben asociarse a la etiqueta y SHA concretos, sin sustituirlos por los resultados de este PC.

## Incidencia previa

La salida de un servidor registrada durante la consolidación anterior sigue sin causa demostrada. Se revisaron supervisor, bloqueos y propiedad de procesos Windows; no se reprodujeron procesos huérfanos ni se encontró un defecto que permita atribuirla retrospectivamente. Ahora cada arranque marca los logs con `run_id`/hora y conserva su resultado final en `var/logs/runtime-<run_id>.json`, incluso tras otro reinicio.

Cualquier recurrencia invalida el ensayo y requiere conservar ese diagnóstico, resolver el fallo y repetir lo afectado. Un ensayo correcto aporta evidencia operativa, pero no identifica por sí mismo la causa histórica.

## Evidencia

En el sobremesa, antes de fijar el commit: **368 pruebas y 91 subtests superados**, con los dos avisos anteriores de TestClient; contratos, TypeScript, lint de aplicación, `pip check` y compilación con manifiesto correctos. Son 40 regresiones nuevas respecto al bloque de 328: versión coherente, archivo del diagnóstico, validador de recorridos y monitor. No equivalen a una CI remota o a 48 horas transcurridas.

Los resultados detallados quedan fuera de Git en `output/validation/` y `var/validation/`. El registro local `output/validation/candidate_release.json` enlaza commit, pruebas, recorrido independiente, CI y carpeta del monitor. El estado de las 48 horas se consulta mediante `tools/soak_atlas.py status --output RUTA_DEL_ENSAYO`. La ausencia de un resultado o un estado pendiente no cuenta como superado.

La preparación de esta candidata no incorpora McClellan, gráficos nuevos, aprendizaje, acceso remoto, móvil, bróker ni órdenes reales. La deuda de arquitectura documentada se mantiene fuera de este cierre salvo que revele un defecto funcional bloqueante.
