"""Calcula cuántos mm mide un píxel con las fotos del ArUco sobre la banda.

Uso:  py calibrar.py "Fotos Herramienta/dataset_distancia"
      py calibrar.py                (usa la carpeta calibracion/)

Antes: poner en medicion.py LADO_REF_MM = lo que midió la regla en el ArUco impreso.
Si la cámara se mueve, hay que volver a calibrar.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

import medicion as med

EXT = (".jpg", ".jpeg", ".png")
carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else med.BASE / "calibracion"
fotos = sorted(p for p in carpeta.glob("*") if p.suffix.lower() in EXT)
if not fotos:
    raise SystemExit(f"No hay fotos en {carpeta}")

revision = med.BASE / "calibracion_revision"
revision.mkdir(exist_ok=True)
lados, resol = {}, None

for f in fotos:
    img = med.leer_imagen(f)
    if img is None:
        print(f"  {f.name}: no se pudo leer")
        continue
    if resol and resol != [img.shape[1], img.shape[0]]:
        raise SystemExit(f"{f.name} tiene otra resolución: todas las fotos deben ser iguales")
    resol = [img.shape[1], img.shape[0]]
    esq, tipo = med.detectar_referencia(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    if esq is None:
        print(f"  {f.name}: no se encontró la referencia")
        continue
    l = med.lados_px(esq)
    deformacion = (max(l) / min(l) - 1) * 100
    lados[f.name] = float(np.mean(l))
    print(f"  {f.name}: {tipo}, lado {np.mean(l):.1f} px (deformación {deformacion:.1f} %)")
    cv2.polylines(img, [esq.astype(np.int32)], True, (0, 255, 0), 2)
    med.guardar_imagen(revision / f.name, img)

if not lados:
    raise SystemExit("Ninguna foto sirvió para calibrar")

# Se descartan las fotos que se alejan más de 2 % de la mediana (hoja levantada, mano, desenfoque)
mediana = float(np.median(list(lados.values())))
buenas = {k: v for k, v in lados.items() if abs(v - mediana) / mediana <= 0.02}
for k in sorted(set(lados) - set(buenas)):
    print(f"  descartada {k}: {lados[k]:.1f} px, se aleja de la mediana {mediana:.1f} px")
lado = float(np.mean(list(buenas.values())))
mm_px = med.LADO_REF_MM / lado
if lado < 100:
    print(f"\n¡Ojo! El ArUco mide solo {lado:.0f} px: cada píxel son {mm_px:.2f} mm. "
          "Para medir brocas que se diferencian en 0.4 mm conviene acercar la cámara o subir la resolución.")

cal = med.cargar_calibracion() if med.ARCHIVO_CAL.exists() else {}
cal.update({"mm_por_px": mm_px, "lado_ref_mm": med.LADO_REF_MM, "lado_ref_px": lado, "resolucion": resol,
            "fotos": sorted(buenas), "fecha": datetime.now().isoformat(timespec="seconds")})
med.ARCHIVO_CAL.write_text(json.dumps(cal, indent=2), encoding="utf-8")
print(f"\n{len(buenas)} fotos útiles. 1 píxel = {mm_px:.4f} mm ({1 / mm_px:.2f} px por mm), "
      f"resolución {resol[0]}x{resol[1]}")
print("Guardado en", med.ARCHIVO_CAL.name, "| fotos con el ArUco marcado en", revision.name)
