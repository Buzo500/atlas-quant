# v0.6 · Walk-forward con parámetros fijos

Actualización posterior: este bloque se ha subido junto a [sensibilidad y candidatas](v0_6_sensibilidad_candidatas.md) en dev.3. La validación/publicación vigente está en [continuidad](CONTINUIDAD.md); el cierre de abajo conserva lo comprobado al terminar la tarea original.

El usuario autoriza el primer siguiente paso: concretar e implementar la validación
walk-forward. Desarrollo local `0.6.0-dev.2`, misma rama `codex/v0.6-evaluador` y
esquema 5. No amplía la autorización a sensibilidad, registro de candidatas,
datos personales, revisión del portátil, fusión/etiqueta o ensayo de 48 horas.

## Protocolo inicial

- Configuración opcional dentro de un nuevo protocolo de Laboratorio, congelada
  antes de calcular. Los protocolos existentes mantienen sus hashes y resultados.
- Ventana previa móvil de **252 sesiones** y evaluación de **63 sesiones** por
  defecto, ambas configurables. Avance igual al tamaño de evaluación: sus tramos
  no se solapan. Solo ventanas completas; informar de la cola sin evaluar.
- SMA fija, mismos costes y presupuestos en todas las ventanas. La ventana previa
  ofrece una referencia histórica y sus últimos `slow` cierres calientan la SMA.
  No se ajustan parámetros ni se seleccionan candidatos en este bloque.
- Cada evaluación comienza en efectivo. El calentamiento no crea posición ni
  arrastra órdenes: la primera compra exige un nuevo cruce en evaluación y se
  simula en la siguiente apertura. Las cuentas se reinician entre ventanas.
- Comprar/mantener empieza en la primera apertura de evaluación; efectivo no
  genera intereses. Los tres comparten fechas, capital y política de costes.
- Todo sucede dentro del desarrollo. Nunca se leen precios de la prueba final
  al calcular el walk-forward. Repetirlo no abre ni consume esa reserva.

## Criterios iniciales, visibles y configurables

Cada ventana necesita precios y aperturas acreditados, calentamiento completo,
al menos **una ejecución SMA**, retorno neto **no negativo**, retorno al menos
igual al de comprar/mantener y caída máxima de cierre **no superior al 15 %**.
El resumen necesita **tres ventanas**, todas evaluables, y que cumplan los criterios
al menos el **60 %**. Son umbrales iniciales de diagnóstico, no estimaciones de
significación ni autorización de inversión. Deben revisarse para cada investigación.

Los datos incompletos se distinguen del incumplimiento. Se presentan motivos por
ventana, media aritmética de retornos, peor caída y proporción que cumple; no se
concatenan ni capitalizan cuentas independientes como si fueran una cartera continua.
Mínimo dos ventanas para calcular; máximo veinte y 20.000 sesiones procesadas entre
referencias previas y evaluaciones. Continúa el límite global de 2.000 sesiones.

Esta es una evaluación temporal retrospectiva de una estrategia fija dentro del
desarrollo. No certifica datos nunca vistos ni generalización futura. La separación
cronológica y la reserva final siguen el principio de evaluar después del pasado
disponible, recogido en la [documentación de validación temporal de scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-of-time-series-data).
No se instala esa biblioteca ni se introduce un modelo entrenable.

## Uso

