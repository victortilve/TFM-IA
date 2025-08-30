from rdflib import Graph, Namespace
from rdflib.namespace import RDF
from shapely import wkt
import matplotlib.pyplot as plt


# === Rutas ===
ttl_path = "/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/CodigosPython/eventos_astronomicos/observacionesLunaConZonas.ttl"  
output_png ="/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/CodigosPython/eventos_astronomicos/zonasLuna.png"

# === Cargar grafo RDF ===
g = Graph()
g.parse(ttl_path, format="turtle")

# === Namespaces ===
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
SF  = Namespace("http://www.opengis.net/ont/sf#")

# --- función auxiliar: elimina el prefijo de CRS del literal WKT ---
def strip_crs_iri(wkt_text: str) -> str:
    s = wkt_text.strip()
    if s.startswith("<"):
        j = s.find(">")
        if j != -1:
            s = s[j+1:].strip()
    return s

# === Extraer WKT: POLÍGONOS y PUNTOS por separado ===
poly_wkts = []
for geom in g.subjects(RDF.type, SF.Polygon):
    for _, _, lit in g.triples((geom, GEO.asWKT, None)):
        poly_wkts.append(strip_crs_iri(str(lit)))
        
point_wkts = []
for geom in g.subjects(RDF.type, SF.Point):
    for _, _, lit in g.triples((geom, GEO.asWKT, None)):
        point_wkts.append(strip_crs_iri(str(lit)))

# === Crear gráfico ===
plt.figure(figsize=(10, 10))
ax = plt.gca()

# polígonos
for wkt_text in poly_wkts:
    try:
        polygon = wkt.loads(wkt_text)
        x, y = polygon.exterior.xy
        ax.plot(x, y, linestyle='-', alpha=0.6, color='blue')
    except Exception as e:
        print(f"Error POLYGON: {wkt_text[:60]}... -> {e}")
        
# puntos (centroides)
for wkt_text in point_wkts:
    try:
        point = wkt.loads(wkt_text)
        ax.plot(point.x, point.y, marker='o', markersize=3, linestyle='None', alpha=0.8)
    except Exception as e:
        print(f"Error POINT: {wkt_text[:60]}... -> {e}")


ax.set_title("Geometrías GeoSPARQL (polígonos y centroides)")
ax.set_xlabel("Longitud")
ax.set_ylabel("Latitud")
ax.grid(True)
plt.axis('equal')
plt.tight_layout()
plt.savefig(output_png, dpi=300, bbox_inches='tight')
print(f"Salida plot guardada en: {output_png}")
