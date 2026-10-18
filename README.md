# Árboles Exóticos Occidente 🌿

Catálogo botánico bilingüe estático, listo para GitHub Pages.

## Cómo probar en Visual Studio Code
1. Descomprimir el ZIP y abrir la carpeta en VS Code.
2. Usar la extensión **Live Server** y abrir `index.html` con **Open with Live Server**. No abrir mediante `file://`, porque `fetch()` de `plantas.json` puede bloquearse.
3. Buscar plantas y cambiar ES/EN.

## Publicar en GitHub Pages
1. Crear repositorio público `arboles-exoticos-occidente`.
2. Subir **el contenido de esta carpeta** a la raíz del repositorio (`index.html`, `app.js`, `styles.css`, `plantas.json`, `imagenes/`).
3. En Settings → Pages → Build and deployment → Deploy from a branch → `main` → `/ (root)` → Save.
4. Esperar el despliegue y abrir la URL indicada por GitHub.

## Editar datos
- `plantas.json`: fichas. Los campos `price` y `stock` están sin confirmar (`null`).
- `en` y `scientific` se completaron solo en coincidencias botánicas seleccionadas; el resto requiere revisión.
- `benefit_es`, `benefit_en`, `care_es`, `care_en`: campos vacíos hasta verificación.
- `app.js`: definir `WHATSAPP` con el número autorizado para recibir pedidos.
- Imágenes extraídas de las páginas 2–87 del PDF entregado, sin verificar licencias de terceros. Confirmar derechos de publicación antes de hacer público el repositorio.

## Pendiente
- Conciliar todas las variedades del inventario TXT con las fichas del PDF.
- Verificar taxonomía, beneficios, cuidados y fuentes científicas.
- Confirmar precios, tamaños y existencias reales.
- Implementar administración segura con backend y autenticación si se requiere edición desde la web.


## Versión 2
- Tarjetas con resumen breve y botón «Ver más / Read more».
- Ficha completa en ventana emergente, sin abandonar el catálogo.
- Cambio de idioma también dentro de la ficha abierta.
- Primeras cinco descripciones botánicas, notas nutricionales y cuidados orientativos. El resto continúa pendiente de verificación.
- Se corrigió la aplicación del filtro por categoría.

### Actualización en GitHub
Reemplazar `app.js`, `styles.css`, `plantas.json` y `README.md` en la raíz del repositorio. Las imágenes y `index.html` permanecen iguales. En Settings > Pages, la publicación se actualizará después del commit.

**Nota:** la información nutricional es general, no una indicación médica. Los nombres y fotos de variedades deben validarse con el vivero.
