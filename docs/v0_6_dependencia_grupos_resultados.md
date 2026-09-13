# Medias por grupos temporales: resultados predeclarados

13/09/2026. Protocolo `atlas-dependence-groups-v1`, [fijado antes del cálculo](v0_6_dependencia_grupos_plan.md).
**q4 supera los filtros en ambos lotes.** Puede proponerse una revisión de método y contrato, pendiente de autorización.
El método exploratorio de ATLAS permanece intacto. q8 es sensibilidad; L10, referencia. No se elige otro candidato tras observar los resultados.

## Ejecución y trazabilidad

- Código y once oráculos congelados antes de ejecutar en `380e7375f86e09b8c5549c24591041b4f43158e7`.
- 18.000 historias por lote: seis procesos × tres tamaños × 1.000 historias. Semillas 20260916 y 20260917, PCG64/NumPy 2.5.2, Python 3.14.4.
- Confirmación iniciada únicamente después del resultado principal completo, 36 reproducciones exactas y auditoría aritmética independiente correcta.
- 5.000 réplicas bootstrap L10 por historia. 66.000 intervalos por lote incluyendo los oráculos normales: 132.000 en total, más las reproducciones de auditoría.
- Fuentes, 36.000 identidades de semilla y 18.000 casos/hash por lote guardados localmente. Ambos lotes usan las mismas huellas de código y los filtros originales, sin reanudaciones.
- Todos los hashes auditados y 72 historias reproducidas exactamente (0/999 de cada celda en cada lote). Comprobación aritmética adicional desde las 36.000 fuentes con biblioteca estándar, sin importar funciones del experimento.
- Seis procesos de cálculo como máximo y menos de 60 minutos por lote. Sin mercado, GPU, IA, API, bróker ni gasto externo.

| Lote | Cálculo, segundos | Pico por worker, MiB | Pico coordinador, MiB | Reproducciones | Decisión |
|---|---:|---:|---:|---:|---|
| principal | 1455,4944 | 70,1875 | 58,7148 | 36/36 | Pasa |
| confirmacion | 1509,9649 | 70,2500 | 59,8320 | 36/36 | Pasa |

Tiempo/memoria corresponden al lote de cálculo; el pico del coordinador se registra antes de cargar el resumen y no representa un pico total de todo el árbol de procesos. La auditoría y reproducción son fases posteriores. El E2E del producto coincidió con parte del lote principal; no es una medición de rendimiento con CPU desocupada.

## Cobertura: todas las celdas

Cada fila contiene 1.000 historias; porcentajes de intervalos que incluyen la media verdadera 0. Wilson bilateral nominal 95 % para q4. Las 15 filas estacionarias de cada lote deben pasar individualmente; no se promedian.

El cambio de media se publica como estrés: su promedio temporal es 0, pero no tiene una media estacionaria común. Su cobertura alta no acredita el supuesto.

### Lote principal

| Proceso | n | q4 | Wilson q4 | q8 | L10 | Oráculo |
|---|---:|---:|---|---:|---:|---:|
| IID normal | 504 | 93,90 % | 92,24 %–95,22 % | 95,00 % | 94,00 % | 94,80 % |
| IID normal | 1008 | 95,20 % | 93,69 %–96,36 % | 94,90 % | 95,00 % | 95,40 % |
| IID normal | 2016 | 95,60 % | 94,14 %–96,71 % | 94,50 % | 95,00 % | 95,40 % |
| AR(1) 0,6 | 504 | 95,60 % | 94,14 %–96,71 % | 94,40 % | 91,30 % | 95,50 % |
| AR(1) 0,6 | 1008 | 94,10 % | 92,46 %–95,40 % | 94,20 % | 91,80 % | 95,80 % |
| AR(1) 0,6 | 2016 | 94,60 % | 93,02 %–95,84 % | 94,70 % | 91,80 % | 94,50 % |
| AR(1) 0,9 | 504 | 94,60 % | 93,02 %–95,84 % | 94,00 % | 79,50 % | 94,10 % |
| AR(1) 0,9 | 1008 | 95,40 % | 93,92 %–96,53 % | 94,30 % | 82,10 % | 94,90 % |
| AR(1) 0,9 | 2016 | 94,60 % | 93,02 %–95,84 % | 94,60 % | 83,60 % | 95,60 % |
| AR(1) 0,95 | 504 | 94,20 % | 92,58 %–95,49 % | 90,60 % | 68,80 % | 94,40 % |
| AR(1) 0,95 | 1008 | 94,10 % | 92,46 %–95,40 % | 92,50 % | 71,70 % | 94,50 % |
| AR(1) 0,95 | 2016 | 93,80 % | 92,13 %–95,13 % | 94,30 % | 71,50 % | 93,30 % |
| IID t(5) | 504 | 95,00 % | 93,47 %–96,19 % | 93,10 % | 92,90 % | No aplica |
| IID t(5) | 1008 | 95,70 % | 94,26 %–96,79 % | 96,80 % | 96,00 % | No aplica |
| IID t(5) | 2016 | 95,40 % | 93,92 %–96,53 % | 95,90 % | 95,70 % | No aplica |
| Cambio de media | 504 | 100,00 % | 99,62 %–100,00 % | 100,00 % | 100,00 % | No aplica |
| Cambio de media | 1008 | 100,00 % | 99,62 %–100,00 % | 100,00 % | 100,00 % | No aplica |
| Cambio de media | 2016 | 100,00 % | 99,62 %–100,00 % | 100,00 % | 100,00 % | No aplica |

