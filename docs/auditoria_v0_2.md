# ATLAS Quant · Auditoría y avance de v0.2

**Cierre posterior:** preparada la candidata `0.2.0-rc.1`; seguimiento y evidencia del commit en [candidata_v0_2.md](candidata_v0_2.md). Las cifras y el estado del motor citados abajo corresponden al bloque anterior. La condición estable sigue pendiente de sus comprobaciones de cierre.

Fecha: 6 de septiembre de 2026. Base de trabajo: commit `97520b8` (`traslado al sobremesa`), árbol limpio al comenzar. Los cambios descritos se han probado como árbol de trabajo local sobre esa base; no se ha publicado ni etiquetado una versión nueva.

**Actualización posterior:** CORE-001 y los controles concurrentes se han corregido tras la revisión inicial. La [consolidación del núcleo](consolidacion_core.md) registra los cambios, 328 pruebas y 91 subtests superados, contratos, lint de aplicación y validación de la demo. Las 254 pruebas descritas más abajo corresponden al bloque operativo previo; no son la última ejecución de la suite. La escala horizontal sigue fuera del alcance.

## Conclusión de la auditoría

La base v0.1 ya resuelve el recorrido de cartera, laboratorio y experimento sintético. El siguiente trabajo útil es hacer reproducibles la ejecución y la recuperación. El [plan de v0.2](plan_v0_2.md) y la [hoja de ruta](hoja_de_ruta.md) fijan ese alcance.

| Situación de partida | Consecuencia | Cambio implementado |
|---|---|---|
| Inicio en segundo plano sin esperar a la salud de ambos servidores. | Un mensaje de arranque podía preceder a un fallo real. | El lanzador espera API, proxy y página, propaga errores y registra estado. |
| Registro de PID y parada sin propiedad robusta de toda la instancia. | Los registros podían quedar obsoletos y los descendientes sobrevivir al lanzador. | Bloqueo del sistema operativo, archivos de parada por ejecución y Windows Job Object sobre procesos creados por el supervisor. |
| La vida de los dos servidores no se supervisaba como una unidad. | Podía quedar un servidor activo después del fallo del otro. | Salida de un hijo o tres fallos de salud detienen ambos; no se reintentan trabajos automáticamente. |
| Servidor frontend de desarrollo en el uso diario. | Ejecución dependiente del entorno de desarrollo. | Servidor Node compilado en loopback y proxy explícito; comprobación de fuentes y artefactos antes de arrancar. |
| Sin copias automáticas ni recuperación comprobada. | Restaurar dependía de una copia manual de SQLite/WAL. | API de backup SQLite, validación de esquema/contenido, publicación completa, retención y restauración controlada. |
| Esquema sin versión explícita. | No había un punto formal para rechazar incompatibilidad o migrar. | `user_version=1`, adopción transaccional y comprobación de nombres, tipos, nulabilidad y claves primarias. |
| Instalación con comprobaciones mínimas y sin compilación de uso diario. | Era posible actualizar mientras había procesos activos o sin recuperar una compilación válida. | Bloqueo compartido, versiones comprobadas, copia previa, lockfile congelado, `pip check` y build verificado. |
| Sin hoja de ruta operativa ni validación remota configurada. | Los próximos pasos se confundían con el diseño completo. | Versiones, criterios de cierre, guía Windows, changelog y workflow manual sin secretos. |

## Evidencia local del sobremesa

Entorno: Windows 11 Home x64, Python 3.14.4, Node 24.15.0 y pnpm 11.19.0. RTX 3080 de 10 GB presente; esta entrega no utiliza la GPU. WSL y otros sistemas no se han certificado.

- **Pruebas automatizadas:** 254 pruebas y 91 subtests superados; dos avisos ya existentes de deprecación de TestClient. Datos de pruebas aislados en `var/`. Incluyen migraciones, integridad y corrupción de copias, restauración, retención, archivos obsoletos, bloqueo entre procesos, rechazo de compilaciones modificadas y control de descendientes en Windows. Se reprodujo y corrigió además la pérdida de salida de las dependencias al ejecutarlas sin consola; cuatro regresiones comprueban ambos canales y los errores.
- **Interfaz:** TypeScript y compilación verificada correctos. En navegador, la cartera conservó sus tres posiciones y NAV de 25.118,66876 EUR; la comparación de DEMO_BOND devolvió candidatos y sensibilidad a costes, y el informe del experimento existente siguió accesible con gasto y reserva cero.
- **Arranque real:** motor, proxy y página correctos. Repetir inicio mantuvo la misma instancia. La parada confirmó cierre de los puertos 3000/8000 y `forced_stop: false`.
- **Fallo real durante integración:** el primer servidor frontend compilado falló por resolver una exportación ESM mediante CommonJS. El lanzador devolvió fallo y cerró el backend. Se corrigió usando el punto de entrada ESM desde `frontend/local-server.mjs` y se repitió el arranque satisfactoriamente.
- **Actualización de esta instalación:** `Install-Atlas.ps1` creó una copia previa en `backups/before-update/`, instaló y comprobó las dependencias fijadas y reconstruyó la interfaz con resultado correcto. No se cambió la cartera ni los archivos de dependencias fijadas.
- **Copias con la aplicación activa:** se creó y verificó una copia manual sin detener el motor. Los tests de restauración trabajan sobre destinos independientes, conservan importes/IDs y comprueban el bloqueo de ejecución y la conservación de reservas inciertas.

