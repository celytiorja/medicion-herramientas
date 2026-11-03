"""Medición en vivo con DroidCam (el celular como cámara).

Teclas:  b = broca en mm   p = broca en pulgadas   f = fresa   m = macho
         s = guardar foto  q = salir

DroidCam se puede abrir de dos formas (cambiar FUENTE):
  - Cliente de DroidCam en Windows: aparece como una cámara más -> FUENTE = 0, 1 o 2.
  - Por wifi, sin cliente: FUENTE = "http://IP_DEL_CELULAR:4747/video" (la IP sale en la app).
La cámara debe estar en la misma posición y resolución que en la calibración.
"""
import time
from collections import deque

import cv2
import numpy as np

import inventario
import medicion as med

FUENTE = 1          # índice de la cámara de DroidCam o URL "http://IP:4747/video"
N_PROMEDIO = 15     # cuadros que se combinan para dar una medida estable
TECLAS = {ord("b"): "broca_mm", ord("p"): "broca_pulg", ord("f"): "fresa", ord("m"): "macho"}

cal = med.cargar_calibracion()
ancho_cal, alto_cal = cal["resolucion"]
cap = cv2.VideoCapture(FUENTE, cv2.CAP_DSHOW) if isinstance(FUENTE, int) else cv2.VideoCapture(FUENTE)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho_cal)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto_cal)
if not cap.isOpened():
    raise SystemExit(f"No se pudo abrir la cámara {FUENTE!r}. Probar con otro índice o con la URL de DroidCam.")

carpeta_fotos = med.BASE / "capturas"
carpeta_fotos.mkdir(exist_ok=True)
tipo = "broca_mm"
diametros = deque(maxlen=N_PROMEDIO)
perdidos = 0
fallos_lectura = 0
print("Teclas: b/p/f/m elige herramienta, s guarda foto, q sale")

while True:
    ok, frame = cap.read()
    if not ok:
        # Por wifi DroidCam a veces pierde cuadros: solo se sale si el corte dura ~1 segundo
        fallos_lectura += 1
        if fallos_lectura > 30:
            print("Se perdió la señal de la cámara")
            break
        continue
    fallos_lectura = 0
    vista = frame.copy()
    if [frame.shape[1], frame.shape[0]] != cal["resolucion"]:
        texto, color = f"Resolucion {frame.shape[1]}x{frame.shape[0]} distinta a la calibrada", (0, 0, 255)
    else:
        r = med.medir(frame, tipo, cal)
        if "error" in r:
            perdidos += 1
            if perdidos > 5:            # la pieza salió: se empieza de cero con la siguiente
                diametros.clear()
        else:
            perdidos = 0
            diametros.append(r["diametro_mm"])
            cv2.drawContours(vista, [r["contorno"]], -1, (0, 0, 255), 1)
        if len(diametros) >= 3:
            # Mediana de los últimos cuadros: filtra el ruido de cada imagen
            d = float(np.median(diametros))
            texto = med.etiqueta(tipo, med.medida_comercial(tipo, d), d)
            color = (0, 160, 0) if len(diametros) == N_PROMEDIO else (0, 160, 255)
        else:
            texto, color = f"{inventario.NOMBRES[tipo]}: sin herramienta", (90, 90, 90)

    x0, y0, x1, y1 = med.ZONA_BANDA
    cv2.rectangle(vista, (x0, y0), (x1, y1), (255, 0, 0), 1)
    cv2.rectangle(vista, (0, 0), (vista.shape[1], 40), color, -1)
    cv2.putText(vista, texto, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imshow("Medicion de herramientas", vista)

    tecla = cv2.waitKey(1) & 0xFF
    if tecla == ord("q"):
        break
    if tecla in TECLAS:
        tipo = TECLAS[tecla]
        diametros.clear()
    if tecla == ord("s"):
        nombre = carpeta_fotos / f"captura_{int(time.time())}.jpg"
        med.guardar_imagen(nombre, frame)
        print("Foto guardada:", nombre.name)

cap.release()
cv2.destroyAllWindows()
