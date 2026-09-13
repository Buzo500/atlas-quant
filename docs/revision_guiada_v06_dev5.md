# Revisión guiada de robustez · v0.6.0-dev.5

13/09/2026, Windows nativo del sobremesa. Recorrido funcional completado con
datos sintéticos; queda un defecto visual del historial en panel estrecho.
No declara estable v0.6 ni acepta la PR #12 de v0.5.

## Comprobaciones

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| Calcular y guardar muestra completa | Correcto: 504 intervalos tras 3 sesiones de calentamiento; bloques 5/10/20, 10 principal; estado Exploratorio | Captura aportada por el usuario del informe de las 15:06:39 |
| Contexto económico, ensayos y método | Revisión realizada | Confirmación del usuario |
| Recuperar tras recargar | Mismo informe, motivo, fecha y valores | Confirmación del usuario y lectura posterior de la interfaz por el agente |
| Reproducción estadística | Mensaje de instantánea y resultado conservados | Usuario pulsa el botón y confirma el mensaje solicitado |
| Muestra insuficiente | No evaluable: 4 intervalos; explica mínimo de 504 y 25 bloques esperados por longitud, sin intervalos estadísticos calculados | Captura y confirmación del usuario del informe de las 15:15:16 |
| Recuperar muestra insuficiente tras recargar | Mismo informe de las 15:15:16, motivo y explicación | Comprobación adicional del agente mediante navegador, sin recalcular |

La media del exceso diario de la muestra completa es −0,010393445904 puntos
porcentuales; las tres bandas incluyen cero. Datos de prueba para revisar el
software: no evidencia observada, rentabilidad esperada o autorización de órdenes.
Las acciones del usuario no se atribuyen a pruebas automatizadas del agente.

## Defecto visual pendiente

El botón «Consultar robustez…» desborda el panel estrecho. Medición de solo lectura
en el navegador integrado, con ancho de contenido de 565 píxeles CSS:

- Panel: 435,35 px; botón: 563,59 px, desde x=65,10 hasta x=628,70.
- Documento: ancho desplazable de 629 px frente a 565 px visibles.
- Estilo calculado del botón: `white-space: nowrap`, `max-width: none`.

El historial en `frontend/features/research/robustness.tsx` usa el `Button`
compartido, cuya base en `frontend/components/ui/button.tsx` incluye
`whitespace-nowrap`. La tabla del informe tiene su desplazamiento propio; el
botón también ensancha el documento. Las comprobaciones anteriores a 960/1366/3440
px no cubrían este panel más estrecho. No se cambió zoom, escala física ni viewport
para esta observación.

Corrección propuesta, aún sin implementar: permitir varias líneas y limitar el
ancho de las entradas de este historial, manteniendo el nombre completo y el
acceso con teclado. Comprobar el caso observado y la muestra completa, con nombres
largos, antes de publicar cambios. No modificar globalmente todos los botones por
este caso sin revisar su alcance.

## Sesiones y cierre

Primera sesión `e2e-d8fc7ecf780a47c8bc9de48f8c3fa904`, 14:30–14:50 aproximadamente:
terminó por el límite de 1.200 segundos antes de que el usuario pudiera revisar.
Recibo correcto, servidores con salida 0 y base habitual intacta.

Al pedir reapertura estaba activo el arranque habitual
`f02eadac431b4a0ea5bf07cbdaee9097`, sin experimentos activos. Se detuvo mediante el
lanzador y se prepararon nuevos casos en otra base aislada, conservando la anterior.

Sesión revisada `e2e-efa0141a11a04f01a1c94729b66e99f1`, desde las 15:04 hasta su
parada cooperativa al finalizar las comprobaciones. Recibo verificado:
`active=false`, `result=0`, ambos servidores con salida 0, sin parada forzada ni
errores de limpieza, `ordinary_database_unchanged=true`, `ports_released=true`,
`integrity=ok`. ATLAS habitual queda detenido. Sin claves, gasto ni nuevas llamadas
a proveedores externos.

Recibos, datos y logs locales excluidos de Git:
`output/validation/dev5-manual-20260913-reapertura.json`, su `.log` y
`var/validation/e2e-efa0141a11a04f01a1c94729b66e99f1/`.
La captura diagnóstica conserva 192 peticiones correlacionadas y dos grupos lentos,
sin fallos declarados en esos grupos ni observación completa del cliente. La causa
no está confirmada; este recorrido no cierra el diagnóstico histórico de la API.

La [continuación posterior autorizada](v0_6_historial_contraste.md) corrige el
historial y verifica el segundo entorno. El párrafo siguiente describe el estado
al acabar la revisión guiada, antes de esa continuación.

Este cierre cambia únicamente documentación local. Sin nueva compilación,
CI remota, subida, PR, fusión o etiqueta. Segundo entorno numérico, datos observados
suficientes y los aplazamientos anteriores conservan su estado.
