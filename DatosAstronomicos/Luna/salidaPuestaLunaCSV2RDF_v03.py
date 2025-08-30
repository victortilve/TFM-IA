import pandas as pd
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD
import ast
from shapely import wkt

# === Cargar CSV ===
csv_path = "observaciones_luna_centroides.csv"  # Ajusta la ruta según tu entorno
df = pd.read_csv(csv_path)

# === Namespaces ===
EX = Namespace("http://example.org#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
TIME = Namespace("http://www.w3.org/2006/time#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
SF = Namespace("http://www.opengis.net/ont/sf#")
SCHEMA = Namespace("http://schema.org/")
GEO_WKT = Namespace("http://www.opengis.net/ont/geosparql#wktLiteral")

# === Crear grafo RDF ===
g = Graph()
g.bind("ex", EX)
g.bind("sosa", SOSA)
g.bind("qudt", QUDT)
g.bind("unit", UNIT)
g.bind("time", TIME)
g.bind("geo", GEO)
g.bind("sf",SF)
g.bind("schema", SCHEMA)

# === Diccionario para evitar duplicados de zonas ===
zonas_vistas = {}

# === Recorrer observaciones ===
for _, row in df.iterrows():
    fecha = row["fecha"]
    salida = row["salida_luna_utc"]
    puesta = row["puesta_luna_utc"]
    iluminacion = float(row["fraccion_iluminada"])
    elevacion = float(row["culminacion_grados"])
    lat = round(float(row["latitud"]), 4)
    lon = round(float(row["longitud"]), 4)
    #coords = ast.literal_eval(row["valido_para"])
    polygon = wkt.loads(row["valido_para"])
    coords = list(polygon.exterior.coords)

    centroide = f"{lat}_{lon}"
    zona_uri = EX[f"zona_centroide_{centroide}"]
    obs_id = f"ObservacionLuna_Luna_{centroide}_{fecha.replace('-', '')}"
    obs_uri = EX[obs_id]
    resultado_uri = EX[f"Resultado_{obs_id}"]

    # --- Zona geográfica (GeoSPARQL: Feature -> hasGeometry -> Polygon + Centroid) ---
    if zona_uri not in zonas_vistas:
        # Cierra el anillo si no lo está
        if coords and coords[0] != coords[-1]:
            coords = coords + [coords[0]]

        # WKT con CRS (CRS84: lon lat en grados)
        wkt_coords  = ", ".join(f"{x} {y}" for x, y in coords[:-1]) + f", {coords[0][0]} {coords[0][1]}"
        crs_iri     = "<http://www.opengis.net/def/crs/OGC/1.3/CRS84>"
        poly_wkt    = f"{crs_iri} POLYGON(({wkt_coords}))"

        # URIs para geometrías
        geom_poly_uri = URIRef(str(zona_uri) + "_geom")
        geom_pt_uri   = URIRef(str(zona_uri) + "_centroid")

        # Declara la Feature y vincula geometrías
        g.add((zona_uri, RDF.type, GEO.Feature))
        g.add((zona_uri, GEO.hasGeometry, geom_poly_uri))
        g.add((zona_uri, GEO.hasGeometry, geom_pt_uri))

        # Geometría polígono
        g.add((geom_poly_uri, RDF.type, SF.Polygon))
        g.add((geom_poly_uri, GEO.asWKT, Literal(poly_wkt, datatype=GEO.wktLiteral)))

        # ---- Centroide (cálculo planar por fórmula del polígono; si área=0, media de vértices) ----
        ring = coords  # cerrado
        n = len(ring)
        # usa n-1 segmentos (último es repetición del primero)
        A = Cx = Cy = 0.0
        for i in range(n - 1):
            x0, y0 = ring[i]
            x1, y1 = ring[i + 1]
            cross = x0 * y1 - x1 * y0
            A  += cross
            Cx += (x0 + x1) * cross
            Cy += (y0 + y1) * cross
        A *= 0.5
        if A != 0.0:
            cx = Cx / (6.0 * A)
            cy = Cy / (6.0 * A)
        else:
            # fallback: media simple de vértices (sin el duplicado final)
            xs = [x for x, _ in ring[:-1]]
            ys = [y for _, y in ring[:-1]]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)

        pt_wkt = f"{crs_iri} POINT({cx} {cy})"

        # Geometría punto (centroide)
        g.add((geom_pt_uri, RDF.type, SF.Point))
        g.add((geom_pt_uri, GEO.asWKT, Literal(pt_wkt, datatype=GEO.wktLiteral)))

        zonas_vistas[zona_uri] = True



    # --- Observación lunar ---
    g.add((obs_uri, RDF.type, SOSA.Observation))
    g.add((obs_uri, SOSA.resultTime, Literal(fecha, datatype=XSD.date)))
    g.add((obs_uri, SOSA.hasFeatureOfInterest, zona_uri))
    #g.add((obs_uri, GEO.lat, Literal(lat, datatype=XSD.float)))
    #g.add((obs_uri, GEO.long, Literal(lon, datatype=XSD.float)))
    g.add((obs_uri, SOSA.hasResult, resultado_uri))

    # --- Resultado ---
    g.add((resultado_uri, RDF.type, SOSA.Result))

    # Iluminación
    iluminacion_uri = URIRef(f"{resultado_uri}_iluminacion")
    g.add((resultado_uri, EX.moonIllumination, iluminacion_uri))
    g.add((iluminacion_uri, RDF.type, QUDT.QuantityValue))
    g.add((iluminacion_uri, QUDT.numericValue, Literal(iluminacion, datatype=XSD.float)))
    g.add((iluminacion_uri, QUDT.unit, UNIT.One))

    # Altura (culminación)
    elevacion_uri = URIRef(f"{resultado_uri}_culminacion")
    g.add((resultado_uri, EX.moonElevation, elevacion_uri))
    g.add((elevacion_uri, RDF.type, QUDT.QuantityValue))
    g.add((elevacion_uri, QUDT.numericValue, Literal(elevacion, datatype=XSD.float)))
    g.add((elevacion_uri, QUDT.unit, UNIT.DEG))

    # Intervalo de visibilidad con zona horaria explícita
    intervalo_uri = URIRef(f"{obs_uri}_intervalo")
    g.add((obs_uri, SOSA.phenomenonTime, intervalo_uri))
    g.add((intervalo_uri, RDF.type, TIME.ProperInterval))
    g.add((intervalo_uri, TIME.hasBeginning, Literal(salida + "+00:00", datatype=XSD.dateTime)))
    g.add((intervalo_uri, TIME.hasEnd, Literal(puesta + "+00:00", datatype=XSD.dateTime)))

# === Guardar el RDF ===
output_file = "observacionesLunaConZonas.ttl"
g.serialize(destination=output_file, format="turtle")
print(f"✅ RDF guardado en {output_file}")
