"""Genera la base botánica independiente del inventario comercial."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
INVENTARIO = ROOT / "Inventario" / "inventario.json"
SALIDA = ROOT / "Inventario" / "fichas_especies.json"


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")


def base_profile(categoria: str, scientific_name: str) -> dict:
    """Only uses broad, documented horticultural ranges; uncertain taxa stay null."""
    unknown = scientific_name.lower().startswith("por verificar") or " sp." in scientific_name.lower()
    if unknown:
        return {
            "altitud_minima": None, "altitud_maxima": None,
            "altitud_ideal_minima": None, "altitud_ideal_maxima": None,
            "temperatura_minima": None, "temperatura_maxima": None,
            "temperatura_optima": None, "clima": [],
            "exposicion_solar": None, "riego": None, "suelo": None,
            "drenaje": None, "resistencia_viento": None, "tolerancia_sequia": None,
            "estado_validacion": "Pendiente de validación botánica específica."
        }

    name = scientific_name.lower()
    if "persea americana" in name:
        cold = "frío" in categoria.lower()
        return {
            "altitud_minima": 800 if cold else 0, "altitud_maxima": 2200 if cold else 1200,
            "altitud_ideal_minima": 1200 if cold else 0, "altitud_ideal_maxima": 1800 if cold else 800,
            "temperatura_minima": 8 if cold else 16, "temperatura_maxima": 28 if cold else 34,
            "temperatura_optima": "16-24 °C" if cold else "20-28 °C",
            "clima": ["tropical húmedo", "templado" if cold else "tropical cálido"],
            "exposicion_solar": "Pleno sol", "riego": "Regular; aumentar durante floración y llenado del fruto.",
            "suelo": "Franco, profundo y rico en materia orgánica.", "drenaje": "Excelente, sin encharcamientos.",
            "resistencia_viento": "Moderada; proteger árboles jóvenes.", "tolerancia_sequia": "Baja a moderada.",
            "estado_validacion": "Referencia hortícola; confirmar según cultivar y microclima."
        }
    if name.startswith("citrus") or name.startswith("citrus ×") or name.startswith("citrus "):
        return {
            "altitud_minima": 0, "altitud_maxima": 1500, "altitud_ideal_minima": 0, "altitud_ideal_maxima": 900,
            "temperatura_minima": 12, "temperatura_maxima": 34, "temperatura_optima": "20-28 °C",
            "clima": ["tropical cálido", "tropical húmedo", "tropical seco"],
            "exposicion_solar": "Pleno sol", "riego": "Regular, profundo; evitar estrés hídrico durante floración y fructificación.",
            "suelo": "Franco a franco-arenoso, fértil y ligeramente ácido.", "drenaje": "Bueno a excelente.",
            "resistencia_viento": "Moderada; requiere protección en sitios expuestos.", "tolerancia_sequia": "Moderada una vez establecido.",
            "estado_validacion": "Referencia hortícola; la variedad y el portainjerto pueden modificar el rango."
        }
    if "mangifera indica" in name:
        return {
            "altitud_minima": 0, "altitud_maxima": 1200, "altitud_ideal_minima": 0, "altitud_ideal_maxima": 700,
            "temperatura_minima": 15, "temperatura_maxima": 35, "temperatura_optima": "24-30 °C",
            "clima": ["tropical seco", "tropical cálido"], "exposicion_solar": "Pleno sol",
            "riego": "Regular durante establecimiento; reducir excesos de humedad antes de floración.",
            "suelo": "Profundo, fértil y bien estructurado.", "drenaje": "Bueno.",
            "resistencia_viento": "Moderada; formar copa baja.", "tolerancia_sequia": "Moderada una vez establecido.",
            "estado_validacion": "Referencia hortícola; el cultivar y la floración dependen del microclima."
        }
    if any(token in name for token in ("rubus", "ugni", "physalis", "passiflora ligularis")):
        return {
            "altitud_minima": 800, "altitud_maxima": 2500, "altitud_ideal_minima": 1200, "altitud_ideal_maxima": 2200,
            "temperatura_minima": 8, "temperatura_maxima": 26, "temperatura_optima": "14-22 °C",
            "clima": ["templado", "montañoso"], "exposicion_solar": "Sol o semisombra luminosa",
            "riego": "Regular, manteniendo humedad uniforme sin saturar.", "suelo": "Franco, fértil y con materia orgánica.",
            "drenaje": "Bueno.", "resistencia_viento": "Baja a moderada; usar soporte cuando corresponda.",
            "tolerancia_sequia": "Baja.", "estado_validacion": "Referencia hortícola; validar cultivar y manejo local."
        }
    return {
        "altitud_minima": 0, "altitud_maxima": 1200, "altitud_ideal_minima": 0, "altitud_ideal_maxima": 800,
        "temperatura_minima": 18, "temperatura_maxima": 34, "temperatura_optima": "22-30 °C",
        "clima": ["tropical húmedo", "tropical cálido"], "exposicion_solar": "Pleno sol o semisombra luminosa",
        "riego": "Regular, ajustado a lluvia y etapa de desarrollo; evitar encharcamientos.",
        "suelo": "Franco, fértil y rico en materia orgánica.", "drenaje": "Bueno a excelente.",
        "resistencia_viento": "Moderada; proteger durante establecimiento.", "tolerancia_sequia": "Baja a moderada.",
        "estado_validacion": "Referencia hortícola general; confirmar por especie y microclima."
    }


def characteristics(name: str, scientific_name: str) -> dict:
    lower = scientific_name.lower()
    if lower.startswith("por verificar") or " sp." in lower:
        return {
            "altura_adulta": None, "diametro_copa": None, "velocidad_crecimiento": None,
            "tiempo_produccion": None, "epoca_floracion": None, "epoca_cosecha": None,
            "produccion_estimada": None, "recomendaciones_poda": None, "distancia_siembra": None,
            "fruto": "Características del fruto pendientes de validación botánica."
        }
    fruit = "Fruto comestible; la forma, color y sabor dependen de la especie o variedad."
    if "citrus" in lower:
        fruit = "Fruto cítrico jugoso y aromático; el sabor puede ser dulce, ácido o amargo según la variedad."
    elif "mangifera" in lower:
        fruit = "Drupa de pulpa aromática, generalmente dulce y de colores variables."
    elif "persea" in lower:
        fruit = "Fruto de pulpa cremosa y semilla grande; la textura y el contenido de aceite varían por cultivar."
    return {
        "altura_adulta": None, "diametro_copa": None, "velocidad_crecimiento": "Variable según especie, suelo y manejo.",
        "tiempo_produccion": "Depende de la especie, propagación y condiciones de cultivo; confirmar para la presentación.",
        "epoca_floracion": None, "epoca_cosecha": None, "produccion_estimada": None,
        "recomendaciones_poda": "Formar durante los primeros años y retirar ramas secas, cruzadas o enfermas.",
        "distancia_siembra": None, "fruto": fruit
    }


def family(scientific_name: str) -> Optional[str]:
    genus = scientific_name.split()[0].lower() if scientific_name else ""
    families = {
        "persea": "Lauraceae", "citrus": "Rutaceae", "mangifera": "Anacardiaceae",
        "annona": "Annonaceae", "artocarpus": "Moraceae", "theobroma": "Malvaceae",
        "psidium": "Myrtaceae", "eugenia": "Myrtaceae", "syzygium": "Myrtaceae",
        "garcinia": "Clusiaceae", "pouteria": "Sapotaceae", "cocos": "Arecaceae",
        "carica": "Caricaceae", "passiflora": "Passifloraceae", "punica": "Lythraceae",
        "tamarindus": "Fabaceae", "moringa": "Moringaceae", "bixa": "Bixaceae",
        "hibiscus": "Malvaceae", "plinia": "Myrtaceae", "nephelium": "Sapindaceae",
        "dimocarpus": "Sapindaceae", "averrhoa": "Oxalidaceae", "cinnamomum": "Lauraceae",
        "syzygium": "Myrtaceae", "piper": "Piperaceae", "bactris": "Arecaceae",
        "salacca": "Arecaceae", "vitis": "Vitaceae", "rubus": "Rosaceae",
        "ugni": "Myrtaceae", "physalis": "Solanaceae", "senna": "Fabaceae",
    }
    return families.get(genus)


def benefits(scientific_name: str) -> dict:
    lower = scientific_name.lower()
    if "citrus" in lower:
        return {"vitaminas": ["vitamina C"], "minerales": ["potasio"], "antioxidantes": ["flavonoides y carotenoides"], "fibra": "Presente principalmente en la pulpa y membranas.", "nutricion": "Frutos generalmente bajos en grasa y con aporte de vitamina C; el contenido cambia según especie y madurez.", "beneficios": "Aporta vitamina C, fibra y compuestos antioxidantes como parte de una alimentación variada.", "usos_gastronomicos": "Jugos, bebidas, postres, mermeladas, conservas y aromatización.", "usos_tradicionales": None}
    if "mangifera" in lower:
        return {"vitaminas": ["vitaminas A y C"], "minerales": ["potasio"], "antioxidantes": ["carotenoides y polifenoles"], "fibra": "Presente en la pulpa.", "nutricion": "Pulpa con carbohidratos naturales, fibra y micronutrientes; su dulzor implica consumo moderado.", "beneficios": "Contribuye con vitamina C, carotenoides y fibra dentro de una dieta equilibrada.", "usos_gastronomicos": "Consumo fresco, batidos, salsas, chutneys, deshidratados y postres.", "usos_tradicionales": None}
    return {"vitaminas": [], "minerales": [], "antioxidantes": [], "fibra": None, "nutricion": "Información nutricional específica pendiente de validación para esta especie o variedad.", "beneficios": None, "usos_gastronomicos": "Consultar usos culinarios documentados para la especie.", "usos_tradicionales": None}


def main() -> None:
    inventory = json.loads(INVENTARIO.read_text(encoding="utf-8"))
    grouped: OrderedDict[str, list] = OrderedDict()
    for product in inventory:
        scientific = product.get("cientifico") or "Por verificar"
        category = product.get("categoria") or ""
        key = f"{scientific}|{'frio' if 'frío' in category.lower() else 'caliente' if 'caliente' in category.lower() else ''}"
        grouped.setdefault(key, []).append(product)

    species = []
    for products in grouped.values():
        first = products[0]
        scientific = first.get("cientifico") or "Por verificar"
        ficha_id = slug(f"{scientific}_{first.get('categoria', '')}")[:90]
        spanish = first.get("especie") or "Especie por identificar"
        english = first.get("ingles") or "Species to be confirmed"
        cultivation = base_profile(first.get("categoria", ""), scientific)
        species.append({
            "id_especie": ficha_id,
            "inventario_ids": [p["id"] for p in products],
            "nombre_es": spanish,
            "nombre_en": english,
            "nombre_cientifico": scientific,
            "familia_botanica": family(scientific),
            "categoria": first.get("categoria"),
            "origen": None,
            "cultivo": cultivation,
            "caracteristicas": characteristics(spanish, scientific),
            "beneficios": benefits(scientific),
            "descripcion": {
                "es": f"{spanish} ({scientific}) es una opción de interés para el jardín y la producción tropical. {characteristics(spanish, scientific)['fruto']} Su adaptación y fecha de producción dependen de la propagación, el microclima y el manejo; en Costa Rica conviene seleccionar un sitio con buen drenaje y confirmar el cultivar.",
                "en": f"{english} ({scientific}) is an interesting option for tropical gardens and production. {characteristics(spanish, scientific)['fruto']} Adaptation and bearing time depend on propagation, microclimate and management; in Costa Rica, choose a well-drained site and confirm the cultivar."
            },
            "fuente_datos": "Referencia hortícola general; los campos sin respaldo específico se mantienen nulos para validación local."
        })

    output = {
        "version": 1,
        "generado_desde": "Inventario/inventario.json",
        "nota": "Base botánica independiente. No sustituye precios, tamaños ni disponibilidad del inventario.",
        "especies": species,
        "referencias_comerciales": {
            "venta_mayor": {"es": "Para viveristas o compras iguales o superiores a ₡300.000 ofrecemos precios al por mayor y transporte, según condiciones comerciales.", "en": "For nurseries or purchases of ₡300,000 or more, wholesale prices and transport are available according to commercial conditions."},
            "citricos_injertados": {"es": ["Presentación pequeña: desde ₡2.500; 50-60 cm en adelante; producción aproximada en 1 año y 3 meses según variedad y manejo.", "Presentación mediana: ₡12.000; aproximadamente 1,50 m.", "Presentación adulta: ₡45.000; árbol adulto en producción."], "en": ["Small presentation: from ₡2,500; 50-60 cm or more; approximate bearing in 1 year and 3 months depending on variety and management.", "Medium presentation: ₡12,000; approximately 1.50 m.", "Mature presentation: ₡45,000; mature tree in production."]},
            "mangas_injertadas": {"es": [{"altura": "1 m", "precio": "₡3.000"}, {"altura": "1,30 m", "precio": "₡5.000"}, {"altura": "1,60 m", "precio": "₡7.000"}, {"altura": "2 m", "precio": "₡10.000"}, {"altura": "2,50 m", "precio": "₡15.000"}], "en": [{"altura": "1 m", "precio": "₡3,000"}, {"altura": "1.30 m", "precio": "₡5,000"}, {"altura": "1.60 m", "precio": "₡7,000"}, {"altura": "2 m", "precio": "₡10,000"}, {"altura": "2.50 m", "precio": "₡15,000"}]}
        }
    }
    SALIDA.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generadas {len(species)} fichas en {SALIDA}")


if __name__ == "__main__":
    main()