**Instalación limpia y recuperación:** completadas en `var/validation/clean install 37e86b7d`, sobre una copia de las fuentes sin `.venv`, `node_modules` ni base previos. `Install-Atlas.ps1` creó el entorno y compiló; el smoke creó una demo y un experimento sin IA en observación. El doble arranque mantuvo la instancia; la copia se verificó por CLI y la restauración conservó cartera e IDs, dejando el experimento pausado y controles seguros. El HTML sirve recursos compilados sin HMR y el proxy rechazó con HTTP 403 las mutaciones sin cabecera y con origen ajeno. El ciclo funcional duró **24,044 segundos**, con smoke de **1,761 segundos**. Es una prueba en otro directorio del mismo PC, no una instalación en un Windows recién instalado ni un ensayo prolongado.

**Conservación de la base principal:** se comparó con la copia coherente previa al trabajo, todavía con esquema 0. La base actual usa esquema 1; el contenido completo del conjunto conserva el mismo hash, la versión de datos es la misma y no cambian IDs, estado del experimento, proveedor, presupuesto, gasto, reserva ni cuenta paper. Ambas bases superan `integrity_check`. La base principal no se ha restaurado ni sustituido para probar.

Una segunda actualización de la copia aislada, con el helper de salida corregido, volvió a pasar: mensajes de pip/build visibles, hash de base intacto durante instalar y estado conservado tras reiniciar. El ciclo de actualización y comprobación duró 21,177 segundos. La copia terminó detenida sin parada forzada y liberó ambos puertos.

La instalación principal volvió a arrancar invocando `Start-Atlas.ps1` desde otra carpeta. API, proxy, controles y cartera se verificaron de nuevo, incluida su carga final en navegador. Queda funcionando con la demo original y el experimento sin IA en observación.

La evidencia local está en `output/validation/clean_v02.json`, `output/validation/migration_v02_desktop.json` y `output/validation/runtime_v02_desktop.json`, excluidos de Git. El primer punto de recuperación previo al desarrollo es `backups/before-v0.2-20260906T151721Z/`: copia manual mediante SQLite, anterior al formato nuevo con manifiesto. Las copias nuevas publicadas por las herramientas sí incluyen manifiesto.

## Límites y cierre pendiente

- La v0.2 sigue **en desarrollo**. El identificador del motor permanece en 0.1.0 para no presentar esta consolidación como una entrega estable ya cerrada.
- Falta una prueba operativa sostenida de **48 horas**, con salud, recursos, errores, copia automática y persistencia registrados. Los recorridos cortos y las pruebas unitarias no la sustituyen. No se ha iniciado una tarea programada ni un servicio Windows.
- `.github/workflows/validate.yml` prepara instalación, pruebas Python, TypeScript, build y recorrido sintético en Windows. Solo responde a `workflow_dispatch`; no se ha subido ni ejecutado desde esta sesión. Antes de activarlo, comprobar disponibilidad y límites de Actions de la cuenta. No contiene claves ni llamadas pagadas.
- Falta identificar la candidata mediante commit y, tras resolver los pendientes, cerrar los criterios H5/H6 y publicar una etiqueta. La captura de fuentes local de las pruebas no sustituye comprobar el artefacto del commit finalmente publicado.
- Copias y logs están en el mismo equipo; no hay cifrado, copia externa automática, rotación de logs, autoinicio ni recuperación automática de servidores. Las copias manuales/previas a actualizar no tienen retención automática.
- No se han incorporado gráficos del backlog, aprendizaje acumulativo, modelos locales, conexión a IBKR ni órdenes reales. Presupuesto, gasto y reserva de API permanecen en cero en la demo usada.

## Próximo paso concreto

La consolidación prioritaria ya está implementada y validada; consultar su documento para las deudas que siguen abiertas. Revisar y guardar este conjunto como candidata, ejecutar su CI cuando estén comprobados los límites y completar el ensayo de 48 horas. Si aparecen fallos, corregirlos dentro de v0.2 y repetir solo la validación afectada. No adelantar gráficos, móvil o aprendizaje durante esta consolidación.