1. Prepara la serie nativa EUR y su evidencia según la [guía del Laboratorio](v0_6_laboratorio.md#uso).
2. En **Laboratorio → Simulación SMA con protocolo temporal**, completa el nuevo
   protocolo y marca **Añadir validación walk-forward** antes de guardarlo.
3. Fija sesiones de contexto/evaluación, número mínimo de ventanas, proporción
   exigida, ejecuciones mínimas y caída máxima. El contexto necesita al menos
   `slow + 2` sesiones. Con los valores por defecto hacen falta 378 sesiones de
   desarrollo para calcular dos ventanas y 441 para alcanzar el mínimo diagnóstico
   de tres, además de la prueba final separada.
4. **Congelar y simular desarrollo** guarda desarrollo y walk-forward juntos.
   Consulta tabla, motivos, cola incompleta y **Detalle de la ventana** para ver
   su curva, comparadores y operaciones. Los criterios mostrados son los guardados;
   editar el formulario no cambia un informe anterior.
5. **Comprobar reproducción** verifica también el walk-forward guardado, sin abrir
   la reserva final. La apertura de esa prueba conserva su confirmación explícita.

### Ejemplo ficticio pequeño

`fixtures/v0_6_walk_forward_reference.json` contiene entradas y oráculo numérico.
Los CSV `v0_6_walk_forward_prices.csv`, `v0_6_walk_forward_calendar.csv` y
`v0_6_walk_forward_sessions.csv` permiten revisar el flujo con los formularios.
Mercado `TEST`, zona `UTC`, todas las fechas abiertas ficticiamente. Es material
de pruebas para una base aislada, no evidencia de un mercado observado.

SMA 2/3, capital 1.000 EUR, comisión fija 1 EUR, sin comisión proporcional ni
deslizamiento; contexto/evaluación de 7 sesiones. Desarrollo 01–30/01/2025,
reserva final 31/01–06/02/2025. Produce tres evaluaciones (08–14, 15–21 y
22–28 de enero) y deja dos sesiones en la cola. Cada cuenta compra 99 títulos
a 10 EUR y vende a 8 EUR, con 2 EUR de comisiones: **800 EUR**; comprar/mantener
acaba en **801 EUR**, efectivo en **1.000 EUR**. Retorno medio SMA **−20 %**,
exceso medio **−0,1 puntos porcentuales**, **0/3** ventanas cumplen.

## Verificación local

ATLAS detenido antes de modificar código. Copia previa:
`backups/atlas-20260911T105820889993Z-c20a5e3b`.
La CI anterior 34590252591 valida `e797ca3`, no esta ampliación posterior.

- **961 Python + 91 subcasos**: temporalidad, calentamiento/recuperación, resultado
  numérico independiente, ventanas y límites, datos ausentes, umbrales exactos,
  hashes previos, guardado concurrente, conflicto de evidencia y rollback de auditoría.
- **300 frontend**, **8 Node**, TypeScript, contratos OpenAPI, lint y build canónico
  correctos. Dos avisos de deprecación Python preexistentes, sin fallos.
- **22 E2E** completos en `e2e-c4d7791a582c438db39960ca35bc04e4`: API real, importación,
  configuración, informes, recarga, reproducción y reserva final cerrada en el
  recorrido walk-forward. Anchos 960/1366/3440 px; datos habituales sin cambios,
  integridad `ok`, servidores detenidos y puertos liberados.
- Revisión visual adicional en base aislada `e2e-30c96cd4aa4f42a2a0adbf791588051b`:
  tablas y detalle de curva inspeccionados a esos anchos. Cierre correcto y base
  habitual intacta. Corrección posterior: estado incumplido en ámbar y etiqueta
  del benchmark específica para Laboratorio, conservando la curva anterior.

Evidencias locales: `output/validation/v06-walk-forward-*`. Son pruebas realizadas
en el sobremesa; no constituyen aceptación manual en el portátil ni prueba física
de escala de Windows. No hay nuevas dependencias, servicios de pago ni órdenes.

Medición sintética del límite: 2.000 sesiones de fuente, desarrollo de 1.900,
20 ventanas de contexto 900/evaluación 50 y calentamiento 50; **20.000 sesiones
procesadas** por walk-forward. Desarrollo + validación: **12,110 s** en este
sobremesa mientras corrían otras comprobaciones; informe WF de 122.695 bytes.
Es una medición puntual, no garantía de latencia. Comparación adicional contra
el motor y calculador del commit anterior: informe de desarrollo sin calentamiento
idéntico, incluidos hashes. Evidencia `v06-walk-forward-bound.json`.

La repetición selectiva posterior al ajuste visual (`e2e-0ca3c0d438df4e329825b6ae5117e7a0`)
terminó con 3 recorridos correctos y un timeout de 10 s en GET `/api/state` durante
`ensureDemo`, antes de usar el gráfico nativo. No es un fallo de cálculo walk-forward.
Se conserva como recurrencia de la incidencia intermitente de transporte y no se
oculta ampliando el timeout ni reintentando mutaciones. La base siguió intacta,
servidores cerrados y puertos liberados. Confirmación completa posterior registrada
en el cierre; una ejecución correcta no demuestra que esa incidencia esté resuelta.

## Cierre de esta tarea

Suite E2E completa final **22/22** correcta en
`e2e-7872a710e89941a6874c8ace34e1d4e2`, incluida la navegación gráfica nativa que
había agotado la espera al preparar la demo. Integridad `ok`, base habitual sin
cambios y cierre sin procesos ni puertos retenidos. Tras el ajuste visual también
se repitieron las **300 pruebas frontend**, TypeScript, lint y build, correctos;
la comprobación de contratos y manifiesto compilado pasa.

ATLAS habitual arrancado con run `a2902c6436714915bc3ec7fa1255b5c7`, versión
`0.6.0-dev.2`: salud directa/proxy `ok`, HTML 200, parada global activa, ningún
proveedor configurado. Las **tres carteras y todas las tablas** coinciden con la
copia anterior; esquema 5 e integridad `ok`. Laboratorio habitual vacío: todas las
referencias se ejecutaron en bases aisladas. Evidencias `v06-walk-forward-health.json`
y `v06-walk-forward-data-online.json`.

Código conservado en la rama local; no se ha subido, ejecutado una nueva CI remota,
fusionado PR #12 ni publicado etiqueta. Ensayo, portátil y movimientos personales
siguen aplazados. La primera tarea está implementada; los siguientes pasos son
propuestas, no trabajos iniciados: diagnosticar el timeout de transporte,
publicar/CI gratuita, contrastar un CSV observado, sensibilidad y registro de candidatas.
