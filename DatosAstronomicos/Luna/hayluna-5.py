# -*- coding: utf-8 -*-
import os
import re
import csv
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD
from datetime import datetime, timezone
from skyfield.api import load, Topos
from skyfield import almanac

# =========================
# CONFIGURACIÓN
# =========================
# Carpeta con RDF/XML de observaciones (medidas)
INPUT_FOLDER = "/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/DatosMeteogalicia/RDF"   
OUTPUT_FOLDER = "/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/DatosMeteogalicia/RDF/Caso2"          

# Grafo con sensores y sus geometrías POINT WKT
SENSORS_GRAPH_PATH = "/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/DefinicionCacharros/VersionFinal/SensoresSQM-Meteogalicia.ttl"  

# CSV de informe
CSV_REPORT_PATH = "/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/CodigosPython/eventos_astronomicos/hayLuna_informe.csv"  

# Umbrales para “hay Luna”
ALT_MIN_DEG = 0.0      # Luna sobre horizonte
ILLUM_MIN   = 0.01     # fracción iluminada mínima

# Namespaces
EX    = Namespace("http://example.org#")
SOSA  = Namespace("http://www.w3.org/ns/sosa/")
GEO   = Namespace("http://www.opengis.net/ont/geosparql#")

# =========================
# CARGA SENSORES Y COORDENADAS
# =========================
sens_g = Graph()
if SENSORS_GRAPH_PATH.lower().endswith((".ttl", ".turtle")):
    sens_g.parse(SENSORS_GRAPH_PATH, format="turtle")
else:
    sens_g.parse(SENSORS_GRAPH_PATH)  # intenta auto-detectar

sensor_coords = {}  # sensor URI -> (lat, lon)

POINT_RE = re.compile(r'POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)', re.I)
for s in sens_g.subjects():
    geom = sens_g.value(s, GEO.hasGeometry)
    if geom is None:
        continue
    wkt_literal = sens_g.value(geom, GEO.asWKT)
    if not wkt_literal:
        continue
    m = POINT_RE.search(str(wkt_literal))
    if not m:
        continue
    lon = float(m.group(1))
    lat = float(m.group(2))
    sensor_coords[s] = (lat, lon)

print(f"✅ Sensores con coordenadas: {len(sensor_coords)}")

# =========================
# SKYFIELD (efemérides)
# =========================
eph = load('de421.bsp')
moon = eph['moon']
earth = eph['earth']
ts = load.timescale()

observer_cache = {}  # (lat,lon) redondeados -> observer

def observer_for(lat, lon):
    key = (round(lat, 6), round(lon, 6))
    obs = observer_cache.get(key)
    if obs is None:
        obs = earth + Topos(latitude_degrees=lat, longitude_degrees=lon)
        observer_cache[key] = obs
    return obs

def hay_luna_en(lat, lon, dt_utc):
    """Devuelve (hay_luna: bool, alt_deg: float, illum: float)"""
    t = ts.from_datetime(dt_utc)
    obs = observer_for(lat, lon)
    alt, az, _ = obs.at(t).observe(moon).apparent().altaz()
    alt_deg = alt.degrees
    illum = almanac.fraction_illuminated(eph, 'moon', t)
    return (alt_deg > ALT_MIN_DEG and illum > ILLUM_MIN), float(alt_deg), float(illum)

# =========================
# CSV de informe
# =========================
os.makedirs(os.path.dirname(CSV_REPORT_PATH), exist_ok=True)
csv_file = open(CSV_REPORT_PATH, "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
writer.writerow([
    "source_file", "obs_uri", "sensor_uri",
    "lat", "lon",
    "resultTime_utc",
    "moon_alt_deg", "illum_frac",
    "hayLuna"
])

# =========================
# PROCESAR ARCHIVOS DE OBSERVACIONES
# =========================
for filename in os.listdir(INPUT_FOLDER):
    if not filename.lower().endswith((".xml", ".rdf")):
        continue

    in_path  = os.path.join(INPUT_FOLDER, filename)
    out_path = os.path.join(OUTPUT_FOLDER, filename.rsplit(".", 1)[0] + "_LUNA.xml")

    print(f"🟡 Procesando: {filename}")

    g = Graph()
    try:
        g.parse(in_path)  # intenta auto
    except Exception:
        g.parse(in_path, format="xml")

    ge = Graph()
    ge.bind("ex", EX)
    ge.bind("sosa", SOSA)
    ge += g  # copia todo

    for obs in g.subjects(RDF.type, SOSA.Observation):
        sensor_uri = g.value(obs, SOSA.madeBySensor)
        if sensor_uri is None:
            continue

        coords = sensor_coords.get(sensor_uri)
        if not coords:
            continue
        lat, lon = coords

        t_literal = g.value(obs, SOSA.resultTime)
        if t_literal is None:
            continue

        # Normalizar a datetime con tz UTC
        s = str(t_literal).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            # último recurso: quitar fracciones de segundo raras
            s2 = s.split(".")[0]
            if not s2.endswith("+00:00"):
                s2 += "+00:00"
            dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        try:
            hay, alt_deg, illum = hay_luna_en(lat, lon, dt)
        except Exception:
            continue

        # Añadir triple booleano
        ge.add((obs, EX.hayBrilloLuna, Literal(hay, datatype=XSD.boolean)))

        # Fila en CSV
        writer.writerow([
            filename, str(obs), str(sensor_uri),
            f"{lat:.6f}", f"{lon:.6f}",
            dt.isoformat(),
            f"{alt_deg:.2f}", f"{illum:.4f}",
            "true" if hay else "false"
        ])

    ge.serialize(destination=out_path, format="xml")
    print(f"✅ Guardado RDF enriquecido: {out_path}")

csv_file.close()
print(f"📄 Informe CSV guardado en: {CSV_REPORT_PATH}")
