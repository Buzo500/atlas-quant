# Dependencia: resultado del experimento fijado

Ejecutado el 13/09/2026, sin cambiar el protocolo ni el método del producto.

## Decisión

**Ninguna longitud pasa los filtros diagnósticos.** L=40 mejora algunos casos de dependencia fuerte, pero tampoco alcanza la cobertura requerida; a n=504 ni siquiera cumple los 25 bloques esperados del contrato de producto. No seleccionar a posteriori, no cambiar L=10 principal ni promover estrategias.

La semilla independiente 20260915 estaba condicionada a seleccionar un diseño que superara los filtros. Al fallar los tres, no se ejecuta para intentar rescatar estos resultados. El siguiente trabajo requiere un protocolo nuevo, justificado y fijado antes de calcular.

Continuación autorizada: [protocolo de medias por grupos temporales](v0_6_dependencia_grupos_plan.md),
definido el 13/09. q4 candidata única, q8 sensibilidad, semillas nuevas; todavía
sin implementar ni ejecutar. No cambia esta decisión ni el método del producto.

## Cobertura sobre 500 historias por celda

| Proceso | n | L10 | L20 | L40 | Oráculo |
|---|---:|---:|---:|---:|---:|
| iid_normal | 504 | 464/500 (92.8 %) | 462/500 (92.4 %) | 461/500 (92.2 %) | 473/500 (94.6 %) |
| iid_normal | 1008 | 476/500 (95.2 %) | 472/500 (94.4 %) | 461/500 (92.2 %) | 477/500 (95.4 %) |
| ar1_0.6 | 504 | 459/500 (91.8 %) | 461/500 (92.2 %) | 453/500 (90.6 %) | 478/500 (95.6 %) |
| ar1_0.6 | 1008 | 460/500 (92.0 %) | 463/500 (92.6 %) | 461/500 (92.2 %) | 469/500 (93.8 %) |
| ar1_0.9 | 504 | 389/500 (77.8 %) | 417/500 (83.4 %) | 419/500 (83.8 %) | 479/500 (95.8 %) |
| ar1_0.9 | 1008 | 401/500 (80.2 %) | 427/500 (85.4 %) | 435/500 (87.0 %) | 475/500 (95.0 %) |
| ar1_0.95 | 504 | 321/500 (64.2 %) | 363/500 (72.6 %) | 380/500 (76.0 %) | 471/500 (94.2 %) |
| ar1_0.95 | 1008 | 361/500 (72.2 %) | 401/500 (80.2 %) | 429/500 (85.8 %) | 476/500 (95.2 %) |
| iid_student5 | 504 | 470/500 (94.0 %) | 465/500 (93.0 %) | 456/500 (91.2 %) | No aplica |
| iid_student5 | 1008 | 481/500 (96.2 %) | 477/500 (95.4 %) | 471/500 (94.2 %) | No aplica |
| mean_break | 504 | 500/500 (100.0 %) | 500/500 (100.0 %) | 500/500 (100.0 %) | No aplica |
| mean_break | 1008 | 500/500 (100.0 %) | 500/500 (100.0 %) | 500/500 (100.0 %) | No aplica |

El oráculo conoce la varianza marginal y la dependencia AR(1) verdaderas, que no están disponibles en datos observados. Sirve como comprobación de la simulación, no es un estimador implementable sin esos conocimientos. t(5) es un contraste de colas; el cambio de media es estrés no estacionario, no evidencia de cobertura general.

## Protocolo y auditoría

- 6 procesos × 2 tamaños × 500 historias = 6.000 historias independientes.
- 5.000 réplicas por longitud, L=10/20/40; semilla 20260914, PCG64 y NumPy 2.5.2, Python 3.14.4 Windows.
- 18.000 resultados bootstrap y 4.000 intervalos oráculo; fuentes, intervalos, colas, sesgos, anchuras, Wilson y tablas pareadas conservados por celda.
- Distribuciones de longitudes realizadas: primeras 100 réplicas de la historia 0 por celda/longitud, incluyendo bloque final truncado.
- Auditoría: 6.000 hashes de fuentes, hashes de plan/código/archivos, resúmenes y tablas pareadas recalculados; 12 historias reproducidas exactamente con 5.000 réplicas por longitud.
- Tiempo de ejecución: 1106.11 segundos, seis procesos locales. Sin API/red ni coste facturable.

Evidencia local: `output/validation/dependence-study-v1/` (`plan.json`, `histories.jsonl`, `cases.jsonl`, `results.json`, `audit.json`). No subir las matrices fuente por defecto. El código de diagnóstico permite reproducirlo en una carpeta nueva:

```powershell
.\.venv\Scripts\python.exe tools/diagnostics/dependence_study.py --output output/validation/dependence-repeat --workers 6
```

Huella del resultado: `2d9ec9f7b08ba912a197e20eeefec54be54a2762b2098c82825beec562423a33`.

[Protocolo previo](v0_6_dependencia_revision.md) · [Alcance autorizado y derivación de semillas](v0_6_dev8_plan.md).

Resumen completo conservado en Git: [JSON con Wilson, sesgos, cuantiles de anchura, tablas pareadas y filtros](evidence/dependence-study-v1-summary.json). Las matrices de historias permanecen locales.

