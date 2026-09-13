# Dev.9: validación local de la entrega

13/09/2026. Windows nativo, Python 3.14.4, Node portable 24.21.0, NumPy 2.5.2.
Esquema 5; presupuesto externo cero. [Uso y contratos](v0_6_dev9_implementacion.md).
La CI 34774872432 pertenece a dev.8: no se ha ejecutado otra CI ni publicado dev.9.

## Pruebas de producto

| Comprobación | Resultado |
|---|---|
| Suite Python completa | 1.193 casos + 91 subcasos, 139,94 s |
| Regresiones finales de exportación | 9 casos correctos tras ajustar solo la presentación del PDF |
| Captura TCP final | 5 casos correctos, incluido un caso nuevo de límite UTF-8; 1,12 s |
| Frontend | 344 casos, 42 archivos, 43,09 s |
| Transporte Node | 8 casos correctos |
| Contratos, TypeScript, lint | Correctos |
| Compilación canónica y manifiesto | Correctos; `build_frontend.py --check` verificado |
| Navegador integrado | 25/25 E2E, con descarga D7 de LaTeX y tres anchos |

La suite completa de 1.193 precede al control nuevo de tamaño: hay **1.194 casos
Python distintos verificados** sumando ese caso, no una segunda ejecución completa
de 1.194. Después del E2E se fija LF explícito en el JSONL para que la traducción
CRLF de Windows no añada bytes por encima del límite; sus cinco pruebas se repiten.
No cambia el cálculo o el transporte. Tres avisos de pytest: dos deprecaciones
existentes de Starlette y el ZIP duplicado creado deliberadamente por una prueba.

Regresiones de exportación: oráculo independiente de aportación/comisión,
conservación del histórico tras modificar el libro aislado, ZIP determinista,
alteraciones/rutas/duplicados rechazados, cantidades finitas y escape TeX,
ausencias conservadas, guardia HTTP y uso exclusivo del informe del servidor.
Frontend: descarga por IDs, error sin reintento, cancelación al desmontar/cambiar
de informe y ausencia de descargas tardías.

Los logs están bajo `output/validation/dev9-*.log`, excluidos de Git. El resumen
compacto y las huellas relevantes se conservan en `docs/evidence/dev9-validation.json`.

## Navegador y estado operativo

Run `e2e-ad01b118a82c40a99b4f3f61fa65ea20`, 19:58:01–20:00:19 UTC.
25 recorridos correctos, salida global 0 y backend/frontend 0/0; sin parada forzada,
sin error de limpieza, integridad `ok` y puertos 3000/8000 liberados.
El ZIP descargado realmente se verifica con el verificador del generador.

Capturas de la sección D7 inspeccionadas a **390, 1.280 y 3.440 px**: botón,
explicación y estados legibles, sin desbordamiento horizontal de página. Son anchos
de navegador automatizado; no una nueva comprobación física de escala de Windows.

El E2E se ejecutó mientras continuaba Monte Carlo offline; no usar sus latencias
como línea base con CPU desocupada. La captura correlaciona 1.895 grupos y 78
incidencias: dos grupos >=1 s, máximo 1.409,0049 ms, sin truncar el informe.
No hubo un nuevo timeout de 10 s o agotamiento de puertos observado en ese recorrido.

Captura TCP real: **26 muestras**, ninguna muestra indisponible, máximo **1.679
sockets** a las 20:00:04,704077 UTC; sin eventos Tcpip 4227/4231 durante el intervalo.
El máximo agrupa el equipo; no equivale a conexiones consumidas por ATLAS.
No identifica al consumidor de D3 ni cierra D4 o la incidencia histórica de API.
Los agregados completos por PID quedan localmente en `tcp-pressure.jsonl`.

Base habitual conservada, SHA-256:
`2791f15e1bb5be5833117810ce5de745e4dfb46817850c4d8d8cbc3cc2bc5549`.
Aplicación habitual detenida. No se usan datos personales, proveedor IA o bróker.
Ensayo, portátil y PR #12 siguen aplazados.

## PDF: compilación y revisión visual

Tres paquetes sintéticos generados con el exportador final y compilados por la CLI
con LuaHBTeX/TeX Live 2026 local, dos pasadas, sin sockets/shell-escape. Fuentes,
logs y recibos conservados junto a los PDF en `output/pdf/dev9-cartera-entrega/`:

| Muestra | Revisión |
|---|---|
| `cartera-sintetica.pdf` | 2 páginas; NAV 1.000→1.098 EUR, flujo 100, coste 2, P&L −2, TWR −0,2 % |
| `cartera-sin-fx.pdf` | 2 páginas; ausencias y motivo de FX, sin presentar una valoración inventada |
| `cartera-tabla-larga.pdf` | 5 páginas; 151 cortes diarios completos, repetición de cabeceras y tablas continuadas |

Todas las páginas renderizadas e inspeccionadas. Cifras y fechas contrastadas por
extracción independiente con pypdf; las 151 fechas de la curva larga están presentes.
La normalización de «−0,00» y el redondeo son exclusivamente de presentación;
JSON/CSV originales intactos. Sin página final casi vacía ni texto recortado.
Los avisos de alineación y epstopdf desactivado no impiden la compilación.

El primer intento de LuaLaTeX bajo el sandbox del agente rechazó la ruta de perfil
Windows; la misma CLI completó la compilación con la ejecución local autorizada.
No se modificaron permisos globales, TeX ni el generador para ocultar ese diagnóstico.

## Experimento estadístico

Código congelado antes de calcular en `380e7375f86e09b8c5549c24591041b4f43158e7`.
Once oráculos independientes previos, fuentes/semillas/huellas conservadas y
reproducción de 36 historias por lote. [Plan original](v0_6_dependencia_grupos_plan.md)
intacto; [resultados y decisión](v0_6_dependencia_grupos_resultados.md) separados de
esta validación del software. El método del producto no se sustituye automáticamente.
