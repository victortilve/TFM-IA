import yaml
from geopy.distance import distance
import math
from shapely.geometry import Polygon

# === CONFIGURACIÓN MANUAL ===
lat_inicial = 42.76450314348505
lon_inicial = -8.037108046555051
num_centroides = 20
radio_km = 50  # este será también la distancia entre centroides tangentes
fecha_inicio = "2023-09-01"
fecha_fin = "2025-07-01"

# === FUNCIONES ===

def generar_cuadricula_tangente(centro_lat, centro_lon, radio_km, total_centroides):
    #Una cuadrícula tiene área lado*lado, entonces para repartir
    #los centroides en una necesito hacer la raíz para saber cuántos
    #deben ir en cada lado
    lado = int(total_centroides**0.5)
    #Si tengo 10 centroides entonces 3x3=9 (3=int(sqrt(10)))se queda corto
    #para completar la cuadrícula. Genero 4x4=16 y cojo los 10 primeros
    if lado * lado < total_centroides:
        lado += 1
    
    #Con lo siguiente se centra la cuadrícula en el punto inicial
    centroides = []
    offset_lat = lado // 2
    offset_lon = lado // 2

    for i in range(lado):
        for j in range(lado):
            if len(centroides) >= total_centroides:
                break
            desplazamiento_ns = (i - offset_lat) * radio_km * 2**(-0.5) * 2 
            desplazamiento_ew = (j - offset_lon) * radio_km * 2**(-0.5) * 2 

            destino = distance(kilometers=desplazamiento_ns).destination((centro_lat, centro_lon), bearing=0) #bearing = Norte
            destino = distance(kilometers=desplazamiento_ew).destination((destino.latitude, destino.longitude), bearing=90) #bearing=Este

            centroides.append((
                round(destino.latitude, 6), #el 6 es el número de decimales
                round(destino.longitude, 6)
            ))

    return centroides

def generar_cuadrado(lat, lon, radio_km):
    """
    Devuelve los 4 vértices de un cuadrado centrado en (lat, lon)
    """
    esquinas = []
    for bearing in [45, 135, 225, 315]:  # NE, SE, SW, NW
        punto = distance(kilometers=radio_km).destination((lat, lon), bearing=bearing)
        esquinas.append((round(punto.longitude, 6), round(punto.latitude, 6)))
    return esquinas

# === GENERACIÓN DE CENTROIDES ===
coords = generar_cuadricula_tangente(lat_inicial, lon_inicial, radio_km, num_centroides)

centroides_yaml = {
    "fecha_inicio": fecha_inicio,
    "fecha_fin": fecha_fin,
    "centroides": []
}

for lat, lon in coords:
    nombre = f"Luna_{round(lat, 4)}_{round(lon, 4)}"
    vertices = generar_cuadrado(lat, lon, radio_km)
    vertices.append(vertices[0])  # cerrar el polígono
    wkt = f"POLYGON(({', '.join(f'{x} {y}' for x, y in vertices)}))"
    
    centroides_yaml["centroides"].append({
        "nombre": nombre,
        "latitud": lat,
        "longitud": lon,
        "radio_km": radio_km,
        "wkt": wkt
    })
# === GUARDAR YAML ===
with open("centroidesAutomaticos.yaml", "w", encoding="utf-8") as f:
    yaml.dump(centroides_yaml, f, allow_unicode=True)

print("✅ Archivo 'centroidesAutomaticos.yaml' generado con", len(coords), "centroides.")
