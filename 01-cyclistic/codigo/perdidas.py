"""
Caso de estudio Cyclistic - análisis de viajes de más de 24 horas
(bicicletas que tardan días en volver).
Uso: python perdidas.py <carpeta_con_los_csv>
"""
import os, sys
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "raw"

# Columnas de 2019 renombradas al esquema de 2020
map_2019 = {"trip_id": "ride_id", "start_time": "started_at", "end_time": "ended_at",
            "from_station_name": "start_station_name", "to_station_name": "end_station_name",
            "usertype": "member_casual"}
map_q2 = {"01 - Rental Details Rental ID": "ride_id",
          "01 - Rental Details Local Start Time": "started_at",
          "01 - Rental Details Local End Time": "ended_at",
          "03 - Rental Start Station Name": "start_station_name",
          "02 - Rental End Station Name": "end_station_name",
          "User Type": "member_casual"}
cols = ["ride_id", "started_at", "ended_at", "start_station_name", "end_station_name", "member_casual"]
archivos = [("Divvy_Trips_2019_Q2.csv", map_q2), ("Divvy_Trips_2019_Q3.csv", map_2019),
            ("Divvy_Trips_2019_Q4.csv", map_2019), ("Divvy_Trips_2020_Q1.csv", None)]

partes = []
for nombre, mapa in archivos:
    d = pd.read_csv(os.path.join(src, nombre), dtype=str)
    if mapa:
        d = d.rename(columns=mapa)
    partes.append(d[cols])
d = pd.concat(partes, ignore_index=True)
d["member_casual"] = d["member_casual"].replace({"Subscriber": "member", "Customer": "casual"})

# Duración en horas; se quita la estación de pruebas HQ QR
d["inicio"] = pd.to_datetime(d.started_at)
d["fin"] = pd.to_datetime(d.ended_at)
d["horas"] = (d.fin - d.inicio).dt.total_seconds() / 3600
d = d[d.start_station_name != "HQ QR"]
total = d.groupby("member_casual").size()

largos = d[d.horas > 24]
g = largos.groupby("member_casual")
print("Viajes de más de 24 h:", len(largos))
print("Por tipo de usuario (%):\n", (g.size() / len(largos) * 100).round(1))
tasa = g.size() / total * 10000
print("Por cada 10.000 viajes:\n", tasa.round(1))
print("Ocasionales vs. socios (veces):", round(tasa["casual"] / tasa["member"], 1))

rangos = pd.cut(largos.horas, bins=[24, 48, 24 * 7, 24 * 30, 1e9],
                labels=["1-2 días", "2-7 días", "7-30 días", "más de 30 días"])
print(pd.crosstab(rangos, largos.member_casual))
print("Sin estación de término:", largos.end_station_name.isna().sum())
