"""Convert and optimize catalog images without deleting originals."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "imagenes"
INVENTORY_FILE = ROOT / "Inventario" / "inventario.json"
SOURCE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_DIMENSION = 1200
QUALITY = 85


@dataclass
class Result:
    found: int = 0
    converted: int = 0
    skipped: int = 0
    errors: int = 0
    original_bytes: int = 0
    optimized_bytes: int = 0
    error_files: list[str] | None = None

    def __post_init__(self) -> None:
        if self.error_files is None:
            self.error_files = []


def authorized_image(path: Path) -> bool:
    """Return whether path is a source image inside the authorized folder."""
    try:
        path.resolve().relative_to(IMAGES_DIR.resolve())
    except ValueError:
        return False
    return path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS


def source_files() -> list[Path]:
    if not IMAGES_DIR.is_dir():
        return []
    return sorted(
        (path for path in IMAGES_DIR.rglob("*") if authorized_image(path)),
        key=lambda path: path.relative_to(IMAGES_DIR).as_posix().lower(),
    )


def webp_files() -> set[str]:
    if not IMAGES_DIR.is_dir():
        return set()
    return {
        relative_image_path(path)
        for path in IMAGES_DIR.rglob("*.webp")
        if path.is_file()
    }


def webp_path(source: Path) -> Path:
    return source.with_suffix(".webp")


def needs_conversion(source: Path, destination: Path) -> bool:
    return not destination.exists() or source.stat().st_mtime_ns > destination.stat().st_mtime_ns


def convert_image(source: Path, destination: Path) -> None:
    """Write a WebP atomically, preserving alpha when the source has it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with Image.open(source) as image:
            image.load()
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            has_alpha = "A" in image.getbands() or image.info.get("transparency") is not None
            prepared = image if has_alpha else image.convert("RGB")
            with tempfile.NamedTemporaryFile(
                suffix=".webp", prefix=f".{destination.stem}-", dir=destination.parent, delete=False
            ) as handle:
                temporary = Path(handle.name)
            prepared.save(temporary, "WEBP", quality=QUALITY, method=6)
        os.replace(temporary, destination)
        temporary = None
        os.utime(destination, ns=(source.stat().st_atime_ns, source.stat().st_mtime_ns))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def relative_image_path(path: Path) -> str:
    return path.relative_to(IMAGES_DIR).as_posix()


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def association_key(path: Path) -> str:
    return normalized_name(re.sub(r"\s*\d+$", "", path.stem))


def associate_new_photos(
    inventory: list[dict],
    webp_paths: set[str],
    interactive: bool = False,
) -> dict[str, list[dict]]:
    """Associate exact, unambiguous filenames with all matching presentations."""
    by_name: dict[str, list[dict]] = {}
    for product in inventory:
        for value in (product.get("especie"), product.get("ingles")):
            key = normalized_name(str(value or ""))
            if key:
                by_name.setdefault(key, []).append(product)

    associations: dict[str, list[dict]] = {}
    for photo in sorted(webp_paths):
        key = association_key(Path(photo))
        candidates = {id(product): product for product in by_name.get(key, [])}
        if not candidates:
            continue
        products = list(candidates.values())
        if len({normalized_name(str(p.get("especie", ""))) for p in products}) > 1:
            print(f"ASOCIACIÓN AMBIGUA: {photo}")
            for product in products:
                print(f"  - id={product.get('id')} {product.get('especie')} ({product.get('tamano', 'sin tamaño')})")
            if not interactive or input("¿Asociar a todos estos productos? [s/N] ").strip().lower() not in {"s", "si", "sí"}:
                continue
        associations[photo] = products
    return associations


