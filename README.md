# Árboles Exóticos Occidente 🌿

Catálogo botánico bilingüe estático, listo para GitHub Pages.

## Cómo probar en Visual Studio Code
1. Descomprimir el ZIP y abrir la carpeta en VS Code.
2. Abrir `index.html` directamente en el navegador o usar la extensión **Live Server**. El catálogo incluye un respaldo local para que también funcione mediante `file://`.
3. Buscar plantas y cambiar ES/EN.

## Publicar en GitHub Pages
1. Crear repositorio público `arboles-exoticos-occidente`.
2. Subir **el contenido de esta carpeta** a la raíz del repositorio (`index.html`, `app.js`, `styles.css`, `plantas.json`, `imagenes/`).
3. En Settings → Pages → Build and deployment → Deploy from a branch → `main` → `/ (root)` → Save.
4. Esperar el despliegue y abrir la URL indicada por GitHub.

## Editar datos
- `plantas.json`: fichas. Los campos `price` y `stock` están sin confirmar (`null`).
- `plantas-data.js`: copia local generada del catálogo para permitir abrir `index.html` directamente; actualizarla cuando cambie `plantas.json`.
- `en` y `scientific` se completaron solo en coincidencias botánicas seleccionadas; el resto requiere revisión.
- `benefit_es`, `benefit_en`, `care_es`, `care_en`: campos vacíos hasta verificación.
- `app.js`: definir `WHATSAPP` con el número autorizado para recibir pedidos.
- Imágenes extraídas de las páginas 2–87 del PDF entregado, sin verificar licencias de terceros. Confirmar derechos de publicación antes de hacer público el repositorio.

## Pendiente
- Conciliar todas las variedades del inventario TXT con las fichas del PDF.
- Verificar taxonomía, beneficios, cuidados y fuentes científicas.
- Confirmar precios, tamaños y existencias reales.
- Implementar administración segura con backend y autenticación si se requiere edición desde la web.
