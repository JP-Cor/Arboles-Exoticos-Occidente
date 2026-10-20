
/* ÁRBOLES EXÓTICOS OCCIDENTE
   Página principal conectada al inventario real.
*/

const WHATSAPP = ""; // Ejemplo: 506XXXXXXXX
const RUTA_INVENTARIO = "Inventario/inventario.json";

let lang = "es";
let plants = [];
let currentPlant = null;

const $ = id => document.getElementById(id);

const strings = {
  es: {
    hero: "Descubrí la naturaleza en cada fruto",
    desc: "Explorá nuestros árboles frutales y especies exóticas.",
    explore: "Explorar catálogo →",
    tag: "NUESTRO VIVERO",
    catalog: "Catálogo de plantas",
    intro: "Conocé nuestras especies, variedades, precios y fotografías.",
    search: "Buscar por especie, variedad o nombre científico...",
    all: "Todas las categorías",
    contact: "Consultas y pedidos",
    contactText: "Consultá disponibilidad, tamaño y precio directamente con el vivero.",
    contactNote: "Consultas por WhatsApp próximamente.",
    footer: "Catálogo botánico",
    view: "Ver más",
    count: "presentaciones",
    notFound: "No se encontraron plantas.",
    pending: "Por confirmar",
    scientific: "Nombre científico",
    english: "Nombre en inglés",
    price: "Precio",
    size: "Tamaño",
    category: "Categoría",
    availability: "Disponibilidad",
    propagation: "Propagación / clima",
    observations: "Observaciones",
    validation: "Validación taxonómica",
    ask: "Consultar por WhatsApp",
    askPending: "WhatsApp aún no configurado",
    error: "No se pudo cargar el inventario."
  },
  en: {
    hero: "Discover nature in every fruit",
    desc: "Explore our fruit trees and exotic plants.",
    explore: "Explore catalog →",
    tag: "OUR NURSERY",
    catalog: "Plant catalog",
    intro: "Discover our species, varieties, prices and photographs.",
    search: "Search by species, variety or scientific name...",
    all: "All categories",
    contact: "Inquiries and orders",
    contactText: "Ask our nursery about prices, sizes and availability.",
    contactNote: "WhatsApp inquiries coming soon.",
    footer: "Botanical catalog",
    view: "Read more",
    count: "listings",
    notFound: "No plants found.",
    pending: "To be confirmed",
    scientific: "Scientific name",
    english: "English name",
    price: "Price",
    size: "Size",
    category: "Category",
    availability: "Availability",
    propagation: "Propagation / climate",
    observations: "Notes",
    validation: "Taxonomic validation",
    ask: "Ask on WhatsApp",
    askPending: "WhatsApp not configured",
    error: "Could not load inventory."
  }
};

function safe(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[c]));
}

function precio(value) {
  if (value === null || value === undefined || value === "") {
    return strings[lang].pending;
  }

  const numero = Number(value);
  if (!Number.isFinite(numero)) return strings[lang].pending;

  return new Intl.NumberFormat("es-CR", {
    style: "currency",
    currency: "CRC",
    maximumFractionDigits: 0
  }).format(numero);
}

function nombre(p) {
  return lang === "en" && p.ingles
    ? p.ingles + (p.especie ? " — " + p.especie : "")
    : p.especie;
}

function rutaFoto(p) {
  
function rutaFoto(p) {
    const fotosAguacates = {
        "catalina": "aguacates/aguacate catalin.jpg",
        "choquette": "aguacates/Chokette.webp",
        "chokette": "aguacates/Chokette.webp",
        "ettinger": "aguacates/Ettinger.jpg",
        "kahalú": "aguacates/Kahalú.jpg",
        "kahalu": "aguacates/Kahalú.jpg",
        "puerto rico": "aguacates/Puerto Rico.jpg",
        "simón": "aguacates/Simón.jpg",
        "simon": "aguacates/Simón.jpg",
        "simpson": "aguacates/Simpson.jpg",
        "vulcano": "aguacates/Vulcano.jpg"
    };

    let foto = p.foto || "";

    if (!foto && p.categoria?.toLowerCase().includes("aguacate")) {
        const variedad = p.especie
            ?.toLowerCase()
            .trim()
            .normalize("NFC");

        foto = fotosAguacates[variedad] || "";
    }

    if (!foto) return "";

    const partes = foto.replace(/\\/g, "/")
        .split("/");

    if (partes.some(x => x === ".." || x === "." || !x)) {
        return "";
    }

    return "imagenes/" +
        partes.map(encodeURIComponent).join("/");
}
}

function fotoHTML(p) {
  const ruta = rutaFoto(p);

  if (!ruta) {
    return '<div class="sin-foto">🌱 Fotografía pendiente</div>';
  }

  return `<img class="foto" loading="lazy"
    src="${safe(ruta)}"
    alt="${safe(p.especie)}"
    onerror="this.hidden=true;this.nextElementSibling.hidden=false">
    <div class="sin-foto" hidden>🌱 Fotografía pendiente</div>`;
}

