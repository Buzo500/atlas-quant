# ATLAS Quant · Operación en Windows

Guía actualizada el 8 de septiembre de 2026 para esta instalación local. La candidata **v0.2.0-rc.2 está en preparación**; rc.1 se conserva como referencia histórica. La [PR #1](https://github.com/Buzo500/atlas-quant/pull/1) está fusionada en `master`, commit `e1f6e020a1d75a81bff97eefcbebe726d47bcdb3`. La nueva CI y la comprobación del escalado físico de Windows al 125 % y 150 % siguen pendientes. El ensayo de 48 horas y su seguimiento continúan aplazados. Esta guía no constituye el cierre de v0.2; el estado de validación está en [CONTINUIDAD](CONTINUIDAD.md) y los criterios pendientes, en el [plan de v0.2](plan_v0_2.md).

El recorrido habitual usa Windows nativo, el motor Python y la interfaz compilada. No necesita WSL, CUDA, claves de API ni presupuesto de pago. El modo de ejecución sigue siendo exclusivamente simulado.

Validación local de rc.2 previa a CI: 446 pruebas Python y 91 subtests, 140 pruebas de interfaz y cinco E2E superados; comprobaciones de tipos, contratos, lint, dependencias y compilación correctas. La base habitual conserva el contenido de su copia de referencia. ATLAS normal y el entorno manual están detenidos en este punto; CI, etiqueta rc.2 y escalado físico siguen pendientes. El control de Windows bloqueó el intento de cambiar la escala al no identificar una URL de confianza; no se alteró el 100 % observado. Evidencia y límites en [candidata_v0_2.md](candidata_v0_2.md).

## Iniciar, consultar el estado y detener

Abre PowerShell y sitúate en la carpeta del proyecto:

```powershell
cd C:\Users\lulae\Documents\Personal\Proyectos\atlas-quant
```

También puedes hacer doble clic en `Abrir-ATLAS.cmd` y usar `Detener-ATLAS.cmd` para cerrar ambos servidores. Los dos accesos están en la raíz del proyecto.

Para iniciar en segundo plano y abrir el navegador desde PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-Atlas.ps1 -OpenBrowser
```

El comando espera a que el motor y el proxy respondan correctamente y la página principal devuelva HTTP 200. Si ya existe una instancia saludable, utiliza esa instancia. La interfaz se abre en [http://127.0.0.1:3000/](http://127.0.0.1:3000/); el motor escucha en `127.0.0.1:8000`. Ambos puertos son locales.

Para consultar el estado:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Status-Atlas.ps1
```

Devuelve un objeto JSON. `running` indica que la instancia tiene el bloqueo y responde a las comprobaciones de salud. `starting` y `stopping` son estados transitorios; `unhealthy` indica que una comprobación ha fallado; `failed` conserva el error del lanzador; `stopped` indica que ya no mantiene el bloqueo. El comando devuelve código de salida 0 únicamente para `running`: un código 1 acompañado de `stopped` puede significar simplemente que ATLAS está apagado. Los PID y otros campos conservados describen la última ejecución y no acreditan por sí solos que siga activa.

Para detener motor e interfaz:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-Atlas.ps1
```

El comando solicita la parada de esa instancia y espera su cierre. Repetirlo cuando ATLAS ya está detenido es seguro. Cerrar la pestaña del navegador deja la aplicación funcionando.

También puedes ejecutar el lanzador en primer plano y detenerlo con Ctrl+C:

```powershell
.\.venv\Scripts\python.exe tools\run_atlas.py --open
```

La opción `ExecutionPolicy Bypass` de los ejemplos afecta únicamente al proceso PowerShell que ejecuta cada script; no cambia la política permanente de Windows.

## Instalar o reconstruir dependencias

Requisitos comprobados por el instalador: Python **3.12 o posterior**, Node.js **22.13 o posterior** y pnpm **11.19.0** en PATH. En este sobremesa se han usado Python 3.14.4, Node 24.15.0 y pnpm 11.19.0. Estas versiones observadas no equivalen a una matriz completa de compatibilidad.

Puedes consultar las versiones disponibles en una ventana nueva de PowerShell:

```powershell
python --version
node --version
pnpm.cmd --version
```

Con ATLAS detenido, ejecuta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-Atlas.ps1
```

El instalador crea `.venv` si falta, instala los paquetes de `requirements.txt`, comprueba sus dependencias, instala la interfaz con `pnpm-lock.yaml` congelado y la compila. Necesita acceso a los registros de paquetes para descargar dependencias; no configura proveedores de IA ni hace llamadas pagadas. Si ya existe una base, crea una copia en `backups/before-update/` antes de modificar la instalación. El mismo bloqueo impide instalar mientras ATLAS está en ejecución; también se rechazan los puertos ocupados.

Solo continúa con el arranque si el instalador termina correctamente. Una instalación fallida no marca como válida una compilación incompleta.

Si únicamente has cambiado código de la interfaz y las dependencias siguen instaladas, puedes reconstruirla con ATLAS detenido:

```powershell
.\.venv\Scripts\python.exe tools\build_frontend.py
```

Para comprobar la compilación sin reconstruirla:

```powershell
.\.venv\Scripts\python.exe tools\build_frontend.py --check
```

El lanzador compara los archivos fuente y los artefactos con el manifiesto de compilación. Una compilación ausente, modificada o desactualizada bloquea el arranque e indica cómo reconstruirla.

## Validación E2E aislada

Este recorrido abre Chromium contra la interfaz compilada y la API real. Requiere las dependencias fijadas de frontend ya instaladas y **ATLAS detenido**. Ejecuta los comandos desde la raíz del proyecto. El recorrido usa los puertos locales 3000 y 8000 y rechaza una instancia existente; no la reutiliza ni la detiene para hacer pruebas.

Detén ATLAS y, cuando termine correctamente, genera la compilación y su manifiesto:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-Atlas.ps1
.\.venv\Scripts\python.exe tools\build_frontend.py
```

Prepara Chromium la primera vez, o cuando cambie la versión fijada de Playwright. La descarga se guarda dentro del proyecto, en `var/playwright-browsers`, y necesita conexión a Internet. No configura proveedores ni consume API de pago:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PWD 'var\playwright-browsers'
node frontend/node_modules/@playwright/test/cli.js install chromium
```

Después de una compilación e instalación correctas, ejecuta:

```powershell
.\.venv\Scripts\python.exe tools/run_e2e.py
```

El ejecutor crea una carpeta nueva `var/validation/e2e-UUID` y una base vacía en su subcarpeta `data`. No carga `.env`, no hereda claves de proveedores y no reutiliza `var/atlas` ni una base de otra prueba. Comprueba datos sintéticos, proveedor `none`, presupuesto, gasto y reserva **0 USD**, sin fuentes externas ni simulación automática. Los experimentos de prueba tienen una duración configurada de una hora y se cancelan al terminar el recorrido; no se espera esa hora ni se inicia el ensayo de 48 horas.

La salida identifica la carpeta de evidencia, con `run.json`, registros de los servidores y de Playwright. El ejecutor cierra sus procesos, comprueba la liberación de los puertos y contrasta que los archivos de la base habitual no han cambiado. Un código de salida 0 indica que el recorrido terminó correctamente; revisar el resultado y los registros si falla. Las carpetas de evidencia y los binarios de Chromium quedan fuera de Git.

Estas pruebas no certifican por sí solas el escalado físico de Windows. La revisión al 125 % y 150 % se registra por separado; cambiar únicamente el viewport o la escala simulada de un navegador no sustituye esa comprobación. El recorrido E2E tampoco reactiva el seguimiento ni reemplaza la prueba sostenida aplazada.

## Actualizar el código conservando los datos

No hay actualizador automático ni un script `Update-Atlas.ps1`. `Install-Atlas.ps1` aplica las dependencias y compilación del código que ya esté en esta carpeta; no descarga cambios de GitHub.

1. Detén ATLAS y espera la confirmación de cierre.
2. Crea una copia manual con el comando del apartado siguiente. Guarda su ruta y el commit de partida, que puedes consultar con `git rev-parse HEAD`.
3. Revisa `git status --short`. Conserva tus cambios pendientes antes de descargar código. En GitHub Desktop usa **Fetch origin** y **Pull origin**; si trabajas con Git en PowerShell y tu rama ya tiene seguimiento, `git pull --ff-only` descarga solo una actualización sin crear una mezcla automática de historiales. Si hay conflictos o divergencia, resuélvelos antes de continuar.
4. Ejecuta `Install-Atlas.ps1`. Si existe la base, generará además su propia copia previa en `backups/before-update/`.
5. Inicia ATLAS, consulta el estado y comprueba en la interfaz que conserva cartera, conjuntos y experimentos. Revisa el resultado del arranque antes de crear trabajos nuevos.

La base se guarda en `var/atlas/atlas.sqlite3`, fuera de Git. La actualización del código no debe sustituirla. Tampoco copies `.venv` o `frontend/node_modules` desde otro equipo: se reconstruyen localmente. Conserva `frontend/.openai/hosting.json`, necesario para la compilación local.

El esquema actual se identifica con `user_version=1`; la base de v0.1 sin versión explícita usa 0 y se reconoce al abrirla. Los esquemas futuros no admitidos se rechazan. Volver a un código anterior puede requerir restaurar una copia compatible: conservar el código y la copia del mismo punto permite preparar esa recuperación. No mezcles bases ni reemplaces archivos SQLite de una instancia activa.

## Copias de seguridad

Para crear una copia manual, incluso con el motor activo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Backup-Atlas.ps1
```

El resultado muestra la ruta completa, con el formato `backups/atlas-FECHA-ID/`. Cada carpeta publicada contiene `atlas.sqlite3` y `manifest.json`. Se utiliza la API de copia de SQLite, que incluye las transacciones confirmadas aunque estén en WAL; no se copia aisladamente el archivo principal de una base activa. La publicación se realiza después de verificar integridad, tablas, contenido JSON, versión, tamaño y SHA256.

Las copias incluyen el estado de la base, sin leer `.env` ni copiar claves del entorno. La base puede contener información personal de cartera e investigación. El SHA256 detecta alteraciones o corrupción, pero no cifra ni firma la copia.

La política vigente es:

| Ubicación | Cuándo se crea | Retención |
|---|---|---|
| `backups/automatic/` | Al arrancar si ya existe una base; después, cada 24 horas mientras el lanzador sigue activo. | Se conservan las 7 copias válidas más recientes por fecha del manifiesto. |
| `backups/` | Con `Backup-Atlas.ps1`; también antes de sustituir una base durante una restauración. | Sin borrado automático. |
| `backups/before-update/` | Antes de instalar o actualizar dependencias si existe la base. | Sin borrado automático. |

En una instalación sin base todavía, la primera copia automática llega tras crear la base y cumplir el siguiente intervalo, o en el siguiente arranque. El intervalo no es una tarea programada de Windows: ATLAS debe permanecer funcionando. La retención solo se aplica tras publicar una copia automática correcta; ignora carpetas desconocidas, enlaces y copias inválidas. Esas entradas pueden ocupar espacio adicional a las siete copias conservadas.

Si una copia obligatoria o su retención falla, el lanzador comunica el error y no continúa operando como si hubiera una copia correcta. Revisa el estado, el espacio y los permisos antes de volver a iniciar.

Estas carpetas están excluidas de Git. **Una copia en el mismo disco permite recuperar un estado anterior, pero no protege de la pérdida de ese disco.** Para esa cobertura, conserva también carpetas completas de copias ya verificadas en otro soporte. Las copias manuales y previas a actualización se acumulan; revisa su espacio y conserva los puntos que necesites.

## Verificar y restaurar una copia

Usa la ruta completa que devolvió la creación de la copia. El argumento es la **carpeta** que contiene ambos archivos, no el archivo SQLite suelto. Por ejemplo, prepara una variable sustituyendo su valor:

```powershell
$atlasBackup = 'PEGA_AQUI_LA_RUTA_COMPLETA_DE_LA_COPIA'
.\.venv\Scripts\python.exe tools\backup_atlas.py --verify $atlasBackup
```

La verificación no restaura datos ni requiere detener el motor. Si falla, conserva la copia y revisa el error; no edites el hash para forzar su aceptación. Las copias antiguas hechas manualmente sin este manifiesto necesitan un procedimiento de recuperación separado.

Para restaurar una copia verificada:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-Atlas.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Restore-Atlas.ps1 -BackupPath $atlasBackup
```

Ejecuta la segunda línea únicamente después de que la parada termine correctamente. `-BackupPath` autoriza expresamente sustituir la base local. La restauración adquiere el bloqueo de instalación y se rechaza si alguno de los puertos está ocupado. Comprueba el manifiesto y prepara el estado restaurado antes de tocar el destino; si existe una base de destino, primero guarda una copia coherente y comunica su ruta en `pre_restore_backup`. No borra WAL pendientes a ciegas.

La recuperación conserva datos y saldos, pero aplica estas medidas operativas:

- Los experimentos activos quedan **pausados**, sin propietarios de ejecución del proceso anterior. Las observaciones seguras pueden reanudarse explícitamente. Una investigación interrumpida no se repite, y una reserva de API sin resolver bloquea la reanudación.
- Se conserva el gasto y la reserva de API; no se libera presupuesto pendiente automáticamente.
- La parada global queda activada, `auto_paper` se desactiva y se cancelan las órdenes simuladas pendientes. No se liquidan posiciones.
- Las fuentes automáticas de datos quedan desconectadas; su configuración se conserva en el registro restaurado. No vuelven a descargar al arrancar. Esta entrega no incorpora un botón específico para reactivar esa configuración guardada.

Después, inicia ATLAS y revisa la cartera y cada experimento antes de reanudarlo. La restauración no arranca el programa ni realiza llamadas a proveedores. Tampoco recupera `.env`: las claves pertenecen a la configuración local de cada equipo.

## Diagnóstico y límites de operación

La pausa y cancelación se guardan aunque haya un cálculo en curso. La interfaz indica que está cerrando esa operación y no permite reanudar hasta terminarla. Una petición de IA ya enviada puede terminar y contabilizarse; no empieza la siguiente fase mientras permanezca pausado/cancelado. La parada global controla la simulación, no cancela la investigación. Detalle y pruebas en [consolidacion_core.md](consolidacion_core.md).

El motor protege un único ejecutor por base también cuando se lanza directamente. La restauración comprueba esos bloqueos además del lanzador. No aumentar workers ni compartir SQLite en red para intentar repartir trabajo entre equipos.

Los registros están en `var/logs/`: `backend.log`, `frontend.log` y un `launcher-ID.log` por arranque en segundo plano. `var/runtime.json` conserva el último estado del lanzador, errores y datos de la última copia automática. Cada ejecución terminada guarda además `var/logs/runtime-<run_id>.json`; los logs de ambos servidores marcan el inicio con ese identificador y hora UTC. Conservar ese snapshot ante un fallo, incluso después de reiniciar. Puedes consultar, por ejemplo:

```powershell
Get-Content .\var\logs\backend.log -Tail 50
Get-Content .\var\logs\frontend.log -Tail 50
```

Un puerto ocupado provoca un rechazo sin matar el proceso ajeno. Si otro servidor se cae, el supervisor detiene la instancia completa. Tres comprobaciones de salud consecutivas fallidas también provocan la parada. La recuperación requiere revisar el error y volver a iniciar; no hay un bucle de reinicios automáticos que repita trabajos.

Utiliza estos lanzadores para arrancar y detener: comparten el bloqueo que protege instalación y restauración. No borres archivos de bloqueo para intentar forzar una operación mientras otro proceso trabaja.

No hay servicio Windows, autoinicio al encender el PC ni funcionamiento durante suspensión o apagado. Los registros y las copias sin retención pueden seguir creciendo. La aplicación mantiene presupuesto inicial cero, proveedor sin IA disponible y operativa simulada; esta mejora de fiabilidad no incorpora gráficos del backlog, aprendizaje, integración con bróker ni órdenes reales.