def update_inventory(
    converted_sources: set[str],
    available_webp: set[str],
    interactive: bool = False,
) -> bool:
    """Replace only successfully optimized source references and validate JSON."""
    if not INVENTORY_FILE.exists():
        return False
    try:
        original_text = INVENTORY_FILE.read_text(encoding="utf-8")
        inventory = json.loads(original_text)
        if not isinstance(inventory, list):
            raise ValueError("El inventario debe contener una lista JSON.")
        changed = False
        for product in inventory:
            if not isinstance(product, dict):
                continue
            photo = product.get("foto")
            if not isinstance(photo, str):
                continue
            normalized = photo.replace("\\", "/").lstrip("/")
            if normalized in converted_sources:
                product["foto"] = f"{Path(normalized).with_suffix('.webp').as_posix()}"
                changed = True
        associations = associate_new_photos(inventory, available_webp, interactive)
        for photo, products in associations.items():
            for product in products:
                if not product.get("foto"):
                    product["foto"] = photo
                    changed = True
        if not changed:
            return False
        serialized = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
        json.loads(serialized)
        temporary = INVENTORY_FILE.with_suffix(".json.tmp")
        temporary.write_text(serialized, encoding="utf-8")
        os.replace(temporary, INVENTORY_FILE)
        return True
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        temporary = INVENTORY_FILE.with_suffix(".json.tmp")
        temporary.unlink(missing_ok=True)
        raise


def optimize(paths: Iterable[Path] | None = None, interactive: bool = False) -> Result:
    selected = [Path(path).resolve() for path in paths] if paths is not None else source_files()
    result = Result(found=len(selected))
    destinations: dict[Path, Path] = {}
    successfully_available: set[str] = set()

    for source in selected:
        if not authorized_image(source):
            continue
        destination = webp_path(source)
        if destination in destinations and destinations[destination] != source:
            result.errors += 1
            result.error_files.append(relative_image_path(source))
            print(f"ERROR: colisión de destino para {relative_image_path(source)}", file=sys.stderr)
            continue
        destinations[destination] = source
        try:
            if needs_conversion(source, destination):
                convert_image(source, destination)
                result.converted += 1
            else:
                result.skipped += 1
            result.original_bytes += source.stat().st_size
            result.optimized_bytes += destination.stat().st_size
            successfully_available.add(relative_image_path(source))
        except (OSError, UnidentifiedImageError, ValueError) as error:
            result.errors += 1
            result.error_files.append(relative_image_path(source))
            print(f"ERROR: {relative_image_path(source)}: {error}", file=sys.stderr)

    try:
        update_inventory(successfully_available, webp_files(), interactive)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        result.errors += 1
        result.error_files.append(str(INVENTORY_FILE.relative_to(ROOT)))
        print(f"ERROR: no se pudo actualizar el inventario: {error}", file=sys.stderr)
    return result


def print_report(result: Result) -> None:
    original_mb = result.original_bytes / (1024 * 1024)
    optimized_mb = result.optimized_bytes / (1024 * 1024)
    savings = (1 - optimized_mb / original_mb) * 100 if original_mb else 0
    print("\nÁRBOLES EXÓTICOS OCCIDENTE")
    print("OPTIMIZACIÓN DE FOTOGRAFÍAS\n")
    print(f"Imágenes encontradas: {result.found}")
    print(f"Imágenes convertidas: {result.converted}")
    print(f"Imágenes omitidas: {result.skipped}")
    print(f"Errores: {result.errors}")
    print(f"Tamaño original procesado: {original_mb:.2f} MB")
    print(f"Tamaño optimizado: {optimized_mb:.2f} MB")
    print(f"Ahorro de espacio: {savings:.2f} %")
    if result.error_files:
        print("\nArchivos que no pudieron convertirse:")
        for filename in result.error_files:
            print(f"- {filename}")


def optimize_one(path: Path) -> None:
    if authorized_image(path):
        print_report(optimize([path]))


def watch() -> None:
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as error:
        raise SystemExit("La vigilancia requiere watchdog. Instalá requirements.txt.") from error

    class Handler(FileSystemEventHandler):
        def on_created(self, event) -> None:
            if not event.is_directory:
                optimize_one(Path(event.src_path))

        def on_modified(self, event) -> None:
            if not event.is_directory:
                optimize_one(Path(event.src_path))

    observer = Observer()
    observer.schedule(Handler(), str(IMAGES_DIR), recursive=True)
    observer.start()
    print(f"Vigilando fotografías en {IMAGES_DIR}. Presioná Ctrl+C para detener.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimiza fotografías del catálogo a WebP.")
    parser.add_argument("--watch", action="store_true", help="vigila imagenes/ y convierte cambios")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="solicita confirmación para asociaciones ambiguas",
    )
    args = parser.parse_args()
    if args.watch:
        watch()
        return 0
    print_report(optimize(interactive=args.interactive))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
