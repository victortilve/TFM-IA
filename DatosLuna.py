from skyfield.api import load, Topos
from datetime import datetime, timedelta
import pytz
import math
import csv

# Coordenadas de Vigo y zona horaria
LAT_VIGO = 42.2406
LON_VIGO = -8.7207
TIMEZONE = pytz.timezone("Europe/Madrid")
location = Topos(latitude_degrees=LAT_VIGO, longitude_degrees=LON_VIGO)

# Intervalo de fechas
start_date = datetime(2023, 9, 1, 0, 0)
end_date = datetime(2025, 2, 1, 0, 0)
intervalo = timedelta(minutes=10)

# Cargar efemérides y escalas de tiempo
eph = load('de421.bsp')
moon = eph['moon']
sun = eph['sun']
earth = eph['earth']
ts = load.timescale()

# Función para fracción iluminada
def fraccion_iluminada(moon_vec, sun_vec):
    # Usamos .separation_from() desde el objeto vectorial lunar
    return (1 + math.cos(moon_vec.separation_from(sun_vec).radians)) / 2

# Función principal de cálculo
def calcular_datos_lunares(instante_local):
    dt_local = TIMEZONE.localize(instante_local)
    dt_utc = dt_local.astimezone(pytz.utc)
    t = ts.utc(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour, dt_utc.minute)

    observer = (earth + location).at(t)
    moon_vec = observer.observe(moon)
    sun_vec = observer.observe(sun)

    alt, az, _ = moon_vec.apparent().altaz()
    iluminacion = fraccion_iluminada(moon_vec, sun_vec)

    return {
        "fecha_hora_local": dt_local.strftime("%Y-%m-%dT%H:%M:00"),
        "fecha_hora_utc": dt_utc.strftime("%Y-%m-%dT%H:%M:00"),
        "altura_luna_grados": round(alt.degrees, 2),
        "fraccion_iluminada": round(iluminacion, 3)
    }

# Guardar resultados en CSV
with open("luna_vigo_cada_10min.csv", mode="w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["fecha_hora_local", "fecha_hora_utc", "altura_luna_grados", "fraccion_iluminada"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    instante = start_date
    while instante <= end_date:
        datos = calcular_datos_lunares(instante)
        writer.writerow(datos)
        instante += intervalo

print("Archivo CSV generado: luna_vigo_cada_10min.csv")
