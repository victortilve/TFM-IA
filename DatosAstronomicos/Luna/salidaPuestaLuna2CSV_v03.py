import pandas as pd
from skyfield.api import load, Topos
from skyfield.almanac import find_discrete, risings_and_settings, fraction_illuminated
from datetime import datetime, timedelta
import yaml
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from geopy.distance import distance
import math

# === CARGAR CENTROIDES DESDE YAML ===
with open("centroidesAutomaticosLuna.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# === CARGA EFEMÉRIDES Y TIEMPO ===
ts = load.timescale()
eph = load('de421.bsp')
earth = eph['earth']
moon = eph['moon']

# Leer intervalo común
start_date = datetime.strptime(config["fecha_inicio"], "%Y-%m-%d")
end_date = datetime.strptime(config["fecha_fin"], "%Y-%m-%d")

datos = []

for centroide in config["centroides"]:
    nombre = centroide["nombre"]
    lat = centroide["latitud"]
    lon = centroide["longitud"]
    radio = centroide.get("radio_km")

    topos = Topos(latitude_degrees=lat, longitude_degrees=lon)
    location = earth + topos
    poligono = centroide["wkt"]

    for single_date in pd.date_range(start=start_date, end=end_date - timedelta(days=1), freq='D'):
        t0 = ts.utc(single_date.year, single_date.month, single_date.day - 1, 12)
        t1 = ts.utc(single_date.year, single_date.month, single_date.day + 1, 12)

        # Eventos lunares
        f = risings_and_settings(eph, moon, topos)
        times, events = find_discrete(t0, t1, f)

        for i in range(len(events) - 1):
            if events[i] == 1 and events[i + 1] == 0:
                salida = times[i].utc_datetime()
                puesta = times[i + 1].utc_datetime()
                centro = salida + (puesta - salida) / 2
                centro_t = ts.utc(centro)

                iluminacion = round(fraction_illuminated(eph, "moon", centro_t), 4)
                alt, _, _ = location.at(centro_t).observe(moon).apparent().altaz()
                altura_maxima = round(alt.degrees, 2)

                datos.append({
                    "centroide": nombre,
                    "fecha": single_date.date(),
                    "salida_luna_utc": salida.strftime("%Y-%m-%d %H:%M:%S"),
                    "puesta_luna_utc": puesta.strftime("%Y-%m-%d %H:%M:%S"),
                    "fraccion_iluminada": iluminacion,
                    "culminacion_grados": altura_maxima,
                    "latitud": lat,
                    "longitud": lon,
                    "valido_para": poligono
                })

# === EXPORTAR A CSV ===
df = pd.DataFrame(datos)
df.to_csv("observaciones_luna_centroides.csv", index=False)
print("✅ CSV generado: observaciones_luna_centroides.csv")
