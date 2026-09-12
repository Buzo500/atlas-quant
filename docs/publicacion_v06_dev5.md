# Publicación de v0.6 dev.5 · 12/09/2026

«Haz el 2» autoriza subir la rama y ejecutar CI gratuita. No incluye nueva PR,
fusión, etiqueta, revisión manual, ensayo o cambios en el programa.

Rama `codex/v0.6-evaluador` subida de `3211b42` a
`6dd01cec456793b506f7f6f44fb4700f60bed6ab`; coincidencia exacta con origin
comprobada. Versión **0.6.0-dev.5**, esquema 5. [Alcance y pruebas locales](v0_6_robustez_implementacion.md).
La app y su base habituales no se han arrancado ni modificado durante esta publicación.

## CI autorizada

[Validar ATLAS en Windows #32](https://github.com/Buzo500/atlas-quant/actions/runs/34707688577),
job `103590615138`, disparo manual `workflow_dispatch` sobre `6dd01ce` a las
17:15 UTC del 12/09. Node 24.21.0 y Python 3.14.4 fijados por el workflow.
**Correcta**, finalizada a las 17:25:51 UTC, primer intento, sin reejecuciones.
Código acreditado: `6dd01ce`; el cierre posterior solo cambia Markdown.

- **1.064 Python + 91 subcasos**, 328 frontend y ocho Node, todos correctos.
  Se conservan dos advertencias de deprecación ya conocidas de Starlette/httpx.
- Instalación/compilación, TypeScript, contratos y lint correctos. La sonda HTTP
  completa 3.632 conexiones, cero fallos, en 30,521 segundos con Node 24.21.0.
- **24/24 E2E** en 3,1 minutos. Run aislado
  `e2e-0dbd4aeee0824238a9df110c5731543d`; backend/frontend salen con código 0,
  sin fallo de propietario ni parada forzada, integridad `ok`, puertos liberados
  y base habitual del runner intacta.
- Arranque y recorrido sintético posteriores: salud `0.6.0-dev.5`, interfaz HTTP
  200 y proxy verificado, gasto de IA 0; parada de ambos servidores correcta.
  Estas comprobaciones pertenecen al runner, no a un nuevo arranque en este PC.

Captura API: 1.816 peticiones correlacionadas y 56 grupos de incidencia; 52 tienen
error/finalización incompleta y seis superan un segundo (dos aparecen en ambos
conjuntos). Cuatro de los seis completan el cuerpo; dos no registran final de proxy.
Máximo registrado 1.333,30 ms, incluido un cálculo de reproducción estadística
de 1.301,84 ms. Sin truncamiento de esta captura ni reproducción de la espera
histórica de diez segundos. No se confirma su causa ni se cambian timeouts.

Log completo conservado localmente, excluido de Git:
`output/validation/ci-34707688577.log`. Los números anteriores proceden de ese
log y de los estados de los pasos, no de trasladar los resultados locales.

## Presupuesto

Antes de ejecutar: sesión de GitHub, **446,7/2.000 minutos** incluidos y
0/0,5 GB de almacenamiento. 2,68 USD de consumo bruto cubiertos por 2,68 USD
de descuentos, **0 USD facturables**. Presupuesto de Actions **0 USD** con
`Stop usage: Yes` comprobado en la cuenta. No se cambia la facturación.

Después de terminar: **465/2.000 minutos**, 0/0,5 GB; 2,79 USD brutos y 2,79 USD
de descuentos, **0 USD facturables**. El cierre documental no lanza otra CI:
el workflow solo se activa manualmente o para etiquetas rc, no al subir la rama.

## Límites

La CI valida esta ampliación en un runner Windows. No sustituye la revisión
funcional del usuario, una comparación numérica con otro sistema operativo,
la evidencia de mercado o el ensayo aplazado. PR #12 mantiene su aceptación
pendiente según la [decisión de integración](integracion_v06_pr12.md).
Dataset observado suficiente y espera API histórica siguen abiertos.
