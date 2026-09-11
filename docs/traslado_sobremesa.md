# Llevar ATLAS al sobremesa y continuar con Codex

**Actualización 11/09/2026:** para instalar ahora en el portátil, seguir [instalacion_portatil.md](instalacion_portatil.md): rama `codex/v0.5-comparador` subida, dev.3, Windows nativo, esquema 5 y comandos actuales. Las instrucciones siguientes conservan el traslado histórico; `master` todavía no contiene dev.3.

Guía preparada el 6 de septiembre de 2026 para Windows. No es necesario usar WSL2 para esta versión.

Para los lanzadores y copias de **v0.2 en desarrollo**, seguir también la [guía de operación en Windows](operacion_windows.md). La instalación actual compila la interfaz, verifica el arranque y admite los accesos `Abrir-ATLAS.cmd` y `Detener-ATLAS.cmd`. La hoja de ruta vigente está en [hoja_de_ruta.md](hoja_de_ruta.md).

La instalación nativa del sobremesa se completó y verificó ese mismo día en `C:\Users\lulae\Documents\Personal\Proyectos\atlas-quant`, con base nueva y demo sin claves ni gasto. Las versiones comprobadas, resultados y comandos de este PC están en [CONTINUIDAD.md](CONTINUIDAD.md). Los pasos de publicación y clonación siguientes se conservan como referencia para otros traslados.

La ruta sencilla es publicar el código en un repositorio privado, clonarlo en el sobremesa y abrir allí una conversación de Codex asociada a esa carpeta. `AGENTS.md` y `docs/CONTINUIDAD.md` llevan el contexto del proyecto. Git no lleva automáticamente la conversación original ni la base de datos de ATLAS.

## 1. Publicar desde el portátil

Si todavía no has creado el repositorio en la web, puedes crearlo directamente desde GitHub Desktop:

1. Instala GitHub Desktop e inicia sesión en tu cuenta.
2. En **File → Add local repository**, selecciona `C:\Users\lulae\Documents\ChatGPT\Atlas`. El repositorio local ya está inicializado; no crees otra carpeta dentro.
3. En **Changes**, revisa los archivos que se van a guardar. Deben incluir `AGENTS.md`, `docs/CONTINUIDAD.md`, el código y los archivos de dependencias.
4. Escribe el resumen `ATLAS v0.1 y documentos de continuidad` y pulsa **Commit to…** en la rama que muestre la aplicación.
5. Pulsa **Publish repository**, indica un nombre como `atlas-quant` y conserva marcada **Keep this code private**. Selecciona tu cuenta personal y publica.
6. Abre **Repository → View on GitHub** y comprueba que aparece como privado y que `docs/CONTINUIDAD.md` está incluido.

Se ha ampliado `.gitignore` para excluir la publicación independiente `pdf-mobile/`, su archivo comprimido, resultados locales de ejecución y copias de seguridad. Ya excluía `.env`, `var/`, `.venv` y `node_modules`. El PDF del diseño sí se conserva en `output/pdf/atlas_quant_diseno.pdf`.

No utilices la carga de carpetas del navegador para subir todo el directorio: esa vía no aplica automáticamente las exclusiones de Git. GitHub Desktop publica los archivos seleccionados y registrados por Git.

El archivo `frontend/.openai/hosting.json` debe estar incluido: es configuración local necesaria para arrancar la interfaz y no contiene claves en la versión revisada.

### Si ya creaste un repositorio privado vacío en la web

No crees otro con el mismo nombre desde Publish repository. Una vez hecho el commit local, puedes conectar el repositorio existente desde PowerShell en la carpeta del portátil. Necesitas Git en PATH y autenticarte con GitHub si lo solicita. Sustituye la URL de ejemplo por la URL HTTPS exacta de tu repositorio:

```powershell
git remote -v
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin HEAD
```

