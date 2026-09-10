# Ejecución autorizada: diez tareas de cierre v0.4

10/09/2026. El usuario indica «Vale, haz las 10» sobre las dos listas consecutivas. Alcance autorizado y orden:

1. Revisar D6.1/D6.2, subir rama y ejecutar CI gratuita.
2. D6.3: CSV propio de precios USD y series FX, versiones y selección temporal.
3. D6.4: NAV por corte con procedencia y estados de calidad.
4. D6.5: interfaz para saldos, importaciones, FX y patrimonio.
5. Continuar Yahoo/TLS y diagnóstico API según evidencia.
6. D6.6: cerrar D6 completo con revisión, recuperación, rendimiento y publicación de desarrollo tras CI gratuita.
7. Concretar D7: convenciones y referencias independientes de rentabilidad.
8. Implementar D7: P&L, flujos, costes, TWR y MWR/XIRR por periodo y motivos de indisponibilidad.
9. D8: integración, concurrencia, recuperación, rendimiento, documentación y CI gratuita de la entrega.
10. Definir el primer alcance pequeño de v0.5, sin implementarlo todavía.

El ensayo de 48 horas y el monitor permanecen aplazados. No introducir movimientos personales, bróker, entrenamiento ni gasto API. Se conserva el monolito modular, políticas heredadas y fuentes históricas.

## Registro de avance

- ATLAS ya estaba detenido al iniciar; se comprueba la parada. Copia previa de esquema 5: `backups/atlas-20260910T152641167910Z-d35a888b`.
- Revisión D6.1/D6.2 sobre `5650c46`: contratos y diff coherentes, evidencias locales previas conservadas. Rama subida y PR #8 abierta. Presupuesto Actions 0 USD con Stop usage Yes; cuota 183,3/2.000 minutos, 0/0,5 GB y 0 USD facturables.
- CI inicial **correcta**, ejecución [34496563421](https://github.com/Buzo500/atlas-quant/actions/runs/34496563421), sobre `5650c46`, 9m01s. Punto 1 completado; PR #8 permanece abierta para integrar el resto de D6.
- D6.3/D6.4 en desarrollo: importación exacta, evidencia/calendarios, versiones de precios y FX, vínculo FX por revisión de cartera, selección de marcas y NAV inmutable. Reutiliza versiones de datasets, libro nativo y tablas vacías de esquema 5; no crea otro motor ni altera datasets EUR anteriores. Verificación enfocada en curso, sin declarar cierre.

El estado final y las fuentes verificadas se incorporarán a CONTINUIDAD y a los documentos de cada bloque.

## Estado posterior

Puntos 1–6 completados: D6 publicado en PR #8 y `v0.4.0-dev.5`, CI 34503177151 correcta. Punto 7 especificado con referencias y punto 8 implementado: D7 con 32 casos nuevos y vista por fechas. Punto 9 validado localmente, pendiente de CI/publicación: 709 Python + 91 subcasos, 274 frontend, 19 E2E, carga y recuperación. Punto 10 definido en `v0_5_alcance_inicial.md`, sin implementación. Mantener trabajo activo hasta cerrar la publicación D7/D8 y registrar el estado operativo.
