# Node en Windows · corrección del cierre nativo

Versión de referencia de ATLAS: **Node 24.21.0 LTS**. Node 24.0–24.15 se rechaza
en Windows por el cierre nativo reproducido al abrir conexiones HTTP cortas.
[Diagnóstico, comparación y límites](diagnostico_ci_20260912.md).

## Este sobremesa

Node 24.21.0 está instalado solo para este checkout, en
`var/tools/node-v24.21.0-win-x64/`. Los lanzadores, instalador, build y E2E lo
seleccionan automáticamente. El Node 24.15.0 de `C:\Program Files\nodejs` se
conserva; ejecutar `node --version` fuera de los lanzadores puede mostrarlo.
No se modifica el PATH del usuario o del sistema. Los subprocesos de ATLAS reciben
la ruta de la versión seleccionada; no se descarga software al arrancar.

Archivo descargado mediante HTTPS verificado:
[ZIP oficial 24.21.0](https://nodejs.org/dist/v24.21.0/node-v24.21.0-win-x64.zip).
SHA-256 comprobado contra el
[manifiesto oficial](https://nodejs.org/dist/v24.21.0/SHASUMS256.txt):
`158f7685b44de51f6c0df1d153526cbcd3e1bc739a8dfc607721cef75de9e541`.
Binarios, ZIP y registro de descarga quedan excluidos de Git bajo `var/`.

Para iniciar y detener, desde la raíz del proyecto:

```powershell
.\Start-Atlas.ps1 -OpenBrowser
.\Stop-Atlas.ps1
```

Para herramientas Node directas, usa el ejecutable seleccionado de esta carpeta:

```powershell
.\var\tools\node-v24.21.0-win-x64\node.exe --version
.\.venv\Scripts\python.exe tools\build_frontend.py
```

Detén ATLAS antes de reconstruir. La ruta y versión del servidor se guardan en
`var/runtime.json`; las ejecuciones E2E conservan las suyas en su descriptor.

## Otra instalación

Git no copia `var/`. Instala Node 24.21.0 desde la
[entrega oficial](https://nodejs.org/en/blog/release/v24.21.0), deja su ejecutable
en PATH y abre una consola nueva. Alternativamente, con ATLAS detenido, descarga
el ZIP anterior, comprueba su SHA-256 y extráelo en `var/tools/` de ese checkout.
La carpeta resultante debe contener `node-v24.21.0-win-x64/node.exe`.
Sin instalación portable, ATLAS utiliza el Node de PATH y comprueba su versión.
Conserva pnpm **11.19.0**. No atribuir esta instalación/verificación al portátil.
