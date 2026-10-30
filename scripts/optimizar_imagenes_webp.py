"""Convert a directory of source images to centered 800x800 WebP files."""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps


def nombre_normalizado(nombre: str) -> str:
    base = unicodedata.normalize("NFKD", Path(nombre).stem)
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "imagen"


def optimizar(origen: Path, destino: Path, calidad: int = 85) -> tuple[int, int]:
    destino.mkdir(parents=True, exist_ok=True)
    procesadas = 0
    fallidas = 0
    extensiones = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

    for entrada in sorted(origen.rglob("*")):
        if not entrada.is_file() or entrada.suffix.lower() not in extensiones:
            continue
        try:
            with Image.open(entrada) as imagen:
                imagen = ImageOps.exif_transpose(imagen).convert("RGB")
                imagen.thumbnail((760, 760), Image.Resampling.LANCZOS)
                lienzo = Image.new("RGB", (800, 800), "white")
                posicion = ((800 - imagen.width) // 2, (800 - imagen.height) // 2)
                lienzo.paste(imagen, posicion)
                salida = destino / f"{nombre_normalizado(entrada.name)}.webp"
                lienzo.save(salida, "WEBP", quality=calidad, method=6)
                with Image.open(salida) as comprobacion:
                    comprobacion.verify()
            procesadas += 1
        except (OSError, ValueError):
            fallidas += 1

    return procesadas, fallidas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("origen", type=Path)
    parser.add_argument("destino", type=Path)
    parser.add_argument("--calidad", type=int, default=85)
    args = parser.parse_args()
    if not 1 <= args.calidad <= 100:
        parser.error("--calidad debe estar entre 1 y 100")
    procesadas, fallidas = optimizar(args.origen, args.destino, args.calidad)
    print(f"Imágenes convertidas: {procesadas}")
    print(f"Imágenes con error: {fallidas}")
    return 1 if fallidas else 0


if __name__ == "__main__":
    raise SystemExit(main())
