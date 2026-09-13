# LaTeX inicial de ATLAS · dev.8

Implementa el desarrollo completo de un informe retrospectivo verificado,
conservando el alcance de [REPORT-001](informes_latex_diseno.md). La selección
arbitraria de fechas y los informes de carteras siguen como ampliaciones futuras.

El usuario acepta expresamente el PDF el 13/09/2026. El siguiente alcance queda
concretado en [informes por periodo](informes_periodo_contrato.md): primero D7
guardado, después detalle de posiciones y recorte retrospectivo. Solo definido.

## Uso desde el Laboratorio

En **Investigación retrospectiva con supuestos**, calcula o reabre un informe
JSON. **Exportar fuente LaTeX** descarga un ZIP con fuente editable, estilo,
datos del desarrollo y manifiesto. La descarga no necesita TeX instalado.
Los botones JSON y JSON/CSV anteriores siguen disponibles y conservan su formato.

`POST /api/lab/retrospective/latex` recibe el mismo `report_json` que la reapertura.
Antes de renderizar se reproduce el cálculo y se comprueba el informe completo.
Mantiene controles de origen/cliente, tamaño de 3 MB, `no-store` y el límite
compartido de cálculos. No lanza compiladores desde HTTP ni escribe una base.

## PDF opcional en Windows

Desde la raíz del proyecto, con una salida nueva:

```powershell
.\.venv\Scripts\python.exe tools/export_research_latex.py ruta/informe.json --output output/pdf/mi-informe.zip --pdf
```

Sin `--pdf`, genera solo la fuente y los datos. Con la opción, añade archivos
hermanos `.pdf`, `.log` y `.build.json`. El recibo identifica motor, límites y
hashes del PDF/ZIP/manifiesto. No sobrescribe salidas existentes; usa otro nombre
para otra generación. Si falta el compilador o falla, conserva el ZIP y el JSON
original, informa del error y termina con código distinto de cero.

LuaHBTeX 1.24.0 / TeX Live 2026 instalado de forma portable bajo
`var/tools/tinytex-2026.09/TinyTeX`; no cambia el Node/Python/TeX global ni el PATH
del usuario. En este PC la herramienta lo encuentra automáticamente. En otro
Windows admite LuaLaTeX de TeX Live 2026 en PATH. La fuente es portable; la
compilación gestionada inicial requiere Windows por su control de memoria.
No se instala TeX ni se descargan paquetes durante el arranque de ATLAS.

Distribución [TinyTeX v2026.09 oficial](https://github.com/rstudio/tinytex-releases/releases/tag/v2026.09),
archivo `TinyTeX-v2026.09.zip`, SHA-256
`e82d8b78fcf5740639f10ac8518f0c83c9202830e6bba364c70104601c12c6be`,
contrastado con el digest del release. Paquetes adicionales gratuitos: pgfplots,
babel-spanish e hyphen-spanish desde espejo oficial CTAN con HTTPS verificado.
GPG no estaba disponible: no afirmar comprobación de firma de esos paquetes.
[Versiones, revisiones, procedencia y licencias registradas](evidence/latex-toolchain-v1.json).
No actualizar automáticamente esa instalación: una actualización requiere
recompilar y revisar los casos. El recibo identifica esta validación, no promete
PDF binariamente idéntico entre distintas versiones/fechas de compilación.

## Contenido y límites

- A4, sans serif, cifras tabulares, cobre/crema y curvas azul pizarra; trazo
  distinto para comprar/mantener. IDs/huellas monoespaciados y divisibles.
- Fechas inclusivas del desarrollo, NAV/rentabilidad/drawdown, comisiones y número
  de ejecuciones; curvas completas y tabla de todas las operaciones, con cabecera
  repetida. Fuente económica sin redondear; impresión a dos decimales y precios
  de operaciones a cuatro decimales.
- Parámetros, costes, moneda, calendario/horarios supuestos, procedencia y límites.
  Reserva solo como fechas/recuento: no se calculan ni exportan sus precios.
- Informe original y hashes conservados. Código diferente solo se acepta cuando
  el recálculo coincide, con aviso explícito; no cambia la autenticidad de los datos.

Paquete `atlas-research-latex-bundle-v1`: 12 miembros fijos. Conserva el manifiesto
JSON/CSV anterior como `research-manifest.json`, y el nuevo identifica el renderer,
plantilla, fecha UTC y SHA-256/tamaño de cada miembro. `verify_archive` reconstruye
las fuentes con el generador actual, verifica todos los miembros y rechaza rutas,
duplicados, cambios y exceso de tamaño sin extraer ni ejecutar archivos. El hash
comprueba integridad; no es una firma de origen. Igual informe/fecha/generador
producen el mismo ZIP.

## Compilación y texto no fiable

La CLI solo acepta JSON de investigación, nunca una ruta TeX aportada por el
informe. Genera recursos con nombres fijos en una carpeta temporal propia; escapa
caracteres TeX y rechaza controles invisibles/bidireccionales. Las notas extensas
se dividen en filas para permitir saltos de página sin perder contenido.

Dos pasadas, sockets y shell-escape desactivados, `openin_any=p`, `openout_any=p`.
Plazo total de compilación 120 s, límite de memoria del grupo 2 GB y control de
salida 32 MB. El Job Object contiene y limpia solo procesos creados por la
herramienta. Son controles de proceso y de entradas; no un sandbox completo del
sistema operativo ni una prohibición de red impuesta por el cortafuegos.

La opción LuaTeX `safer` resultó incompatible con el cargador de fuentes y no se
utiliza. La seguridad de datos se apoya en el modelo verificado y el escape,
no en aceptar y ejecutar fuentes externas. Editar manualmente TeX deja fuera esa
garantía; la fuente sigue siendo útil como documento editable independiente.

## Validación de esta entrega

Registro final de pruebas, documentos y estado operativo en
[continuidad](CONTINUIDAD.md). Maqueta sintética, HFG y ZAL observados bajo supuestos,
cero operaciones y notas/tablas de varias páginas. PDF revisados visualmente y
cifras/filas contrastadas con JSON/CSV; no se modifica la estadística ni la reserva.

Los artefactos PDF/ZIP/log locales se encuentran en `output/pdf/` y están excluidos
de Git; código, plantilla y documentación sí se conservan en la rama.
