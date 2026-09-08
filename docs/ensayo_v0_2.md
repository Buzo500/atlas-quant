# Ensayo sostenido de la candidata v0.2

`tools/soak_atlas.py` recoge evidencia local de **48 horas** sobre una instancia ya arrancada. Es una herramienta de validación, no una función del motor ni un servicio Windows. No arranca, detiene, reinicia o modifica ATLAS; solo consulta HTTP local y SQLite en una transacción de lectura. No cambia el plan de energía. Necesita mantener el PC despierto y el monitor funcionando.

La opción explícita `--keep-awake` solicita a Windows mantener el sistema despierto mientras vive el monitor mediante `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)`. La solicitud se libera al terminar, parar o fallar el monitor, y Windows la elimina al terminar su hilo/proceso. No mantiene la pantalla encendida, modifica ajustes permanentes ni impide una suspensión manual; esta última invalidaría el ensayo por el hueco observado. Si Windows rechaza la solicitud, el ensayo falla antes de tomar muestras. El resumen registra la opción y si la solicitud sigue activa.

La demo existente es adecuada si sus experimentos ya están en observación: datos sintéticos, sin fuentes de red, proveedor `none`, presupuesto/gasto/reserva cero, sin cuenta paper y parada global activa. Durante el ensayo, consultar la interfaz es compatible; cambiar cartera, conjuntos, controles, experimentos o código invalida la referencia. El paso natural de `observing` a `completed` está permitido. No es una prueba de rentabilidad, de carga máxima ni de recepción de nuevas sesiones de mercado.

## Criterios fijados antes del arranque

| Medida | Criterio |
|---|---|
| Duración | 172.800 segundos de intervalos observados consecutivos; 2.881 muestras aproximadamente. |
| Muestreo | Cada 60 segundos; un hueco superior a 90 segundos invalida el ensayo. Diferencia entre reloj civil y monótono superior a 5 segundos también. No sumar horas de suspensión o de monitor perdido. |
| Identidad | Mismo commit Git con árbol limpio, versión API, `run_id` y procesos identificados por PID y fecha de creación del sistema. |
| Salud | API directa y proxy saludables; HTML y recurso compilado responden; estado y carteras por API accesibles. Cualquier fallo observado invalida el ensayo. Esto no sustituye recorridos interactivos en navegador. |
| Datos | Hash coherente de conjuntos, versiones, ledger, controles y contenido económico de experimentos en cada muestra. Auditoría anterior íntegra. `integrity_check` al comenzar y cada 15 minutos. Se permite variar solo metadatos operativos de observación/finalización. |
| Costes y controles | Todos los experimentos con proveedor `none`, presupuesto/gasto/reserva cero y paper desactivado; ninguna fuente conectada, proveedores sin claves y parada global activa. |
| Recursos | Suma de RSS de supervisor/motor/interfaz y descendientes Windows (incluidos intérpretes tras redirectores `.venv`, sin duplicar PID) ≤4 GiB, crecimiento respecto a la primera muestra ≤1 GiB y CPU normalizada al total de procesadores lógicos ≤80%. Incumplir alguno durante 5 muestras consecutivas invalida el ensayo. No se mide la GPU ni se afirma que participe. |
| Logs y disco | Ninguna línea nueva reconocida como `ERROR`, `FATAL`, `Error:` o traceback; sin truncamiento; crecimiento total ≤512 MiB, lectura incremental ≤8 MiB por archivo/muestra y espacio libre ≥1 GiB. La búsqueda de patrones no sustituye investigar una incidencia. |
| Copias | Última copia automática con antigüedad ≤25 h, manifiesto/hash/integridad y contenido económico verificados. Al menos una copia nueva durante las 48 h; una copia anterior al arranque del monitor no cubre este requisito. |

Los límites son criterios operativos de esta candidata en el sobremesa, no garantías universales de rendimiento. Las muestras incluyen mediciones, estado del supervisor y errores; no contienen claves ni contenido de logs. Se guardan en `output/validation/soak-…/samples.jsonl`, con resumen atómico en `summary.json`, ambas rutas ignoradas por Git.

## Iniciar el monitor

Primero cerrar los cambios en un commit, comprobar Git limpio y arrancar ATLAS. La versión estable no se publica todavía. Desde PowerShell en la raíz, usar un nombre de salida nuevo y sin espacios:

```powershell
$atlasCandidate = git rev-parse HEAD
$atlasRuntime = Get-Content .\var\runtime.json -Raw | ConvertFrom-Json
$atlasSoakOutput = 'output/validation/soak-candidata-01'
Start-Process -FilePath (Resolve-Path .\.venv\Scripts\python.exe).Path -ArgumentList @('-u', 'tools/soak_atlas.py', 'run', '--candidate', $atlasCandidate, '--run-id', $atlasRuntime.run_id, '--output', $atlasSoakOutput, '--keep-awake') -WorkingDirectory (Get-Location).Path -WindowStyle Hidden -RedirectStandardOutput .\output\validation\soak-monitor.stdout.log -RedirectStandardError .\output\validation\soak-monitor.stderr.log
```

El monitor crea su carpeta de evidencia y rechaza reutilizar una existente. Verificar después que su estado es `running` y hay muestras correctas. No basta con que `Start-Process` haya devuelto un PID. La herramienta también se puede ejecutar en primer plano con los mismos argumentos; el terminal tendría que permanecer abierto.

Consultar y solicitar la parada del **monitor**:

```powershell
.\.venv\Scripts\python.exe tools\soak_atlas.py status --output output/validation/soak-candidata-01
.\.venv\Scripts\python.exe tools\soak_atlas.py stop --output output/validation/soak-candidata-01
```

La parada del monitor no detiene ATLAS y deja el ensayo incompleto. Para detener ATLAS se usa `Stop-Atlas.ps1`; hacerlo durante el ensayo invalida su continuidad. Un monitor perdido o sin muestras recientes se muestra como `monitor_lost_or_stale`, aunque su último JSON dijera `running`. No se reanuda una evidencia interrumpida: conservarla y comenzar un ensayo nuevo tras resolver la causa.

## Cierre y revisión posterior

Tras superar la duración y los criterios, el único resultado satisfactorio del monitor es `completion_requires_restart_check`. **No significa v0.2 estable**. Registrar por separado una parada limpia y reinicio de la misma candidata, comprobar salud/UI y comparar el hash persistente, auditoría previa y carteras con `persistence_baseline` y la última muestra. El resumen conserva `restart_check: pending` hasta que esa revisión externa quede documentada; leer el estado no ejecuta ni certifica el reinicio.

Si el proceso termina, los datos cambian o falla un criterio, conservar `summary.json`, JSONL y los logs del supervisor antes de corregir o arrancar otra instancia. No hay recuperación automática ni promesa de notificación: cualquier seguimiento programado debe configurarse de forma explícita en la tarea.
