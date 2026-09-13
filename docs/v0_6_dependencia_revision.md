# Dependencia fuerte: revisión y siguiente experimento

13/09/2026. Revisión autorizada, **sin modificar el método del producto**. La
evidencia previa `atlas-robustness-coverage-v2` queda congelada: con n=504 y L=10,
AR(1) phi=0,9 cubrió 73/100 (Wilson 95 %: 63,57–80,73 %). No se convierte el
resultado de L=20 en el principal ni se sustituye una semilla desfavorable.

## Diagnóstico matemático y de implementación

El código comparte índices para ambos retornos, conserva continuidad circular
hasta reinicios independientes de probabilidad 1/L y usa PCG64. La revisión y
los oráculos de índices existentes no revelan un muestreo IID accidental o una
separación de los pares. El contraste Windows–WSL anterior comprueba reproducción,
no cobertura. No atribuir toda la infracobertura a un fallo de implementación.

Para un AR(1) estacionario de media cero y varianza marginal sigma², el cálculo
exacto de la varianza del promedio de n observaciones es:

\[
\operatorname{Var}(\bar X_n)=\frac{\sigma^2}{n^2}
\left[n+2\sum_{k=1}^{n-1}(n-k)\phi^k\right].
\]

Es una identidad del modelo declarado, no un estimador para precios de mercado.
Se obtiene sumando las n² covarianzas, con gamma(k)=sigma² phi^|k|. Para n grande,
el tamaño efectivo aproximado es n(1−phi)/(1+phi): 126 para phi=0,6 y 26,53 para
phi=0,9 cuando n=504. Tener 504 intervalos no garantiza mucha información
independiente. El tamaño efectivo aproximado no sustituye un diagnóstico empírico.

Se contrastó la fórmula con la suma explícita de una matriz de covarianzas de
8 × 8 para phi=0/0,6/0,9/0,95 (tolerancia relativa 1e−13). Con n=504 y sigma=0,01,
las anchuras totales gaussianas al 95 % son 0,174607, 0,348565, 0,753909 y
1,069135 puntos porcentuales diarios. Es un oráculo analítico, no un nuevo ensayo
bootstrap; registro local `output/validation/dev7-ar1-oracle.json`.

En el bootstrap estacionario, sobrevivir k pasos sin reiniciar tiene probabilidad
(1−1/L)^k. Bloques cortos atenúan dependencias largas; aumentar L también reduce
el número de bloques y no garantiza buena cobertura en muestras cortas. Es una
explicación compatible con el experimento, no una descomposición demostrada de
todo su error. El criterio actual de 25 bloques esperados es un límite operativo,
no un teorema de cobertura.

La [propuesta original de Politis y White](https://www.tandfonline.com/doi/abs/10.1081/ETC-120028836)
estima longitud mediante estructura de dependencia. Debe estudiarse junto con la
[corrección de Patton, Politis y White de 2009](https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf),
que modifica la constante de varianza del bootstrap estacionario y el selector
derivado. Optimizar estimación de varianza no garantiza por sí mismo la cobertura
del intervalo percentil que usa ATLAS. No copiar el algoritmo original sin su
corrección ni ajustar L maximizando los resultados de una estrategia.

## Protocolo fijado para el siguiente experimento

Identificador `atlas-dependence-study-v1`, semilla 20260914, PCG64/NumPy 2.5.2.
Este documento define el experimento; **aún no se ha ejecutado ni implementado el
selector alternativo**. No requiere datos de mercado, API ni GPU.

- Objetivo: separar un problema del estimador de incertidumbre de un problema de
  implementación, contrastando la cobertura y anchura contra un oráculo conocido.
- Muestras n=504 y n=1008; 500 historias independientes por celda. Seis DGP:
  IID normal, AR(1) phi=0,6, 0,9 y 0,95 con inicialización estacionaria, IID t(5)
  con varianza igualada y cambio de media simétrico ±0,5 % como estrés aparte.
  Varianza marginal estacionaria 0,01², media cero. No agregar el estrés al
  porcentaje de cobertura estacionaria.
- Comparadores fijados: método publicado L=10, L=20 y L=40 como sensibilidades,
  y oráculo gaussiano de varianza exacta solo en
  los DGP normales estacionarios. El oráculo usa parámetros del generador, no
  información disponible en una estrategia real; no puede convertirse en producto.
- 5.000 réplicas pareadas por método bootstrap, cuantiles lineales. Mismas
  historias para todos los métodos; semillas derivadas del SHA-256 del JSON
  canónico con semilla maestra, DGP, n, historia y longitud, usando los primeros
  16 bytes como entero big-endian. Sin truncar L ni descartar resultados: L=40
  tiene menos de 25 bloques esperados con n=504 y se estudia solo como diagnóstico,
  no como configuración admisible del producto. No hay selector adaptativo en
  este experimento; requiere diseño y validación propios posteriores.
- Salidas obligatorias: cobertura con Wilson, anchura, sesgo de la media, errores
  por ambas colas y distribución de longitudes. Para comparar dos métodos sobre
  las mismas historias, informar las tablas pareadas de aciertos/fallos; no tratar
  sus coberturas como estimaciones independientes.
- Control de implementación: fórmula exacta de varianza contrastada con suma de
  matriz de covarianzas en un n pequeño y límites phi=0; curvas e índices de
  referencia. Fallos del oráculo obligan a diagnosticar el experimento.
- Regla previa: un método candidato no pasa a producto si alguna celda estacionaria
  normal tiene cobertura estimada menor del 92 % o el límite superior Wilson queda
  por debajo del 95 %. Cumplir ese filtro es una condición de investigación, no
  acreditación del 95 % ni decisión automática de promoción. El estrés se publica
  completo aunque favorezca aparentemente al método.
- Después de elegir un diseño, ejecutar un contraste independiente con semilla
  20260915 y 500 historias por celda, sin volver a seleccionar parámetros.
  La semilla independiente no borra que hubo selección de método en la fase anterior.

## Decisión de esta revisión

Conservar L=10 y los informes actuales como exploratorios. No mostrar un sello de
«validado» ni usar estos intervalos para activar paper trading. El siguiente cambio
estadístico debe ejecutar primero el contraste predeclarado y, si se estudia el
selector corregido, fijar por adelantado su fórmula, cotas y tratamiento de fallos.
Las simulaciones observadas de Zalando y HelloFresh siguen siendo
ejemplos retrospectivos económicos; no se ha aplicado este experimento a ellas.
