# ATLAS Quant · Auditoría y avance de v0.2

**Estado vigente:** `0.2.0-rc.2` **en preparación**; seguimiento y evidencia de cada revisión en [candidata_v0_2.md](candidata_v0_2.md). La candidata rc.1 y la [CI superada para `3f1d990`](https://github.com/Buzo500/atlas-quant/actions/runs/34241300060), del 08/09/2026, se conservan como antecedentes identificados. No equivalen a CI de los cambios posteriores de rc.2. H6 sigue pendiente y el ensayo de 48 horas está aplazado. Las cifras y la versión del motor de la auditoría inferior corresponden al bloque histórico del 6 de septiembre; v0.2 no es estable.

Contexto histórico: 6 de septiembre de 2026. Base de trabajo: commit `97520b8` (`traslado al sobremesa`), árbol limpio al comenzar. Los cambios descritos se probaron como árbol de trabajo local sobre esa base; al terminar aquel bloque todavía no se había publicado ni etiquetado una versión nueva.

## Revisión local de rc.2 · 8 de septiembre de 2026

La [PR #1](https://github.com/Buzo500/atlas-quant/pull/1) está fusionada en `master`, commit `e1f6e020a1d75a81bff97eefcbebe726d47bcdb3`; rc.2 se prepara en `codex/v0.2.0-rc.2`. Resultados locales: **446 pruebas Python y 91 subtests** (38,34 s, dos avisos previos), **140 Vitest en 15 archivos** (13,34 s), **5/5 E2E** (9,6 s); TypeScript, contratos, lint, `pip check` y build con manifiesto correctos. La nueva CI y la etiqueta siguen pendientes.

Se corrigieron el foco tras operaciones que retiran controles, la conservación del mensaje de importación y los anuncios repetidos por el sondeo. E2E usa API real y base nueva; valida la familia propia de cada servidor y rechaza una finalización incompleta. Se corrigió además la apertura de la aplicación global durante la colección de pytest, aislando antes de importar los módulos; la suite final utiliza también `ATLAS_DATA_DIR` explícito.

La ejecución `e2e-7e176e2037584e4983d8e2b53428724e` cerró ambos servidores con código 0, integridad correcta, hashes habituales iguales y puertos libres. La base habitual coincide íntegramente con la copia `atlas-20260908T151716582043Z-af195afe`, incluidos esquema, secuencias y 539 eventos de auditoría. El primer intento, fallido antes del navegador, permanece registrado. La creación y retirada de WAL/SHM sin cambios de contenido se reprodujo en copias y es compatible con su diferencia de hash; no demuestra la causa original porque aquel intento no guardó hashes individuales.

El entorno manual `e2e-0de1cebd856c4115984403a8086dc09e` está cerrado con resultado 0 y conservación de la base, sin interacciones de UI manual. **Escalado físico 125 %/150 % no validado:** el control de Windows bloqueó la operación al no identificar una URL de confianza; se mantuvo el 100 % inicial. Las 35 comprobaciones anteriores de viewports CSS son evidencia distinta. ATLAS normal permanece detenido antes del commit y la CI. Ensayo de 48 horas y seguimiento aplazados; sin presupuesto ni llamadas de pago. El [registro de candidata](candidata_v0_2.md) concentra los resultados vigentes.

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