Filtros fallidos: ninguno.

### Lote de confirmación

| Proceso | n | q4 | Wilson q4 | q8 | L10 | Oráculo |
|---|---:|---:|---|---:|---:|---:|
| IID normal | 504 | 93,90 % | 92,24 %–95,22 % | 93,90 % | 93,80 % | 95,10 % |
| IID normal | 1008 | 95,40 % | 93,92 %–96,53 % | 94,40 % | 93,00 % | 93,80 % |
| IID normal | 2016 | 93,90 % | 92,24 %–95,22 % | 94,50 % | 94,80 % | 95,30 % |
| AR(1) 0,6 | 504 | 94,30 % | 92,69 %–95,57 % | 94,50 % | 91,10 % | 94,50 % |
| AR(1) 0,6 | 1008 | 95,00 % | 93,47 %–96,19 % | 95,70 % | 92,70 % | 95,70 % |
| AR(1) 0,6 | 2016 | 94,40 % | 92,80 %–95,66 % | 95,00 % | 91,40 % | 95,00 % |
| AR(1) 0,9 | 504 | 94,00 % | 92,35 %–95,31 % | 93,10 % | 80,90 % | 94,80 % |
| AR(1) 0,9 | 1008 | 94,50 % | 92,91 %–95,75 % | 94,10 % | 79,60 % | 94,70 % |
| AR(1) 0,9 | 2016 | 95,40 % | 93,92 %–96,53 % | 95,00 % | 83,00 % | 95,00 % |
| AR(1) 0,95 | 504 | 95,20 % | 93,69 %–96,36 % | 91,10 % | 70,50 % | 95,70 % |
| AR(1) 0,95 | 1008 | 94,30 % | 92,69 %–95,57 % | 93,50 % | 69,20 % | 94,20 % |
| AR(1) 0,95 | 2016 | 93,90 % | 92,24 %–95,22 % | 94,10 % | 71,60 % | 94,00 % |
| IID t(5) | 504 | 95,60 % | 94,14 %–96,71 % | 95,40 % | 94,30 % | No aplica |
| IID t(5) | 1008 | 94,30 % | 92,69 %–95,57 % | 94,80 % | 94,50 % | No aplica |
| IID t(5) | 2016 | 94,60 % | 93,02 %–95,84 % | 95,00 % | 94,80 % | No aplica |
| Cambio de media | 504 | 100,00 % | 99,62 %–100,00 % | 100,00 % | 100,00 % | No aplica |
| Cambio de media | 1008 | 100,00 % | 99,62 %–100,00 % | 100,00 % | 100,00 % | No aplica |
| Cambio de media | 2016 | 100,00 % | 99,62 %–100,00 % | 100,00 % | 100,00 % | No aplica |

Filtros fallidos: ninguno.

## Anchura e intervalos inválidos

Cero intervalos inválidos en los métodos simulados. Para q4 se exige mediana de anchura/oráculo ≤3 y p95 ≤10 en las 12 celdas normales; no se inventa oráculo para t(5) o cambio de media.

