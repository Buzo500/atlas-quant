# API intermitente · comprobación del 11/09/2026

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
