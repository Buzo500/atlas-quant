# ATLAS Quant · Auditoría y avance de v0.2

**Estado vigente:** `0.2.0-rc.2`, candidata con CI verificada, no estable. La [CI 34249730107](https://github.com/Buzo500/atlas-quant/actions/runs/34249730107) valida `412918b5e9067e44f293b0633068ca932a472d64`; el cierre posterior solo cambia documentación. Integración mediante la [PR #2](https://github.com/Buzo500/atlas-quant/pull/2) y etiqueta `v0.2.0-rc.2` según el procedimiento autorizado.

## Revisión de rc.2 · 8 de septiembre de 2026

En CI Windows: **446 Python + 91 subtests** (22,13 s), **140 Vitest en 15 archivos** (43,86 s), **5/5 E2E** (18,7 s); instalación limpia, build, contratos, tipos, lint, `pip check`, smoke, arranque y parada correctos. E2E remoto `e2e-ea578aac47f341ffac48cd6330edbb5a`: resultado 0, conservación verificada, integridad `ok` y puertos libres. Comprobaciones locales separadas: 446+91 (38,34 s, dos avisos previos), 140 Vitest (13,34 s) y 5/5 E2E (9,6 s).

Se corrigieron foco, anuncios por sondeo, mensaje de importación, identificación del intérprete mediante su grupo de procesos y aislamiento antes de recoger módulos de pytest. La primera [CI 34248790750](https://github.com/Buzo500/atlas-quant/actions/runs/34248790750) se conserva fallida: 444 Python superadas, dos fallidas y 91 subtests (21,99 s), 140 Vitest superadas, sin E2E remoto acreditado en ese intento. Los dos fallos por alias Windows 8.3 se corrigieron con `samefile`: dos fallos antes y dos casos correctos después con ruta corta, y dos correctos con ruta larga.

La base habitual coincide con `atlas-20260908T151716582043Z-af195afe`, incluidos contenido completo, esquema, secuencias y 539 eventos de auditoría. La creación y retirada de WAL/SHM sin cambios de datos se reprodujo en copias y es compatible con la diferencia de hash del primer intento E2E local; no demuestra su causa original. Se conservan logs y resultados fallidos. El entorno manual `e2e-0de1cebd856c4115984403a8086dc09e` cerró con resultado 0, sin interacciones de UI manual.

ATLAS normal está arrancado, ejecución `7fa354c2b8d5425fa4818dab68acd8a0`, con salud rc.2, cartera y controles conservados, sin claves y con consumo cero. **Escalado físico 125 %/150 % pendiente:** el control de Windows bloqueó la operación al no identificar una URL de confianza; no se cambió el 100 % inicial. Los 35 viewports CSS históricos son evidencia distinta. Ensayo de 48 horas y seguimiento aplazados. [Registro completo de candidata](candidata_v0_2.md).

## Registro histórico de la auditoría inicial

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

La instalación principal volvió a arrancar invocando `Start-Atlas.ps1` desde otra carpeta. API, proxy, controles y cartera se verificaron de nuevo, incluida su carga final en navegador. Al terminar aquel bloque quedó funcionando con la demo original y el experimento sin IA en observación; no describe el estado de la instancia actual.

La evidencia local está en `output/validation/clean_v02.json`, `output/validation/migration_v02_desktop.json` y `output/validation/runtime_v02_desktop.json`, excluidos de Git. El primer punto de recuperación previo al desarrollo es `backups/before-v0.2-20260906T151721Z/`: copia manual mediante SQLite, anterior al formato nuevo con manifiesto. Las copias nuevas publicadas por las herramientas sí incluyen manifiesto.

## Límites actuales y cierre pendiente

- La versión vigente es **0.2.0-rc.2 en preparación**, todavía no estable. El identificador 0.1.0 citado en la evidencia anterior corresponde al bloque original.
- Falta completar satisfactoriamente una prueba operativa sostenida de **48 horas**, con salud, recursos, errores, copia automática y persistencia registrados. El ensayo de rc.1 se interrumpió; su repetición y el seguimiento están aplazados. Los recorridos cortos y las pruebas unitarias no lo sustituyen. No se ha instalado un servicio Windows.
- `.github/workflows/validate.yml` incluye instalación, pruebas de interfaz y Python, TypeScript, contratos, lint, build y recorrido sintético en Windows. Permite activación manual y por etiqueta candidata. La ejecución superada de `3f1d990` está identificada arriba; la validación de rc.2 debe asociarse a sus propias fuentes. Antes de activarlo, comprobar disponibilidad y límites de Actions de la cuenta. No contiene claves ni llamadas pagadas.
- Falta registrar el commit final, la integración y los resultados de rc.2 y cerrar los criterios H5/H6 antes de una etiqueta estable. La captura de fuentes local de las pruebas no sustituye comprobar el artefacto del commit finalmente publicado.
- Copias y logs están en el mismo equipo; no hay cifrado, copia externa automática, rotación de logs, autoinicio ni recuperación automática de servidores. Las copias manuales/previas a actualizar no tienen retención automática.
- No se han incorporado gráficos del backlog, aprendizaje acumulativo, modelos locales, conexión a IBKR ni órdenes reales. Presupuesto, gasto y reserva de API permanecen en cero en la demo usada.

## Próximo paso concreto

Preparar rc.2 integrando el trabajo previamente validado, automatizando recorridos de navegador y revisando el uso, con sus resultados ligados a las fuentes finales. La revisión `3f1d990` ya superó CI, pero esa evidencia no se transfiere a cambios posteriores. H6 y el ensayo de 48 horas permanecen aplazados y no se inician en este bloque. Si aparecen fallos, corregirlos dentro de v0.2 y repetir la validación afectada. No adelantar gráficos avanzados, móvil o aprendizaje durante esta consolidación.
