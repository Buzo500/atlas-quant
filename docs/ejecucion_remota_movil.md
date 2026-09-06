# ATLAS Quant · Ejecución remota y acceso móvil

Fecha: 6 de septiembre de 2026. **Solo planificación y estudio de viabilidad.** El usuario solicita registrar estas funciones futuras y valorar su utilidad; no autoriza implementarlas, configurar red, instalar servicios ni modificar el programa en esta tarea.

## Necesidades solicitadas

1. Preparar una prueba de estrategia desde el portátil y enviarla al sobremesa, para que siga funcionando aunque el usuario esté fuera varios días y cierre o apague el portátil.
2. Disponer de una app móvil para elegir estrategias, iniciar y controlar experimentos, consultar su rendimiento y, en fases posteriores, gestionar órdenes según las capacidades y permisos disponibles.

Ambas necesidades encajan con un producto personal: el sobremesa mantiene el trabajo y los otros dispositivos permiten consultarlo y dirigirlo. La arquitectura propuesta aquí es una recomendación pendiente de concretar al iniciar su versión.

## Qué existe y qué falta

El backend actual tiene una API, persistencia de experimentos en SQLite, informes y acciones de pausa, reanudación y cancelación. El motor continúa sin la pestaña abierta mientras los procesos y el equipo permanezcan activos. Esa base permite evolucionar sin construir otro motor financiero para el móvil.

Todavía no existen un canal remoto de ATLAS, autenticación de usuarios/dispositivos para ese acceso, una PWA de ATLAS, una aplicación nativa móvil ni traslado de cálculos entre ejecutores. Los controles HTTP actuales admiten localhost y usan una cabecera de cliente local: esa cabecera pública no es una credencial. La publicación `pdf-mobile/` contiene el documento de diseño, no una app móvil de gestión de ATLAS.

El lanzador de v0.2 en desarrollo detecta fallos y permite recuperar datos, pero no instala un servicio Windows ni arranca al reiniciar el equipo. La disponibilidad durante varios días aún exige diseño y pruebas específicos.

## REMOTE-001 · Sobremesa como servidor personal

Alcance inicial propuesto:

- El sobremesa es el responsable único de la base de los experimentos remotos, su cola y sus resultados. Portátil y móvil consultan y envían solicitudes al mismo servidor. Las instalaciones locales independientes siguen siendo entornos distintos.
- Enviar una nueva ejecución con estrategia identificada y versionada, parámetros, conjunto y versión de datos, costes, duración y presupuesto. Si los datos solo existen en el portátil, importarlos y verificar su integridad en el servidor antes de aceptar el trabajo.
- Admitir primero estrategias soportadas y parámetros validados; esta función no habilita ejecución de código arbitrario recibido de un dispositivo.
- Devolver un identificador persistente y confirmar cuándo el servidor ha aceptado la solicitud. Un reintento con la misma identidad no crea otra ejecución ni otra reserva; un resultado incierto debe consultarse antes de repetir efectos externos.
- Mostrar cola, estado, última actualización, resultados, incidencias y disponibilidad del sobremesa. Separar «solicitud de pausa enviada» de «experimento pausado».
- Mantener cálculos independientes de la conexión del cliente; permitir consultar, pausar, reanudar o cancelar con semántica y tiempo de respuesta definidos. El bloqueo que hoy comparten el cálculo y sus controles necesita revisión antes de prometer respuesta rápida durante investigaciones largas.
- Acotar concurrencia y recursos de CPU, RAM y, cuando haya tareas compatibles, GPU/VRAM. Guardar la versión del programa y de los datos usada por cada resultado.
- Preparar inicio después de reinicios y recuperación de trabajos recuperables, manteniendo la política de no repetir llamadas o envíos inciertos. Probar cortes de red, reinicios, sesiones caducadas y pérdida de alimentación.

No se propone sincronizar archivos SQLite activos entre equipos. Tampoco se incluye en el primer hito migrar un cálculo ya iniciado en el portátil hasta el mismo punto de ejecución en el sobremesa: eso requeriría checkpoints y compatibilidad adicionales. «Enviar al sobremesa» significa inicialmente crear allí una nueva ejecución reproducible.

## MOBILE-001 · Panel móvil de consulta y control

Propuesta inicial: web adaptada a pantallas pequeñas y **PWA instalable**, reutilizando la interfaz y la API del proyecto. Una PWA puede tener icono y abrirse como aplicación; instalación y capacidades varían según sistema y navegador. Necesitaría HTTPS, manifiesto y validación en los dispositivos elegidos. [MDN: instalación de PWA](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable).

Funciones propuestas:

- Ver estrategias y experimentos disponibles, elegir parámetros y destino, iniciar un trabajo y recibir confirmación del servidor.
- Consultar progreso, rendimiento, curva de patrimonio, caída, costes, posiciones simuladas y comparación con el benchmark cuando esas métricas existan.
- Distinguir resultados históricos, observación de sesiones posteriores, simulación y futura operativa real. Mostrar fecha del último dato y si el servidor está desconectado; no presentar una cotización diaria como tiempo real.
- Pausar, reanudar o cancelar experimentos y solicitar la parada de ejecución simulada. Mostrar la confirmación efectiva y conservar un registro de acciones.
- Avisos opcionales de finalización, fallo, datos atrasados o necesidad de revisión. Elegir el canal y comprobar permisos/entrega en el móvil concreto; las notificaciones no son garantía de disponibilidad.
- Manejar cortes de cobertura: no aparentar una orden aceptada ni reenviar una instrucción sensible al recuperar conexión sin comprobar estado y vigencia. La consulta offline, si se añade, debe identificar sus datos como almacenados y posiblemente atrasados.
- Autenticar sesiones, limitar acciones y permitir revocar un dispositivo perdido. Las claves de IA y del futuro bróker permanecen en el servidor.

