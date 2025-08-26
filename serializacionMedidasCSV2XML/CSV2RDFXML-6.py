import pandas as pd
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, XSD
from astral.sun import dusk, dawn
from astral import LocationInfo
import pytz
from datetime import timedelta
import yaml
from astral.sun import sun
import os
from dateutil import parser
from datetime import timedelta, datetime, timezone
import time
import logging

# Configuración básica del log
logging.basicConfig(
    filename="mi_log.log",       # Nombre del archivo donde se guarda
    level=logging.INFO,          # Nivel de registro
    format="%(asctime)s - %(levelname)s - %(message)s"  # Formato del log
)

# === Cargar configuración YAML ===
with open("/media/victor/1FPB-COTARE/Cousas/TFM-IA/TFM-traballo/00.CousasDefinitivas/DatosMeteogalicia/RDF/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# === CARGAR CSV ===
columna_fecha = "Fecha" #"Timestamp" #"Time" #Fecha SQM o Time TESS o Timestamp FreeDSM
columna_valor = "Valor" #"Value" #"mag" # Valor o mag
formato_fecha = '%d/%m/%Y %H:%M' #"%Y-%m-%d %H:%M:%SZ" #'%d/%m/%Y %H:%M'

# === Namespaces RDF
EX = Namespace("http://example.org#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
XSDT = XSD

for caso in config["casos"]:
    csv_path = caso["csv_path"]
    utc_boolean = caso["utc"].upper()
    logging.info(f"utc = {utc_boolean}")
    localidad = caso["localidad"].upper()
    lat = caso["lat"]
    lon = caso["lon"]
    nombre_sensor = caso["nombre_sensor"]
    zona_horaria = caso["zona_horaria"]
    output_path = caso["output_path"]

    # Cargar datos CSV
    df = pd.read_csv(csv_path)
    print(f"✅ CSV cargado: {csv_path}")
    #df[columna_fecha] = pd.to_datetime(df[columna_fecha], format=formato_fecha, utc=True)

    # Zona horaria y localización astronómica
    tz = pytz.timezone(zona_horaria)
    loc = LocationInfo(name=localidad, region="ES", timezone=zona_horaria, latitude=lat, longitude=lon)

    # Crear grafo
    g = Graph()
    g.bind("ex", EX)
    g.bind("sosa", SOSA)
    g.bind("xsd", XSDT)

    sensor_uri = EX[f"{nombre_sensor}_{localidad[:3].upper()}_{lat:.6f}_{lon:.6f}"]

    for _, row in df.iterrows():
        
        if utc_boolean:
            dt_utc_crudo = row[columna_fecha]
            dt_utc_crudo = datetime.strptime(dt_utc_crudo, formato_fecha)
            logging.info(f"dt_utc_crudo = {dt_utc_crudo}")
            #dt_utc = parser.parse(dt_utc)  # convierte str en datetime
            if dt_utc_crudo.tzinfo is None:
                dt_utc = dt_utc_crudo.replace(tzinfo=timezone.utc)
            logging.info(f"dt_utc = {dt_utc}")
            dt_local = dt_utc.astimezone(tz)
            logging.info(f"dt_local = {dt_local}")
        else:
          dt_local = row[columna_fecha]
          dt_local = datetime.strptime(dt_local, formato_fecha)
          if dt_local.tzinfo is None:
            tz = pytz.timezone(zona_horaria)
            dt_local = dt_local.tz_localize(tz, ambiguous=False)  # Por ejemplo, tz = pytz.timezone('Europe/Madrid')
            # ambiguous es para el cambio de hora. En TESS aparecen dos veces la misma hora
            # porque no maneja UTC
            # Opción 1: interpretarlo como horario de verano (antes del cambio)
              #dt_local = dt_local.tz_localize(tz, ambiguous=True)

            # Opción 2: interpretarlo como horario estándar (después del cambio)
              #dt_local = dt_local.tz_localize(tz, ambiguous=False)
          dt_utc = dt_local.astimezone(pytz.UTC)        
        
        #dt_utc = row['Fecha']
        #dt_local = dt_utc.astimezone(tz)
        brillo = row[columna_valor]

        # ~ try:
            # ~ comienza_noche = dusk(observer=loc.observer, date=dt_local.date(), tzinfo=tz, depression=18).astimezone(pytz.utc)
            # ~ termina_noche = dawn(observer=loc.observer, date=dt_local.date() + timedelta(days=1), tzinfo=tz, depression=18).astimezone(pytz.utc)
        # ~ except ValueError as e:
            # ~ print(f"Error en {dt_local} ({localidad}): {e}")
            # ~ continue
            
        s = sun(loc.observer, date=dt_local.date(), tzinfo=tz)
        comienza_noche = s['dusk'].astimezone(pytz.UTC) #s['dusk'] cuando el Sol baja 6° bajo el horizonte (crepúsculo civil)
        termina_noche = s['dawn'].astimezone(pytz.UTC) #s['dawn'] cuando el Sol está a 6º del horizonte subiendo
        #Otra cosa sería puesta_sol = s['sunset']

        es_noche = dt_utc < termina_noche or dt_utc > comienza_noche

        obs_id = f"observacion_{nombre_sensor}_{localidad[:3].upper()}_{lat:.6f}_{lon:.6f}_{dt_utc.strftime('%Y%m%d%H%M%S')}"
        obs_uri = EX[obs_id]

        g.add((obs_uri, RDF.type, SOSA.Observation))
        g.add((obs_uri, SOSA.madeBySensor, sensor_uri))
        logging.info(f"se va a añadir la fecha = {dt_utc.strftime('%Y-%m-%dT%H:%M:%S+00:00')}")
        g.add((obs_uri, SOSA.resultTime, Literal(dt_utc.strftime('%Y-%m-%dT%H:%M:%S+00:00'), datatype=XSD.dateTime)))
        g.add((obs_uri, SOSA.hasSimpleResult, Literal(brillo, datatype=XSD.decimal)))
        g.add((obs_uri, EX.esNocheAstronomica, Literal(str(es_noche).lower(), datatype=XSD.boolean)))

    g.add((sensor_uri, RDF.type, SOSA.Sensor))
    g.add((sensor_uri, EX.lat, Literal(lat, datatype=XSD.decimal)))
    g.add((sensor_uri, EX.lon, Literal(lon, datatype=XSD.decimal)))

    g.serialize(destination=output_path, format="xml")
    print(f"✅ RDF generado para {localidad}: {output_path}")