| Lote | Proceso | n | Mediana anchura/oráculo | p95 |
|---|---|---:|---:|---:|
| principal | IID normal | 504 | 1,4528 | 2,6595 |
| principal | IID normal | 1008 | 1,4393 | 2,5790 |
| principal | IID normal | 2016 | 1,4372 | 2,6315 |
| principal | AR(1) 0,6 | 504 | 1,4349 | 2,6989 |
| principal | AR(1) 0,6 | 1008 | 1,4701 | 2,6040 |
| principal | AR(1) 0,6 | 2016 | 1,4436 | 2,5930 |
| principal | AR(1) 0,9 | 504 | 1,4052 | 2,5359 |
| principal | AR(1) 0,9 | 1008 | 1,4016 | 2,5927 |
| principal | AR(1) 0,9 | 2016 | 1,4713 | 2,6247 |
| principal | AR(1) 0,95 | 504 | 1,3350 | 2,3991 |
| principal | AR(1) 0,95 | 1008 | 1,3962 | 2,4930 |
| principal | AR(1) 0,95 | 2016 | 1,4409 | 2,6107 |
| confirmacion | IID normal | 504 | 1,4586 | 2,6395 |
| confirmacion | IID normal | 1008 | 1,4321 | 2,6192 |
| confirmacion | IID normal | 2016 | 1,4199 | 2,6690 |
| confirmacion | AR(1) 0,6 | 504 | 1,4623 | 2,7085 |
| confirmacion | AR(1) 0,6 | 1008 | 1,4224 | 2,5794 |
| confirmacion | AR(1) 0,6 | 2016 | 1,4342 | 2,6452 |
| confirmacion | AR(1) 0,9 | 504 | 1,3710 | 2,5928 |
| confirmacion | AR(1) 0,9 | 1008 | 1,4315 | 2,5042 |
| confirmacion | AR(1) 0,9 | 2016 | 1,4576 | 2,5963 |
| confirmacion | AR(1) 0,95 | 504 | 1,3538 | 2,4183 |
| confirmacion | AR(1) 0,95 | 1008 | 1,4042 | 2,5255 |
| confirmacion | AR(1) 0,95 | 2016 | 1,4218 | 2,5476 |

## Diagnósticos y límites

El resumen JSON conserva las 132 filas método/celda de ambos lotes: coberturas/Wilson, sesgo de la media, seis cuantiles de anchura, ratios frente al oráculo, fallos por cola y degeneraciones. Incluye 72 tablas pareadas 2×2 (q4–q8 y q4–L10) y 72 conjuntos de correlaciones entre grupos vecinos, estimados entre historias.

Las tablas pareadas usan `00` ninguno cubre, `01` solo el comparador, `10` solo q4, `11` ambos. Comparan las mismas fuentes; no son una nueva prueba de selección. Las correlaciones observadas distintas de cero recuerdan que dividir una serie no crea independencia.

Los filtros son criterios diagnósticos de ingeniería: no certifican cobertura simultánea entre celdas, equivalencia estadística, normalidad de retornos reales, estabilidad entre regímenes ni rentabilidad de una estrategia. Los datos no son ensayos observados de ATLAS. No se abre ninguna reserva ni se promueve una candidata de trading.

La referencia conceptual se mantiene en el protocolo: [Ibragimov y Müller (2010)](https://www.princeton.edu/~umueller/tstat.pdf) requiere estimadores de grupo aproximadamente normales y asintóticamente independientes; [NIST](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3672.htm) sirve de referencia para cuantiles t, contrastados mediante integración numérica independiente antes de Monte Carlo.

## Evidencia y reproducción

[Resumen completo versionado](evidence/dependence-groups-v1-summary.json): planes, hashes de código, resultados, inventarios, reproducciones, recursos y auditorías de ambos lotes. Fuentes completas bajo `var/validation/dependence-groups-main/` y `var/validation/dependence-groups-confirmation/`, excluidas de Git; conservar esas carpetas para auditar los casos sin volver a simular.

- Resultado principal: `03b365224d12a7fb1ac3a753c19802a12e4291e94c47c5940c9999f3852489b8`.
- Resultado confirmacion: `67f504ec826b928dd914e34bd9c92f483fee3566c885dc5e32d2f7b4638cb82a`.

Auditoría independiente sobre las carpetas ya calculadas:

```powershell
.\.venv\Scripts\python.exe tools/diagnostics/audit_dependence_groups.py --directory var/validation/dependence-groups-main
.\.venv\Scripts\python.exe tools/diagnostics/audit_dependence_groups.py --directory var/validation/dependence-groups-confirmation
```

Para repetir el cálculo completo, usar salidas nuevas con los archivos congelados:

```powershell
.\.venv\Scripts\python.exe tools/diagnostics/dependence_groups.py --output var/validation/groups-replica-principal --seed 20260916 --workers 6
.\.venv\Scripts\python.exe tools/diagnostics/dependence_groups.py --output var/validation/groups-replica-confirmacion --seed 20260917 --workers 6 --confirm-from var/validation/groups-replica-principal
```

El coordinador impide confirmar un principal que no haya pasado o cambiar las huellas entre lotes. No sustituir semillas tras un resultado negativo. Estos comandos reproducen el estudio; no son necesarios para arrancar ATLAS.

Estado del producto y comprobaciones de UI/PDF: [validación dev.9](v0_6_dev9_validacion.md).
