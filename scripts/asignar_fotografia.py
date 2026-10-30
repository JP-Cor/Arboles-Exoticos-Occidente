"""Local GUI to permanently assign optimized photographs to inventory products."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk

from PIL import Image, ImageTk, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_FILE = ROOT / "Inventario" / "inventario.json"
IMAGES_DIR = ROOT / "imagenes"
MAX_DIMENSION = 1200
QUALITY = 85


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def category_folder(category: str) -> str:
    value = normalize(category)
    if "aguacate" in value:
        return "aguacates"
    if "citrico" in value:
        return "citricos"
    if "mango" in value:
        return "mangos"
    if "criollo" in value:
        return "criollos"
    if "exotico" in value:
        return "exoticos"
    if "frutal" in value:
        return "frutales"
    return ""


def safe_stem(value: str) -> str:
    value = unicodedata.normalize("NFC", value).strip()
    value = re.sub(r'[<>:"/\\|?*]+', "-", value)
    return value.rstrip(". ") or "fotografia"


def load_inventory() -> list[dict]:
    data = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("El inventario debe ser una lista de objetos JSON.")
    return data


def optimized_destination(source: Path, product: dict) -> tuple[Path, str]:
    folder = IMAGES_DIR / category_folder(str(product.get("categoria", "")))
    stem = safe_stem(source.stem)
    destination = folder / f"{stem}.webp"
    return destination, destination.relative_to(IMAGES_DIR).as_posix()


def save_webp(source: Path, destination: Path) -> None:
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
        temporary.replace(destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def backup_inventory() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = INVENTORY_FILE.with_name(f"{INVENTORY_FILE.stem}.backup-{stamp}.json")
    shutil.copy2(INVENTORY_FILE, backup)
    return backup


def write_inventory(inventory: list[dict]) -> None:
    serialized = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    json.loads(serialized)
    temporary = INVENTORY_FILE.with_suffix(".json.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(INVENTORY_FILE)
    finally:
        temporary.unlink(missing_ok=True)


class PhotoAssigner:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Asignar fotografía permanente - Árboles Exóticos Occidente")
        self.root.geometry("980x650")
        self.inventory = load_inventory()
        self.filtered: list[dict] = self.inventory
        self.selected_photo: Path | None = None
        self.preview: ImageTk.PhotoImage | None = None
        self.search = StringVar()
        self.scope = StringVar(value="one")
        self.photo_label = StringVar(value="Ninguna fotografía seleccionada")
        self.status = StringVar(value="Seleccioná un producto y una fotografía.")
        self._build()
        self._refresh_products()

    def _build(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(2, weight=1)

        ttk.Label(main, text="Buscar por ID, especie o categoría").grid(row=0, column=0, sticky="w")
        search = ttk.Entry(main, textvariable=self.search)
        search.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(4, 8))
        search.bind("<KeyRelease>", lambda _event: self._refresh_products())

        ttk.Label(main, text="Presentaciones del inventario").grid(row=0, column=1, sticky="w")
        self.products = ttk.Treeview(main, columns=("id", "especie", "tamano", "foto"), show="headings", selectmode="browse")
        for column, heading, width in (
            ("id", "ID", 55),
            ("especie", "Especie", 180),
            ("tamano", "Presentación", 180),
            ("foto", "Fotografía", 220),
        ):
            self.products.heading(column, text=heading)
            self.products.column(column, width=width, anchor="w")
        self.products.grid(row=1, column=1, rowspan=2, sticky="nsew", pady=(4, 8))
        self.products.bind("<<TreeviewSelect>>", lambda _event: self._update_scope_label())
        scrollbar = ttk.Scrollbar(main, orient="vertical", command=self.products.yview)
        scrollbar.grid(row=1, column=2, rowspan=2, sticky="ns", pady=(4, 8))
        self.products.configure(yscrollcommand=scrollbar.set)

        left = ttk.LabelFrame(main, text="Fotografía desde la computadora", padding=10)
        left.grid(row=2, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Button(left, text="Elegir fotografía", command=self._choose_photo).grid(row=0, column=0, sticky="w")
        ttk.Label(left, textvariable=self.photo_label, wraplength=400).grid(row=1, column=0, sticky="n", pady=8)
        self.preview_label = ttk.Label(left, text="Vista previa")
        self.preview_label.grid(row=2, column=0, sticky="nsew")

        options = ttk.LabelFrame(main, text="Alcance de la asignación", padding=10)
        options.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Radiobutton(options, text="Solo esta presentación", variable=self.scope, value="one").pack(anchor="w")
        self.all_scope_label = ttk.Radiobutton(options, text="Todas las presentaciones de la misma especie", variable=self.scope, value="species")
        self.all_scope_label.pack(anchor="w")
        ttk.Label(options, textvariable=self.status, foreground="#174a35").pack(anchor="w", pady=(8, 0))
        ttk.Button(options, text="Confirmar asignación permanente", command=self._assign).pack(anchor="e", pady=(8, 0))

    def _refresh_products(self) -> None:
        query = normalize(self.search.get())
        self.filtered = [
            product for product in self.inventory
            if not query or query in normalize(f"{product.get('id', '')} {product.get('especie', '')} {product.get('categoria', '')}")
        ]
        for item in self.products.get_children():
            self.products.delete(item)
        for product in self.filtered:
            self.products.insert("", "end", iid=str(product["id"]), values=(
                product.get("id", ""),
                product.get("especie", ""),
                product.get("tamano", ""),
                product.get("foto", "") or "Sin fotografía",
            ))
        self._update_scope_label()

    def _selected_product(self) -> dict | None:
        selected = self.products.selection()
        if not selected:
            return None
        product_id = int(selected[0])
        return next((product for product in self.inventory if product.get("id") == product_id), None)

    def _update_scope_label(self) -> None:
        product = self._selected_product()
        if product is None:
            self.all_scope_label.configure(state="disabled")
            return
        same_species = [
            item for item in self.inventory
            if normalize(item.get("especie")) == normalize(product.get("especie"))
        ]
        self.all_scope_label.configure(state="normal" if len(same_species) > 1 else "disabled")

    def _choose_photo(self) -> None:
        filename = filedialog.askopenfilename(
            title="Elegir fotografía",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp"), ("Todos los archivos", "*.*")],
        )
        if not filename:
            return
        try:
            with Image.open(filename) as image:
                image.verify()
            self.selected_photo = Path(filename)
            self.photo_label.set(str(self.selected_photo))
            with Image.open(self.selected_photo) as image:
                preview = image.copy()
            preview.thumbnail((420, 280), Image.Resampling.LANCZOS)
            self.preview = ImageTk.PhotoImage(preview)
            self.preview_label.configure(image=self.preview, text="")
            self.status.set("Fotografía lista para asignar.")
        except (OSError, UnidentifiedImageError) as error:
            self.selected_photo = None
            messagebox.showerror("Fotografía inválida", f"No se pudo abrir la fotografía:\n{error}")

    def _assign(self) -> None:
        product = self._selected_product()
        if product is None or self.selected_photo is None:
            messagebox.showwarning("Datos incompletos", "Seleccioná un producto y una fotografía.")
            return
        targets = [product]
        if self.scope.get() == "species":
            targets = [
                item for item in self.inventory
                if normalize(item.get("especie")) == normalize(product.get("especie"))
            ]
        destination, relative = optimized_destination(self.selected_photo, product)
        if destination.exists() and not messagebox.askyesno(
            "Confirmar reemplazo",
            f"Ya existe:\n{relative}\n\n¿Deseás sobrescribirla?",
        ):
            return
        if not messagebox.askyesno(
            "Confirmar asignación",
            f"Se asignará {relative} a {len(targets)} presentación(es).\n\n¿Continuar?",
        ):
            return
        try:
            save_webp(self.selected_photo, destination)
            for target in targets:
                target["foto"] = relative
            backup = backup_inventory()
            write_inventory(self.inventory)
            self._refresh_products()
            self.status.set(f"Fotografía asignada correctamente. Respaldo: {backup.name}")
            messagebox.showinfo("Asignación completada", f"Fotografía permanente asignada.\n\nRespaldo creado:\n{backup}")
        except (OSError, ValueError, UnidentifiedImageError) as error:
            messagebox.showerror("No se pudo guardar", str(error))


def main() -> int:
    root = Tk()
    try:
        PhotoAssigner(root)
        root.mainloop()
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        messagebox.showerror("No se pudo iniciar", str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
