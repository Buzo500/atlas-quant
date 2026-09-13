# Dev.9: informes de cartera y diagnóstico

Desarrollo local 0.6.0-dev.9 en `codex/v0.6-evaluador`, esquema 5. Implementa
las cinco tareas autorizadas en [el plan de entrega](v0_6_dev9_plan.md). La CI
34774872432 corresponde a dev.8; no acredita esta ampliación local.

## Uso de los informes de cartera

En **Cartera → Rentabilidad por periodo**:

1. Elige **Cierre de referencia del periodo** y **Cierre final del periodo**.
   Para todo enero, 31/12 y 31/01; se conservan los días civiles y flujos (inicio, fin].
2. Calcula y revisa el informe; pulsa **Guardar informe de rentabilidad**.
3. En ese informe, o al recuperar uno del historial, pulsa **Exportar fuente LaTeX**.
4. Conserva el ZIP: incluye el informe D7 original, modelo de presentación, curva,
   flujos y costes en CSV, fuente/estilo TeX y manifiesto con huellas.

No hace falta TeX para descargar. Para compilar el paquete sin modificar en este PC:

```powershell
.\.venv\Scripts\python.exe tools/export_period_latex.py ruta\atlas-cartera-latex.zip --output output\pdf\mi-cartera.pdf
```

El PDF/log/recibo requieren rutas nuevas. Usa el mismo LuaLaTeX portable y los
límites de [dev.8](informes_latex_implementacion.md): compilación local, dos pasadas,
sin shell-escape/sockets, 2 GB/120 s/32 MB. Ningún compilador se ejecuta por HTTP.
No acepta un TeX externo o alterado como fuente verificada.

## Contrato y conservación

`atlas-period-report-v1` y `atlas-period-latex-bundle-v1` son formatos nuevos;
no cambian D7, el ZIP retrospectivo o el esquema. Adaptador puro sobre
`PerformanceReport` validado, sin recalcular P&L/TWR/MWR y sin nuevas escrituras.
`POST /api/v2/portfolios/{ident}/performance/{report_id}/latex` recupera el original
del servidor por sus IDs; conserva guardias de cliente/origen, `no-store` y límite
compartido de dos cálculos. Un JSON del cliente no sustituye el resultado guardado.

La fuente se lee y su vigencia se observa en una transacción coherente. Después se
renderiza esa instantánea en memoria: cambios posteriores no mezclan datos con el
archivo. El original se conserva sin alterar su `current` histórico; la vigencia
observada para esta descarga está explícitamente en el manifiesto y el PDF.
No se reconstruyen posiciones desde la revisión actual. `initial_state`,
`final_state`, movimientos internos y benchmark son `null` con motivos explícitos.
El primer alcance excluye legacy, detalle patrimonial y recorte retrospectivo;
sus dependencias siguen en [el contrato por periodo](informes_periodo_contrato.md).

Modelo/hash económico separados de fecha/generador. JSON/CSV conservan las cifras
guardadas, incluidas las ausentes. La impresión redondea; no descuenta costes otra
vez, rellena FX o concatena huecos de NAV. No añade benchmark ni autentica datos por
su huella. D7 no conserva un hash de código original: no inventarlo en el documento.
El verificador reconstruye archivos fijos sin extraer/ejecutar entradas arbitrarias;
comprueba miembros, tamaños y huellas. Números que llegan al gráfico se validan
léxicamente y como valores finitos; todos los textos TeX se escapan.

La descarga de la UI se cancela al cambiar de informe/cartera y no genera una
descarga tardía. Errores visibles, sin reintentos automáticos. El botón y las
explicaciones se adaptan al ancho del panel.

## Captura de presión TCP en Windows

`tools/diagnostics/run_api_diagnostic.py` activa automáticamente la captura durante
su E2E aislado. Cada cinco segundos registra agregados de `netstat -anoq`: PID,
estado (incluido BOUND), IPv4/IPv6, loopback, número de sockets y puertos locales
distintos; nombre de proceso consultado después, sin rutas/argumentos. No guarda
direcciones remotas. Consulta eventos Tcpip 4227/4231, con UTC y RecordId.

Guarda `tcp-pressure.jsonl` en el directorio de la ejecución y publica un resumen
compacto de máximos/eventos en el log, también recuperable en una futura CI. Límite
de una hora/8 MB y subprocesos acotados; finalización cooperativa y fallos de la
captura visibles sin reemplazar el resultado del E2E. No cambia red, puertos,
registro, cortafuegos o política de conexiones.

Captura independiente, cuando se necesite observar ATLAS en uso:

```powershell
.\.venv\Scripts\python.exe tools/diagnostics/tcp_capture.py --output output\validation\tcp-sesion.jsonl --seconds 900
```

La salida debe ser nueva. Ctrl+C finaliza la captura; no detiene ATLAS. El PID puede
reciclarse y el nombre se observa después del muestreo; TIME_WAIT/PID 0 no identifica
al consumidor original. Picos/eventos correlacionados son evidencia para diagnosticar,
no demostración automática de causa. D3 anterior está localizado; D4 y la incidencia
API histórica no se declaran resueltos por añadir instrumentación.

## Experimento aislado

Código/pruebas congelados antes de Monte Carlo en `380e7375f86e09b8c5549c24591041b4f43158e7`.
Protocolo y resultados se registran aparte: [q4 pasa principal y confirmación](v0_6_dependencia_grupos_resultados.md),
36.000 historias, 72 reproducciones exactas y auditoría aritmética independiente.
No se altera el bootstrap del producto ni se integra automáticamente q4/q8.
[Plan estadístico original](v0_6_dependencia_grupos_plan.md).

Validación de pruebas, navegador y tres PDF: [evidencia local](v0_6_dev9_validacion.md).
Resultados estadísticos y estado operativo final: [continuidad](CONTINUIDAD.md).
