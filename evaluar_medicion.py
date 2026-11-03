"""Mide las fotos de medida conocida, ajusta la conversión a mm y reporta la precisión.

Uso:  py evaluar_medicion.py "Fotos Herramienta"             (solo reporta)
      py evaluar_medicion.py "Fotos Herramienta" --guardar   (además guarda el ajuste en calibracion.json)

Las 2 primeras fotos de cada medida sirven para ajustar la conversión a mm (ajuste); las
demás solo se usan para comprobar el acierto (prueba), así el resultado no es tramposo.
Qué foto es qué medida está en inventario.FOTOS.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

import inventario
import medicion as med

N_AJUSTE = 2
args = [a for a in sys.argv[1:] if not a.startswith("--")]
guardar = "--guardar" in sys.argv
base = Path(args[0]) if args else med.BASE / "Fotos Herramienta"
salida = med.BASE / "medicion_resultados"
salida.mkdir(exist_ok=True)
cal = med.cargar_calibracion()

# 1. Ancho en px de cada foto
filas = []
for carpeta, desde, hasta, tipo, medida in inventario.FOTOS:
    for i in range(desde, hasta + 1):
        ruta = base / carpeta / f"foto_{i:04d}.jpg"
        fila = {"foto": f"{carpeta}/{ruta.name}", "tipo": tipo, "real": medida,
                "real_mm": round(inventario.TABLAS[tipo][medida], 3),
                "uso": "ajuste" if i - desde < N_AJUSTE else "prueba", "_ruta": ruta}
        img = med.leer_imagen(ruta)
        r, motivo = med.medir_ancho(img) if img is not None else (None, "no se pudo leer")
        if r is None:
            fila["error"] = motivo
        else:
            fila["anchos"] = r["anchos"]
            fila["ancho_px"] = "/".join(f"{c}={w:.2f}" for c, w in r["anchos"].items())
            fila["_contorno"] = r["contorno"]
        filas.append(fila)
print(f"{sum('anchos' in f for f in filas)} de {len(filas)} fotos medidas")
for f in filas:
    if "error" in f:
        print(f"  {f['foto']}: {f['error']}")

# 2. Curva de calibración por familia y canal con las fotos de ajuste. Se ajusta lo medido en
#    función de lo real (mm_aruco = a * mm_real + b) y se invierte; al revés, el ruido aplanaría la recta.
ajuste = {}
for fam, canales in med.CANALES.items():
    ajuste[fam] = {}
    for canal in canales:
        pts = np.array([(f["real_mm"], f["anchos"][canal] * cal["mm_por_px"]) for f in filas
                        if med.familia(f["tipo"]) == fam and f["uso"] == "ajuste" and canal in f.get("anchos", {})])
        a, b = np.polyfit(pts[:, 0], pts[:, 1], 1)
        ajuste[fam][canal] = {"ganancia": round(float(1 / a), 4), "desfase": round(float(-b / a), 4)}
cal_eval = dict(cal, ajuste=ajuste)

# 3. Medida asignada a cada foto
for f in filas:
    d = med.a_mm(f["anchos"], f["tipo"], cal_eval) if "anchos" in f else None
    if d is None:
        f.setdefault("error", "faltan bordes")
        continue
    f["medido_mm"] = round(d, 2)
    f["error_mm"] = round(d - f["real_mm"], 2)
    f["medida"] = med.medida_comercial(f["tipo"], d)
    f["acierto"] = f["medida"] == f["real"]

medidas = [f for f in filas if "medido_mm" in f]

# 4. Reporte (solo fotos de prueba)
print("\nPrecisión en las fotos de PRUEBA (no se usaron para ajustar):")
print(f"{'tipo':13} {'medida':14} {'medido (mm)':>12} {'error':>7}  aciertos")
for tipo in inventario.TABLAS:
    grupos = defaultdict(list)
    for f in medidas:
        if f["tipo"] == tipo and f["uso"] == "prueba":
            grupos[f["real"]].append(f)
    for real, fs in grupos.items():
        d = np.array([f["medido_mm"] for f in fs])
        ok = sum(f["acierto"] for f in fs)
        fallos = ", ".join(sorted({f["medida"] for f in fs if not f["acierto"]}))
        print(f"{inventario.NOMBRES[tipo]:13} {real:14} {d.mean():8.2f}±{d.std():.2f} {d.mean() - fs[0]['real_mm']:+7.2f}"
              f"  {ok}/{len(fs)}" + (f"  (dio {fallos})" if fallos else ""))

print("\nResumen:")
for tipo in inventario.TABLAS:
    fs = [f for f in medidas if f["tipo"] == tipo and f["uso"] == "prueba"]
    e = np.abs([f["error_mm"] for f in fs])
    ok = sum(f["acierto"] for f in fs)
    print(f"  {inventario.NOMBRES[tipo]:13} aciertos {ok}/{len(fs)} ({100 * ok / len(fs):.0f} %) | "
          f"error medio {e.mean():.2f} mm | máximo {e.max():.2f} mm")

print("\nAjuste (mm_real = ganancia × mm_ArUco + desfase):")
for fam, por_canal in ajuste.items():
    for canal, aj in por_canal.items():
        print(f"  {fam:6} canal {canal}: ganancia {aj['ganancia']:.3f}  desfase {aj['desfase']:+.2f} mm")

# 5. Archivos de salida
columnas = ["foto", "tipo", "real", "real_mm", "uso", "ancho_px", "medido_mm", "error_mm", "medida", "acierto", "error"]
with open(salida / "resultados.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, columnas, delimiter=";", extrasaction="ignore")
    w.writeheader()
    w.writerows(filas)
for f in medidas:
    img = med.leer_imagen(f["_ruta"])
    r = {"tipo": f["tipo"], "medida": f["medida"], "diametro_mm": f["medido_mm"], "contorno": f["_contorno"]}
    med.dibujar(img, r)
    cv2.putText(img, f"real: {f['real']}  {'OK' if f['acierto'] else 'X'}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 160, 0) if f["acierto"] else (0, 0, 255), 2)
    med.guardar_imagen(salida / f["foto"].replace("/", "_").replace(" ", "_"), img)
print("\nTabla completa en", salida / "resultados.csv", "| fotos marcadas en", salida.name)

if guardar:
    cal["ajuste"] = ajuste
    med.ARCHIVO_CAL.write_text(json.dumps(cal, indent=2), encoding="utf-8")
    print("Ajuste guardado en", med.ARCHIVO_CAL.name)
