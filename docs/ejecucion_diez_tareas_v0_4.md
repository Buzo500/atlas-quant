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

## Estado final: las diez tareas atendidas

Puntos 1–6: D6 completo publicado en PR #8 / `v0.4.0-dev.5`, CI 34503177151 correcta. Punto 5 continúa y documenta el diagnóstico: caché/TLS corregidos; Yahoo 429 y transporte intermitente pendientes de resolución.

Punto 7: D7 especificado con referencias independientes. Punto 8: D7 implementado, incluidas cuatro regresiones posteriores de interfaz. Punto 9: D8 validado y publicado en PR #9 / `v0.4.0-dev.6`, CI 34509155203 correcta, 709 Python + 91 subcasos, 278 frontend y 19 E2E; carga, concurrencia, migración y recuperación documentadas. Primer intento remoto fallido conservado; no se fusionó ese resultado. Coste cero y cuota suficiente verificados.

Punto 10: `v0_5_alcance_inicial.md` define objetivos, bandas y diagnóstico de desviaciones, sin implementar v0.5. Requiere nueva autorización para su código.

Master actualizado y ATLAS compilado/arrancado, con las tres carteras habituales y sus libros intactos, parada global activa y gasto/reserva cero. Inicio `Abrir-ATLAS.cmd`, parada `Detener-ATLAS.cmd`. [Continuidad](CONTINUIDAD.md) registra commits, etiqueta, CI, copias y ejecución final. Ensayo, monitor y movimientos personales siguen aplazados; no se declara estable.