El comando `remote add` corresponde al estado revisado sin remotos. Si `remote -v` ya muestra `origin`, comprueba su destino antes de usarlo; no borres ni sustituyas un remoto a ciegas. Si el repositorio web ya tiene un README u otros commits y Git rechaza el envío, conserva ambos historiales y resuelve la diferencia con Codex; no fuerces el push.

Referencias: [añadir un repositorio local](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-a-repository-from-your-local-computer-to-github-desktop), [publicarlo de forma privada](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop).

## 2. Descargar en el sobremesa

1. Instala GitHub Desktop e inicia sesión en la misma cuenta de GitHub.
2. Selecciona **File → Clone repository** y elige tu repositorio de ATLAS.
3. Como destino, usa por ejemplo `C:\Proyectos\Atlas`, fuera de una carpeta sincronizada por OneDrive. No tiene que coincidir con la ruta del portátil.
4. Pulsa **Clone**. Comprueba que en la carpeta descargada aparecen `README.md`, `AGENTS.md`, `Install-Atlas.ps1`, `backend`, `frontend` y `docs`.

[Guía oficial para clonar con GitHub Desktop](https://docs.github.com/en/desktop/adding-and-cloning-repositories/cloning-and-forking-repositories-from-github-desktop).

## 3. Abrir Codex y recuperar el contexto

1. Abre Codex en el sobremesa con tu cuenta habitual. Si tu aplicación agrupa ChatGPT y Codex, selecciona el modo Codex para trabajar con archivos locales.
2. Añade o abre un **proyecto local** y vincula la carpeta que acabas de clonar, por ejemplo `C:\Proyectos\Atlas`. Usa esa carpeta como principal; no selecciones solo `frontend`.
3. Abre una conversación nueva dentro de ese proyecto. Si puedes elegir dónde trabajar, selecciona **Local / Este equipo** para esta instalación inicial, de forma que use la carpeta clonada.
4. Pega este mensaje:

> Estoy retomando ATLAS Quant desde mi sobremesa. Lee primero AGENTS.md, docs/CONTINUIDAD.md, docs/traslado_sobremesa.md, README.md y docs/version_0_1.md. Tengo Windows con WSL2 y una RTX 3080 de 10 GB. Quiero instalar y arrancar la versión actual en Windows nativo desde esta carpeta. Comprueba las dependencias, instala las que falten y verifica que abren la interfaz y el motor. Empezamos con una base nueva y datos de demostración, sin claves de API y con presupuesto cero. No implementes todavía las mejoras de gráficos o aprendizaje del backlog. Al terminar, dime cómo iniciar y detener ATLAS en este PC.

No necesitas que la conversación original aparezca para retomar el desarrollo. El nuevo chat tendrá los archivos de contexto y el código; no debe afirmar que recuerda cada mensaje anterior. Mantener actualizada la documentación evita depender de una transcripción local. [Proyectos y contexto de Codex](https://learn.chatgpt.com/docs/projects).

## 4. Instalación manual, si prefieres hacerla tú

En el portátil se comprobaron Python **3.12.14**, Node **24.19.0** y pnpm **11.19.0**. El mínimo declarado es Python 3.12 y Node 22.13; igualar las versiones comprobadas reduce diferencias. Python 3.12.14 procede del runtime empaquetado de Codex; esta guía no presupone que exista un instalador oficial de Windows de esa revisión exacta. El entorno Python debe ser Windows x64, no un entorno copiado desde WSL.

Instala Python y Node para Windows y comprueba que están en PATH. Después, en una nueva ventana de PowerShell:

```powershell
python --version
node --version
npm.cmd install --global pnpm@11.19.0
pnpm.cmd --version
```

Desde la carpeta clonada —cambia la ruta si has elegido otra—:

```powershell
cd C:\Proyectos\Atlas
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-Atlas.ps1
.\.venv\Scripts\python.exe tools\run_atlas.py --open
```

La opción `ExecutionPolicy Bypass` se limita al proceso que ejecuta este instalador revisado; no cambia la política permanente de Windows. Continúa con el arranque solo si el instalador termina correctamente. Descarga los paquetes de las dependencias fijadas y crea `.venv` y `frontend/node_modules` en el sobremesa.

La interfaz se abre en `http://127.0.0.1:3000/`. Mantén esa ventana abierta mientras trabajas. Para detener ATLAS, pulsa Ctrl+C en ella. Para futuras aperturas basta con ejecutar de nuevo la última línea desde la carpeta de ATLAS.

Para comprobar que la interfaz conecta con el motor, abre otra ventana de PowerShell y ejecuta:

```powershell
Invoke-RestMethod http://127.0.0.1:3000/api/health
```

Debe devolver `status: ok`, `mode: local` y `live_available: false`. Después abre la interfaz y prueba **Cargar demostración** en esta base nueva. Un mensaje de «arrancando» del lanzador no sustituye esta comprobación.

Alternativa de arranque en segundo plano:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-Atlas.ps1 -OpenBrowser
```

Y para solicitar la parada:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-Atlas.ps1
```

Si algo falla, los registros están en `var/logs/`. La nueva conversación de Codex puede inspeccionarlos en esa carpeta. La instalación del sobremesa no se ha ejecutado ni validado desde el portátil.

## 5. Datos y experimentos

El clon nuevo empieza sin cartera, datasets ni experimentos anteriores: estaban en `var/atlas`, excluido de Git. Puedes cargar la demo sin claves. Tampoco tienes que configurar CUDA para abrir v0.1.

Si deseas conservar el estado del portátil, haz una migración separada: espera a que no haya una fase de cálculo o llamada en curso, detén ATLAS y verifica que sus procesos han terminado; copia la carpeta `var/atlas` completa con todos sus archivos presentes. Detén también el destino y guarda una copia de su estado antes de sustituirlo. Si hay dudas sobre el cierre o WAL, usa una copia mediante la API de backup de SQLite con ayuda de Codex.

No arranques a la vez copias de los mismos experimentos activos: serían dos motores independientes y podrían repetir trabajos o llamadas. Git no fusiona bases de datos. Esta guía no ha trasladado, eliminado ni pausado ningún experimento.

## 6. Volver al portátil

Antes de trabajar en cualquiera de los dos equipos, usa **Fetch origin** y **Pull origin** si hay cambios. Al terminar una modificación, crea un commit y usa **Push origin**. Esos cambios estarán disponibles en el otro equipo después de descargarlos. Una modificación sin commit y sin push todavía no ha viajado a GitHub.

Como hábito inicial, termina y sube una sesión antes de empezar a editar desde el otro ordenador. Mantén las ejecuciones largas del sobremesa en una versión fija y aplica actualizaciones entre experimentos. El portátil puede usar datos de prueba distintos.

## 7. Si quieres conservar exactamente la conversación original

La documentación oficial contempla dos opciones adicionales; dependen de que aparezcan en tu versión/cuenta y de conectar los equipos:

- **Acceso remoto:** en el portátil, revisa **Settings → Connections → Control this PC**; en el sobremesa, **Control other devices**. Completa el emparejamiento que muestre la aplicación. Esto permite acceder a trabajo del portátil, que debe seguir encendido y conectado; no lo convierte en trabajo ejecutado en el sobremesa.
- **Handoff:** con el sobremesa conectado como host y el mismo repositorio guardado como proyecto en ambos equipos, abre la conversación original y selecciona el destino desde el selector de ubicación de ejecución al pie del chat. Revisa el destino y la rama, y elige **Hand off**. La aplicación traslada conversación y estado Git a un worktree del destino; instala allí sus dependencias si faltan. No presupongas que mueve `.env` o la base excluida de Git.

No se ha configurado ninguna de estas conexiones. Si los controles no están disponibles, utiliza el procedimiento de conversación nueva con los documentos de continuidad. [Documentación oficial de conexiones y handoff](https://learn.chatgpt.com/docs/remote-connections).
