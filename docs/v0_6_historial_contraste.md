# Dev.5: historial adaptable y contraste entre entornos

13/09/2026. Continuación autorizada de la [revisión guiada](revision_guiada_v06_dev5.md).
Se mantienen `0.6.0-dev.5`, esquema 5 y rama `codex/v0.6-evaluador`.

## Alcance y resultado local

1. Corregido el botón del historial de robustez: admite varias líneas y nombres
   largos sin salir del panel. El contexto y sus identificadores también pueden
   partirse. No cambia el componente Button compartido ni el cálculo.
2. Verificación a 565, 960, 1366 y 3440 píxeles CSS, este último a 1440 de alto.
   La navegación compacta conserva el desplazamiento dentro de su contenedor
   hasta 1200 px, cerrando el hueco entre el diseño móvil y el de escritorio.
   El E2E usa un nombre de 98 caracteres con una secuencia larga sin espacios;
   comprueba límites del documento/botón, texto completo, foco y apertura con Enter.
   Capturas revisadas de botón estrecho e informe ultrapanorámico. Es una prueba
   de viewport, no una nueva comprobación física de escala Windows.
3. Rama subida sobre `2ee0dec`; CI gratuita **34760823911 correcta**.
4. Contraste real Windows–Ubuntu/WSL: seis casos coinciden exactamente.
5. Ampliada la búsqueda de fuente observada; **no se ha conseguido una fuente
   suficiente**. [Auditoría y decisión](v0_6_csv_observado.md). No se importa ni
   se acredita un CSV incompleto para forzar el simulador.

328 pruebas frontend, ocho de transporte Node, TypeScript, contratos y lint
correctos. Compilación canónica con manifiesto. Los 24 E2E locales pasan en 1,9 min,
sin omitidos ni reintentos: `e2e-b31067aa3e4342609c044d60c3f7d6a9`.
Resultado 0, ambos servidores con salida 0, integridad correcta, puertos liberados,
sin parada forzada y base habitual intacta. Captura API: 1.839 peticiones
correlacionadas, ninguna agrupación lenta de al menos un segundo; no establece
la causa de la incidencia histórica. Tras aplicar solo formato al código se
recompiló y repitió el recorrido de robustez: 1/1 en 7,7 s,
`e2e-3bccff0fa9964e6995ac2e7c52874d4b`, cierre e integridad correctos.

## Publicación y CI gratuita

Commit de código `2ee0dec4c916f36b981118571d88d8a1bdbccef5`, en GitHub dentro de
`codex/v0.6-evaluador`. [CI 34760823911](https://github.com/Buzo500/atlas-quant/actions/runs/34760823911),
trabajo `103733237448`, finalizada correctamente el 13/09 a las 16:00:28
(Europe/Madrid). Resultado remoto verificado mediante API y registro descargado:

- 1.064 Python + 91 subcasos, 108,26 s; dos avisos de dependencias, sin fallos.
- 328 frontend, ocho Node, TypeScript, contratos, lint y build correctos.
- 24 E2E en 3,6 min, sin omitidos ni reintentos; arranque/smoke/parada correctos.
- Node 24.21.0: 3.683 conexiones de la sonda completadas sin fallos.
- Servidores E2E con salida 0, sin pérdida de propietario ni parada forzada.
  Captura API: 1.839 peticiones correlacionadas, seis grupos de al menos un segundo,
  máximo observado en incidentes 1.577,284 ms; causa histórica aún no confirmada.

Presupuesto comprobado antes y después en GitHub: Actions 0 USD, `Stop usage: Yes`.
Lectura de uso incluido: 465 → 486,7 / 2.000 minutos; importe bruto y descuento
iguales, 2,92 USD, **0 USD facturables**. Es el uso mostrado en la consulta de cierre,
no una medición local ni una predicción de facturación. No se cambian presupuestos.
Log local excluido: `output/validation/github-job-103733237448.log`.

Cierre posterior solo Markdown, subido sin una segunda ejecución de CI. Sin nueva
PR, fusión ni etiqueta. Compilación local comprobada mediante `build_frontend.py --check`;
app habitual detenida, base y libros intactos.

## Segundo entorno numérico

Herramienta reproducible: `tools/diagnostics/robustness_cross_environment.py`.
No abre servidores, bases, proveedores ni reserva final. Cada ejecución registra
hashes del código y de las entradas, entorno, oráculo de índices PCG64 y resultados.
La comparación exige sistemas distintos, entradas/código/NumPy iguales y resultados
exactos; no añade una tolerancia después de observar diferencias.

| Entorno ejecutado | Python | NumPy | Arquitectura |
| --- | --- | --- | --- |
| Windows 11 nativo | 3.14.4 | 2.5.2 | AMD64 |
| Ubuntu 24.04 / WSL2, Linux 6.6.87.2 | 3.12.3 | 2.5.2 | x86_64 |

Se usa un venv aislado bajo `var/validation/robustness-linux-venv`, sin cambiar
Python global ni instalar servicios. Casos: NAV constante con 504 intervalos,
NAV variable con 504 y 2000, muestra insuficiente de 4 y los dos informes
sintéticos guardados durante la revisión guiada. Estos últimos se exportan por
proyección SQL de desarrollo/resultado desde la base aislada ya detenida;
SHA-256 de la base sin cambios. No se exportan carteras ni datos reservados.

Los seis resultados completos, hashes de índices, semillas, cuantiles y estados
coinciden exactamente. Los dos casos guardados coinciden además con el resultado
persistido. Se comprobó que el comparador rechaza seis alteraciones: resultado,
código, entradas, mismo sistema, resultado guardado discordante y nombres de casos.

Reproducción, desde la raíz del proyecto con el Python de cada entorno y las
dependencias fijadas disponibles:

```text
python tools/diagnostics/robustness_cross_environment.py run --output output/validation/environment-a.json
python tools/diagnostics/robustness_cross_environment.py run --output output/validation/environment-b.json
python tools/diagnostics/robustness_cross_environment.py compare output/validation/environment-a.json output/validation/environment-b.json --output output/validation/comparison.json
```

Las dos órdenes `run` deben ejecutarse en sus respectivos entornos. Sin `--input`
se usan cuatro casos sintéticos incorporados; para repetir los seis de esta sesión
se pasa en ambos entornos el mismo `--input output/validation/robustness-saved-inputs.json`.
Ese fichero local tiene SHA-256
`655d118bdeb8db588b6b43e166a36cb936c2f22db14e24b5b4d75c98f9421ba5`.

Resultados excluidos de Git: `output/validation/robustness-windows.json`,
`robustness-linux.json`, `robustness-cross-environment.json` y
`robustness-comparator-negatives.json`. Comparación principal: `passed=true`.
Esto acredita esos casos en dos entornos del mismo PC; no certifica otro hardware,
la instalación completa de ATLAS en Ubuntu ni la cobertura estadística del 95 %.
No se ha repetido el experimento Monte Carlo de cobertura en Linux.

## Límites conservados

ATLAS habitual permanece detenido; libros y fuentes habituales intactos, gasto cero.
No se fusiona PR #12 ni se publica etiqueta. La aceptación v0.5 de esa PR, revisión
restante del portátil, ensayo largo y movimientos personales siguen aplazados.
La revisión dev.5 comunicada por el usuario queda registrada y no se le pide repetirla.
