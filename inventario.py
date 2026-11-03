"""Medidas nominales de cada herramienta y qué fotos corresponden a cada una.

Las medidas y los rangos de fotos salen de la hoja de registro del grupo.
"""
PULG = 25.4  # mm


def pulg(fraccion):
    """'13/64' -> 5.159 mm"""
    a, b = fraccion.split("/")
    return int(a) / int(b) * PULG


# Diámetro nominal de cada medida (nombre -> mm), por tipo de herramienta
TABLAS = {
    "broca_mm": {f"{d:g} mm": float(d) for d in [5, 5.5, 6.5, 7, 7.5, 8, 8.5, 9, 9.5]},
    "broca_pulg": {f'{f}"': pulg(f) for f in ["3/16", "13/64", "7/32", "15/64", "1/4", "17/64", "9/32",
                                               "19/64", "5/16", "21/64", "11/32", "23/64", "3/8"]},
    "fresa": {'9/16" x 1/2"': pulg("9/16"), "10 mm": 10.0},
    "macho": {"M10 x 1.5": 10.0, '5/16"-18 NC': pulg("5/16")},
}

NOMBRES = {"broca_mm": "Broca (mm)", "broca_pulg": "Broca (pulg)", "fresa": "Fresa", "macho": "Macho"}

# (carpeta, primera foto, última foto, tipo, medida)
FOTOS = [
    ("dataset_herramientas", 0, 4, "broca_mm", "5 mm"),
    ("dataset_herramientas", 5, 9, "broca_mm", "5.5 mm"),
    ("dataset_herramientas", 10, 14, "broca_mm", "6.5 mm"),
    ("dataset_herramientas", 15, 19, "broca_mm", "7 mm"),
    ("dataset_herramientas", 20, 24, "broca_mm", "7.5 mm"),
    ("dataset_herramientas", 25, 29, "broca_mm", "8 mm"),
    ("dataset_herramientas", 30, 34, "broca_mm", "8.5 mm"),
    ("dataset_herramientas", 35, 39, "broca_mm", "9 mm"),
    ("dataset_herramientas", 40, 44, "broca_mm", "9.5 mm"),
    ("dataset_herramientas", 45, 49, "broca_pulg", '3/16"'),
    ("dataset_herramientas", 50, 54, "broca_pulg", '13/64"'),
    ("dataset_herramientas", 55, 59, "broca_pulg", '7/32"'),
    ("dataset_herramientas", 60, 64, "broca_pulg", '15/64"'),
    ("dataset_herramientas", 65, 69, "broca_pulg", '1/4"'),
    ("dataset_herramientas", 70, 74, "broca_pulg", '17/64"'),
    ("dataset_herramientas", 75, 79, "broca_pulg", '9/32"'),
    ("dataset_herramientas", 80, 84, "broca_pulg", '19/64"'),
    ("dataset_herramientas", 85, 89, "broca_pulg", '5/16"'),
    ("dataset_herramientas", 90, 94, "broca_pulg", '21/64"'),
    ("dataset_herramientas", 95, 99, "broca_pulg", '11/32"'),
    ("dataset_herramientas", 100, 104, "broca_pulg", '23/64"'),
    ("dataset_herramientas", 105, 109, "broca_pulg", '3/8"'),
    ("dataset_herramientas fres", 0, 19, "fresa", '9/16" x 1/2"'),
    ("dataset_herramientas fres", 20, 41, "fresa", "10 mm"),
    ("dataset_herramientas machos", 1, 20, "macho", "M10 x 1.5"),     # la foto 0 es la banda vacía
    ("dataset_herramientas machos", 21, 40, "macho", '5/16"-18 NC'),
]
