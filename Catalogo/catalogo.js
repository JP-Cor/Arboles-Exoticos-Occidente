// Catálogo generado a partir de Inventario/inventario.json.
// Las fotos subidas desde el navegador se guardan LOCALMENTE en IndexedDB de ese navegador.
const RUTA = '../Inventario/inventario.json';
const WHATSAPP = ''; // Escribir número con código de país, por ejemplo 506XXXXXXXX.
const WHATSAPP_PEDIDOS = '50685574977';
const CLAVE_CARRITO = 'vivero-carrito';
const $ = id => document.getElementById(id);
let productos = [];
let carrito = [];
let datosPedido = null;
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
        alert('Este producto no tiene un precio válido y no se puede agregar al carrito.');
        return;
    }
    cantidad = cantidadValida(cantidad);
    const existente = productoEnCarrito(p.id);
    if (existente) existente.cantidad += cantidad;
    else carrito.push({ id: p.id, cantidad });
    guardarCarrito();
    actualizarContador();
    mostrarCarrito();
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
async function imagen(p) {
    // 1. Buscar fotografía guardada en este navegador
    const local = await fotoLocal(p.id);

    if (local) {
        const url = URL.createObjectURL(local);
        const img = nodo('img', 'foto');

        img.src = url;
        img.alt = p.especie;

        img.onload = () => URL.revokeObjectURL(url);

        return img;
    }

    // 2. Buscar fotografía permanente del catálogo
    if (p.foto) {
        const img = nodo('img', 'foto');

        const ruta = String(p.foto)
            .replace(/\\/g, '/')
            .replace(/^\/+/, '');

        img.src = '../imagenes/' +
            ruta.split('/').map(encodeURIComponent).join('/');

        img.alt = p.especie;
        img.loading = 'lazy';

        img.onerror = () => {
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
function detalle(p) { const c = $('contenido-detalle'); c.replaceChildren(); c.append(nodo('h2', null, p.especie)); linea(c, 'Categoría', p.categoria); linea(c, 'Nombre científico', p.cientifico); linea(c, 'Nombre en inglés', p.ingles); linea(c, 'Precio', moneda(p.precio)); linea(c, 'Tamaño', p.tamano); linea(c, 'Propagación / clima', p.propagacion); linea(c, 'Observaciones', p.observaciones); linea(c, 'Disponibilidad', p.disponibilidad || 'Consultar'); linea(c, 'Validación taxonómica', p.validacion); $('detalle').showModal() }
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
    const btn = nodo('button', null, 'Ver detalles');
    btn.onclick = () => detalle(p);
    bs.append(btn);
    const agregar = nodo('button', 'agregar-carrito', tienePrecio ? '🛒 Agregar 1 al carrito' : 'Consultar precio');
    agregar.type = 'button';
    agregar.disabled = !tienePrecio;
    agregar.onclick = () => {
        const unidades = cantidadValida(cantidad.value);
        agregarAlCarrito(p, unidades);
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
    const label = nodo('label', 'muted', 'Agregar/cambiar foto (solo este navegador)');
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
let renderVersion = 0;
async function pintar() { const v = ++renderVersion; const q = $('buscar').value.toLocaleLowerCase('es').trim(), cat = $('categoria').value, ord = $('orden').value; const filtered = productos.filter(p => (!cat || p.categoria === cat) && [p.especie, p.cientifico, p.ingles, p.categoria].join(' ').toLocaleLowerCase('es').includes(q)); filtered.sort((a, b) => ord === 'precio-asc' ? Number(a.precio || 0) - Number(b.precio || 0) : ord === 'precio-desc' ? Number(b.precio || 0) - Number(a.precio || 0) : a.especie.localeCompare(b.especie, 'es')); $('total').textContent = `${filtered.length} presentaciones encontradas`; const cont = document.createDocumentFragment(); for (const p of filtered) { if (v !== renderVersion) return; cont.append(await tarjeta(p)) } if (v === renderVersion) $('tarjetas').replaceChildren(cont) }
async function iniciar() {
    try {
        const r = await fetch(RUTA);
        if (!r.ok) throw Error('No se pudo abrir el JSON');
        productos = await r.json();
        cargarCarrito();
        sincronizarCarrito();
        for (const cat of [...new Set(productos.map(p => p.categoria))].sort((a, b) => a.localeCompare(b, 'es'))) { const op = nodo('option', null, cat); op.value = cat; $('categoria').append(op) }
        for (const id of ['buscar', 'categoria', 'orden']) $(id).addEventListener(id === 'buscar' ? 'input' : 'change', pintar);
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
    } catch (e) { $('total').textContent = 'Error cargando el inventario. Abrí el proyecto con Live Server en VS Code. ' + e.message }
}
iniciar();