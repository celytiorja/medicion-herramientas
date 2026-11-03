"""Medición del diámetro de brocas, fresas y machos sobre la banda transportadora.

No usa IA ni identifica la herramienta: el tipo lo indica quien llama. Todo es
procesamiento de imagen y de señales.

Pasos:
 1. Modelo de color de la banda: media y covarianza (Lab) de sus píxeles amarillos.
 2. Distancia de Mahalanobis de cada píxel a ese modelo: lejos = no es banda.
 3. Filtros morfológicos: se quitan las rayas verticales de la banda y la marca de agua;
    queda la herramienta (objeto alargado y denso). Con ella se obtiene el eje y se endereza.
 4. Perfil transversal: en cada tramo de la herramienta se toma la mediana, columna a
    columna, de un canal de color (L = luminosidad, b = amarillo-azul). Promediar a lo
    largo de la pieza reduce el ruido y borra el patrón de la banda.
 5. Bordes: picos del gradiente del perfil, buscados desde afuera e interpolados con una
    parábola (precisión sub-píxel). Ancho = distancia entre bordes; mediana de 4 tramos.
 6. px -> mm con la calibración (ArUco + curva con piezas de medida conocida). En las brocas
    se promedian los diámetros de los canales L y b, que se equivocan por razones distintas.
"""
import json
from pathlib import Path

import cv2
import numpy as np

import inventario

BASE = Path(__file__).resolve().parent
ARCHIVO_CAL = BASE / "calibracion.json"

LADO_REF_MM = 30.0                  # lado real del ArUco impreso: medirlo con regla
ZONA_BANDA = (225, 160, 575, 330)   # (x0, y0, x1, y1) en px: parte útil de la banda (imagen 640x480)
D_UMBRAL = 6.0                      # distancia de color a partir de la cual un píxel ya no es banda
CANALES = {"broca": ["L", "b"], "fresa": ["b"], "macho": ["b"]}   # elegidos con las fotos de ajuste
TRAMOS = 4                          # la herramienta se mide en 4 tramos y se toma la mediana
FRACCION_PICO = 0.5                 # un borde es el primer pico de gradiente >= 50 % del máximo
MARGEN_PX = 7                       # cuánto más allá del borde aproximado se busca el borde fino
TOLERANCIA_MM = 1.0                 # más allá de esto por fuera del rango de la tabla -> "fuera de tabla"


def familia(tipo):
    """'broca_mm' y 'broca_pulg' comparten calibración: 'broca'."""
    return tipo.split("_")[0]


def leer_imagen(ruta):
    """Como cv2.imread, pero funciona con tildes y ñ en la ruta (cv2.imread falla en Windows)."""
    datos = np.fromfile(str(ruta), dtype=np.uint8)
    return cv2.imdecode(datos, cv2.IMREAD_COLOR) if datos.size else None


def guardar_imagen(ruta, imagen):
    cv2.imencode(Path(ruta).suffix, imagen)[1].tofile(str(ruta))


# ---------- Referencia y calibración ----------

