# Integración de v0.6 y PR #12 · decisión del 12/09/2026

Consulta remota: PR #12 abierta, no fusionada, base `master` en `524feac`, cabeza
`codex/v0.5-comparador` en `c3ec20c`. GitHub informa que se puede fusionar, pero
eso no sustituye la aceptación funcional pendiente. Conserva su alcance de
fichas/comparador/correlaciones y la CI anterior de v0.5.

`git merge-base codex/v0.5-comparador codex/v0.6-evaluador` devuelve exactamente
`c3ec20c4e1c80c2fad4663121234d08f0b3ef4a4`: v0.6 ya incluye toda esa rama.
No necesita copiar sus commits de nuevo, cambiar contratos históricos ni incluir
el Laboratorio en la PR #12. La corrección de Node está en v0.6, no en v0.5.

Decisión: conservar la secuencia **v0.5 → v0.6**, con revisiones separadas.
Cuando se acepte lo pendiente de v0.5, fusionar PR #12 y su etiqueta de desarrollo
según la autorización condicionada anterior. Preparar después una PR v0.6 contra
el `master` resultante. Si se usa squash, preparar una rama `codex/` de integración
desde el nuevo master y trasladar solo los commits posteriores a `c3ec20c`,
sin reescribir la rama compartida de trabajo. Resolver y verificar allí cualquier
conflicto; CI nueva cuando se autorice su publicación.

Esta decisión no fusiona, etiqueta ni cambia la base de la PR existente. Revisión
manual pendiente del portátil y revisión manual de dev.4 siguen aplazadas. La
implementación estadística dev.5 continúa por separado en `codex/v0.6-evaluador`.
La [publicación posterior y CI](publicacion_v06_dev5.md) no cambian esta decisión.
