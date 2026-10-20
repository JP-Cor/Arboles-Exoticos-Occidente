
import json
import sys
import pathlib
import re
import unicodedata
from openpyxl import load_workbook

# =====================================
# CONFIGURACIÓN
# =====================================

RAIZ = pathlib.Path(__file__).resolve().parents[1]
INVENTARIO = RAIZ / "Inventario"
IMAGENES = RAIZ / "imagenes"

JSON_FILE = INVENTARIO / "inventario.json"
EQUIVALENCIAS_FILE = INVENTARIO / "equivalencias_fotos.json"

EXCEL_FILE = (
    pathlib.Path(sys.argv[1]).resolve()
    if len(sys.argv) > 1
    else INVENTARIO / "inventario.xlsx"
)

COLUMNAS = [
    "id",
    "categoria",
    "especie",
    "precio",
    "tamano",
    "propagacion",
    "observaciones",
    "disponibilidad",
    "cientifico",
    "ingles",
    "validacion"
]

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


# =====================================
# NORMALIZAR NOMBRES
# =====================================

def normalizar(texto):
    texto = str(texto or "").lower().strip()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9]+", " ", texto)

    return " ".join(texto.split())


# =====================================
# IDENTIFICAR CARPETA DE CATEGORÍA
# =====================================

def carpeta_categoria(categoria):
    cat = normalizar(categoria)

    if "aguacate" in cat:
        return "aguacates"

    if "citrico" in cat:
        return "citricos"

    if "mango" in cat:
        return "mangos"

    if "criollo" in cat:
        return "criollos"

    if "exotico" in cat:
        return "exoticos"

    if "frutal" in cat:
        return "frutales"

    return ""


# =====================================
# FOTOGRAFÍAS ESPECIALES
# =====================================

FOTOS_ESPECIALES = {
    "aguacates": {
        "catalina": "aguacate catalin.jpg",
        "chokette": "Chokette.webp",
        "choquette": "Chokette.webp",
        "ettinger": "Ettinger.jpg",
        "kahalu": "Kahalú.jpg",
        "puerto rico": "Puerto Rico.jpg",
        "simon": "Simón.jpg",
        "simpson": "Simpson.jpg",
        "vulcano": "Vulcano.jpg"
    }
}


# =====================================
# LEER EQUIVALENCIAS
# =====================================

EQUIVALENCIAS = {}

if EQUIVALENCIAS_FILE.exists():
    datos = json.loads(
        EQUIVALENCIAS_FILE.read_text(encoding="utf-8")
    )

    EQUIVALENCIAS = {
        normalizar(nombre): ruta
        for nombre, ruta in datos.items()
    }


# =====================================
# VALIDAR RUTA DE FOTOGRAFÍA
# =====================================

def validar_foto(ruta):
    if not isinstance(ruta, str) or not ruta.strip():
        return ""

    base = IMAGENES.resolve()
    archivo = (base / ruta).resolve()

    if (
        not archivo.is_relative_to(base)
        or not archivo.is_file()
        or archivo.suffix.lower() not in EXTENSIONES
    ):
        return ""

    return archivo.relative_to(base).as_posix()


# =====================================
# BUSCAR FOTOGRAFÍA AUTOMÁTICAMENTE
# =====================================

def buscar_foto(especie, categoria, archivos):
    nombre = normalizar(especie)
    carpeta = carpeta_categoria(categoria)

    if not nombre:
        return ""

    # 1. Equivalencias manuales
    ruta = EQUIVALENCIAS.get(nombre, "")

    if ruta:
        foto = validar_foto(ruta)
        if foto:
            return foto

    # 2. Fotografías especiales
    especial = FOTOS_ESPECIALES.get(
        carpeta, {}
    ).get(nombre, "")

    if especial:
        foto = validar_foto(f"{carpeta}/{especial}")
        if foto:
            return foto

    # 3. Priorizar la carpeta de categoría
    ordenados = sorted(
        archivos,
        key=lambda archivo: (
            0 if archivo.relative_to(IMAGENES).parts[0].lower()
            == carpeta else 1,
            str(archivo).lower()
        )
    )

    # 4. Coincidencia exacta
    for archivo in ordenados:
        if normalizar(archivo.stem) == nombre:
            return archivo.relative_to(IMAGENES).as_posix()

    # 5. Coincidencia con número
    for archivo in ordenados:
        nombre_archivo = normalizar(archivo.stem)

        if re.fullmatch(
            re.escape(nombre) + r"\s*\d+",
            nombre_archivo
        ):
            return archivo.relative_to(IMAGENES).as_posix()

    # 6. Coincidencia por prefijo
    for archivo in ordenados:
        nombre_archivo = normalizar(archivo.stem)

        if nombre_archivo.startswith(nombre + " "):
            return archivo.relative_to(IMAGENES).as_posix()

    return ""


# =====================================
# ARCHIVOS DE IMAGEN DISPONIBLES
# =====================================

archivos_imagenes = []

if IMAGENES.exists():
    archivos_imagenes = [
        archivo
        for archivo in IMAGENES.rglob("*")
        if archivo.is_file()
        and archivo.suffix.lower() in EXTENSIONES
    ]


# =====================================
# CONSERVAR FOTOGRAFÍAS ANTERIORES
# =====================================

fotos_anteriores = {}

if JSON_FILE.exists():
    datos_anteriores = json.loads(
        JSON_FILE.read_text(encoding="utf-8")
    )

    for producto in datos_anteriores:
        fotos_anteriores[producto["id"]] = producto.get(
            "foto", ""
        )


# =====================================
# LEER EXCEL
# =====================================

if not EXCEL_FILE.exists():
    raise FileNotFoundError(
        f"No existe el Excel: {EXCEL_FILE}"
    )

wb = load_workbook(
    EXCEL_FILE,
    read_only=True,
    data_only=True
)

hoja = (
    wb["Catálogo completo"]
    if "Catálogo completo" in wb.sheetnames
    else wb.active
)

registros = []
sin_foto = []

for fila in hoja.iter_rows(min_row=2, values_only=True):

    if not fila or not isinstance(fila[0], (int, float)):
        continue

    producto = {
        clave: (
            fila[i]
            if i < len(fila) and fila[i] is not None
            else ""
        )
        for i, clave in enumerate(COLUMNAS)
    }

    producto["id"] = int(producto["id"])

    foto_anterior = fotos_anteriores.get(
        producto["id"], ""
    )

    foto = validar_foto(foto_anterior)

    if not foto:
        foto = buscar_foto(
            producto["especie"],
            producto["categoria"],
            archivos_imagenes
        )

    producto["foto"] = foto

    if not foto:
        sin_foto.append(
            f'{producto["categoria"]} - {producto["especie"]}'
        )

    registros.append(producto)

wb.close()


# =====================================
# GUARDAR INVENTARIO JSON
# =====================================

INVENTARIO.mkdir(parents=True, exist_ok=True)

JSON_FILE.write_text(
    json.dumps(
        registros,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print("\nINVENTARIO ACTUALIZADO")
print("-----------------------------")
print(f"Presentaciones: {len(registros)}")
print(f"Con fotografía: {len(registros) - len(sin_foto)}")
print(f"Sin fotografía: {len(sin_foto)}")
print(f"Archivo generado: {JSON_FILE}")

if sin_foto:
    print("\nESPECIES SIN FOTOGRAFÍA:")

    for especie in sorted(set(sin_foto)):
        print(" -", especie)