def detectar_referencia(gris):
    """Esquinas (4x2, px) del ArUco o, si no hay, del cuadrado negro más grande."""
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50))
    esquinas, ids, _ = det.detectMarkers(gris)
    if ids is not None:
        return esquinas[0][0], "aruco"
    _, oscuro = cv2.threshold(cv2.GaussianBlur(gris, (5, 5), 0), 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mejor = None
    for c in cv2.findContours(oscuro, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]:
        aprox = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(aprox) != 4 or not cv2.isContourConvex(aprox):
            continue
        lados = lados_px(aprox.reshape(4, 2).astype(np.float32))
        if min(lados) < 20 or max(lados) / min(lados) > 1.15:
            continue
        if mejor is None or cv2.contourArea(aprox) > cv2.contourArea(mejor):
            mejor = aprox
    if mejor is None:
        return None, None
    return mejor.reshape(4, 2).astype(np.float32), "cuadrado"


def lados_px(esq):
    return [float(np.linalg.norm(esq[i] - esq[(i + 1) % 4])) for i in range(4)]


def cargar_calibracion():
    if not ARCHIVO_CAL.exists():
        raise SystemExit(f"No existe {ARCHIVO_CAL.name}: primero ejecutar calibrar.py")
    return json.loads(ARCHIVO_CAL.read_text(encoding="utf-8"))


# ---------- Ubicar la herramienta ----------

def mapa_distancia(roi):
    """Distancia de Mahalanobis (en Lab) de cada píxel al color de la banda."""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    h, s, v = cv2.split(hsv)
    amarillo = (h >= 22) & (h <= 35) & (s > 150) & (v > 170)
    if amarillo.sum() < 500:
        return None
    px = lab[amarillo]
    inversa = np.linalg.inv(np.cov(px.T) + np.eye(3) * 4)
    d = lab - px.mean(axis=0)
    return np.sqrt(np.einsum("...i,ij,...j->...", d, inversa, d))


def mascara_herramienta(D):
    """Máscara (0/1) aproximada de la herramienta, o None si no hay."""
    no_banda = (D > D_UMBRAL).astype(np.uint8)
    # Apertura horizontal: borra las rayas verticales de la banda y las letras de la marca de agua
    m = cv2.morphologyEx(no_banda, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (17, 1)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3)))
    n, etiquetas, st, _ = cv2.connectedComponentsWithStats(m)
    mejor, area = None, 0
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if w < 40 or not 6 <= h <= 60 or w < 3 * h or y <= 0 or y + h >= m.shape[0]:
            continue
        if no_banda[etiquetas == i].mean() < 0.75:    # la marca de agua es poco densa
            continue
        if a > area:
            mejor, area = i, a
    return None if mejor is None else (etiquetas == mejor).astype(np.uint8)


# ---------- Perfil transversal y bordes ----------

def _primer_pico(g):
    """Primer máximo local de g (desde el índice 0) que llega a FRACCION_PICO del máximo, sub-píxel."""
    umbral = FRACCION_PICO * g.max()
    for i in range(1, len(g) - 1):
        if g[i] >= umbral and g[i] >= g[i - 1] and g[i] >= g[i + 1]:
            den = g[i - 1] - 2 * g[i] + g[i + 1]
            return i + (0.5 * (g[i - 1] - g[i + 1]) / den if den != 0 else 0.0)   # vértice de la parábola
    return None


def ancho_perfil(perfil):
    """Distancia (px) entre el borde superior e inferior de un perfil transversal."""
    g = np.gradient(cv2.GaussianBlur(perfil.reshape(-1, 1), (1, 5), 0.8).ravel())
    c = len(perfil) // 2
    arriba = _primer_pico(g[:c])                # desde afuera: sube al entrar a la herramienta
    abajo = _primer_pico(-g[c:][::-1])          # desde afuera por abajo
    if arriba is None or abajo is None:
        return None
    return float((len(perfil) - 1 - abajo) - arriba)


