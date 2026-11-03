# Medición del diámetro de herramientas en la banda transportadora

Parte 2 del proyecto final de Señales: con la cámara (DroidCam) sobre la banda, mide el diámetro de
**brocas, fresas y machos** y dice su medida comercial, por ejemplo:

```
Broca (mm): 6.5 mm (6.54 mm)
```

**No usa IA ni identifica la herramienta.** Todo es procesamiento de imagen y de señales. El tipo de
herramienta se elige con una tecla o lo entrega la parte 1 del proyecto (el detector YOLO).

---

## 1. Instalación (una sola vez)

Requisitos: Windows con Python 3.10 o superior.

```powershell
git clone <URL de este repositorio>
cd medicion-herramientas
py -m pip install -r requirements.txt
```

> Si en el mismo Python ya está instalado `opencv-python-headless` (a veces lo trae otra librería), la
> ventana de la cámara no abre. Solución: `py -m pip uninstall opencv-python-headless` y volver a
> instalar `requirements.txt`.

## 2. Uso en vivo con DroidCam

1. Instalar **DroidCam** en el celular y el **cliente DroidCam** en el PC. Conectar el celular por wifi o USB.
2. Poner el celular en **el mismo soporte y posición** con que se tomaron las fotos de `Fotos Herramienta/`.
   La calibración incluida (`calibracion.json`) es para esa posición y para **640×480**.
3. En `camara_medida.py`, ajustar `FUENTE`:
   - Con el cliente de Windows: `FUENTE = 1` (si no abre, probar `0` o `2`).
   - Sin cliente, por wifi: `FUENTE = "http://IP_DEL_CELULAR:4747/video"` (la IP sale en la app).
4. Ejecutar:

   ```powershell
   py camara_medida.py
   ```

| Tecla | Acción |
|---|---|
| `b` | Broca en milímetros |
| `p` | Broca en pulgadas |
| `f` | Fresa |
| `m` | Macho |
| `s` | Guardar la imagen en `capturas/` |
| `q` | Salir |

Poner **una pieza a la vez, acostada a lo largo de la banda**, dentro del rectángulo azul. La franja de
arriba muestra la medida: **naranja** mientras junta cuadros y **verde** cuando ya combinó 15 cuadros
(medida estable). La banda puede ir en movimiento.

