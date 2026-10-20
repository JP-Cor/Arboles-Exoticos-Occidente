// Catálogo generado a partir de Inventario/inventario.json.
// Las fotos subidas desde el navegador se guardan LOCALMENTE en IndexedDB de ese navegador.
const RUTA = '../Inventario/inventario.json';
const WHATSAPP = ''; // Escribir número con código de país, por ejemplo 506XXXXXXXX.
const $ = id => document.getElementById(id);
let productos = [];
const dbReady = new Promise((resolve, reject) => { const r = indexedDB.open('vivero-fotos', 1); r.onupgradeneeded = () => r.result.createObjectStore('fotos'); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error) });
async function fotoLocal(id) { const db = await dbReady; return new Promise(resolve => { const tx = db.transaction('fotos', 'readonly'); const req = tx.objectStore('fotos').get(id); req.onsuccess = () => resolve(req.result || null); req.onerror = () => resolve(null) }) }
async function guardarFoto(id, file) { if (!file.type.startsWith('image/')) throw Error('Seleccioná una imagen'); if (file.size > 3 * 1024 * 1024) throw Error('Máximo 3 MB'); const db = await dbReady; return new Promise((resolve, reject) => { const tx = db.transaction('fotos', 'readwrite'); tx.objectStore('fotos').put(file, id); tx.oncomplete = resolve; tx.onerror = () => reject(tx.error) }) }
function nodo(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = String(text); return e }
function moneda(n) { return Number.isFinite(Number(n)) && n !== null && n !== '' ? new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', maximumFractionDigits: 0 }).format(n) : 'Consultar' }
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
async function tarjeta(p) { const card = nodo('article', 'tarjeta'); card.append(await imagen(p)); const d = nodo('div', 'datos'); d.append(nodo('span', 'muted', p.categoria), nodo('h2', null, p.especie), nodo('div', 'muted', p.cientifico || 'Nombre científico pendiente'), nodo('div', 'muted', p.ingles || 'Nombre inglés pendiente'), nodo('p', 'precio', moneda(p.precio)), nodo('p', 'muted', p.tamano || 'Tamaño por consultar')); const bs = nodo('div', 'botones'); const btn = nodo('button', null, 'Ver detalles'); btn.onclick = () => detalle(p); bs.append(btn); const wa = enlaceWA(p); if (wa) { const a = nodo('a', null, 'WhatsApp'); a.href = wa; a.target = '_blank'; a.rel = 'noopener noreferrer'; bs.append(a) } d.append(bs); const label = nodo('label', 'muted', 'Agregar/cambiar foto (solo este navegador)'); const file = nodo('input', 'foto-input'); file.type = 'file'; file.accept = 'image/*'; file.setAttribute('aria-label', 'Foto de ' + p.especie); file.onchange = async () => { try { if (!file.files[0]) return; await guardarFoto(p.id, file.files[0]); const nueva = await imagen(p); card.firstChild.replaceWith(nueva) } catch (e) { alert(e.message) } }; label.append(file); d.append(label); card.append(d); return card }
let renderVersion = 0;
async function pintar() { const v = ++renderVersion; const q = $('buscar').value.toLocaleLowerCase('es').trim(), cat = $('categoria').value, ord = $('orden').value; const filtered = productos.filter(p => (!cat || p.categoria === cat) && [p.especie, p.cientifico, p.ingles, p.categoria].join(' ').toLocaleLowerCase('es').includes(q)); filtered.sort((a, b) => ord === 'precio-asc' ? Number(a.precio || 0) - Number(b.precio || 0) : ord === 'precio-desc' ? Number(b.precio || 0) - Number(a.precio || 0) : a.especie.localeCompare(b.especie, 'es')); $('total').textContent = `${filtered.length} presentaciones encontradas`; const cont = document.createDocumentFragment(); for (const p of filtered) { if (v !== renderVersion) return; cont.append(await tarjeta(p)) } if (v === renderVersion) $('tarjetas').replaceChildren(cont) }
async function iniciar() { try { const r = await fetch(RUTA); if (!r.ok) throw Error('No se pudo abrir el JSON'); productos = await r.json(); for (const cat of [...new Set(productos.map(p => p.categoria))].sort((a, b) => a.localeCompare(b, 'es'))) { const op = nodo('option', null, cat); op.value = cat; $('categoria').append(op) } for (const id of ['buscar', 'categoria', 'orden']) $(id).addEventListener(id === 'buscar' ? 'input' : 'change', pintar); $('cerrar').onclick = () => $('detalle').close(); await pintar() } catch (e) { $('total').textContent = 'Error cargando el inventario. Abrí el proyecto con Live Server en VS Code. ' + e.message } }
iniciar();