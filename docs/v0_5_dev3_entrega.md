# v0.5.0-dev.3 · Revisión y publicación

11/09/2026. El usuario autoriza cinco pasos: revisión manual del cierre v0.5/portátil, PR y CI gratuita, fusión/etiqueta tras revisión, diagnóstico NVIDIA y comenzar el evaluador SMA de v0.6. La implementación nueva se mantiene fuera de la PR de v0.5.

## Revisión técnica y CI

[PR #12](https://github.com/Buzo500/atlas-quant/pull/12) ya existía sobre `ccb4b4ad0883c09fc217307b2ffb8d46e79f8bd4`; se reutiliza y se completa su título/descripción. [CI 34578070191](https://github.com/Buzo500/atlas-quant/actions/runs/34578070191) **correcta sobre ese commit**: 808 Python + 91 subcasos, 294 frontend, ocho Node, tipos/lint/contratos, instalación/build y arranque/parada. E2E **20/20 en 3,9 min**, sin errores de limpieza, base ordinaria intacta e integridad correcta; run remoto `e2e-f8a66515258a45df8a7d9bb8c48aac03`.

Evidencia descargada localmente en `output/validation/v05-dev3-ci.log`. La actualización documental de este cierre solo modifica Markdown, no las fuentes validadas. El ensayo de 48 horas sigue aplazado y no se usa una etiqueta estable.

Coste verificado en la sesión de GitHub: antes 310/2.000 minutos, después 330/2.000; 0/0,5 GB y **0 USD facturables**. Consumo bruto 1,98 USD, descuento 1,98 USD. Presupuesto Actions 0 USD con `Stop usage Yes`; no se cambió la configuración ni se usaron APIs pagadas.

## Revisión manual y decisión de publicación

La matriz del [cierre funcional](v0_5_cierre.md), el [caso guiado](v0_5_ejemplo_guiado.md) y la guía del [comparador](v0_5_comparador.md) están preparados y tienen evidencia técnica. Sigue **pendiente la respuesta del usuario** sobre su aceptación y el resultado de arranque/parada del portátil; no se acredita esa comprobación con las pruebas del sobremesa.

La fusión y la etiqueta de desarrollo están autorizadas dentro de los cinco pasos, condicionadas a la revisión aceptada. La CI ya satisface su condición técnica. No se requiere una segunda autorización genérica de publicación, pero no se atribuye al usuario una revisión que todavía no ha confirmado. Estado de PR, etiqueta y equipo se actualiza en continuidad cuando se complete ese paso.

## NVIDIA y comienzo de v0.6

[Diagnóstico de NVIDIA](diagnostico_nvidia_20260911.md): la salida Yahoo/yfinance anterior al validador sigue sin cierre el 10/09; se rechaza sin alterar los históricos. Ambos conjuntos NVD.DE mantienen v2 hasta 09/09. Calendario, base, disponibilidad y tratamiento de eventos requieren evidencia antes de utilizarlos en investigación acreditada.

Primer bloque SMA implementado aparte en `codex/v0.6-evaluador`, commit local `2dbeb41`: contrato restringido, transición pura, replay/paridad/checkpoint, bloqueo por datos/eventos y guardia temporal de siguiente apertura. **861 Python + 91 subcasos**, incluidos 53 nuevos casos. No forma parte de esta PR ni de su CI; no cambia UI/API, esquema 5 o versión de aplicación dev.3. Todavía no integra simulación económica ni ejecuta operaciones. El usuario ha autorizado esta implementación posterior; sustituye las menciones antiguas a «v0.6 solo definida».

## Operación

ATLAS se detuvo antes de modificar código. Copia previa `backups/atlas-20260911T081309290792Z-36ef7a06`. Todas las pruebas nuevas y la sonda se ejecutan aisladas. No se importan movimientos personales ni se reactivan ensayo/monitor, IA de pago, bróker, móvil/remoto o LaTeX. Comprobación final de base, arranque y rama en continuidad.
