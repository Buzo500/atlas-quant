# Instalar la versión actual en el portátil · Windows

11/09/2026. Rama `codex/v0.5-comparador`, versión `0.5.0-dev.3`, esquema 5. Código `5482e3f` subido y verificado en GitHub; esta guía se incorpora después en la misma rama. La PR, CI remota, fusión y etiqueta dev.3 siguen pendientes. Las pruebas locales se hicieron en el sobremesa; la instalación de esta entrega en el portátil todavía debe comprobarse allí.

Estos pasos usan Windows nativo x64 y una carpeta nueva. No requieren WSL, CUDA, GPU dedicada, claves de IA ni presupuesto de pago. La GPU no acelera automáticamente los cálculos actuales. Si conservas una instalación anterior en el portátil, detenla antes de instalar/arrancar esta copia: ambas usan los puertos 3000 y 8000.

## 1. Preparar las herramientas

Si ya están instaladas, comprueba las versiones antes de instalar nada más. Descargas oficiales: [Git para Windows](https://git-scm.com/install/windows), [Python para Windows](https://www.python.org/downloads/windows/) y [Node.js](https://nodejs.org/en/download). Para una instalación nueva: Python 3.14 de 64 bits y Node 24 LTS. Deja Python y Node accesibles en PATH y abre una ventana nueva de PowerShell después de instalarlos.

El instalador de ATLAS exige Python >=3.12, Node >=22.13 y **pnpm exactamente 11.19.0**. Entorno comprobado en el sobremesa: Python 3.14.4, Node 24.15.0, pnpm 11.19.0; no es una matriz de compatibilidad exhaustiva para todas las revisiones posteriores.

```powershell
git --version
python --version
node --version
npm.cmd install --global pnpm@11.19.0
pnpm.cmd --version
```

## 2. Clonar la rama actual

Escoge una carpeta local fuera de OneDrive. Este ejemplo usa una carpeta nueva `C:\Proyectos\ATLAS-actual`; no la uses como destino si ya contiene archivos. Inicia sesión en GitHub con tu cuenta cuando Git lo solicite. No incluyas claves ni tokens en el comando.

```powershell
New-Item -ItemType Directory -Force C:\Proyectos | Out-Null
Set-Location C:\Proyectos
git clone --branch codex/v0.5-comparador https://github.com/Buzo500/atlas-quant.git ATLAS-actual
Set-Location .\ATLAS-actual
git branch --show-current
git log -1 --oneline
```

La rama debe ser `codex/v0.5-comparador`. `master` conserva dev.2 hasta que se fusione la nueva entrega. El último commit puede ser documentación posterior a `5482e3f`.

## 3. Instalar y compilar

Desde la raíz clonada, donde están `Install-Atlas.ps1`, `backend` y `frontend`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-Atlas.ps1
```

Espera al mensaje «Instalación y compilación verificadas». El instalador crea `.venv`, instala las dependencias fijadas, comprueba compatibilidad, instala el frontend y genera su compilación con manifiesto. Necesita conexión a Internet para descargar paquetes. No configura servicios de IA de pago. La opción de PowerShell afecta solo a ese proceso, no cambia su política permanente.

Si falla, conserva el error y no continúes con el arranque. No copies `.venv`, `node_modules` ni `frontend/dist` desde otro equipo: se crean aquí. No sustituir este paso por un `pnpm build` directo, que no genera el manifiesto de ATLAS.

## 4. Abrir y verificar

```powershell
.\Abrir-ATLAS.cmd
Invoke-RestMethod http://127.0.0.1:3000/api/health
```

Debe indicar `status: ok`, `version: 0.5.0-dev.3`, `mode: local` y `live_available: false`. La interfaz abre en [http://127.0.0.1:3000/](http://127.0.0.1:3000/) y debe mostrar **Motor conectado**. En Datos debe aparecer **Fichas y comparador de activos**.

Una clonación nueva empieza con base vacía. Puedes pulsar **Cargar demostración**; no necesitas crear `.env` ni introducir claves. Las fichas explican la falta de evidencia de calendario/precios cuando corresponde: la demo no convierte por sí sola una serie en datos acreditados.

## 5. Detener y volver a iniciar

```powershell
.\Detener-ATLAS.cmd
```

Para siguientes usos basta con doble clic en `Abrir-ATLAS.cmd`; no necesitas reinstalar cada vez. Cerrar la pestaña del navegador no detiene el motor. Los registros están en `var/logs/`. Verificar también una parada y un segundo arranque antes de dar por validada la instalación en este portátil.

## Datos del sobremesa y actualizaciones

GitHub lleva código y documentación, **no la base `var/atlas`, `.env`, copias de seguridad ni instalaciones locales**. Las carteras/operaciones/informes no se sincronizan entre equipos. La instalación descrita arriba no copia ni modifica tus datos del sobremesa ni la instalación anterior del portátil.

Si quieres llevar las carteras del sobremesa, utiliza una copia completa creada con `Backup-Atlas.ps1`, transfiere la carpeta de backup por un medio privado y verifica/restaura con ATLAS detenido en el destino. `Restore-Atlas.ps1 -BackupPath ...` sustituye la base del destino; no fusiona dos carteras o bases y exige revisar antes qué estado vas a conservar. Procedimiento detallado en [operacion_windows.md](operacion_windows.md). No subir la base a GitHub ni copiar una base SQLite abierta. Esta guía no ejecuta ninguna migración de datos.

Para actualizar esta misma carpeta más adelante: detén ATLAS, comprueba `git status`, descarga cambios con `git pull --ff-only` y vuelve a ejecutar `Install-Atlas.ps1`. Si hay modificaciones locales o el pull falla, conserva el estado y revisa el conflicto; no uses reset/force para saltarlo. El instalador respalda la base existente antes de actualizar dependencias, pero no reemplaza una revisión previa de compatibilidad.

Para continuar el desarrollo desde el portátil, lee `AGENTS.md`, `docs/CONTINUIDAD.md` y `README.md`. Registra allí las versiones y verificaciones hechas realmente en ese equipo; no atribuyas al portátil las pruebas del sobremesa. Ensayo de 48 horas, movimientos personales y demás trabajos aplazados siguen pendientes.