def medir_ancho(imagen):
    """({"anchos": {canal: px}, "contorno": ...}, None) o (None, motivo)."""
    x0, y0, x1, y1 = ZONA_BANDA
    roi = imagen[y0:y1, x0:x1]
    D = mapa_distancia(roi)
    if D is None:
        return None, "no se ve la banda"
    comp = mascara_herramienta(D)
    if comp is None:
        return None, "sin herramienta"

    # Enderezar: el lado largo del rectángulo mínimo queda horizontal
    cnt = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0][0]
    rect = cv2.minAreaRect(cnt)
    p = cv2.boxPoints(rect)
    v = max([p[1] - p[0], p[2] - p[1]], key=np.linalg.norm)
    M = cv2.getRotationMatrix2D(rect[0], float(np.degrees(np.arctan2(v[1], v[0]))), 1.0)
    tam = (D.shape[1], D.shape[0])
    ys, xs = np.nonzero(cv2.warpAffine(comp, M, tam, flags=cv2.INTER_NEAREST))
    yc = int(round(ys.mean()))
    mitad = int((ys.max() - ys.min() + 1) / 2 + MARGEN_PX)
    if yc - mitad < 0 or yc + mitad >= D.shape[0]:
        return None, "herramienta en el borde de la zona"

    # Largo: la máscara puede no cubrir las partes doradas; se extiende mientras el eje no sea banda
    eje = cv2.warpAffine(D.astype(np.float32), M, tam, flags=cv2.INTER_LINEAR)[yc - 2:yc + 3].mean(axis=0)
    xa, xb = xs.min(), xs.max()
    while xa > 0 and eje[xa - 1] > 4:
        xa -= 1
    while xb < len(eje) - 1 and eje[xb + 1] > 4:
        xb += 1
    recorte = int(0.1 * (xb - xa))                 # fuera las puntas (cónica / bajo las escobillas)
    xa, xb = xa + recorte, xb - recorte
    if xb - xa < 4 * 8:
        return None, "herramienta poco visible"

    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    canales = {"L": lab[..., 0], "b": -lab[..., 2]}
    anchos = {}
    for nombre, canal in canales.items():
        banda = cv2.warpAffine(canal, M, tam, flags=cv2.INTER_LINEAR)[yc - mitad:yc + mitad + 1, xa:xb]
        ws = [ancho_perfil(np.median(tramo, axis=1)) for tramo in np.array_split(banda, TRAMOS, axis=1)]
        ws = [w for w in ws if w is not None]
        if ws:
            anchos[nombre] = float(np.median(ws))
    if not anchos:
        return None, "no se encontraron los bordes"
    return {"anchos": anchos, "contorno": cnt + np.array([x0, y0])}, None


# ---------- Medida ----------

def medida_comercial(tipo, diametro):
    """Medida de la tabla más cercana; 'fuera de tabla' si cae lejos del rango de la tabla."""
    tabla = inventario.TABLAS[tipo]
    if not min(tabla.values()) - TOLERANCIA_MM <= diametro <= max(tabla.values()) + TOLERANCIA_MM:
        return "fuera de tabla"
    return min(tabla, key=lambda nombre: abs(tabla[nombre] - diametro))


def a_mm(anchos, tipo, cal):
    """px -> mm. Cada canal tiene su curva (escala del ArUco + ajuste con piezas conocidas);
    se promedian los canales de la familia. None si falta algún canal."""
    fam = familia(tipo)
    ds = []
    for canal in CANALES[fam]:
        if canal not in anchos:
            return None
        aj = cal.get("ajuste", {}).get(fam, {}).get(canal, {"ganancia": 1.0, "desfase": 0.0})
        ds.append(aj["ganancia"] * anchos[canal] * cal["mm_por_px"] + aj["desfase"])
    return float(np.mean(ds))


def medir(imagen, tipo, cal=None):
    """Mide la herramienta de la imagen. tipo: 'broca_mm', 'broca_pulg', 'fresa' o 'macho'.

    Devuelve un dict con diametro_mm, medida y contorno, o con "error".
    """
    cal = cal or cargar_calibracion()
    if [imagen.shape[1], imagen.shape[0]] != cal["resolucion"]:
        return {"error": f"resolución {imagen.shape[1]}x{imagen.shape[0]} distinta a la calibrada"}
    r, motivo = medir_ancho(imagen)
    if r is None:
        return {"error": motivo}
    d = a_mm(r["anchos"], tipo, cal)
    if d is None:
        return {"error": "no se encontraron los bordes"}
    return {"tipo": tipo, "anchos_px": r["anchos"], "diametro_mm": d,
            "medida": medida_comercial(tipo, d), "contorno": r["contorno"]}


def etiqueta(tipo, medida, diametro):
    return f"{inventario.NOMBRES[tipo]}: {medida} ({diametro:.2f} mm)"


def dibujar(imagen, r):
    x0, y0, x1, y1 = ZONA_BANDA
    cv2.rectangle(imagen, (x0, y0), (x1, y1), (255, 0, 0), 1)
    if "contorno" in r:
        cv2.drawContours(imagen, [r["contorno"]], -1, (0, 0, 255), 1)
        cv2.putText(imagen, etiqueta(r["tipo"], r["medida"], r["diametro_mm"]), (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    return imagen