function cargarCategorias() {
  const selector = $("category");
  const actual = selector.value;

  const categorias = [...new Set(
    plants.map(p => p.categoria).filter(Boolean)
  )].sort((a, b) => a.localeCompare(b, "es"));

  selector.replaceChildren();

  const todas = document.createElement("option");
  todas.value = "all";
  todas.textContent = strings[lang].all;
  selector.append(todas);

  categorias.forEach(cat => {
    const option = document.createElement("option");
    option.value = cat;
    option.textContent = cat;
    selector.append(option);
  });

  selector.value = categorias.includes(actual) ? actual : "all";
}

function render() {
  const t = strings[lang];

  document.documentElement.lang = lang;

  $("lang").textContent = lang === "es" ? "EN" : "ES";
  $("hero-title").textContent = t.hero;
  $("hero-desc").textContent = t.desc;
  $("explore").textContent = t.explore;
  $("sectiontag").textContent = t.tag;
  $("catalog-title").textContent = t.catalog;
  $("intro").textContent = t.intro;
  $("search").placeholder = t.search;
  $("contact-title").textContent = t.contact;
  $("contact-text").textContent = t.contactText;
  $("contact-note").textContent = t.contactNote;
  $("footer-text").textContent = t.footer;
  $("empty").textContent = t.notFound;

  document.querySelectorAll("[data-es]").forEach(element => {
    element.textContent = element.dataset[lang];
  });

  cargarCategorias();

  const query = $("search").value.toLocaleLowerCase("es").trim();
  const categoria = $("category").value;

  const filtradas = plants.filter(p => {
    const texto = [
      p.especie,
      p.cientifico,
      p.ingles,
      p.categoria,
      p.observaciones
    ].join(" ").toLocaleLowerCase("es");

    return texto.includes(query) &&
      (categoria === "all" || p.categoria === categoria);
  });

  $("count").textContent = `${filtradas.length} ${t.count}`;
  $("empty").hidden = filtradas.length > 0;

  $("grid").innerHTML = filtradas.map(p => `
    <article class="plant">
      ${fotoHTML(p)}
      <div class="plant-body">
        <div class="muted">${safe(p.categoria)}</div>
        <h3>${safe(nombre(p))}</h3>
        <p class="latin"><em>${safe(p.cientifico || t.pending)}</em></p>
        <p class="muted">${safe(p.ingles || t.pending)}</p>
        <p class="precio">${safe(precio(p.precio))}</p>
        <p class="plant-summary">${safe(p.tamano || "")}</p>
        <button type="button" data-id="${safe(p.id)}">
          ${t.view} →
        </button>
      </div>
    </article>
  `).join("");

  document.querySelectorAll("#grid button[data-id]").forEach(btn => {
    btn.addEventListener("click", () => {
      const planta = plants.find(p => String(p.id) === btn.dataset.id);
      detail(planta);
    });
  });
}

function detail(p) {
  if (!p) return;

  currentPlant = p;
  const t = strings[lang];

  const fila = (titulo, valor) => {
    if (valor === null || valor === undefined || valor === "") return "";
    return `<p><strong>${safe(titulo)}:</strong> ${safe(valor)}</p>`;
  };

  const whatsapp = WHATSAPP
    ? `<a class="primary" target="_blank" rel="noopener noreferrer"
        href="https://wa.me/${encodeURIComponent(WHATSAPP)}?text=${
          encodeURIComponent(
            "Hola, deseo consultar por " + p.especie +
            ", tamaño " + (p.tamano || "por confirmar") +
            ", precio " + precio(p.precio)
          )
        }">${t.ask}</a>`
    : `<p class="muted">${t.askPending}</p>`;

  $("detail-content").innerHTML = `
    ${fotoHTML(p)}
    <h2>${safe(nombre(p))}</h2>
    ${fila(t.category, p.categoria)}
    ${fila(t.scientific, p.cientifico)}
    ${fila(t.english, p.ingles)}
    ${fila(t.price, precio(p.precio))}
    ${fila(t.size, p.tamano)}
    ${fila(t.propagation, p.propagacion)}
    ${fila(t.observations, p.observaciones)}
    ${fila(t.availability, p.disponibilidad || t.pending)}
    ${fila(t.validation, p.validacion)}
    <div class="detail-section">${whatsapp}</div>
  `;

  if (!$("detail").open) $("detail").showModal();
}

$("lang").addEventListener("click", () => {
  lang = lang === "es" ? "en" : "es";
  render();
  if ($("detail").open && currentPlant) detail(currentPlant);
});

$("search").addEventListener("input", render);
$("category").addEventListener("change", render);

$("close").addEventListener("click", () => $("detail").close());

$("detail").addEventListener("click", e => {
  if (e.target === $("detail")) $("detail").close();
});

$("year").textContent = new Date().getFullYear();

async function iniciar() {
  try {
    const response = await fetch(RUTA_INVENTARIO, {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error("HTTP " + response.status);
    }

    const datos = await response.json();

    if (!Array.isArray(datos)) {
      throw new Error("El inventario no es una lista");
    }

    plants = datos;
    render();

    console.log("Inventario cargado:", plants.length);

  } catch (error) {
    console.error("Error cargando inventario:", error);
    $("grid").textContent = strings[lang].error;
  }
}

iniciar();
