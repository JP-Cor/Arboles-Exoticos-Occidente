// Catálogo generado a partir de Inventario/inventario.json.
// Las fotos subidas desde el navegador se guardan LOCALMENTE en IndexedDB de ese navegador.
const RUTA = '../Inventario/inventario.json?v=20261026-2';
const RUTA_FICHAS = '../Inventario/fichas_especies.json?v=1';
const WHATSAPP = window.VIVERO_WHATSAPP;
const WHATSAPP_PEDIDOS = window.VIVERO_WHATSAPP;
const CLAVE_CARRITO = 'vivero-carrito';
const DIAGNOSTICO_FOTOS = new URLSearchParams(window.location.search).has('diagnosticoFotos');
const $ = id => document.getElementById(id);
let productos = [];
let fichas = [];
let carrito = [];
let datosPedido = null;
let idioma = localStorage.getItem('vivero-idioma') === 'en' ? 'en' : 'es';
const textos = {
    es: {
        catalogSubtitle: 'Catálogo de especies y variedades', cart: '🛒 Carrito',
        searchPlaceholder: 'Buscar especie, variedad, nombre científico o inglés',
        allCategories: 'Todas las categorías', sortName: 'Ordenar por nombre', sortLow: 'Menor precio', sortHigh: 'Mayor precio',
        zoneTitle: '¿Qué árboles puedo sembrar en mi zona?', zoneIntro: 'Indica la altitud y, opcionalmente, el clima y la temperatura aproximada de tu propiedad.',
        altitude: 'Altitud (msnm)', climate: 'Clima', anyClimate: 'Cualquier clima', temperature: 'Temperatura (°C, opcional)',
        categoryOptional: 'Categoría (opcional)', search: 'Buscar', searchZone: '🌳 Buscar árboles',
        recommendations: '🌳 Recomendaciones', backToCatalog: '← Volver al catálogo',
        searchDone: '✓ Búsqueda realizada', noProductMatches: 'No se encontraron presentaciones con esos criterios.',
        zoneWarning: 'El suelo, la temperatura, las lluvias, el viento y el manejo agrícola también influyen en el desarrollo.',
        resultsFor: 'Resultados para tu zona', noResults: 'No hay especies con información suficiente para esos filtros.',
        ideal: 'Ideal', compatible: 'Compatible', notRecommended: 'No recomendado', insufficient: 'Sin información suficiente',
        altitudeRange: 'Rango documentado', idealRange: 'Rango óptimo', climateLabel: 'Climas',
        viewInfo: 'Ver información del árbol', details: 'Detalles comerciales', botanical: 'Información botánica',
        scientific: 'Nombre científico', family: 'Familia botánica', origin: 'Origen', cultivation: 'Condiciones de cultivo',
        characteristics: 'Características del árbol', nutrition: 'Beneficios y usos', sowing: 'Recomendaciones de siembra',
        pending: 'Pendiente de validación', notAvailable: 'No disponible'
    },
    en: {
        catalogSubtitle: 'Species and varieties catalog', cart: '🛒 Cart',
        searchPlaceholder: 'Search species, variety, scientific or English name',
        allCategories: 'All categories', sortName: 'Sort by name', sortLow: 'Lowest price', sortHigh: 'Highest price',
        zoneTitle: 'Which trees can I grow in my area?', zoneIntro: 'Enter your property altitude and, optionally, climate and approximate temperature.',
        altitude: 'Altitude (m.a.s.l.)', climate: 'Climate', anyClimate: 'Any climate', temperature: 'Temperature (°C, optional)',
        categoryOptional: 'Category (optional)', search: 'Search', searchZone: '🌳 Find trees',
        recommendations: '🌳 Recommendations', backToCatalog: '← Back to catalog',
        searchDone: '✓ Search completed', noProductMatches: 'No presentations matched those criteria.',
        zoneWarning: 'Soil, temperature, rainfall, wind and agricultural management also influence growth.',
        resultsFor: 'Results for your area', noResults: 'No species has enough information for these filters.',
        ideal: 'Ideal', compatible: 'Compatible', notRecommended: 'Not recommended', insufficient: 'Not enough information',
        altitudeRange: 'Documented range', idealRange: 'Optimal range', climateLabel: 'Climates',
        viewInfo: 'View tree information', details: 'Commercial details', botanical: 'Botanical information',
        scientific: 'Scientific name', family: 'Botanical family', origin: 'Origin', cultivation: 'Growing conditions',
        characteristics: 'Tree characteristics', nutrition: 'Benefits and uses', sowing: 'Planting recommendations',
        pending: 'Pending validation', notAvailable: 'Not available'
    }
};
function t(key) { return textos[idioma][key] || key }
function cambiarVista(vista) {
    const mostrarRecomendaciones = vista === 'recomendaciones';
    $('vista-catalogo').hidden = mostrarRecomendaciones;
    $('vista-recomendaciones').hidden = !mostrarRecomendaciones;
    $('abrir-recomendaciones').setAttribute('aria-expanded', String(mostrarRecomendaciones));
    if (mostrarRecomendaciones) $('altitud-zona').focus();
    else $('buscar').focus();
}
function mostrarEstadoBoton(id) {
    const boton = $(id);
    boton.classList.add('busqueda-ejecutada');
    const texto = boton.querySelector('[data-i18n]');
    if (texto) texto.textContent = t('searchDone');
    window.setTimeout(() => {
        boton.classList.remove('busqueda-ejecutada');
        if (texto) texto.textContent = t(texto.dataset.i18n);
    }, 1200);
}
function actualizarIdioma() {
    document.documentElement.lang = idioma;
    document.querySelectorAll('[data-i18n]').forEach(elemento => { elemento.textContent = t(elemento.dataset.i18n) });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(elemento => { elemento.placeholder = t(elemento.dataset.i18nPlaceholder) });
    $('cambiar-idioma').textContent = idioma === 'es' ? 'EN' : 'ES';
    $('cambiar-idioma').setAttribute('aria-label', idioma === 'es' ? 'Switch to English' : 'Cambiar a español');
}
const dbReady = new Promise((resolve, reject) => { const r = indexedDB.open('vivero-fotos', 1); r.onupgradeneeded = () => r.result.createObjectStore('fotos'); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error) });
async function fotoLocal(id) { const db = await dbReady; return new Promise(resolve => { const tx = db.transaction('fotos', 'readonly'); const req = tx.objectStore('fotos').get(id); req.onsuccess = () => resolve(req.result || null); req.onerror = () => resolve(null) }) }
async function guardarFoto(id, file) { if (!file.type.startsWith('image/')) throw Error('Seleccioná una imagen'); if (file.size > 3 * 1024 * 1024) throw Error('Máximo 3 MB'); const db = await dbReady; return new Promise((resolve, reject) => { const tx = db.transaction('fotos', 'readwrite'); tx.objectStore('fotos').put(file, id); tx.oncomplete = resolve; tx.onerror = () => reject(tx.error) }) }
function nodo(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = String(text); return e }
function moneda(n) { return Number.isFinite(Number(n)) && n !== null && n !== '' ? new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', maximumFractionDigits: 0 }).format(n) : 'Consultar' }
function precioValido(p) { return p && Number.isFinite(Number(p.precio)) && Number(p.precio) > 0 }
function cantidadValida(valor) { const cantidad = Number(valor); return Number.isSafeInteger(cantidad) && cantidad >= 1 ? cantidad : 1 }
function guardarCarrito() { localStorage.setItem(CLAVE_CARRITO, JSON.stringify(carrito.map(i => ({ id: i.id, cantidad: i.cantidad })))) }
function cargarCarrito() {
    
    try {
        const guardado = JSON.parse(localStorage.getItem(CLAVE_CARRITO) || '[]');
        carrito = Array.isArray(guardado) ? guardado.filter(i => Number.isInteger(i.id) && Number.isInteger(i.cantidad) && i.cantidad > 0) : [];
    } catch (e) {
        carrito = [];
        localStorage.removeItem(CLAVE_CARRITO);
    }
}
function sincronizarCarrito() {
    const disponibles = new Map(productos.map(p => [p.id, p]));
    carrito = carrito.filter(i => precioValido(disponibles.get(i.id)) && Number.isSafeInteger(i.cantidad) && i.cantidad > 0).map(i => ({
        id: i.id,
        cantidad: i.cantidad
    }));
    guardarCarrito();
    actualizarContador();
}
function productoEnCarrito(id) { return carrito.find(i => i.id === id) }
function actualizarContador() { $('contador-carrito').textContent = String(carrito.reduce((total, i) => total + i.cantidad, 0)) }
function totalCarrito() {
    return carrito.reduce((total, i) => {
        const p = productos.find(producto => producto.id === i.id);
        return total + (precioValido(p) ? Number(p.precio) * i.cantidad : 0);
    }, 0);
}
function agregarAlCarrito(p, cantidad) {
    if (!precioValido(p)) {
        return false;
    }
    cantidad = cantidadValida(cantidad);
    const existente = productoEnCarrito(p.id);
    if (existente) existente.cantidad += cantidad;
    else carrito.push({ id: p.id, cantidad });
    guardarCarrito();
    actualizarContador();
    mostrarCarrito();
    return true;
}
function mostrarNotificacionCarrito(p, cantidad) {
    const contenedor = $('notificaciones-carrito');
    const notificaciones = contenedor.querySelectorAll('.notificacion-carrito');
    if (notificaciones.length >= 3) notificaciones[0].remove();
    const toast = nodo('div', 'notificacion-carrito');
    const cerrar = nodo('button', 'cerrar-notificacion', '×');
    cerrar.type = 'button';
    cerrar.setAttribute('aria-label', 'Cerrar notificación');
    const titulo = nodo('strong', null, '✅ ¡Producto agregado al carrito!');
    const producto = nodo('span', null, `🌳 Producto: ${p.especie}`);
    const detalle = nodo('span', null, `📦 Cantidad agregada: ${cantidad} ${cantidad === 1 ? 'unidad' : 'unidades'}`);
    const subtotal = nodo('span', null, `💰 Subtotal agregado: ${moneda(Number(p.precio) * cantidad)}`);
    toast.append(cerrar, titulo, producto, detalle, subtotal);
    contenedor.append(toast);
    const retirar = () => {
        if (!toast.isConnected) return;
        toast.classList.add('saliendo');
        window.setTimeout(() => toast.remove(), 180);
    };
    cerrar.onclick = retirar;
    window.setTimeout(retirar, 4000);
}
function cambiarCantidad(id, delta) {
    const item = productoEnCarrito(id);
    if (!item) return;
    item.cantidad += delta;
    if (item.cantidad <= 0) carrito = carrito.filter(i => i.id !== id);
    else item.cantidad = cantidadValida(item.cantidad);
    guardarCarrito();
    actualizarContador();
    mostrarCarrito();
}
function eliminarDelCarrito(id) {
    carrito = carrito.filter(i => i.id !== id);
    guardarCarrito();
    actualizarContador();
    mostrarCarrito();
}
function textoProducto(p) { return `${p.especie}${p.tamano ? ` (${p.tamano})` : ''}` }
async function mostrarCarrito() {
    const contenedor = $('contenido-carrito');
    contenedor.replaceChildren();
    const items = carrito.map(i => ({ item: i, producto: productos.find(p => p.id === i.id) })).filter(x => precioValido(x.producto));
    if (!items.length) {
        contenedor.append(nodo('p', 'muted', 'Tu carrito está vacío.'));
        $('realizar-pedido').disabled = true;
        return;
    }
    for (const { item, producto } of items) {
        const fila = nodo('article', 'item-carrito');
        const img = await imagen(producto);
        img.classList.add('miniatura-carrito');
        fila.append(img);
        const info = nodo('div');
        info.append(nodo('h3', null, producto.especie), nodo('p', 'muted', producto.tamano || 'Presentación por confirmar'));
        info.append(nodo('p', null, `Precio unitario: ${moneda(producto.precio)}`));
        const controles = nodo('div', 'control-cantidad');
        const menos = nodo('button', null, '−');
        menos.type = 'button';
        menos.setAttribute('aria-label', `Disminuir cantidad de ${producto.especie}`);
        menos.onclick = () => cambiarCantidad(producto.id, -1);
        const cantidad = nodo('span', null, `Cantidad: ${item.cantidad}`);
        const mas = nodo('button', null, '+');
        mas.type = 'button';
        mas.setAttribute('aria-label', `Aumentar cantidad de ${producto.especie}`);
        mas.onclick = () => cambiarCantidad(producto.id, 1);
        controles.append(menos, cantidad, mas);
        info.append(controles);
        fila.append(info);
        const acciones = nodo('div');
        acciones.append(nodo('strong', null, `Subtotal: ${moneda(Number(producto.precio) * item.cantidad)}`));
        const quitar = nodo('button', 'eliminar-item', 'Eliminar');
        quitar.type = 'button';
        quitar.onclick = () => eliminarDelCarrito(producto.id);
        acciones.append(quitar);
        fila.append(acciones);
        contenedor.append(fila);
    }
    const resumen = nodo('div', 'resumen-carrito');
    resumen.append(nodo('div', null, `Total de unidades: ${carrito.reduce((sum, i) => sum + i.cantidad, 0)}`));
    resumen.append(nodo('div', 'total-carrito', `Total estimado: ${moneda(totalCarrito())}`));
    contenedor.append(resumen);
    $('realizar-pedido').disabled = false;
}
function abrirDialogo(id) { const dialogo = $(id); if (!dialogo.open) dialogo.showModal() }
function validarFormulario(formulario) {
    const nombre = formulario.nombre.value.trim();
    const telefonoOriginal = formulario.telefono.value.trim();
    const telefono = telefonoOriginal.replace(/[\s-]/g, '');
    const direccion = formulario.direccion.value.trim();
    const observaciones = formulario.observaciones.value.trim();
    if (nombre.split(/\s+/).length < 2 || nombre.length < 5) return 'Escribí tu nombre y apellido.';
    if (!/^(?:\+?506)?[2-9]\d{7}$/.test(telefono)) return 'Ingresá un teléfono válido de Costa Rica (8 dígitos o +506).';
    if (direccion.length < 10) return 'Ingresá una dirección de entrega suficientemente descriptiva.';
    return { nombre, telefono, direccion, observaciones };
}
function mostrarRevision() {
    const contenedor = $('contenido-revision');
    contenedor.replaceChildren();
    const cliente = nodo('div', 'revision-seccion');
    cliente.append(nodo('h3', null, 'Datos del cliente'));
    cliente.append(nodo('p', null, `Nombre: ${datosPedido.nombre}`), nodo('p', null, `Teléfono: ${datosPedido.telefono}`), nodo('p', null, `Dirección: ${datosPedido.direccion}`));
    if (datosPedido.observaciones) cliente.append(nodo('p', null, `Observaciones: ${datosPedido.observaciones}`));
    contenedor.append(cliente);
    const productosRevision = nodo('div', 'revision-seccion');
    productosRevision.append(nodo('h3', null, 'Productos'));
    for (const item of carrito) {
        const p = productos.find(producto => producto.id === item.id);
        if (precioValido(p)) productosRevision.append(nodo('p', null, `${textoProducto(p)} — ${item.cantidad} × ${moneda(p.precio)} = ${moneda(Number(p.precio) * item.cantidad)}`));
    }
    productosRevision.append(nodo('p', 'total-carrito', `Total: ${moneda(totalCarrito())}`));
    contenedor.append(productosRevision);
}
function mensajeWhatsApp() {
    const lineas = [
        '🌳 *ÁRBOLES EXÓTICOS OCCIDENTE*', '🛒 *NUEVO PEDIDO*', '',
        '📋 *DATOS DEL CLIENTE*', `👤 Nombre: ${datosPedido.nombre}`, `📱 Teléfono: ${datosPedido.telefono}`,
        `📍 Dirección: ${datosPedido.direccion}`, '', '🌱 *PRODUCTOS SOLICITADOS*'
    ];
    carrito.forEach((item, index) => {
        const p = productos.find(producto => producto.id === item.id);
        if (precioValido(p)) lineas.push(`${index + 1}. ${p.especie}`, `Presentación: ${p.tamano || 'Por confirmar'}`, `Cantidad: ${item.cantidad}`, `Precio unitario: ${moneda(p.precio)}`, `Subtotal: ${moneda(Number(p.precio) * item.cantidad)}`);
    });
    lineas.push('━━━━━━━━━━━━━━━━', `📦 Total de unidades: ${carrito.reduce((sum, i) => sum + i.cantidad, 0)}`, `💰 *TOTAL ESTIMADO: ${moneda(totalCarrito())}*`, '━━━━━━━━━━━━━━━━');
    if (datosPedido.observaciones) lineas.push('', `📝 Observaciones: ${datosPedido.observaciones}`);
    lineas.push('', '🚚 Transporte pendiente de confirmar.', '', '🌳 Gracias por comprar en Árboles Exóticos Occidente.');
    return lineas.join('\n');
}
function enlaceWA(p) { if (!WHATSAPP) return null; const msg = `Hola, consulto por ${p.especie} (${p.cientifico || 'sin nombre científico confirmado'}), presentación ${p.tamano || 'por confirmar'}, precio ${moneda(p.precio)}.`; return 'https://wa.me/' + WHATSAPP + '?text=' + encodeURIComponent(msg) }
function rutaFotoPermanente(foto) {
    let ruta = String(foto || '').replace(/\\/g, '/').trim();
    if (!ruta) return null;
    try {
        ruta = decodeURIComponent(ruta);
    } catch (error) {
        if (DIAGNOSTICO_FOTOS) console.warn('Ruta de fotografía con codificación inválida:', foto, error);
    }
    ruta = ruta.replace(/^\/+/, '');
    if (ruta.toLowerCase().startsWith('imagenes/')) ruta = ruta.slice('imagenes/'.length);
    if (!ruta || ruta.split('/').some(segmento => !segmento || segmento === '..')) return null;
    const segmentos = ruta.split('/').map(encodeURIComponent);
    return new URL(`../imagenes/${segmentos.join('/')}`, document.baseURI).href;
}
async function imagen(p) {
    // El diagnóstico fuerza la comprobación de la fotografía permanente.
    const local = DIAGNOSTICO_FOTOS ? null : await fotoLocal(p.id);

    if (local) {
        const url = URL.createObjectURL(local);
        const img = nodo('img', 'foto');

        img.src = url;
        img.alt = p.especie;
        img.dataset.fotoOrigen = 'indexeddb';

        img.onload = () => URL.revokeObjectURL(url);

        return img;
    }

    // Buscar fotografía permanente del catálogo.
    if (p.foto) {
        const img = nodo('img', 'foto');

        const url = rutaFotoPermanente(p.foto);
        if (!url) {
            if (DIAGNOSTICO_FOTOS) console.warn('Fotografía permanente sin ruta válida:', {
                id: p.id, producto: p.especie, rutaInventario: p.foto
            });
            return nodo('div', 'sin-foto', '🌱 Fotografía pendiente');
        }
        img.src = url;

        img.alt = p.especie;
        img.loading = 'lazy';
        img.dataset.fotoOrigen = 'permanente';

        img.onerror = () => {
            if (DIAGNOSTICO_FOTOS) console.error('No se pudo cargar fotografía permanente:', {
                id: p.id,
                producto: p.especie,
                rutaInventario: p.foto,
                urlFinal: url,
                tipo: 'error de carga HTTP o archivo no disponible'
            });
            img.replaceWith(
                nodo('div', 'sin-foto', '🌱 Fotografía pendiente')
            );
        };

        return img;
    }

    // 3. Mostrar imagen pendiente
    return nodo(
        'div',
        'sin-foto',
        '🌱 Fotografía pendiente'
    );
}
function linea(contenedor, etiqueta, valor) { if (!valor) return; const p = nodo('p'); const b = nodo('strong', null, etiqueta + ': '); p.append(b, document.createTextNode(String(valor))); contenedor.append(p) }
function fichaProducto(p) { return fichas.find(ficha => ficha.inventario_ids.includes(p.id)) || null }
function valorFicha(valor) { return valor || t('pending') }
function listaFicha(contenedor, etiqueta, valores) {
    if (!Array.isArray(valores) || !valores.length) return;
    const section = nodo('div', 'ficha-seccion');
    section.append(nodo('h3', null, etiqueta));
    const ul = nodo('ul', 'ficha-lista');
    valores.forEach(valor => ul.append(nodo('li', null, valor)));
    section.append(ul);
    contenedor.append(section);
}
async function detalle(p) {
    const c = $('contenido-detalle');
    c.replaceChildren();
    const ficha = fichaProducto(p);
    c.append(nodo('h2', null, idioma === 'es' ? p.especie : (p.ingles || p.especie)));
    const foto = await imagen(p);
    foto.classList.add('ficha-foto');
    c.append(foto);
    const comercial = nodo('div', 'ficha-seccion');
    comercial.append(nodo('h3', null, t('details')));
    linea(comercial, idioma === 'es' ? 'Categoría' : 'Category', p.categoria);
    linea(comercial, t('scientific'), p.cientifico);
    linea(comercial, idioma === 'es' ? 'Precio' : 'Price', moneda(p.precio));
    linea(comercial, idioma === 'es' ? 'Tamaño' : 'Size', p.tamano);
    linea(comercial, idioma === 'es' ? 'Disponibilidad' : 'Availability', p.disponibilidad || t('notAvailable'));
    c.append(comercial);
    if (ficha) {
        c.append(nodo('div', 'ficha-seccion', ficha.descripcion[idioma]));
        linea(c, t('family'), valorFicha(ficha.familia_botanica));
        linea(c, t('origin'), valorFicha(ficha.origen));
        const cultivo = ficha.cultivo;
        const condiciones = nodo('div', 'ficha-seccion');
        condiciones.append(nodo('h3', null, t('cultivation')));
        linea(condiciones, idioma === 'es' ? 'Altitud recomendada' : 'Recommended altitude', cultivo.altitud_minima === null ? t('pending') : `${cultivo.altitud_minima}-${cultivo.altitud_maxima} msnm`);
        linea(condiciones, idioma === 'es' ? 'Clima' : 'Climate', cultivo.clima.join(', ') || t('pending'));
        linea(condiciones, idioma === 'es' ? 'Temperatura óptima' : 'Optimal temperature', valorFicha(cultivo.temperatura_optima));
        linea(condiciones, idioma === 'es' ? 'Exposición solar' : 'Sun exposure', valorFicha(cultivo.exposicion_solar));
        linea(condiciones, idioma === 'es' ? 'Riego' : 'Watering', valorFicha(cultivo.riego));
        linea(condiciones, idioma === 'es' ? 'Suelo y drenaje' : 'Soil and drainage', `${valorFicha(cultivo.suelo)} ${cultivo.drenaje ? `(${cultivo.drenaje})` : ''}`);
        c.append(condiciones);
        const caracteristicas = ficha.caracteristicas;
        const arbol = nodo('div', 'ficha-seccion');
        arbol.append(nodo('h3', null, t('characteristics')));
        linea(arbol, idioma === 'es' ? 'Altura adulta' : 'Mature height', valorFicha(caracteristicas.altura_adulta));
        linea(arbol, idioma === 'es' ? 'Producción' : 'Bearing time', valorFicha(caracteristicas.tiempo_produccion));
        linea(arbol, idioma === 'es' ? 'Poda' : 'Pruning', valorFicha(caracteristicas.recomendaciones_poda));
        c.append(arbol);
        const beneficios = nodo('div', 'ficha-seccion');
        beneficios.append(nodo('h3', null, t('nutrition')));
        linea(beneficios, idioma === 'es' ? 'Vitaminas' : 'Vitamins', ficha.beneficios.vitaminas.join(', ') || t('pending'));
        linea(beneficios, idioma === 'es' ? 'Minerales' : 'Minerals', ficha.beneficios.minerales.join(', ') || t('pending'));
        linea(beneficios, idioma === 'es' ? 'Antioxidantes' : 'Antioxidants', ficha.beneficios.antioxidantes.join(', ') || t('pending'));
        linea(beneficios, idioma === 'es' ? 'Características nutricionales' : 'Nutritional characteristics', valorFicha(ficha.beneficios.nutricion));
        linea(beneficios, idioma === 'es' ? 'Usos gastronómicos' : 'Culinary uses', valorFicha(ficha.beneficios.usos_gastronomicos));
        c.append(beneficios);
        linea(c, idioma === 'es' ? 'Validación' : 'Validation', ficha.cultivo.estado_validacion);
    }
    $('detalle').showModal();
}
async function tarjeta(p) {
    const card = nodo('article', 'tarjeta');
    card.append(await imagen(p));
    const d = nodo('div', 'datos');
    d.append(nodo('span', 'muted', p.categoria), nodo('h2', null, p.especie), nodo('div', 'muted', p.cientifico || 'Nombre científico pendiente'), nodo('div', 'muted', p.ingles || 'Nombre inglés pendiente'), nodo('p', 'precio', moneda(p.precio)), nodo('p', 'muted', p.tamano || 'Tamaño por consultar'));

    const tienePrecio = precioValido(p);
    const selector = nodo('div', 'selector-cantidad');
    const menos = nodo('button', null, '−');
    menos.type = 'button';
    menos.setAttribute('aria-label', `Disminuir cantidad de ${p.especie}`);
    const cantidad = nodo('input');
    cantidad.type = 'number';
    cantidad.min = '1';
    cantidad.step = '1';
    cantidad.value = '1';
    cantidad.inputMode = 'numeric';
    cantidad.setAttribute('aria-label', `Cantidad de ${p.especie}`);
    const mas = nodo('button', null, '+');
    mas.type = 'button';
    mas.setAttribute('aria-label', `Aumentar cantidad de ${p.especie}`);
    menos.disabled = !tienePrecio;
    cantidad.disabled = !tienePrecio;
    mas.disabled = !tienePrecio;
    const subtotal = nodo('p', 'subtotal-tarjeta');
    const actualizarSelector = () => {
        cantidad.value = String(cantidadValida(cantidad.value));
        subtotal.textContent = tienePrecio ? `Subtotal: ${moneda(Number(p.precio) * Number(cantidad.value))}` : 'Consultar precio';
        agregar.textContent = tienePrecio ? `🛒 Agregar ${cantidad.value} al carrito` : 'Consultar precio';
    };
    menos.onclick = () => { cantidad.value = String(Math.max(1, cantidadValida(cantidad.value) - 1)); actualizarSelector() };
    mas.onclick = () => { cantidad.value = String(cantidadValida(cantidad.value) + 1); actualizarSelector() };
    cantidad.addEventListener('input', actualizarSelector);
    cantidad.addEventListener('blur', actualizarSelector);
    selector.append(menos, cantidad, mas);
    d.append(selector, subtotal);

    const bs = nodo('div', 'botones');
    const btn = nodo('button', null, t('viewInfo'));
    btn.onclick = () => detalle(p);
    bs.append(btn);
    const agregar = nodo('button', 'agregar-carrito', tienePrecio ? '🛒 Agregar 1 al carrito' : 'Consultar precio');
    agregar.type = 'button';
    agregar.disabled = !tienePrecio;
    agregar.onclick = () => {
        const unidades = cantidadValida(cantidad.value);
        if (!agregarAlCarrito(p, unidades)) return;
        mostrarNotificacionCarrito(p, unidades);
        cantidad.value = '1';
        actualizarSelector();
        const confirmacion = nodo('span', 'confirmacion-carrito', `${unidades} agregado${unidades === 1 ? '' : 's'} al carrito`);
        bs.append(confirmacion);
        window.setTimeout(() => confirmacion.remove(), 2200);
    };
    bs.append(agregar);
    const wa = enlaceWA(p);
    if (wa) { const a = nodo('a', null, 'WhatsApp'); a.href = wa; a.target = '_blank'; a.rel = 'noopener noreferrer'; bs.append(a) }
    d.append(bs);
    const label = nodo('label', 'muted', idioma === 'es' ? 'Agregar/cambiar foto (solo este navegador)' : 'Add/change photo (this browser only)');
    const file = nodo('input', 'foto-input');
    file.type = 'file';
    file.accept = 'image/*';
    file.setAttribute('aria-label', 'Foto de ' + p.especie);
    file.onchange = async () => { try { if (!file.files[0]) return; await guardarFoto(p.id, file.files[0]); const nueva = await imagen(p); card.firstChild.replaceWith(nueva) } catch (e) { alert(e.message) } };
    label.append(file);
    d.append(label);
    card.append(d);
    actualizarSelector();
    return card;
}
function rangoTexto(min, max) { return min === null || max === null ? t('pending') : `${min}-${max} msnm` }
function evaluarFicha(ficha, altitud, clima, temperatura) {
    const cultivo = ficha.cultivo;
    if (cultivo.altitud_minima === null || cultivo.altitud_maxima === null) return 'insufficient';
    if (clima && !cultivo.clima.some(item => item.toLocaleLowerCase('es') === clima)) return 'no-recomendado';
    if (temperatura !== null && (cultivo.temperatura_minima === null || cultivo.temperatura_maxima === null)) return 'insufficient';
    if (temperatura !== null && (temperatura < cultivo.temperatura_minima || temperatura > cultivo.temperatura_maxima)) return 'no-recomendado';
    if (altitud >= cultivo.altitud_ideal_minima && altitud <= cultivo.altitud_ideal_maxima) return 'ideal';
    if (altitud >= cultivo.altitud_minima && altitud <= cultivo.altitud_maxima) return 'compatible';
    return 'no-recomendado';
}
function mostrarResultadosZona() {
    const altitud = Number($('altitud-zona').value);
    const temperaturaValor = $('temperatura-zona').value.trim();
    const temperatura = temperaturaValor === '' ? null : Number(temperaturaValor);
    const clima = $('clima-zona').value;
    const categoria = $('categoria-zona').value;
    const resultados = $('resultados-zona');
    resultados.replaceChildren();
    if (!Number.isFinite(altitud) || altitud < 0) {
        resultados.append(nodo('p', 'muted', idioma === 'es' ? 'Ingresa una altitud válida en msnm.' : 'Enter a valid altitude in m.a.s.l.'));
        return;
    }
    const clasificados = fichas
        .filter(ficha => !categoria || ficha.categoria === categoria)
        .map(ficha => ({ ficha, estado: evaluarFicha(ficha, altitud, clima, temperatura) }))
        .sort((a, b) => {
            const prioridad = ['ideal', 'compatible', 'no-recomendado', 'insufficient'];
            const diferencia = prioridad.indexOf(a.estado) - prioridad.indexOf(b.estado);
            if (diferencia !== 0) return diferencia;
            const nombreA = idioma === 'es' ? a.ficha.nombre_es : a.ficha.nombre_en;
            const nombreB = idioma === 'es' ? b.ficha.nombre_es : b.ficha.nombre_en;
            return nombreA.localeCompare(nombreB, idioma);
        });
    if (!clasificados.length) {
        resultados.append(nodo('p', 'muted', t('noResults')));
        return;
    }
    resultados.append(nodo('h3', null, `${t('resultsFor')} (${clasificados.length})`));
    const grid = nodo('div', 'resultados-zona-grid');
    clasificados.forEach(({ ficha, estado }) => {
        const card = nodo('article', `resultado-zona ${estado}`);
        const titulo = nodo('h3', null, idioma === 'es' ? ficha.nombre_es : ficha.nombre_en);
        const estadoTexto = t(estado === 'no-recomendado' ? 'notRecommended' : estado);
        card.append(titulo, nodo('p', 'etiqueta-compatibilidad', estadoTexto));
        card.append(nodo('p', null, `${t('altitudeRange')}: ${rangoTexto(ficha.cultivo.altitud_minima, ficha.cultivo.altitud_maxima)}`));
        card.append(nodo('p', null, `${t('idealRange')}: ${rangoTexto(ficha.cultivo.altitud_ideal_minima, ficha.cultivo.altitud_ideal_maxima)}`));
        if (ficha.cultivo.clima.length) card.append(nodo('p', null, `${t('climateLabel')}: ${ficha.cultivo.clima.join(', ')}`));
        if (ficha.cultivo.temperatura_optima) card.append(nodo('p', null, `${idioma === 'es' ? 'Temperatura recomendada' : 'Recommended temperature'}: ${ficha.cultivo.temperatura_optima}`));
        const info = nodo('button', null, t('viewInfo'));
        info.type = 'button';
        info.onclick = () => {
            const producto = productos.find(item => ficha.inventario_ids.includes(item.id));
            if (producto) detalle(producto);
        };
        card.append(info);
        grid.append(card);
    });
    resultados.append(grid);
}
let renderVersion = 0;
async function pintar() {
    const v = ++renderVersion;
    const q = $('buscar').value.toLocaleLowerCase('es').trim();
    const cat = $('categoria').value;
    const ord = $('orden').value;
    const filtered = productos.filter(p => (!cat || p.categoria === cat) && [p.especie, p.cientifico, p.ingles, p.categoria].join(' ').toLocaleLowerCase('es').includes(q));
    filtered.sort((a, b) => ord === 'precio-asc'
        ? Number(a.precio || 0) - Number(b.precio || 0)
        : ord === 'precio-desc'
            ? Number(b.precio || 0) - Number(a.precio || 0)
            : a.especie.localeCompare(b.especie, 'es'));
    $('total').textContent = `${filtered.length} ${idioma === 'es' ? 'presentaciones encontradas' : 'presentations found'}`;
    const cont = document.createDocumentFragment();
    if (!filtered.length) {
        cont.append(nodo('p', 'sin-resultados', t('noProductMatches')));
    } else {
        for (const p of filtered) {
            if (v !== renderVersion) return;
            cont.append(await tarjeta(p));
        }
    }
    if (v === renderVersion) $('tarjetas').replaceChildren(cont);
}
async function iniciar() {
    try {
        const [inventarioResponse, fichasResponse] = await Promise.all([fetch(RUTA), fetch(RUTA_FICHAS)]);
        if (!inventarioResponse.ok || !fichasResponse.ok) throw Error('No se pudo abrir el inventario botánico o comercial');
        productos = await inventarioResponse.json();
        const fichasData = await fichasResponse.json();
        fichas = Array.isArray(fichasData.especies) ? fichasData.especies : [];
        if (!fichas.length) throw Error('La base botánica no contiene especies');
        actualizarIdioma();
        cargarCarrito();
        sincronizarCarrito();
        for (const cat of [...new Set(productos.map(p => p.categoria))].sort((a, b) => a.localeCompare(b, 'es'))) {
            const op = nodo('option', null, cat); op.value = cat; $('categoria').append(op);
            const zonaOp = op.cloneNode(true); $('categoria-zona').append(zonaOp);
        }
        for (const id of ['buscar', 'categoria', 'orden']) $(id).addEventListener(id === 'buscar' ? 'input' : 'change', pintar);
        $('formulario-busqueda').onsubmit = event => {
            event.preventDefault();
            pintar();
            mostrarEstadoBoton('buscar-catalogo');
        };
        $('formulario-busqueda-zona').onsubmit = event => {
            event.preventDefault();
            mostrarResultadosZona();
            mostrarEstadoBoton('buscar-zona');
        };
        $('cambiar-idioma').onclick = () => {
            idioma = idioma === 'es' ? 'en' : 'es';
            localStorage.setItem('vivero-idioma', idioma);
            actualizarIdioma();
            pintar();
            if ($('vista-recomendaciones').hidden === false && $('altitud-zona').value) mostrarResultadosZona();
        };
        $('abrir-recomendaciones').onclick = () => cambiarVista('recomendaciones');
        $('volver-catalogo').onclick = () => cambiarVista('catalogo');
        $('cerrar').onclick = () => $('detalle').close();
        $('abrir-carrito').onclick = () => { abrirDialogo('carrito'); mostrarCarrito() };
        $('cerrar-carrito').onclick = () => $('carrito').close();
        $('continuar-comprando').onclick = () => $('carrito').close();
        $('realizar-pedido').onclick = () => { $('carrito').close(); abrirDialogo('datos-pedido') };
        $('cerrar-datos').onclick = () => $('datos-pedido').close();
        $('formulario-pedido').onsubmit = event => {
            event.preventDefault();
            const resultado = validarFormulario(event.currentTarget);
            if (typeof resultado === 'string') { $('error-formulario').textContent = resultado; return }
            datosPedido = resultado;
            $('error-formulario').textContent = '';
            $('datos-pedido').close();
            mostrarRevision();
            abrirDialogo('revision-pedido');
        };
        $('cerrar-revision').onclick = () => $('revision-pedido').close();
        $('modificar-pedido').onclick = () => { $('revision-pedido').close(); abrirDialogo('datos-pedido') };
        $('enviar-whatsapp').onclick = event => {
            const boton = event.currentTarget;
            boton.disabled = true;
            window.open(`https://wa.me/${WHATSAPP_PEDIDOS}?text=${encodeURIComponent(mensajeWhatsApp())}`, '_blank', 'noopener,noreferrer');
            window.setTimeout(() => { boton.disabled = false }, 1000);
        };
        await pintar();
        if (new URLSearchParams(window.location.search).get('seccion') === 'recomendaciones') {
            cambiarVista('recomendaciones');
        }
    } catch (e) { $('total').textContent = 'Error cargando el inventario. Abrí el proyecto con Live Server en VS Code. ' + e.message }
}
iniciar();