"""Añade especies nuevas sin inventar precios, tamaños o identificaciones."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTARIO = ROOT / "Inventario" / "inventario.json"
FICHAS = ROOT / "Inventario" / "fichas_especies.json"

MADERABLES = [
    "Aceituno", "Caoba", "Cedro Amargo", "Cedro Dulce", "Ceiba", "Cenízaro",
    "Ciprés", "Cocobolo", "Cristóbal", "Espavel", "Eucalipto", "Guachipelín",
    "Guapinol", "Nogal", "Pochote", "Ron Ron",
]
AVES = [
    "Aguacatito", "Almendro de Montaña", "Almendro de Playa", "Capulín", "Cereza",
    "Damas", "Guayaba de Mono", "Güitite", "Icaco", "Jaboticaba", "Manzanita",
    "Papaturro", "Pitanga", "Tucuico", "Uva de la Selva",
]


def clave(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def nueva_ficha(product: dict) -> dict:
    nombre = product["especie"]
    return {
        "id_especie": f"pendiente_{product['id']}_{clave(nombre).replace(' ', '_')}",
        "inventario_ids": [product["id"]],
        "nombre_es": nombre,
        "nombre_en": "Identification pending",
        "nombre_cientifico": "Por verificar",
        "familia_botanica": None,
        "categoria": product["categoria"],
        "origen": None,
        "cultivo": {
            "altitud_minima": None, "altitud_maxima": None,
            "altitud_ideal_minima": None, "altitud_ideal_maxima": None,
            "temperatura_minima": None, "temperatura_maxima": None,
            "temperatura_optima": None, "clima": [],
            "exposicion_solar": None, "riego": None, "suelo": None,
            "drenaje": None, "resistencia_viento": None, "tolerancia_sequia": None,
            "estado_validacion": "Identificación científica pendiente de confirmación.",
        },
        "caracteristicas": {
            "altura_adulta": None, "diametro_copa": None, "velocidad_crecimiento": None,
            "tiempo_produccion": None, "epoca_floracion": None, "epoca_cosecha": None,
            "produccion_estimada": None, "recomendaciones_poda": None,
            "distancia_siembra": None, "fruto": None,
        },
        "beneficios": {
            "vitaminas": [], "minerales": [], "antioxidantes": [], "fibra": None,
            "nutricion": None, "beneficios": None, "usos_gastronomicos": None,
            "usos_tradicionales": None,
        },
        "descripcion": {
            "es": f"Ficha botánica de {nombre} pendiente de identificación científica y validación de condiciones de cultivo.",
            "en": f"Botanical record for {nombre} pending scientific identification and growing-condition validation.",
        },
        "fuente_datos": "Investigación pendiente; no se asignan valores sin confirmar la especie utilizada en Costa Rica.",
        "estado_investigacion": "Pendiente",
        "fuentes": [],
        "datos_especiales": {},
    }


def main() -> None:
    inventory = json.loads(INVENTARIO.read_text(encoding="utf-8"))
    botanical = json.loads(FICHAS.read_text(encoding="utf-8"))
    existing_names = {clave(item.get("especie", "")) for item in inventory}
    existing_scientific = {item.get("cientifico") for item in inventory}
    next_id = max(item["id"] for item in inventory) + 1
    added: list[dict] = []
    already_present: list[str] = []
    for category, names in (("Maderables", MADERABLES), ("Frutas para Aves", AVES)):
        for name in names:
            if clave(name) in existing_names:
                already_present.append(name)
                continue
            product = {
                "id": next_id, "categoria": category, "especie": name, "precio": None,
                "tamano": "", "propagacion": "", "observaciones": "Precio, tamaño e identificación científica pendientes de confirmación.",
                "disponibilidad": "Consultar", "cientifico": "Por verificar", "ingles": "Identification pending",
                "validacion": "Identificación científica pendiente de confirmación.", "foto": "",
            }
            inventory.append(product)
            botanical["especies"].append(nueva_ficha(product))
            added.append(product)
            next_id += 1

    INVENTARIO.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    FICHAS.write_text(json.dumps(botanical, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = ROOT / "Inventario" / "reporte_ampliacion_categorias.md"
    report.write_text(
        "# Reporte de ampliación de categorías\n\n"
        f"- Productos originales conservados: 258\n"
        f"- Productos nuevos incorporados: {len(added)}\n"
        f"- Total de productos después de la ampliación: {len(inventory)}\n"
        f"- Especies objetivo ya existentes y no duplicadas: {', '.join(already_present) if already_present else 'Ninguna'}\n"
        f"- Productos pendientes de precio: {len(added)}\n"
        f"- Productos pendientes de fotografía: {len(added)}\n"
        "- Las identificaciones científicas nuevas quedan pendientes de confirmación; no se asignaron valores botánicos ambiguos.\n"
        "- Los productos nuevos usan precio `null`, no se agregan al carrito y muestran consulta de precio.\n",
        encoding="utf-8",
    )
    print(f"Added {len(added)} products; existing targets skipped: {len(already_present)}")


if __name__ == "__main__":
    main()
