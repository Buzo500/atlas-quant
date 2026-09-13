# v0.6 dev.5 · Primer bloque estadístico

Autorizado el 12/09/2026 con «Haz los 4 últimos»: decidir integración con PR #12,
buscar CSV observado apto, capturar la espera API si reaparece e implementar el
primer bloque estadístico. El diseño `v0_6_robustez_estadistica.md` queda aceptado
para esta implementación. No autoriza nuevas órdenes, datos personales, ensayo,
fusión, etiqueta ni una nueva CI remota.

Autorización posterior «Haz el 2»: rama subida y **CI gratuita correcta** sobre
`6dd01ce`. [Publicación y resultados remotos](publicacion_v06_dev5.md). El alcance
del cálculo no cambia; las verificaciones de abajo corresponden al trabajo local.

## Contrato de implementación

Informe independiente, sin modificar `LabInput` ni identidades o resultados
anteriores. Consulta una revisión inmutable de candidata, el protocolo principal
y todos los protocolos vinculados a esa revisión, declarados explícitamente como
ensayos relacionados. No acredita que ese conjunto incluya experimentos externos
ni variantes OAT como ensayos independientes. Los parámetros bootstrap se fijan
en la política, no son controles para buscar un resultado favorable.

Solo NAV del desarrollo almacenado y calendario de desarrollo; la consulta SQL
no entrega barras, aperturas ni resultados de la reserva al módulo estadístico.
504–2.000 intervalos, posteriores a las primeras `slow` sesiones; el primer
intervalo va del cierre de la sesión `slow` al siguiente. Un hueco en el tramo,
NAV no positivo/no finito o benchmark ausente impide el cálculo. Capital externo
no permitido. Los costes ya forman parte del NAV; no se vuelven a descontar.

NumPy **2.5.2**, ya fijado en requirements. PCG64, semilla 20260911, longitudes
5/10/20, 5.000 réplicas y principal 10. Por longitud: SHA-256 de JSON canónico
UTF-8 `{policy, seed, L, development_hash}`, primeros 16 bytes big-endian.
Por réplica: `integers(0,n,size=n,dtype=int64)` y después `random(n-1)`; el primer
índice es el primer entero. En cada siguiente posición, usar su entero si el
uniforme es menor que `1/L`; si no, avanzar circularmente. Se generan también
enteros que no se usan cuando no hay reinicio. Hash SHA-256 de índices uint32
little-endian, réplica tras réplica. Parejas SMA/BH usan exactamente los mismos.

Media y cuantiles percentiles con interpolación lineal tipo 7, en puntos
porcentuales diarios, redondeo a 12 decimales con half-even. La clasificación de
signo usa los extremos publicados; un cero por redondeo mantiene incertidumbre.
Sin p-valor, anualización, selección de ganadores ni probabilidad de éxito.
Máximo 30 millones de índices por informe y semáforo compartido de dos cálculos.
Publicación y auditoría atómicas con comprobación del contexto; reproducción
desde la instantánea conservada. No se guarda el informe si hay conflicto.

## Experimento de cobertura predeclarado

Definido antes de ejecutarlo, separado de los tests y del flujo del producto.
60 históricos por escenario, 504 intervalos, semilla 20260912 y ruido normal
con desviación marginal 0,01. Escenarios: IID de media cero; AR(1) estacionario
con phi 0,6 y media cero; cambio de media de -0,005 a +0,005 en la mitad del
histórico con ruido IID. Objetivo de referencia: media temporal cero. Las
tres longitudes y 5.000 réplicas se mantienen sin ajustar tras ver resultados.

Se informan cobertura observada, error Monte Carlo mediante intervalo Wilson,
anchura media e interpretación del escenario no estacionario. No es un test
de aceptación con umbral ajustable ni evidencia de cobertura universal. No se
cambia el método para conseguir un 95 % en estas muestras. Plataformas verificadas
y resultados se añadirán tras ejecutarlo; no se atribuye validación al portátil.

## Resultado del experimento de cobertura

Ejecutado en Windows AMD64, Python 3.14.4 y NumPy 2.5.2, 149,87 segundos.
Generador de datos por escenario: PCG64 con `SeedSequence([20260912, índice])`,
índices 0, 1 y 2 en el orden indicado arriba. AR(1) se inicializa con su varianza
marginal; las innovaciones posteriores se escalan con `sqrt(1-0.6²)`.
Cada desarrollo sintético usa el hash de escenario, número e histórico para
derivar las semillas bootstrap con la misma función del producto.

| Escenario | L | Cobertura observada | Wilson 95 % Monte Carlo | Anchura media pp/día |
|---|---:|---:|---:|---:|
| IID | 5 | 57/60 · 95,0 % | 86,3–98,3 % | 0,1735 |
| IID | 10 | 57/60 · 95,0 % | 86,3–98,3 % | 0,1723 |
| IID | 20 | 59/60 · 98,3 % | 91,1–99,7 % | 0,1688 |
| AR(1), phi 0,6 | 5 | 52/60 · 86,7 % | 75,8–93,1 % | 0,2844 |
| AR(1), phi 0,6 | 10 | 53/60 · 88,3 % | 77,8–94,2 % | 0,3032 |
| AR(1), phi 0,6 | 20 | 54/60 · 90,0 % | 79,9–95,3 % | 0,3076 |
| Cambio de media | 5 | 60/60 · 100 % | 94,0–100 % | 0,3076 |
| Cambio de media | 10 | 60/60 · 100 % | 94,0–100 % | 0,3964 |
| Cambio de media | 20 | 60/60 · 100 % | 94,0–100 % | 0,5118 |

