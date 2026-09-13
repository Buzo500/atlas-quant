# Siguiente experimento: medias por grupos temporales

13/09/2026. **Definición autorizada; sin implementar ni ejecutar el experimento.**
Protocolo `atlas-dependence-groups-v1`. No altera el método de ATLAS ni las
evidencias guardadas. Responde al [resultado negativo anterior](v0_6_dependencia_resultados.md).

## Pregunta y método elegido antes del cálculo

Contrastar si un intervalo t sobre pocas medias de grupos temporales mejora la
cobertura con dependencia fuerte, a costa de anchura. Candidata única: **q=4**.
q=8 será sensibilidad diagnóstica; no podrá sustituir a q=4 si esta falla.
No hay selector de L, optimización por rentabilidad o búsqueda de particiones.

Referencia primaria: [Ibragimov y Müller (2010), secciones 2 y 3](https://www.princeton.edu/~umueller/tstat.pdf).
Su justificación requiere estimadores de grupo aproximadamente normales y
asintóticamente independientes, con una media común. Cortar una serie en grupos
no garantiza esas condiciones en una muestra finita. Esta propuesta contrasta
esa limitación; no presupone que el artículo valide los retornos de una estrategia.

Para una serie de excesos diarios X de longitud n, dividir desde el primer dato
en q grupos consecutivos disjuntos de igual tamaño m=n/q, sin huecos ni circularidad.
Todos los tamaños fijados son divisibles por 4 y 8. Sea g_j la media del grupo:

\[
\bar g=q^{-1}\sum_j g_j=\bar X,\qquad
SE_g=\sqrt{\frac{\sum_j(g_j-\bar g)^2}{q(q-1)}}.
\]

Intervalo bilateral nominal 95 %:
`[g_bar − t(0.975, q−1) × SE_g, g_bar + t(0.975, q−1) × SE_g]`.
No usar 1,96 ni grados de libertad n−1. Sin truncar los extremos a cero.
Para SE_g=0: estado degenerado explícito, no intervalo de certeza; se registra
como resultado no evaluable, incluyendo los controles deterministas constantes.

Las series sintéticas representan excesos, no precios. En un eventual uso en
ATLAS, se agruparían retornos de una ejecución ya fijada, sin reiniciar la estrategia
o su cuenta en cada grupo. No se adapta ni se calcula esa integración ahora.

## Diseño fijo

| Elemento | Decisión previa |
|---|---|
| Datos | Solo simulación local, sin mercado, claves, IA o GPU |
| n | 504, 1008, 2016 intervalos |
| Historias | 1.000 por proceso y n; 18.000 en total |
| Procesos | IID normal, AR(1) phi=0,6/0,9/0,95, IID t(5), cambio de media |
| Media/escala | Media 0 y desviación marginal 0,01 en los cinco estacionarios |
| AR(1) | X_0 normal estacionaria; innovación normal de sd 0,01√(1−phi²) |
| t(5) | t estándar × 0,01√(3/5), sin dependencia |
| Estrés | Ruido IID normal sd 0,01; media −0,005 primera mitad y +0,005 segunda |
| Métodos | q4 candidata; q8 sensibilidad; bootstrap actual L10 de referencia |
| Réplicas L10 | 5.000, índices pareados y cuantiles lineales, implementación actual |
| Oráculo | Gaussiano con varianza exacta conocida solo en los cuatro procesos normales estacionarios |
| Semilla principal | 20260916, PCG64/NumPy 2.5.2, float64 |
| Confirmación | 20260917, mismo diseño, solo si q4 supera todos los filtros principales |

Usar las mismas historias para los tres métodos. Derivar semilla por SHA-256 del
JSON UTF-8 canónico, claves ordenadas, sin espacios: `protocol`, `seed`, `dgp`,
`n`, `history` (0–999), `method`. Valores dgp iguales al estudio anterior;
`method="source"` para historia y `method="stationary_L10"` para remuestreo.
Tomar los primeros 16 bytes como entero big-endian. q4/q8 no consumen RNG.
Registrar el JSON exacto y su hash antes de ejecutar; nunca reutilizar historias
anteriores como confirmación independiente. No ejecutar la semilla 20260915 del
estudio fallido para rescatarlo.

## Filtros y decisión

Aplicar a q4 en **cada una de las 15 celdas estacionarias**, sin promediar entre
procesos o descartar phi=0,95 tras verlo:

1. Cero errores numéricos/intervalos no finitos o degenerados en esas celdas.
2. Cobertura empírica entre 0,93 y 0,99, y límite inferior Wilson bilateral 95 % ≥0,92.
3. En las 12 celdas con oráculo: mediana de anchura/oráculo ≤3 y percentil 95 ≤10.
4. Reproducción y oráculos de implementación correctos antes de leer la decisión.

Son umbrales diagnósticos de ingeniería, fijados aquí; no certifican cobertura
simultánea del 95 % entre celdas ni constituyen una prueba de equivalencia.
El límite de anchura evita declarar útil un intervalo casi vacuo. El cambio
de media se publica separado; su media temporal 0 no es una media estacionaria.
Ni siquiera 100 % de cobertura en ese estrés lo convierte en caso acreditado.

Si q4 falla un filtro, conservar el resultado negativo y no ejecutar confirmación.
Si pasa, ejecutar 20260917 sin cambiar código, parámetros, tamaños o filtros;
exigir que también pase, separando ambos lotes. Pasar permite proponer una revisión
de método y contrato, **no integrar automáticamente ni promover una estrategia**.

## Evidencia y oráculos antes de ejecutar

- Por historia: fuente/hash, media, medias de grupos, SE, cuantil t empleado,
  intervalo, cobertura, cola del fallo, anchura y resultados de L10/oráculo.
- Por celda: cobertura/Wilson, sesgo de la media, frecuencia de degeneración,
  cuantiles de anchura, dos colas y tablas pareadas 2×2 q4–q8 y q4–L10.
- Como diagnóstico del supuesto, correlación entre medias de grupos vecinos
  estimada **entre historias** de la misma celda; nunca estimarla con solo cuatro
  medias de una única historia y presentarla como evidencia suficiente.
- Oráculo IID normal: medias de grupos independientes normales; estadístico t
  con q−1 grados de libertad. Cuantiles contrastados con una referencia independiente
  y CDF numérica con tolerancia 1e−10 antes de ejecutar las simulaciones.
- Vector de medias [-3,-1,1,3]: centro 0 y SE=√(5/3). Traslación y escala positiva
  trasladan/escalan el intervalo; escala negativa intercambia sus extremos.
- AR(1): contrastar varianza de la media y covarianzas de medias de grupos contra
  suma explícita de gamma(k)=0,01² phi^|k| en un caso pequeño. No simular el oráculo.
- Conservar plan, código, versiones, 18.000 fuentes y casos; auditar hashes y
  reproducir historias 0 y 999 de cada celda, no solo ejemplos favorables.

Implementación futura separada bajo `tools/diagnostics`, sin nuevas dependencias
de arranque. Máximo seis procesos locales, 60 min por lote, cancelación limpia;
si vence el límite, registrar lote incompleto y reanudar los mismos identificadores,
sin sustituir semillas o eliminar casos. Registrar tiempo/memoria. Gasto externo cero.

## Orden de ejecución pendiente

1. Implementar cálculo aislado, referencias independientes y manifiesto de plan.
2. Revisar fórmulas, semillas y límites; congelar commit antes de Monte Carlo.
3. Ejecutar lote principal y publicar todas las celdas.
4. Ejecutar confirmación solo si se cumple su condición previa.
5. Decidir si merece una propuesta versionada para ATLAS; el producto sigue exploratorio.
