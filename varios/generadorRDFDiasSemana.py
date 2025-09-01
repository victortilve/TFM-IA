from datetime import datetime, timedelta

wikidata_dias = {
    0: "Q105",  # Monday
    1: "Q127",
    2: "Q128",
    3: "Q129",
    4: "Q130",
    5: "Q131",  # Saturday
    6: "Q132"   # Sunday
}

def generar_grafo_wikidata(inicio, fin, salida="dias_con_qcodes.ttl"):
    ttl = """@prefix ex: <http://example.org#> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> .
@prefix schema: <http://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

"""

    actual = inicio
    while actual <= fin:
        fecha_str = actual.strftime('%Y-%m-%d')
        uri = f"ex:dia_{fecha_str.replace('-', '_')}"
        q_dia = wikidata_dias[actual.weekday()]
        q_categoria = "Q211391" if actual.weekday() >= 5 else "Q12779928"  # weekend / business day

        ttl += f"""{uri} a wd:Q573 ;
    schema:date "{fecha_str}"^^xsd:date ;
    schema:dayOfWeek wd:{q_dia} ;
    wdt:P361 wd:{q_categoria} .

"""

        actual += timedelta(days=1)

    with open(salida, "w", encoding="utf-8") as f:
        f.write(ttl)

    print(f"Grafo RDF guardado en: {salida}")

# Uso
generar_grafo_wikidata(datetime(2022, 9, 1), datetime(2025, 7, 30))
