# API intermitente · comprobación del 11/09/2026

Actualización del 12/09: [diagnóstico y corrección de Node](diagnostico_ci_20260912.md).
Un cierre nativo `0xC0000409` de Node 24.15.0 se reproduce con HTTP local sin ATLAS;
se actualiza a 24.21.0 y se refuerza la captura E2E. El job antiguo no conservó
su código de salida: la coincidencia no demuestra su causa exacta. La espera API
histórica sigue abierta. Las entradas siguientes registran la evidencia del 11/09.

## CI dev.4: servidor E2E sin propietario comprobable, causa pendiente

[CI 34610747174](https://github.com/Buzo500/atlas-quant/actions/runs/34610747174),
código `8dadb74`, job 103300338249. **Fallida**, sin reintento. El entorno aislado
`e2e-af41d2b021384cde87a63647412c930a` registra 14 recorridos correctos de 23
antes de abortar con «El puerto 3000 no pertenece al proceso E2E frontend».
El mismo control impide la cancelación por API durante la limpieza. El cierre
final confirma integridad, puertos liberados y base habitual del runner sin cambios;
los pasos posteriores del workflow de arranque/recorrido y parada se omiten.

La condición de `assert_owned` admite proceso terminado, listener ausente o PID
fuera del grupo. El mensaje por sí solo no distingue esas causas. El log retenido
imprime Playwright y el informe correlacionado, pero no el código de salida ni la
cola del log del servidor: **no se puede atribuir el fallo a una excepción concreta**.
No se modifican comprobaciones de propiedad, timeouts ni reintentos.

Captura: 740 peticiones correlacionadas, 12 grupos sin truncamiento; nueve de
error/cancelación y tres con duración de al menos un segundo. Las tres lentas
completan el cuerpo HTTP 200; máximo observado 1.345 ms. Una última lectura de
`/api/state`, `client-5416-287`, falla a los 343,6 ms: consta entrada en proxy,
sin envío upstream ni recepción ASGI correlacionada. No reproduce la espera de
diez segundos y no confirma su causa. Las cancelaciones de pruebas/navegación
tampoco deben clasificarse automáticamente como el fallo histórico.

Siguiente diagnóstico propuesto: retener código de salida y cola acotada de
`frontend.log`/`backend.log`, junto a PID/listener observado, y reproducir en base
aislada antes de corregir. Estos cambios y otra CI no se han ejecutado por la
petición limitada a subir/ejecutar. Evidencia local excluida de Git:
`output/validation/dev4-ci-34610747174.log` y `dev4-ci-publication.json`.

La sonda de salud del PC habitual también obtuvo conexión rechazada en 8000 en
este turno; es una observación local separada, no evidencia del fallo del runner.

## Ampliación dev.4: captura preparada, causa todavía abierta

El nuevo wrapper correlaciona navegador y helper E2E `readApi` con proxy/ASGI,
sin cuerpos ni secretos. Genera `diagnostic-report.json` y lo imprime acotado
en consola. El siguiente workflow autorizado usará el wrapper; esta ampliación
no dispara CI ni monitoriza la base habitual. [Uso y límites](v0_6_prevalidacion_consulta.md).

Recorrido dirigido final `e2e-49871b9dda4744f1917ce89079d45c66`: 3/3 correctos,
186 peticiones correlacionadas. Detecta un HTTP 502 de la sonda de arranque con
ECONNREFUSED antes de comenzar el cliente E2E; no corresponde a la espera original.
Suite completa `e2e-48ea8fb5ecc84a728994ca1c2758ac45`: 23/23 en 1,7 min,
1.769 peticiones correlacionadas, 74 grupos de error/cancelación y cero grupos
con duración de al menos 1 s. Incluye desconexiones/cancelaciones de los recorridos;
no todos los eventos `failed` identifican la incidencia buscada. Sin truncamiento,
integridad/limpieza correctas y base habitual intacta. No se atribuye causa raíz.

Dos pases dirigidos anteriores fallaron por problemas de la nueva UI (desbordamiento
de tabla y filtro vacío HTTP 422), corregidos antes del pase dirigido final y de la
suite completa. No se presentan como fallos del transporte ni como recorridos correctos.

## Comprobación previa dev.3

La espera original sigue abierta: no se ha reproducido en este diagnóstico y no
se atribuye una causa sin evidencia. No se cambia el proxy ni el bucle Python,
no se amplían los tiempos de espera y no se añaden reintentos de mutaciones.
Antecedente: [diagnóstico del 10/09](diagnostico_api_20260910.md).

## Recurrencia que motiva la comprobación

En la revisión de walk-forward, `e2e-0ca3c0d438df4e329825b6ae5117e7a0`
agotó los 10 segundos de GET `/api/state` al preparar la demo, antes de interactuar
con el gráfico. El recorrido completo posterior pasó 22/22; ese pase no acredita
una corrección del transporte.

## Diagnóstico acotado e instrumentado

ATLAS habitual detenido. Bases nuevas y sondas existentes de
`tools/diagnostics/run_api_diagnostic.py`, `api_backend.py` y `api_proxy.cjs`:

| Comprobación | Resultado |
|---|---|
| Navegación gráfica nativa y alternativa | 2/2; 6,2 y 4,6 segundos |
| Solicitudes proxy de ese recorrido | 85; máximo hasta terminar 137,7321 ms |
| Máximo backend de ese recorrido | 129,026 ms |
| 100 carreras entre POST demo, fetch, APIRequestContext y acceso directo | 301 lecturas medidas, todas correctas |
| Máximo del cliente en las carreras | 96,0676 ms |
| Solicitudes proxy instrumentadas durante las carreras | 348; máximo 141,9907 ms |
| Máximo backend durante las carreras | 134,888 ms |
| Solicitudes pendientes a un segundo / errores Node | 0 / 0 en ambos ensayos |

Identificadores: `e2e-07ca0cf1697d4377b9359f574be6cc06` y
`e2e-1388e3a8d68b488fab8f8894b94d878c`. No confundir las 301 lecturas medidas
por el cliente con todas las peticiones instrumentadas por el servidor.
Ambos entornos cerraron con código 0, integridad correcta, puertos liberados y
base habitual intacta. No hay ensayo de 48 horas ni seguimiento automático nuevo.

Evidencia local excluida de Git: `output/validation/v06-five-api-initial.log`,
`v06-five-api-race.log` y
`api-clients-e2e-1388e3a8d68b488fab8f8894b94d878c.json`; trazas por ejecución en
`var/validation/`. Las sondas no registran cuerpos, claves ni cadenas de consulta.

Si vuelve a ocurrir, el siguiente diagnóstico debe correlacionar la misma petición
en cliente, proxy y backend; repetir muchas veces una prueba que pasa no demuestra
la causa ni sustituye esa captura.
