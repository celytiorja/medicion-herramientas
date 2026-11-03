# CLAUDE.md

Contexto para Claude Code (y para quien trabaje en este repositorio).

## Qué es

Parte 2 del proyecto final de la materia Señales (UMNG): medir el diámetro de brocas, fresas y machos
sobre una banda transportadora amarilla con una cámara DroidCam (640×480) y entregar su medida comercial.
La parte 1 (otro equipo) detecta el tipo de herramienta con YOLO; este repositorio **solo mide**.

## Restricciones del proyecto (no negociables)

- **Nada de IA ni modelos entrenados** aquí: solo procesamiento de imagen y de señales (OpenCV + NumPy).
- **No se pueden tomar fotos nuevas ni cambiar el montaje** (banda, luz, cámara, herramientas). Las
  mejoras tienen que venir del código.
- El tipo de herramienta lo da quien llama (`"broca_mm"`, `"broca_pulg"`, `"fresa"`, `"macho"`).
- Una pieza a la vez, acostada a lo largo de la banda (horizontal en la imagen).

## Comandos

```powershell
py -m pip install -r requirements.txt
py evaluar_medicion.py "Fotos Herramienta"            # reporte de precisión (no modifica nada)
py evaluar_medicion.py "Fotos Herramienta" --guardar  # re-ajusta curvas y las guarda en calibracion.json
py calibrar.py "Fotos Herramienta/dataset_distancia"  # escala mm/px con el ArUco (30 mm)
py camara_medida.py                                   # en vivo (requiere DroidCam)
```

No hay tests unitarios: **`evaluar_medicion.py` es la prueba de regresión**. Ejecutarlo después de
cualquier cambio en `medicion.py` y comparar con la línea base.

## Arquitectura

- `medicion.py` — núcleo. `medir(imagen, tipo, cal)` → dict con `diametro_mm`, `medida`, `contorno` o `error`.
  1. `mapa_distancia`: Mahalanobis en Lab respecto al color de la banda (estimado en cada imagen).
  2. `mascara_herramienta`: umbral `D_UMBRAL` + apertura horizontal (borra rayas verticales de la banda y
     la marca de agua de DroidCam) + filtro de densidad. Solo da la ubicación y el eje.
  3. `medir_ancho`: endereza, extiende el largo por el eje (las partes doradas no salen en la máscara),
     recorta 10 % de cada punta, divide en `TRAMOS` y en cada tramo toma la mediana por fila del canal
     → perfil transversal → `ancho_perfil` (primer pico de gradiente ≥ `FRACCION_PICO` desde afuera,
     interpolación parabólica). Mediana de los tramos.
  4. `a_mm`: `ganancia × ancho_px × mm_por_px + desfase` por familia y canal; se promedian los
     canales de `CANALES[familia]` (brocas: L y b; fresas y machos: b).
  5. `medida_comercial`: la más cercana de `inventario.TABLAS[tipo]`; "fuera de tabla" solo si cae
     fuera del rango de la tabla ± `TOLERANCIA_MM`.
- `inventario.py` — medidas nominales (`TABLAS`) y qué foto es qué medida (`FOTOS`).
- `evaluar_medicion.py` — mide las fotos, ajusta las curvas con las **2 primeras fotos de cada medida**
  y reporta el acierto en **las demás** (prueba).
- `calibrar.py` — mm/px con el ArUco; descarta fotos a más de 2 % de la mediana.
- `camara_medida.py` — bucle en vivo: mediana de los últimos 15 cuadros; tolera cortes de DroidCam.

## Línea base (no empeorarla)

Fotos de prueba de `evaluar_medicion.py`: brocas mm 23/27, brocas pulgadas 26/39, fresas 38/38,
machos 31/35. Unos 25 ms por cuadro.

## Cosas que ya se aprendieron (evitar repetir errores)

- **Protocolo**: elegir canales y parámetros solo con las fotos de ajuste (validación cruzada entre la
  foto 0 y la 1 de cada medida). Ajustar mirando las fotos de prueba infla los resultados.
- **Curva de calibración clásica**: se ajusta `medido = a·real + b` y se invierte. Ajustar `real` en
  función de `medido` aplana la recta por el ruido (dilución por regresión) y comprime las medidas.
- `cv2.imread`/`cv2.imwrite` fallan con tildes o ñ en la ruta en Windows (la carpeta del grupo se llama
  "Señales"): usar `leer_imagen` / `guardar_imagen`.
- Las brocas doradas se parecen al amarillo de la banda: segmentar por saturación o por umbral
  pixel a pixel las mide de menos. El perfil promediado + gradiente lo resolvió.
- La ganancia del canal L no es la escala real (detecta un borde interno); el canal b sí es coherente
  con el ArUco de 30 mm. No usar la ganancia de L para dudar del tamaño del ArUco.
- Brocas en mm y en pulgadas casi iguales (9.5 mm vs 3/8") son físicamente indistinguibles a esta
  resolución (~1.5 px/mm): la serie la elige el usuario.
- `ZONA_BANDA` y `calibracion.json` dependen de la posición de la cámara y de la resolución 640×480.

## Estilo

Código y comentarios en español, nombres en español, comentarios breves que explican el porqué.
Parámetros ajustables como constantes en mayúsculas arriba de `medicion.py`.