## Detalle por celda y método

| Proceso | n | Método | Wilson 95 % | Anchura media pp/día | Intervalo por encima / por debajo de 0 |
|---|---:|---|---|---:|---|
| iid_normal | 504 | L10 | 90.19–94.75 % | 0.170090 | 16 / 20 |
| iid_normal | 504 | L20 | 89.74–94.41 % | 0.165725 | 17 / 21 |
| iid_normal | 504 | L40 | 89.51–94.24 % | 0.157445 | 20 / 19 |
| iid_normal | 504 | oracle | 92.26–96.26 % | 0.174607 | 12 / 15 |
| iid_normal | 1008 | L10 | 92.96–96.75 % | 0.121583 | 16 / 8 |
| iid_normal | 1008 | L20 | 92.03–96.10 % | 0.120275 | 16 / 12 |
| iid_normal | 1008 | L40 | 89.51–94.24 % | 0.117605 | 20 / 19 |
| iid_normal | 1008 | oracle | 93.19–96.92 % | 0.123466 | 16 / 7 |
| ar1_0.6 | 504 | L10 | 89.06–93.90 % | 0.306226 | 24 / 17 |
| ar1_0.6 | 504 | L20 | 89.51–94.24 % | 0.311329 | 23 / 16 |
| ar1_0.6 | 504 | L40 | 87.72–92.86 % | 0.303711 | 29 / 18 |
| ar1_0.6 | 504 | oracle | 93.43–97.08 % | 0.348565 | 10 / 12 |
| ar1_0.6 | 1008 | L10 | 89.29–94.07 % | 0.221962 | 23 / 17 |
| ar1_0.6 | 1008 | L20 | 89.97–94.58 % | 0.228605 | 21 / 16 |
| ar1_0.6 | 1008 | L40 | 89.51–94.24 % | 0.228061 | 21 / 18 |
| ar1_0.6 | 1008 | oracle | 91.33–95.60 % | 0.246702 | 17 / 14 |
| ar1_0.9 | 504 | L10 | 73.95–81.22 % | 0.507988 | 59 / 52 |
| ar1_0.9 | 504 | L20 | 79.89–86.40 % | 0.572266 | 43 / 40 |
| ar1_0.9 | 504 | L40 | 80.31–86.77 % | 0.592390 | 42 / 39 |
| ar1_0.9 | 504 | oracle | 93.66–97.24 % | 0.753909 | 6 / 15 |
| ar1_0.9 | 1008 | L10 | 76.48–83.46 % | 0.369166 | 45 / 54 |
| ar1_0.9 | 1008 | L20 | 82.04–88.23 % | 0.423470 | 32 / 41 |
| ar1_0.9 | 1008 | L40 | 83.77–89.67 % | 0.452091 | 30 / 35 |
| ar1_0.9 | 1008 | oracle | 92.72–96.59 % | 0.535641 | 15 / 10 |
| ar1_0.95 | 504 | L10 | 59.90–68.28 % | 0.567446 | 93 / 86 |
| ar1_0.95 | 504 | L20 | 68.53–76.33 % | 0.677012 | 75 / 62 |
| ar1_0.95 | 504 | L40 | 72.07–79.54 % | 0.736156 | 64 / 56 |
| ar1_0.95 | 504 | oracle | 91.79–95.93 % | 1.069135 | 16 / 13 |
| ar1_0.95 | 1008 | L10 | 68.12–75.95 % | 0.424796 | 76 / 63 |
| ar1_0.95 | 1008 | L20 | 76.48–83.46 % | 0.516448 | 50 / 49 |
| ar1_0.95 | 1008 | L40 | 82.47–88.59 % | 0.580181 | 33 / 38 |
| ar1_0.95 | 1008 | oracle | 92.96–96.75 % | 0.763556 | 11 / 13 |
| iid_student5 | 504 | L10 | 91.56–95.77 % | 0.169994 | 15 / 15 |
| iid_student5 | 504 | L20 | 90.42–94.92 % | 0.165985 | 17 / 18 |
| iid_student5 | 504 | L40 | 88.39–93.38 % | 0.158357 | 21 / 23 |
| iid_student5 | 1008 | L10 | 94.14–97.55 % | 0.122317 | 6 / 13 |
| iid_student5 | 1008 | L20 | 93.19–96.92 % | 0.121013 | 6 / 17 |
| iid_student5 | 1008 | L40 | 91.79–95.93 % | 0.117842 | 7 / 22 |
| mean_break | 504 | L10 | 99.24–100.00 % | 0.400275 | 0 / 0 |
| mean_break | 504 | L20 | 99.24–100.00 % | 0.517191 | 0 / 0 |
| mean_break | 504 | L40 | 99.24–100.00 % | 0.641079 | 0 / 0 |
| mean_break | 1008 | L10 | 99.24–100.00 % | 0.288454 | 0 / 0 |
| mean_break | 1008 | L20 | 99.24–100.00 % | 0.384216 | 0 / 0 |
| mean_break | 1008 | L40 | 99.24–100.00 % | 0.504550 | 0 / 0 |
