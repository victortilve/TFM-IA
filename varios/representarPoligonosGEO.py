from rdflib import Graph, Namespace
from shapely import wkt
import matplotlib.pyplot as plt

# === Rutas ===
ttl_path = "/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/CodigosPython/eventos_astronomicos/observaciones_luna_con_zonas_final_ejecucionLocal.ttl"  
output_png ="/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/CodigosPython/eventos_astronomicos/zonasLuna.png"

# === Cargar grafo RDF ===
g = Graph()
g.parse(ttl_path, format="turtle")

# === Namespaces ===
GEO = Namespace("http://www.opengis.net/ont/geosparql#")

# === Extraer los WKT de los polígonos ===
wkt_literals = []
for _, _, o in g.triples((None, GEO.asWKT, None)):
    wkt_literals.append(str(o))

# === Crear gráfico ===
plt.figure(figsize=(10, 10))
ax = plt.gca()

for wkt_text in wkt_literals:
    try:
        polygon = wkt.loads(wkt_text)
        x, y = polygon.exterior.xy
        ax.plot(x, y, linestyle='-', alpha=0.5, color='blue')
    except Exception as e:
        print(f"Error en WKT: {wkt_text[:50]}... -> {e}")

ax.set_title("Zonas RDF con geo:Polygon (desde geo:asWKT)")
ax.set_xlabel("Longitud")
ax.set_ylabel("Latitud")
ax.grid(True)
plt.axis('equal')
plt.tight_layout()
plt.savefig(output_png, dpi=300, bbox_inches='tight')
print(f"Salida plot guardada en: {output_png}")