> Las brocas en mm y en pulgadas casi iguales (por ejemplo 9.5 mm y 3/8", que difieren 0.03 mm) no se
> pueden distinguir con ninguna cámara: por eso se indica la serie con `b` o `p`.

## 3. Uso desde otro programa (integración con YOLO)

```python
import medicion as med

cal = med.cargar_calibracion()                # una vez al inicio
r = med.medir(frame, "broca_mm", cal)          # frame = imagen BGR de OpenCV (640x480)
if "error" in r:
    print(r["error"])                          # p. ej. "sin herramienta"
else:
    print(r["medida"], r["diametro_mm"])       # '6.5 mm' 6.54
    print(med.etiqueta(r["tipo"], r["medida"], r["diametro_mm"]))
```

Tipos válidos: `"broca_mm"`, `"broca_pulg"`, `"fresa"`, `"macho"`. Si YOLO dice qué herramienta es,
basta un diccionario con los nombres de sus clases, por ejemplo:

```python
TIPO = {"Brocas": "broca_mm", "Fresa": "fresa", "Macho": "macho"}   # ajustar a las clases de su modelo
r = med.medir(frame, TIPO[nombre_clase_yolo], cal)
```

La medición mide **la herramienta más grande de la zona de la banda**: si YOLO trabaja con una pieza a
la vez, no hace falta pasarle la caja. Para medidas estables, combinar varios cuadros con la mediana,
como hace `camara_medida.py`.

## 4. Si se mueve la cámara (recalibrar)

La calibración depende de la posición, la altura y la resolución de la cámara. Si alguna cambia:

1. **Escala (ArUco).** Imprimir `referencias_calibracion.pdf` al 100 % (sin "ajustar a la página"). El
   ArUco mide 30 × 30 mm; si con regla da otra cosa, poner ese valor en `LADO_REF_MM` (`medicion.py`).
   Ponerlo plano sobre la banda detenida, guardar varias imágenes con la tecla `s` moviéndolo de lugar, y:

   ```powershell
   py calibrar.py capturas
   ```

2. **Zona de la banda.** Si cambió el encuadre, abrir una captura (en Paint, abajo salen las
   coordenadas del puntero) y corregir `ZONA_BANDA = (x0, y0, x1, y1)` en `medicion.py`: el rectángulo
   de la parte útil de la banda, sin las escobillas ni el marco de madera.

3. **Ajuste con piezas conocidas (recomendado).** Tomar al menos 2 fotos de cada medida, guardarlas
   con la misma estructura de carpetas, registrar en `inventario.FOTOS` qué foto es qué medida, y:

   ```powershell
   py evaluar_medicion.py "Fotos Herramienta" --guardar
   ```

   Usa las 2 primeras fotos de cada medida para ajustar y las demás para comprobar el acierto.

Para revisar el estado actual sin cambiar nada: `py evaluar_medicion.py "Fotos Herramienta"`.

## 5. Archivos

| Archivo | Qué hace |
|---|---|
| `medicion.py` | Núcleo: ubica la herramienta y mide su diámetro. Parámetros arriba del archivo |
| `camara_medida.py` | Medición en vivo con DroidCam |
| `calibrar.py` | mm por píxel a partir de fotos del ArUco |
| `evaluar_medicion.py` | Ajusta la conversión a mm con fotos de medida conocida y reporta el acierto |
| `inventario.py` | Medidas comerciales de cada herramienta y qué foto corresponde a cada medida |
| `calibracion.json` | Calibración actual (escala + curvas de ajuste) |
| `referencias_calibracion.pdf` | Hoja para imprimir con el ArUco de 30 mm |
| `Fotos Herramienta/` | Fotos del grupo: `dataset_distancia` (ArUco), brocas, fresas y machos |

Inventario de las fotos (según la hoja de registro del grupo):

| Carpeta | Fotos | Medida |
|---|---|---|
| `dataset_herramientas` | 0–44, de 5 en 5 | Brocas 5, 5.5, 6.5, 7, 7.5, 8, 8.5, 9, 9.5 mm |
| `dataset_herramientas` | 45–109, de 5 en 5 | Brocas 3/16, 13/64, 7/32, 15/64, 1/4, 17/64, 9/32, 19/64, 5/16, 21/64, 11/32, 23/64, 3/8" |
| `dataset_herramientas fres` | 0–19 / 20–41 | Fresa 9/16" × 1/2" / Fresa 10 mm |
| `dataset_herramientas machos` | 1–20 / 21–40 | Macho M10 × 1.5 / Macho 5/16"-18 NC (la foto 0 es la banda vacía) |

## 6. Precisión

Medida en las fotos de prueba, que no se usaron para ajustar:

| Herramienta | Acierto por foto | Combinando las fotos de cada pieza |
|---|---|---|
| Brocas en mm | 85 % (error medio 0.15 mm) | 9/9 medidas |
| Brocas en pulgadas | 67 % (error medio 0.27 mm) | 11/13 medidas |
| Fresas | 100 % | 2/2 |
| Machos | 89 % | 2/2 |

Procesa unos 40 cuadros por segundo (~25 ms por cuadro).

## 7. Cómo mide

1. **Modelo de color de la banda**: media y covarianza en Lab de sus píxeles amarillos.
2. **Distancia de Mahalanobis** de cada píxel a ese modelo: lejos del amarillo = herramienta.
3. **Morfología**: una apertura horizontal borra las rayas verticales de la banda y la marca de agua de
   DroidCam. Queda la herramienta, con la que se obtiene su eje y se endereza.
4. **Perfil transversal promediado**: en 4 tramos de la pieza se toma la mediana, columna a columna,
   de un canal de color (L = luminosidad, b = amarillo-azul). Promediar ~200 columnas reduce el
   ruido unas 14 veces (√N) y cancela el patrón de la banda.
5. **Bordes por gradiente**: picos de la derivada del perfil, buscados desde afuera e interpolados con
   una parábola (precisión sub-píxel). Ancho = distancia entre bordes; se toma la mediana de los 4 tramos.
6. **Calibración**: escala del ArUco y una curva de calibración por canal ajustada con piezas de medida
   conocida. En las brocas se promedian los canales L y b, que se equivocan por razones distintas.
7. **En vivo**: mediana de los últimos 15 cuadros (filtro de mediana en el tiempo).

## 8. Problemas frecuentes

| Problema | Solución |
|---|---|
| `No se pudo abrir la cámara` | Probar otro número en `FUENTE` o la URL de DroidCam; cerrar otros programas que usen la cámara |
| La franja dice que la resolución es distinta | En el cliente de DroidCam elegir 640×480, o recalibrar a la nueva resolución (sección 4) |
| Siempre "sin herramienta" | La pieza debe estar dentro del rectángulo azul y acostada a lo largo de la banda |
| Todas las medidas corridas por la misma cantidad | Se movió la cámara: recalibrar (sección 4) |
| `No existe calibracion.json` | Ejecutar `calibrar.py` desde la carpeta del repositorio |
