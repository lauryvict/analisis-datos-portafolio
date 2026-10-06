"""
Caso de estudio Cyclistic – Google Data Analytics (Capstone, vía A)
Período: abril 2019 – marzo 2020 (Divvy 2019 T2, T3, T4 y 2020 T1)
Uso: python cyclistic_analisis.py <carpeta_con_los_csv> <carpeta_salida>
"""
import sys, json, os
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "raw"
out = sys.argv[2] if len(sys.argv) > 2 else "out"
os.makedirs(out, exist_ok=True)
log = {}

# ---------- PREPARAR: leer y estandarizar al esquema 2020 ----------
map_2019 = {
    "trip_id": "ride_id", "start_time": "started_at", "end_time": "ended_at",
    "from_station_id": "start_station_id", "from_station_name": "start_station_name",
    "to_station_id": "end_station_id", "to_station_name": "end_station_name",
    "usertype": "member_casual",
}
map_q2 = {
    "01 - Rental Details Rental ID": "ride_id",
    "01 - Rental Details Local Start Time": "started_at",
    "01 - Rental Details Local End Time": "ended_at",
    "03 - Rental Start Station ID": "start_station_id",
    "03 - Rental Start Station Name": "start_station_name",
    "02 - Rental End Station ID": "end_station_id",
    "02 - Rental End Station Name": "end_station_name",
    "User Type": "member_casual",
}
cols = ["ride_id", "started_at", "ended_at", "start_station_id", "start_station_name",
        "end_station_id", "end_station_name", "member_casual"]

frames = []
for fname, m in [("Divvy_Trips_2019_Q2.csv", map_q2), ("Divvy_Trips_2019_Q3.csv", map_2019),
                 ("Divvy_Trips_2019_Q4.csv", map_2019), ("Divvy_Trips_2020_Q1.csv", None)]:
    df = pd.read_csv(os.path.join(src, fname), dtype=str)
    if m:
        df = df.rename(columns=m)
    df = df[cols]
    log[f"filas_{fname}"] = len(df)
    frames.append(df)
d = pd.concat(frames, ignore_index=True)
log["filas_unidas"] = len(d)

# ---------- PROCESAR: limpieza ----------
d["member_casual"] = d["member_casual"].replace({"Subscriber": "member", "Customer": "casual"})
log["valores_member_casual"] = d["member_casual"].value_counts(dropna=False).to_dict()
d["started_at"] = pd.to_datetime(d["started_at"])
d["ended_at"] = pd.to_datetime(d["ended_at"])
d["ride_length_min"] = (d["ended_at"] - d["started_at"]).dt.total_seconds() / 60

n = len(d); d = d.drop_duplicates(subset="ride_id"); log["quitadas_duplicadas"] = n - len(d)
n = len(d); d = d[d["start_station_name"] != "HQ QR"]; log["quitadas_HQ_QR"] = n - len(d)
n = len(d); d = d[d["ride_length_min"] > 0]; log["quitadas_duracion_cero_o_negativa"] = n - len(d)
n = len(d); d = d[d["ride_length_min"] <= 24 * 60]; log["quitadas_mas_de_24h"] = n - len(d)
n = len(d); d = d.dropna(subset=["member_casual", "start_station_name", "end_station_name"])
log["quitadas_sin_tipo_o_estacion"] = n - len(d)
log["filas_finales"] = len(d)

dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
d["dia"] = d["started_at"].dt.dayofweek.map(lambda i: dias[i])
d["hora"] = d["started_at"].dt.hour
d["mes_n"] = d["started_at"].dt.month
d["round_trip"] = d["start_station_name"] == d["end_station_name"]

# ---------- ANALIZAR ----------
res = {}
g = d.groupby("member_casual")
res["viajes"] = g.size().to_dict()
res["pct_viajes"] = (g.size() / len(d) * 100).round(1).to_dict()
res["duracion_media_min"] = g["ride_length_min"].mean().round(1).to_dict()
res["duracion_mediana_min"] = g["ride_length_min"].median().round(1).to_dict()
res["pct_ida_y_vuelta_misma_estacion"] = (g["round_trip"].mean() * 100).round(1).to_dict()
res["pct_fin_de_semana"] = (d.assign(fds=d["dia"].isin(["Sábado", "Domingo"]))
                            .groupby("member_casual")["fds"].mean() * 100).round(1).to_dict()

por_dia = d.pivot_table(index="dia", columns="member_casual", values="ride_id", aggfunc="count").reindex(dias)
dur_dia = d.pivot_table(index="dia", columns="member_casual", values="ride_length_min", aggfunc="median").reindex(dias).round(1)
por_hora = d.pivot_table(index="hora", columns="member_casual", values="ride_id", aggfunc="count")
por_mes = d.pivot_table(index="mes_n", columns="member_casual", values="ride_id", aggfunc="count")
orden_meses = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
por_mes = por_mes.reindex(orden_meses); por_mes.index = [meses[m - 1] for m in orden_meses]

top_cas = d[d.member_casual == "casual"]["start_station_name"].value_counts().head(10)
top_mem = d[d.member_casual == "member"]["start_station_name"].value_counts().head(10)

for name, t in [("viajes_por_dia", por_dia), ("mediana_duracion_por_dia", dur_dia),
                ("viajes_por_hora", por_hora), ("viajes_por_mes", por_mes)]:
    t.to_csv(os.path.join(out, f"{name}.csv"))
top_cas.rename("viajes").to_csv(os.path.join(out, "top10_estaciones_casual.csv"))
top_mem.rename("viajes").to_csv(os.path.join(out, "top10_estaciones_member.csv"))

res["hora_pico"] = {k: int(por_hora[k].idxmax()) for k in por_hora.columns}
res["dia_pico"] = {k: por_dia[k].idxmax() for k in por_dia.columns}
res["mes_pico"] = {k: por_mes[k].idxmax() for k in por_mes.columns}
res["pct_casual_jun_ago"] = round(por_mes.loc[["Jun", "Jul", "Ago"], "casual"].sum() / por_mes["casual"].sum() * 100, 1)
res["pct_member_jun_ago"] = round(por_mes.loc[["Jun", "Jul", "Ago"], "member"].sum() / por_mes["member"].sum() * 100, 1)
res["top3_estaciones_casual"] = top_cas.head(3).to_dict()
res["pct_casual_en_top10_estaciones"] = round(top_cas.sum() / res["viajes"]["casual"] * 100, 1)
res["pct_member_en_top10_estaciones"] = round(top_mem.sum() / res["viajes"]["member"] * 100, 1)

json.dump({"limpieza": log, "resultados": res}, open(os.path.join(out, "resumen.json"), "w"),
          ensure_ascii=False, indent=2, default=str)
print(json.dumps({"limpieza": log, "resultados": res}, ensure_ascii=False, indent=2, default=str))