Los cálculos prolongados viven en el sobremesa. Cerrar o suspender la app móvil no debe parar los experimentos; tampoco se confía en que el móvil ejecute un motor financiero continuamente en segundo plano. Una app nativa se evaluaría después si aporta capacidades que justifiquen su mantenimiento adicional.

«Mandar órdenes» tiene dos alcances distintos: controlar un experimento/simulación y enviar una compra o venta real al bróker. El primer panel puede cubrir el primero. Las órdenes reales dependen de la integración, conciliación, límites y autorización de v1.2; la automatización acotada conserva los requisitos de v1.3. Añadir un cliente móvil no habilita dinero real por sí mismo.

## Conectividad, disponibilidad y coste

La opción inicial a evaluar es acceso privado entre los dispositivos del usuario, con HTTPS y autenticación/autorización de aplicación. Tailscale Serve es un ejemplo de herramienta que conecta un servicio local con otros dispositivos de una red privada; sus políticas de acceso se aplican al servicio. Es un candidato, no una elección ni una configuración ya hecha. [Documentación de Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).

El plan Personal de Tailscale anuncia acceso gratuito para uso personal no comercial; se comprobarían sus condiciones y las necesidades concretas antes de adoptarlo. Permite estudiar un piloto sin alojamiento cloud contratado ni cuotas nuevas de ese servicio. Esto no elimina electricidad, conexión doméstica ni mantenimiento, ni cambia el presupuesto de API cero de ATLAS. [Condiciones y precios consultados el 06/09/2026](https://tailscale.com/pricing).

No basta con exponer los puertos 3000/8000 actuales: hay que adaptar de forma controlada autenticación, hosts/orígenes permitidos y el proxy. No se propone desactivar sus comprobaciones. La red privada limita acceso, pero no sustituye permisos ni validación de las acciones dentro de ATLAS.

Para trabajar varios días fuera, el sobremesa debe permanecer encendido, sin suspensión y disponible. Un cálculo sobre datos ya almacenados puede seguir durante una caída de internet, pero el control remoto, los datos nuevos y los servicios externos necesitan conexión. Un corte de luz detiene el motor. Avisar de que el propio servidor ha muerto puede requerir detección desde el cliente o un componente independiente; no se promete que el equipo apagado envíe su propia alerta. No se configura ahora energía, arranque automático, monitorización externa ni acceso remoto.

## Papel de la RTX 3080

Los backtests actuales usan Python/NumPy en CPU y no implementan CUDA. Tener una GPU más potente no los acelera automáticamente, ni demuestra que la CPU del sobremesa supere a la del portátil en cada tarea. El beneficio inmediato es liberar el portátil y mantener una ejecución central disponible.

La GPU podría resultar útil para inferencia local, entrenamiento compatible o futuros cálculos diseñados para ella. Requiere implementación y medición; no se ha probado aquí ningún modelo, entrenamiento ni aceleración. Los 10 GB de VRAM también limitan tamaño y concurrencia. La selección de modelos y herramientas pertenece a su piloto posterior.

Un backtest termina al procesar el histórico. Mantenerlo días encendido no añade evidencia por sí solo. Dejar una estrategia en observación sí permite incorporar nuevas sesiones cuando lleguen datos; una GPU no acelera el calendario del mercado. Se distinguirán esas tareas de una búsqueda extensa o un entrenamiento prolongado.

## Ubicación propuesta en las versiones

| Versión | Alcance incorporado a planificación |
|---|---|
| v0.2 | Mantener el alcance actual de fiabilidad local; no añadir acceso remoto ni móvil en esta tarea. |
| **v0.8 · Ejecución remota personal** | Servidor en sobremesa, solicitudes desde portátil, identidad de trabajos, acceso privado, recursos y continuidad. |
| **v0.9 · Panel móvil** | Interfaz adaptada e instalable, resultados, control de experimentos/simulación y avisos opcionales. |
| v1.0 | Consolidar y probar también esos recorridos si se acepta su inclusión en la primera estable. |
| v1.2 / v1.3 | Extender al móvil las acciones reales supervisadas / mandatos automáticos ya autorizados, con los mismos límites del servidor. |

La numeración de v0.8/v0.9 es una propuesta de planificación, sin fecha ni inicio autorizados. La conexión remota no depende técnicamente del conector de bróker de v0.7: podría adelantarse si el uso entre equipos se vuelve prioritario. Tampoco depende de instalar un modelo local o usar GPU.

## Criterios para aceptar las futuras funciones

1. Crear desde el portátil un experimento, cerrar el portátil y comprobar después que el sobremesa conserva el mismo trabajo, configuración y resultados.
2. Repetir una petición tras perder cobertura y obtener la misma identidad sin duplicar trabajos, reservas ni efectos externos. Mostrar estados inciertos y resolverlos sin reenvíos ciegos.
3. Reiniciar el sobremesa durante un trabajo y verificar recuperación según su estado, integridad, versiones y política de interrupción. Ejecutar una prueba sostenida con duración y umbrales definidos.
4. Rechazar sesiones/dispositivos no autorizados y permitir revocación. Una desconexión nunca debe presentarse como pausa, cancelación u orden aceptada.
5. Mantener controles con respuesta acotada durante cálculos largos y límites de recursos comprobados. Presentar métricas con tipo de prueba, fecha y cobertura verificables.
6. Validar instalación, navegación táctil, pérdidas de conexión y comportamiento de avisos en el sistema y navegador del móvil del usuario, aún sin identificar.

No se modifica el programa, la base, la red, los procesos en ejecución ni los dispositivos durante este estudio. La planificación no autoriza operar con dinero real ni contratar servicios.
