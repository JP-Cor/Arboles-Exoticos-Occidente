"""Audita fichas botánicas y genera reportes reproducibles."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FICHAS = ROOT / "Inventario" / "fichas_especies.json"
REPORTE = ROOT / "Inventario" / "reporte_validacion_botanica.md"
PENDIENTES = ROOT / "Inventario" / "especies_pendientes.csv"

GENERIC_TEXT = (
    "referencia hortícola general",
    "referencia hortícola;",
    "confirmar según",
    "depende de la especie",
    "variable según especie",
    "pendiente de validación",
    "consultar usos culinarios",
)
CRITICAL = (
    ("cultivo", "altitud_minima"),
    ("cultivo", "altitud_maxima"),
    ("cultivo", "altitud_ideal_minima"),
    ("cultivo", "altitud_ideal_maxima"),
    ("cultivo", "temperatura_minima"),
    ("cultivo", "temperatura_maxima"),
    ("cultivo", "clima"),
    ("caracteristicas", "tiempo_produccion"),
    ("beneficios", "nutricion"),
)


def empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def add_issue(issues: list[str], label: str) -> None:
    if label not in issues:
        issues.append(label)


def validate_ranges(ficha: dict[str, Any], issues: list[str]) -> None:
    cultivo = ficha.get("cultivo", {})
    altitude = [cultivo.get(key) for key in ("altitud_minima", "altitud_maxima", "altitud_ideal_minima", "altitud_ideal_maxima")]
    if any(value is not None and not isinstance(value, (int, float)) for value in altitude):
        add_issue(issues, "rangos de altitud no numéricos")
    numeric_altitude = [value for value in altitude if isinstance(value, (int, float))]
    if len(numeric_altitude) == 4 and not (altitude[0] <= altitude[2] <= altitude[3] <= altitude[1]):
        add_issue(issues, "rangos de altitud inconsistentes")

    temperature = [cultivo.get(key) for key in ("temperatura_minima", "temperatura_maxima")]
    if any(value is not None and not isinstance(value, (int, float)) for value in temperature):
        add_issue(issues, "rangos de temperatura no numéricos")
    if all(isinstance(value, (int, float)) for value in temperature) and temperature[0] > temperature[1]:
        add_issue(issues, "rangos de temperatura inconsistentes")


def inspect(ficha: dict[str, Any]) -> tuple[str, list[str]]:
    issues: list[str] = []
    for section, field in CRITICAL:
        if empty(ficha.get(section, {}).get(field)):
            add_issue(issues, f"{section}.{field} vacío o null")

    for section_name in ("cultivo", "caracteristicas", "beneficios"):
        for field, value in ficha.get(section_name, {}).items():
            if isinstance(value, str) and any(text in value.lower() for text in GENERIC_TEXT):
                add_issue(issues, f"dato genérico o pendiente en {section_name}.{field}")

    scientific = str(ficha.get("nombre_cientifico") or "").strip().lower()
    if not scientific or scientific.startswith("por verificar") or " sp." in scientific:
        add_issue(issues, "nombre científico no confiable")
    sources = ficha.get("fuentes")
    if not isinstance(sources, list) or not any(isinstance(source, dict) and source.get("url") for source in sources):
        add_issue(issues, "sin fuentes bibliográficas verificables")
    if not any(ficha.get("beneficios", {}).get(field) for field in ("vitaminas", "minerales", "antioxidantes", "fibra", "nutricion", "beneficios")):
        add_issue(issues, "sin información nutricional")
    if not any(ficha.get("cultivo", {}).get(field) for field in ("exposicion_solar", "riego", "suelo", "drenaje")):
        add_issue(issues, "sin recomendaciones de cultivo")
    validate_ranges(ficha, issues)

    if not issues:
        return "Validada", issues
    if "nombre científico no confiable" in issues or "sin fuentes bibliográficas verificables" in issues:
        return "Pendiente", issues
    return "Parcialmente validada", issues


def main() -> None:
    data = json.loads(FICHAS.read_text(encoding="utf-8"))
    fichas = data.get("especies", [])
    rows: list[dict[str, str]] = []
    counts = {"Validada": 0, "Parcialmente validada": 0, "Pendiente": 0}
    field_counts: dict[str, int] = {}
    source_records: dict[str, str] = {}
    for ficha in fichas:
        status, issues = inspect(ficha)
        counts[status] += 1
        for issue in issues:
            field_counts[issue] = field_counts.get(issue, 0) + 1
        for source in ficha.get("fuentes", []):
            if isinstance(source, dict) and source.get("url"):
                source_records[source["url"]] = source.get("titulo", source["url"])
        if status != "Validada":
            rows.append({
                "ID de especie": ficha.get("id_especie", ""),
                "Nombre común": ficha.get("nombre_es", ""),
                "Nombre científico": ficha.get("nombre_cientifico", ""),
                "Campos pendientes": "; ".join(issues),
                "Motivo": "Requiere fuente verificable o completar datos críticos.",
                "Estado de investigación": status,
            })

    with PENDIENTES.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [
            "ID de especie", "Nombre común", "Nombre científico", "Campos pendientes", "Motivo", "Estado de investigación"
        ])
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Reporte de validación botánica",
        "",
        f"- Generado: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- Total de presentaciones comerciales relacionadas: {sum(len(f.get('inventario_ids', [])) for f in fichas)}",
        f"- Total de fichas: {len(fichas)}",
        f"- Fichas validadas: {counts['Validada']}",
        f"- Fichas parcialmente validadas: {counts['Parcialmente validada']}",
        f"- Fichas pendientes: {counts['Pendiente']}",
        "",
        "## Hallazgos por ficha",
        "",
        "| Hallazgo | Fichas |",
        "|---|---:|",
    ]
    lines.extend(f"| {issue} | {count} |" for issue, count in sorted(field_counts.items(), key=lambda item: (-item[1], item[0])))
    lines.extend([
        "",
        "## Criterio de clasificación",
        "",
        "Una ficha solo se clasifica como `Validada` si no presenta campos críticos vacíos, rangos inconsistentes, textos genéricos o pendientes, y contiene al menos una fuente bibliográfica con URL.",
        "Las fichas sin nombre científico confiable o sin fuentes verificables se clasifican como `Pendiente`.",
        "Las demás fichas con datos incompletos o genéricos se clasifican como `Parcialmente validada`.",
        "",
        "## Fuentes registradas",
        "",
    ])
    if source_records:
        lines.extend(f"- [{title}]({url})" for url, title in sorted(source_records.items()))
    else:
        lines.append("No hay fuentes bibliográficas verificables registradas.")
    lines.extend([
        "",
        "## Archivos generados",
        "",
        f"- `{PENDIENTES.relative_to(ROOT)}` contiene el detalle de fichas no validadas.",
        "- Este reporte no modifica el inventario comercial ni los precios.",
    ])
    REPORTE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Auditadas {len(fichas)} fichas: {counts}")


if __name__ == "__main__":
    main()