La dependencia persistente produce infracobertura en esta referencia, aun siendo
estacionaria. El 95 % es nominal; la muestra mínima y el número de réplicas no
garantizan esa cobertura. No se ajustaron parámetros después del experimento.
El cambio de media genera intervalos más anchos y cubre la media temporal cero,
pero viola la hipótesis de estacionariedad: no valida inferencia sobre un régimen
futuro ni convierte 100 % de estas muestras en un resultado deseable.

Comando reproducible: `.venv/Scripts/python.exe tools/diagnostics/robustness_coverage.py`.
Artefacto local excluido de Git: `output/validation/robustness-coverage.json`, con
540 resultados (180 históricos × tres L), semillas implícitamente derivables e
índices/huellas; hash del resultado
`28aa6ebedb017b077d725f8699c2d1c534fafd6c3549d5fcf84411eec71349c2`.
La igualdad binaria entre equipos todavía no se ha comprobado; la reproducción
registra diferencias de entorno y contrasta los resultados efectivamente calculados.

## Uso

En **Laboratorio → Hipótesis y candidatas de investigación**, abrir una candidata
y desplegar **Robustez estadística del desarrollo**. Elegir un protocolo vinculado,
escribir el motivo, revisar la lista de ensayos y confirmar el alcance exploratorio.
**Calcular y guardar robustez** conserva un informe independiente o un motivo
de no evaluabilidad. Se muestran siempre las tres longitudes cuando se calcula.

El historial permite recuperar informes de revisiones anteriores con su contexto;
**Comprobar reproducción estadística** usa su instantánea, sin volver a importar
datos o abrir la reserva. Cambiar de candidata/revisión reinicia el formulario.
Las métricas económicas cubren todo el desarrollo; los intervalos estadísticos
excluyen el calentamiento. Se muestran límites de exposición configurados, no una
serie de exposición realizada que el informe económico actual no conserva.

Rutas nuevas: POST/GET `/api/lab/robustness`, GET `/{id}` y POST `/{id}/reproduce`.
El listado requiere candidata y está paginado a 20. La creación requiere revisión,
huella, motivo y todos sus protocolos relacionados; no permite editar L, semilla
o réplicas. Escrituras con protección local y sin reintento automático.
Esquema SQLite 5 y los identificadores/resultados previos permanecen intactos.

## Verificación local

- **1.064 Python + 91 subcasos**: 40 casos nuevos, incluidos oráculos numéricos,
  rechazo antes de remuestrear, reproducción, corrupción deliberada aislada,
  auditoría/rollback, conflicto y guardado concurrente idempotente. Oráculo PCG
  pequeño con hash de índices fijo. Recorrido real servicio/datos/candidata con
  504 intervalos sintéticos evaluables; registros previos y reserva intactos.
- **328 frontend**, seis casos nuevos: longitudes/incertidumbre, no evaluable,
  declaración obligatoria, doble envío, conflicto sin reintento, recuperación y
  respuesta tardía tras cambiar candidata. Ocho pruebas Node de transporte.
- Contratos OpenAPI/TypeScript, lint y compilación canónica con manifiesto correctos.
  Lint detectó inicialmente un elemento de estado sin etiqueta semántica; se usa
  `output`. El formulario evita activar el estado de cálculo si falta la declaración.
- **24/24 E2E**, sin omitidos ni reintentos, 102,58 segundos. Entorno
  `e2e-fcfb5be04b53451a976d6a77cd603e2c`; creación/recarga/reproducción del informe
  y comparación exacta de candidata/protocolo antes y después. Anchos CSS
  960/1366/3440 sin desbordamiento; capturas revisadas en 960 y 3440. No es una
  nueva validación física del monitor o del portátil.
- [Captura API](diagnostico_api_20260911.md): 1.840 peticiones correlacionadas,
  ninguna agrupación de al menos un segundo. Incidencia histórica sin reproducir.
  Cierre de ambos servidores con código 0, integridad correcta, puertos liberados
  y base habitual intacta. La app habitual ya estaba detenida y continúa así.

Al cerrar la implementación local todavía no se habían ejecutado subida/CI dev.5.
La [publicación posterior](publicacion_v06_dev5.md) acredita esta ampliación en
Windows, sin nueva PR/fusión/etiqueta. La [revisión guiada posterior](revision_guiada_v06_dev5.md)
completa el recorrido de robustez con el usuario y detecta un defecto visual del
historial en un panel de 565 px CSS. La [corrección posterior](v0_6_historial_contraste.md)
resuelve el desbordamiento, verifica cuatro anchos y contrasta seis casos exactos
en Windows y Ubuntu/WSL. Fuente observada suficiente aún pendiente; no se declara
una versión estable ni se certifica toda la aplicación en Linux.
