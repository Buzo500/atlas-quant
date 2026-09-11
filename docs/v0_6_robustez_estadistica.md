# v0.6 · Diseño inicial de robustez estadística

Definición autorizada el 11/09/2026. **No implementada**: no añade un test,
una aprobación ni una probabilidad de éxito al Laboratorio actual. La siguiente
implementación requiere aceptar este contrato y disponer de datos suficientes.

## Pregunta y unidad de análisis

Estimar la incertidumbre de la media diaria del exceso de rentabilidad neta de
una SMA fija respecto a comprar y mantener, sobre el **desarrollo** de un protocolo
congelado. Efectivo queda como contraste descriptivo. No responder con este cálculo
si la estrategia será rentable en el futuro ni si es apta para operar.

Entradas: protocolo y huella de desarrollo, versión de política económica,
configuración, fuente y calendario, conjunto explícito de ensayos relacionados y
revisión de candidata que motivó la consulta. No elegir retrospectivamente el
benchmark que favorezca el resultado. El registro actual no acredita haber
registrado todos los experimentos realizados fuera de ATLAS.

Para cada intervalo consecutivo del calendario, calcular
`r_SMA,t = NAV_SMA,t / NAV_SMA,t-1 - 1`, análogo para comprar y mantener, y
`d_t = r_SMA,t - r_BH,t`. Incluir costes ya contabilizados; no cobrarlos otra vez.
No confundir este exceso aritmético con rentabilidad relativa compuesta. No
mezclar curvas de cuentas walk-forward independientes ni sus reinicios de capital.

Solo intervalos posteriores al calentamiento de la media lenta, fijado por el
protocolo, con NAV positivo, completo y disponible para ambas estrategias. Un hueco
invalida el periodo, no se elimina silenciosamente. El último punto previo al
intervalo también debe cumplir. No convertir movimientos externos en rendimiento.

## Método propuesto

Bootstrap estacionario **pareado** de los vectores `(r_SMA,t, r_BH,t)`: elegir un
índice uniforme al empezar; en cada paso reiniciar en otro índice uniforme con
probabilidad `1/L`, y en otro caso avanzar circularmente. Misma secuencia de índices
para ambas estrategias. Conservar la dependencia local; no barajar operaciones
individuales ni volver a aplicar el evaluador SMA a precios sintéticos así unidos.

Este método está pensado para observaciones estacionarias débilmente dependientes;
esas hipótesis no quedan demostradas por un gráfico o un resultado favorable.
[Politis y Romano, The Stationary Bootstrap](https://www.stat.purdue.edu/docs/research/tech-reports/1991/tr91-03.pdf).

Decisiones de producto propuestas, no umbrales universales del artículo:

- `L = 10` sesiones como especificación principal; `L = 5` y `20` como sensibilidad
  predeclarada. Mostrar las tres, sin escoger después la más favorable.
- 5.000 réplicas por longitud; tamaño de réplica igual al número de intervalos.
  Mínimo 504 intervalos completos y al menos 25 bloques esperados (`n/L`) en cada
  longitud. Máximo 2.000 intervalos y 30 millones de índices en conjunto; contador
  de trabajo previo y límite compartido de dos cálculos simultáneos.
- Distribución de la media diaria del exceso; intervalo percentil bilateral al
  95 %, cuantiles con interpolación lineal, definición exacta fijada en el contrato.
  Media y extremos en puntos porcentuales diarios. No multiplicar por 252 para
  convertirlo en una predicción anual. No presentar `P(media > 0)` de réplicas
  como probabilidad de que la estrategia funcione.
- Sin p-valor confirmatorio ni etiqueta «significativa» en el alcance inicial.
  Es un intervalo exploratorio condicionado al histórico y al método, sin ajuste
  por selección entre candidatas. Una muestra mínima no garantiza validez.

## Reproducibilidad

Identificador propuesto `atlas-robustness-stationary-v1`. PRNG PCG64 de una versión
fijada de NumPy (dependencia a evaluar antes de instalar), semilla maestra entera
`20260911`. Derivar tres semillas con SHA-256 de una codificación canónica de
`{policy, seed, L, development_hash}`, primeros 128 bits big-endian; documentar
el orden de llamadas al generador y la generación uniforme sin sesgo.

Guardar semilla, PRNG y versión, orden de índices y su hash, fuente, protocolo,
hashes de NAV/retornos, configuración, resultados y motivos de no evaluabilidad.
Datos económicos decimales permanecen intactos; conversión explícita a float64
solo en esta capa estadística, rechazo de no finitos y salida redondeada según
contrato. Calcular fuera de transacción, comprobar contexto al guardar y publicar
informe/auditoría atómicos. Nunca reescribir el protocolo o sus resultados.

Pruebas de referencia fijarán tolerancias numéricas e índices exactos. No prometer
igualdad binaria multiplataforma antes de probar Windows y el segundo entorno;
el informe declarará las versiones realmente verificadas.

## Interpretación y criterios

Estados: `no_evaluable` si falla un requisito; `exploratory` si se puede calcular.
Dentro de exploratory, describir por separado si el intervalo principal incluye
cero y si la conclusión cambia con L. Cualquier intervalo que incluya cero deja
la dirección incierta bajo esa especificación; todos positivos siguen sin autorizar
promoción automática. Mostrar pérdidas, costes, operaciones y exposición del
informe económico como contexto, sin convertir 504 días en 504 apuestas independientes.

Si hay búsqueda de parámetros o candidatas, el resultado seleccionado necesita
control de selección. PBO/CSCV es un trabajo posterior con matriz alineada de
todos los ensayos y universo declarado; no se puede inferir PBO de las ocho
variantes OAT ni de una revisión aislada. La multiplicidad puede producir falsos
positivos aun con buenos resultados individuales.
[Bailey, Borwein, López de Prado y Zhu](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

La prueba final reservada permanece sin leer ni abrir. Tras elegir parámetros,
cualquier uso confirmatorio requerirá contrato separado, una sola apertura
explícita y constancia de toda exposición previa. No reutilizar la misma reserva
para ajustar bloques, semillas, hipótesis o umbrales.

## Pruebas que debe superar la implementación futura

1. Oráculo pequeño con índices predefinidos: medias, pares, reinicios circulares,
   calentamiento y cuantiles exactos; semilla fija reproducible.
2. Rechazo de huecos, NAV cero/no finito, muestra insuficiente, trabajo excesivo,
   benchmark o fuente incompatibles; sin rellenar observaciones.
3. Series sintéticas independientes, autocorrelacionadas y con cambio de régimen:
   evaluar cobertura y limitaciones del método. La cobertura se contrasta en un
   experimento separado predeclarado, sin ajustar parámetros hasta que «pase».
4. Acceso protegido a la reserva que falle ante cualquier lectura; hashes antiguos
   intactos, rollback ante conflicto y auditoría en una única transacción.
5. Interfaz con las tres longitudes y limitaciones, reproducción desde almacenamiento
   y prueba entre equipos; jamás un botón de activar estrategia desde este informe.
