"""Safely organize, optimize, and associate catalog photographs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "imagenes"
INVENTORY_FILE = ROOT / "Inventario" / "inventario.json"
REPORT_DIR = ROOT / "scripts" / "reportes"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SOURCE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_DIMENSION = 1200
QUALITY = 85

CATEGORY_FOLDERS = {
    "aguacates clima caliente": "aguacates",
    "aguacates clima frio": "aguacates",
    "citricos": "citricos",
    "criollos de semilla": "criollos",
    "exoticos": "exoticos",
    "mangos": "mangos",
    "otros frutales injertados": "frutales",
}


@dataclass
class Photo:
    path: Path
    relative: str
    valid: bool = True
    error: str = ""
    digest: str = ""


@dataclass
class Plan:
    products: list[dict]
    photos: list[Photo]
    assignments: dict[int, str] = field(default_factory=dict)
    ambiguous: dict[str, list[int]] = field(default_factory=dict)
    unrecognized: list[str] = field(default_factory=list)
    invalid_references: list[tuple[int, str]] = field(default_factory=list)
    duplicates: dict[str, list[str]] = field(default_factory=dict)
    conversions: list[tuple[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    repaired: dict[int, str] = field(default_factory=dict)


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def category_folder(category: object) -> str | None:
    return CATEGORY_FOLDERS.get(normalize(category))


def relative_path(path: Path) -> str:
    return path.relative_to(IMAGES_DIR).as_posix()


def photo_key(path: Path) -> str:
    return normalize(re.sub(r"\s*\d+$", "", path.stem))


def load_inventory() -> list[dict]:
    data = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("Inventario inválido: se esperaba una lista de objetos.")
    return data


def scan_photos() -> list[Photo]:
    photos: list[Photo] = []
    for path in sorted(IMAGES_DIR.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        photo = Photo(path=path, relative=relative_path(path))
        try:
            with Image.open(path) as image:
                image.verify()
            photo.digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except (OSError, UnidentifiedImageError) as error:
            photo.valid = False
            photo.error = str(error)
        photos.append(photo)
    return photos


def referenced_paths(products: list[dict]) -> set[str]:
    paths: set[str] = set()
    for product in products:
        value = product.get("foto")
        if not isinstance(value, str) or not value.strip():
            continue
        path = value.replace("\\", "/").lstrip("/")
        if path.lower().startswith("imagenes/"):
            path = path[9:]
        paths.add(path)
    return paths


def choose_primary(photos: list[Photo]) -> Photo:
    return sorted(photos, key=lambda item: (bool(re.search(r"\d+$", Path(item.relative).stem)), item.relative.lower()))[0]


def candidate_photos(
    product: dict,
    photos_by_key: dict[str, list[Photo]],
) -> list[Photo]:
    candidates: list[Photo] = []
    common = photos_by_key.get(normalize(product.get("especie")), [])
    candidates.extend(common)
    if not candidates and normalize(product.get("ingles")) == normalize(product.get("especie")):
        candidates.extend(photos_by_key.get(normalize(product.get("ingles")), []))
    expected = category_folder(product.get("categoria"))
    unique = {photo.relative: photo for photo in candidates}
    return [
        photo for photo in unique.values()
        if expected and Path(photo.relative).parent.as_posix() == expected
    ]


def build_plan(products: list[dict], photos: list[Photo]) -> Plan:
    plan = Plan(products=products, photos=photos)
    available = {photo.relative: photo for photo in photos if photo.valid}
    referenced = referenced_paths(products)
    photos_by_key: dict[str, list[Photo]] = {}
    for photo in photos:
        if photo.valid:
            photos_by_key.setdefault(photo_key(photo.path), []).append(photo)
    by_key: dict[str, list[dict]] = {}
    for product in products:
        for value in (product.get("especie"), product.get("ingles")):
            key = normalize(value)
            if key:
                by_key.setdefault(key, []).append(product)

        current = product.get("foto")
        if isinstance(current, str) and current:
            normalized = current.replace("\\", "/").lstrip("/")
            if normalized.lower().startswith("imagenes/"):
                normalized = normalized[9:]
            if normalized not in available:
                plan.invalid_references.append((int(product.get("id", 0)), current))
                candidates = candidate_photos(product, photos_by_key)
                if candidates:
                    plan.repaired[int(product["id"])] = choose_primary(candidates).relative

    digests: dict[str, list[str]] = {}
    for photo in photos:
        if photo.valid:
            digests.setdefault(photo.digest, []).append(photo.relative)
        if photo.path.suffix.lower() in SOURCE_EXTENSIONS:
            destination = photo.path.with_suffix(".webp")
            if not destination.exists() or photo.path.stat().st_mtime_ns > destination.stat().st_mtime_ns:
                plan.conversions.append((photo.relative, relative_path(destination)))

    plan.duplicates = {digest: names for digest, names in digests.items() if len(names) > 1}

    for photo in photos:
        if not photo.valid:
            continue
        if photo.relative in referenced:
            continue
        key = photo_key(photo.path)
        candidates = list({id(item): item for item in by_key.get(key, [])}.values())
        if not candidates:
            plan.unrecognized.append(photo.relative)
            continue
        folders = {category_folder(item.get("categoria")) for item in candidates}
        if None in folders or len(folders) != 1:
            plan.ambiguous[photo.relative] = [int(item.get("id", 0)) for item in candidates]
            continue
        expected_folder = next(iter(folders))
        if Path(photo.relative).parent.as_posix() != expected_folder:
            plan.ambiguous[photo.relative] = [int(item.get("id", 0)) for item in candidates]
            continue
        primary = choose_primary([item for item in photos if photo_key(item.path) == key and item.valid])
        target_path = primary.path.with_suffix(".webp")
        if not target_path.exists():
            continue
        missing = [item for item in candidates if not item.get("foto")]
        if not missing:
            continue
        if len({normalize(item.get("especie")) for item in missing}) != 1:
            plan.ambiguous[photo.relative] = [int(item.get("id", 0)) for item in candidates]
            continue
        for item in missing:
            plan.assignments[int(item["id"])] = relative_path(target_path)

    return plan


def optimize_sources(plan: Plan, apply: bool) -> None:
    for photo in plan.photos:
        if not photo.valid or photo.path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        destination = photo.path.with_suffix(".webp")
        if not apply or not any(source == photo.relative for source, _ in plan.conversions):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with Image.open(photo.path) as image:
                image.load()
                image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
                prepared = image if "A" in image.getbands() or image.info.get("transparency") else image.convert("RGB")
                with tempfile.NamedTemporaryFile(suffix=".webp", dir=destination.parent, delete=False) as handle:
                    temporary = Path(handle.name)
                prepared.save(temporary, "WEBP", quality=QUALITY, method=6)
            temporary.replace(destination)
        except (OSError, UnidentifiedImageError, ValueError) as error:
            plan.errors.append(f"{photo.relative}: {error}")
            if temporary:
                temporary.unlink(missing_ok=True)


def write_inventory(products: list[dict]) -> None:
    serialized = json.dumps(products, ensure_ascii=False, indent=2) + "\n"
    json.loads(serialized)
    temporary = INVENTORY_FILE.with_suffix(".json.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(INVENTORY_FILE)
    finally:
        temporary.unlink(missing_ok=True)


def write_reports(plan: Plan, dry_run: bool) -> None:
    if dry_run:
        return
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report = REPORT_DIR / f"organizacion-{stamp}.json"
    pending = REPORT_DIR / f"productos-sin-fotografia-{stamp}.csv"
    report.write_text(json.dumps(summary(plan), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pending.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "especie", "categoria", "tamano"])
        for product in plan.products:
            if not product.get("foto"):
                writer.writerow([product.get("id"), product.get("especie"), product.get("categoria"), product.get("tamano")])


def summary(plan: Plan) -> dict:
    referenced = referenced_paths(plan.products)
    return {
        "total_productos": len(plan.products),
        "fotografias_encontradas": len(plan.photos),
        "fotografias_asociadas": len(referenced),
        "fotografias_sin_producto_identificado": plan.unrecognized,
        "productos_sin_fotografia": [p.get("id") for p in plan.products if not p.get("foto")],
        "fotografias_duplicadas": list(plan.duplicates.values()),
        "fotografias_con_conflictos": plan.ambiguous,
        "fotografias_convertidas_a_webp": plan.conversions,
        "rutas_propuestas": [{"id": id_, "foto": path} for id_, path in sorted(plan.assignments.items())],
        "rutas_reparadas": [{"id": id_, "foto": path} for id_, path in sorted(plan.repaired.items())],
        "referencias_invalidas": plan.invalid_references,
        "pendientes_revision": plan.unrecognized + list(plan.ambiguous),
        "errores": plan.errors,
    }


def print_report(plan: Plan, dry_run: bool) -> None:
    data = summary(plan)
    print("\nÁRBOLES EXÓTICOS OCCIDENTE")
    print("ORGANIZACIÓN Y ASIGNACIÓN DE FOTOGRAFÍAS")
    print(f"\nModo: {'SIMULACIÓN' if dry_run else 'APLICAR'}")
    print(f"Total de productos: {data['total_productos']}")
    print(f"Total de fotografías encontradas: {data['fotografias_encontradas']}")
    print(f"Fotografías asociadas correctamente: {data['fotografias_asociadas']}")
    print(f"Fotografías sin producto identificado: {len(data['fotografias_sin_producto_identificado'])}")
    print(f"Productos sin fotografía: {len(data['productos_sin_fotografia'])}")
    print(f"Fotografías duplicadas: {len(data['fotografias_duplicadas'])}")
    print(f"Fotografías con conflictos: {len(data['fotografias_con_conflictos'])}")
    print(f"Fotografías a convertir a WebP: {len(data['fotografias_convertidas_a_webp'])}")
    print(f"Rutas propuestas: {len(data['rutas_propuestas'])}")
    print(f"Rutas inválidas reparables: {len(data['rutas_reparadas'])}")
    print(f"Referencias inválidas: {len(data['referencias_invalidas'])}")
    if data["rutas_propuestas"]:
        print("\nCambios seguros propuestos:")
        for item in data["rutas_propuestas"]:
            print(f"- ID {item['id']}: {item['foto']}")
    if data["rutas_reparadas"]:
        print("\nReferencias inválidas que se pueden reparar:")
        for item in data["rutas_reparadas"]:
            print(f"- ID {item['id']}: {item['foto']}")
    if data["fotografias_con_conflictos"]:
        print("\nFotografías con conflictos:")
        for photo, ids in data["fotografias_con_conflictos"].items():
            print(f"- {photo}: IDs {', '.join(map(str, ids))}")
    if dry_run:
        print("\nNo se modificaron archivos. Use --apply únicamente después de revisar este reporte.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Organiza y asocia fotografías del inventario.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="muestra cambios sin escribir archivos")
    mode.add_argument("--apply", action="store_true", help="aplica únicamente asociaciones seguras")
    args = parser.parse_args()

    products = load_inventory()
    photos = scan_photos()
    plan = build_plan(products, photos)
    if args.apply:
        backup = INVENTORY_FILE.with_name(
            f"{INVENTORY_FILE.stem}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        shutil.copy2(INVENTORY_FILE, backup)
        optimize_sources(plan, apply=True)
        for product in products:
            if int(product.get("id", 0)) in plan.assignments:
                product["foto"] = plan.assignments[int(product["id"])]
            if int(product.get("id", 0)) in plan.repaired:
                product["foto"] = plan.repaired[int(product["id"])]
        if not plan.errors:
            write_inventory(products)
            write_reports(plan, dry_run=False)
            print(f"Respaldo creado: {backup}")
        else:
            print("No se actualizó el inventario porque hubo errores de conversión.")
    else:
        write_reports(plan, dry_run=True)
    print_report(plan, dry_run=args.dry_run)
    return 1 if plan.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
