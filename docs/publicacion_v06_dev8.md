# Publicación dev.8 · 13/09/2026

El usuario acepta expresamente el PDF («El pdf me parece bien») y autoriza las
cinco propuestas: diagnóstico API, aceptación visual, subida/CI gratuita y definición
del siguiente experimento y de informes por fechas/cartera. La aceptación corresponde
al PDF dev.8 presentado, no a PR #12, portátil o una declaración de versión estable.

Código inicial `823b336`, rama `codex/v0.6-evaluador`, 0.6.0-dev.8, esquema 5.
Se añade captura de fallos de recursos estáticos y cuatro regresiones durante
el [diagnóstico](diagnostico_api_20260913.md); no cambia el motor ni el formato PDF.
Código validado y subido: `2091ea1c2557a9d067049e73673e26e14ded6c6c`.
[CI manual gratuita 34774872432 correcta](https://github.com/Buzo500/atlas-quant/actions/runs/34774872432),
job Windows `103771035946`. Sin PR, fusión o etiqueta nueva.

Antes de ejecutar: 531,7/2.000 minutos incluidos y 0 USD facturables comprobados
en GitHub. Actions mantiene presupuesto 0 USD y `Stop usage: Yes` verificados;
no se cambian ajustes. Consulta posterior, 13/09/2026 a las 18:48 UTC:
**555/2.000 minutos y 0 USD facturables**; 3,33 USD brutos totalmente descontados.
El incremento observado es 23,3 minutos incluidos, no un cargo.

Comprobación local posterior de diagnóstico: ocho pruebas Python de captura,
tres frontend nuevas, TypeScript/lint/build correctos; 25 E2E de 25, sin omitidos
ni reintentos, 110,31 s. Run `e2e-6ced188b297e41e3add95b36d5e84145`:
ambos servidores 0, sin parada forzada, puertos libres, integridad y base habitual
conservadas. Captura 1.887 grupos/78 incidencias cortas, ninguna lenta ≥1 s.
No se repite íntegramente la suite Python/frontend local previa: la CI sí ejecuta
la regresión completa de este commit. La validación previa dev.8 está en continuidad.

## Resultado remoto

- **1.169 Python + 91 subcasos**, dos warnings, 111,47 s; **341 frontend** en 41 archivos.
- **Ocho Node**, contratos, TypeScript, lint y compilación canónica correctos.
- Node **24.21.0**: sonda de **3.666 conexiones sin fallos** en 30,305 s.
- **25 E2E de 25**, sin reintentos ni omitidos, 4,7 min. Run aislado
  `e2e-334f3ec90502429eb43b1c3c639b65ec`, resultado 0, backend/frontend 0/0,
  sin parada forzada ni errores de limpieza/propietario, puertos liberados,
  integridad correcta y base habitual conservada.
- Arranque y parada del smoke remoto correctos; job completo terminado con éxito.
- Captura correlacionada: **1.910 grupos, 73 incidencias**, de las que **23 ≥1 s**
  (ocho API y quince recursos estáticos), máximo **1.547,308 ms**. Veintiuna lentas
  llegan a `client body_end`; dos muestran fin de envío ASGI y cancelación previa
  en el proxy, sin finalización del cliente. No se reproduce el timeout de 10 s
  ni `net::ERR_NO_BUFFER_SPACE`. El informe correlacionado no está truncado;
  las colas adicionales de logs de servidor sí lo están.

La incidencia API histórica permanece abierta. El fallo local D3 sí queda vinculado
a agotamiento de puertos con evento Windows 4231; no atribuir ese origen a todas
las incidencias. [Diagnóstico y evidencia](diagnostico_api_20260913.md).

## Cierre y alcance

El siguiente [experimento por grupos](v0_6_dependencia_grupos_plan.md) queda definido
con filtros previos y confirmación condicionada, sin ejecutarlo ni cambiar el método.
El [contrato de informes por periodo](informes_periodo_contrato.md) especifica primero
exportar informes D7 guardados; posiciones históricas y subperiodos retrospectivos
necesitan sus propias proyecciones coherentes. No se implementa todavía esa ampliación.

Los commits posteriores, desde `d889b14`, solo añaden documentación y evidencia
seleccionada. No atribuirles una nueva ejecución de CI ni confundirlos con otro
cambio de producto.

Durante el trabajo la carpeta habitual apareció en `master`; se continuó en un
checkout aislado. Por respuesta expresa del usuario se vuelve a
`codex/v0.6-evaluador` dev.8 y se recompila mediante `tools/build_frontend.py`.
Manifiesto verificado, checkout temporal retirado después de comprobarlo limpio.
La carpeta `output/analysis/`, ajena a este cierre y sin seguimiento, se conserva
sin añadirla a Git.

La aplicación habitual sigue detenida, puertos 3000/8000 libres y base intacta:
SHA-256 `2791f15e1bb5be5833117810ce5de745e4dfb46817850c4d8d8cbc3cc2bc5549`.
Trabajos aplazados conservados. Sin nuevas órdenes, IA de pago o datos personales.
