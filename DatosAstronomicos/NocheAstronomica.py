#En Google Colab se ejecuta en 40minutos para un año de noches

from skyfield.api import load, Topos
from datetime import datetime, timedelta
import pytz
import csv
from astral import LocationInfo
from astral.sun import sun

# Configuración
Localidad = "Vigo"
Pais = "España"
ZonaHoraria = "Europe/Madrid"
LAT = 42.2406
LON = -8.7207
TIMEZONE = pytz.timezone(ZonaHoraria)
SKYFIELD_LOCATION = Topos(latitude_degrees=LAT, longitude_degrees=LON)
ASTRAL_LOCATION = LocationInfo(Localidad, Pais, ZonaHoraria, LAT, LON)

start_date = datetime(2023, 9, 1)
end_date = datetime(2025, 1, 31)  # puedes ampliar
STEP_MINUTES = 1 # Dejar en uno porque el código analiza alturas de cada minuto para decidir cuándo comienza o finaliza cada evento

# Efemérides Skyfield
eph = load('de421.bsp')
sun_skyfield = eph['sun']
earth = eph['earth']
ts = load.timescale()

# Función para buscar cruce de altitud (ej. –18°)
def encontrar_cruce_altura(times, alturas, objetivo, sentido='bajar'):
    for i in range(1, len(alturas)):
        alt_prev = alturas[i-1]
        alt_now = alturas[i]
        if sentido == 'bajar' and alt_prev > objetivo >= alt_now:
            return times[i]
        elif sentido == 'subir' and alt_prev < objetivo <= alt_now:
            return times[i]
    return None

def calcular_eventos_sol(fecha):
    # ORTO y OCASO con ASTRAL (realista con refracción)
    datos_solar = sun(observer=ASTRAL_LOCATION.observer, date=fecha, tzinfo=TIMEZONE)
    orto = datos_solar['sunrise'].strftime("%H:%M:00")
    ocaso = datos_solar['sunset'].strftime("%H:%M:00")

    # NOCHE ASTRONÓMICA con SKYFIELD
    dt_local_start = TIMEZONE.localize(datetime(fecha.year, fecha.month, fecha.day, 12, 0))
    dt_local_end = dt_local_start + timedelta(hours=24)
    dt_utc_start = dt_local_start.astimezone(pytz.utc)
    dt_utc_end = dt_local_end.astimezone(pytz.utc)

    current = dt_utc_start
    times = []
    while current <= dt_utc_end:
        times.append(ts.utc(current.year, current.month, current.day, current.hour, current.minute))
        current += timedelta(minutes=STEP_MINUTES)

    alturas = []
    for t in times:
        alt, _, _ = (earth + SKYFIELD_LOCATION).at(t).observe(sun_skyfield).apparent().altaz()
        alturas.append(alt.degrees)

    inicio_noche = encontrar_cruce_altura(times, alturas, -18, 'bajar')
    fin_noche = encontrar_cruce_altura(times, alturas, -18, 'subir')

    def format_time(t):
        return t.utc_datetime().astimezone(TIMEZONE).strftime("%H:%M:00") #if t else "No disponible"

    return {
        "fecha_utc": fecha.strftime("%Y-%m-%d"),
        "inicio_noche_astro": format_time(inicio_noche),
        "fin_noche_astro": format_time(fin_noche),
        "orto": orto,
        "ocaso": ocaso
    }

# Cálculo diario
resultados = []
fecha = start_date
while fecha < end_date:
    eventos = calcular_eventos_sol(fecha)
    resultados.append(eventos)
    fecha += timedelta(days=1)

# Guardar en CSV
with open("eventos_solares.csv", mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["fecha_utc", "inicio_noche_astro", "fin_noche_astro", "orto", "ocaso"])
    writer.writeheader()
    writer.writerows(resultados)

print("✅ Archivo generado: eventos_solares.csv")


