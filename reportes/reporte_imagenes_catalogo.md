# Auditoría de imágenes del catálogo

## Estado del lote 4

- Productos en el inventario: 286.
- Presentaciones con fotografía válida: 137.
- Presentaciones pendientes: 149.
- Presentaciones con referencia a una ruta inexistente antes de este lote: 57.
- Referencias rotas corregidas con archivos locales inequívocos: 2.
- Referencias rotas restantes: 33.
- Imágenes del repositorio antes del lote: 113.
- Imágenes nuevas descargadas en el lote 2: 8.
- Imágenes nuevas convertidas a WebP en el lote 2: 8.
- Especies únicas cubiertas en el lote 2: 8.
- Productos comerciales beneficiados en el lote 2: 10.
- Imágenes nuevas descargadas en el lote 3: 16.
- Imágenes nuevas convertidas a WebP en el lote 3: 16.
- Especies únicas cubiertas en el lote 3: 16.
- Productos comerciales beneficiados en el lote 3: 25.
- Imágenes nuevas descargadas en el lote 4: 7.
- Imágenes nuevas convertidas a WebP en el lote 4: 7.
- Especies o variedades cítricas cubiertas en el lote 4: 7.
- Productos comerciales beneficiados en el lote 4: 21.

Todas las imágenes existentes son WebP válidas, pero no todas tienen relación comercial confirmada con un producto. La existencia de un archivo no se considera prueba suficiente de correspondencia botánica.

## Correcciones aplicadas

Se corrigieron únicamente dos referencias cuyo archivo local coincidía inequívocamente por nombre:

- Producto 126: `cacao blanco.webp`.
- Producto 140: `copoazu.webp`.

En el lote 2 se integraron fotografías externas con licencia documentada para:

- Hass, IDs 17–18.
- Granadilla, ID 26.
- Manzana rosa, ID 28.
- Maracuyá, ID 29.
- Marañón, ID 30.
- Papaya, ID 33.
- Pipa, IDs 34–35.
- Uchuva, ID 36.

Las fuentes, autores y licencias están registradas en [lote2_fuentes.json](./lote2_fuentes.json). Las fotografías fueron optimizadas con [optimizar_imagenes_webp.py](../scripts/optimizar_imagenes_webp.py), sin ampliar la imagen original más allá del lienzo de 800 × 800.

En el lote 3 se integraron `kumquat.webp`, `calamondin.webp`, `mangostan.webp`, `canistel.webp`, `cas.webp`, `grumichama.webp`, `guayaba.webp`, `yaca.webp`, `litchi.webp`, `longan.webp`, `mabolo.webp`, `moringa.webp`, `nance.webp`, `noni.webp`, `pejibaye.webp` y `pitahaya.webp`. El registro central está en [fuentes_fotograficas.json](./fuentes_fotograficas.json) y el detalle del lote en [lote3_fuentes.json](./lote3_fuentes.json).

En el lote 4 se integraron `naranja-agria.webp`, `naranja-navel.webp`, `naranja-washington.webp`, `naranja-ortanique.webp`, `naranja-valencia.webp`, `naranja-sanguinea.webp` y `toronja.webp`. El detalle de autores, licencias y fuentes está en [lote4_fuentes.json](./lote4_fuentes.json).

No se sustituyeron imágenes por especies parecidas ni se asignaron archivos por coincidencias dudosas.

## Observaciones

- Las referencias rotas se concentran en rutas de cítricos y exóticos.
- Hay 149 productos pendientes: 116 sin referencia fotográfica y 33 con referencias rotas. Esto incluye los productos nuevos de Maderables y Frutas para Aves.
- Existen grupos de presentaciones que comparten intencionalmente una imagen; esto no se considera un duplicado innecesario cuando representan la misma variedad o presentación.
- La validación botánica de fotografías nuevas requerirá revisión de especie, variedad y licencia antes de integrarlas.

## Productos que requieren identificación manual

- IDs 109–111: `Toronja china.webp` frente a Toronja.
- ID 124: `biriba brasilensis.webp` frente a Biribí injertado.
- IDs 127–128: `cacao.webp` frente a cacao negro y cacao rojo.
- Granadas, aguacates Holls/Lamb Hass/Oro Verde y cítricos del CSV no recibieron imágenes porque no se confirmó la variedad.
- En este lote quedaron pendientes variedades de mango, tamarindo y anona por no contar simultáneamente con una identificación varietal y una licencia verificable.
- Permanecen pendientes Mandarina King, Naranja Agria variegada, Naranja Dulce variegada, Naranja Malagueña, Naranja Mineola, Naranja Orlando, Naranja Piña y Naranja Washington Roja. No se asignaron fotografías genéricas.

## Créditos visibles

La página principal incluye una sección desplegable de créditos que carga [fuentes_fotograficas.json](./fuentes_fotograficas.json) y muestra especie, autor, fuente y licencia. Las fotografías CC BY y CC BY-SA conservan su atribución y se documentan como recortadas proporcionalmente, colocadas sobre lienzo blanco y convertidas a WebP.

## Cobertura

El catálogo tiene fotografías válidas para 137 de 286 productos (**47,90 %**). El lote 4 completó 7 especies o variedades cítricas y benefició 21 presentaciones comerciales. No se declara el catálogo completo mientras existan referencias rotas, productos sin fotografía o variedades pendientes de confirmación.

## Próximo lote autorizado

Investigar fotografías con licencia compatible, priorizando Wikimedia Commons, repositorios institucionales y otras fuentes que permitan reutilización comercial. Las imágenes se descargarán a un área de trabajo, se convertirán mediante `scripts/optimizar_imagenes_webp.py` y solo después se actualizarán las referencias del inventario.
