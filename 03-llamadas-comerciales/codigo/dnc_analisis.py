"""
Caso de estudio 3 (propio) - Google Data Analytics
Cliente: compañía de telecomunicaciones en Chile que quiere reducir los reclamos por llamadas comerciales.
Datos: FTC "Do Not Call - Reported Calls Data" (EE.UU.), reclamos del 14 sep al 5 oct 2026.
Uso: python dnc_analisis.py <carpeta_csv> <carpeta_salida>
"""
import sys, os, glob, json
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "raw"
out = sys.argv[2] if len(sys.argv) > 2 else "out"
os.makedirs(out, exist_ok=True)
R = {"limpieza": {}}
L = R["limpieza"]

# ---------------- PREPARAR ----------------
fs = sorted(glob.glob(os.path.join(src, "*.csv")))
d = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True)
L["archivos"] = len(fs); L["filas_originales"] = len(d)

# ---------------- PROCESAR ----------------
n = len(d); d = d.drop_duplicates(); L["duplicados_quitados"] = n - len(d)
d["reclamo"] = pd.to_datetime(d["Created_Date"], errors="coerce")
d["llamada"] = pd.to_datetime(d["Violation_Date"], errors="coerce")
n = len(d); d = d.dropna(subset=["reclamo", "llamada"]); L["fechas_ilegibles_quitadas"] = n - len(d)
n = len(d); d = d[d["llamada"] <= d["reclamo"]]; L["llamada_posterior_al_reclamo_quitadas"] = n - len(d)
n = len(d); d = d[d["llamada"] >= "2026-09-01"]; L["llamadas_antes_1_sep_quitadas"] = n - len(d)
L["filas_finales"] = len(d)

# marcas (no se borran): hora desconocida, número inválido, sin dato de robocall
d["hora_conocida"] = d["llamada"].dt.strftime("%H:%M:%S") != "00:00:00"
d["numero"] = d["Company_Phone_Number"].fillna("").str.replace(r"\D", "", regex=True)
d["numero_valido"] = d["numero"].str.len() == 10
d["robocall"] = d["Recorded_Message_Or_Robocall"].map({"Y": "Automatizada", "N": "Con persona"}).fillna("Sin dato")
L["pct_hora_desconocida"] = round((~d["hora_conocida"]).mean() * 100, 1)
L["pct_numero_invalido_o_vacio"] = round((~d["numero_valido"]).mean() * 100, 1)
L["pct_robocall_sin_dato"] = round((d["robocall"] == "Sin dato").mean() * 100, 1)

temas = {
    "Other": "Otro", "Reducing your debt (credit cards, mortgage, student loans)": "Reducir deudas",
    "Calls pretending to be government, businesses, or family and friends": "Suplantación (gobierno, empresas, familia)",
    "Dropped call or no message": "Llamada cortada o sin mensaje", "No Subject Provided": "Sin tema",
    "Medical  & prescriptions": "Salud y medicamentos", "Warranties  & protection plans": "Garantías y seguros",
    "Home improvement  & cleaning": "Mejoras del hogar", "Lotteries, prizes  & sweepstakes": "Premios y sorteos",
    "Vacation  & timeshares": "Vacaciones y tiempo compartido", "Energy, solar,  & utilities": "Energía y servicios",
    "Computer  & technical support": "Soporte técnico", "Work from home  & other ways to make money": "Trabajo desde casa",
    "Home security  & alarms": "Seguridad y alarmas", "Charities": "Beneficencia"}
d["tema"] = d["Subject"].map(temas).fillna(d["Subject"])
regiones = {"Noreste": ["Connecticut", "Maine", "Massachusetts", "New Hampshire", "Rhode Island", "Vermont", "New Jersey", "New York", "Pennsylvania"],
            "Medio Oeste": ["Illinois", "Indiana", "Michigan", "Ohio", "Wisconsin", "Iowa", "Kansas", "Minnesota", "Missouri", "Nebraska", "North Dakota", "South Dakota"],
            "Sur": ["Delaware", "Florida", "Georgia", "Maryland", "North Carolina", "South Carolina", "Virginia", "District of Columbia", "West Virginia", "Alabama", "Kentucky", "Mississippi", "Tennessee", "Arkansas", "Louisiana", "Oklahoma", "Texas"],
            "Oeste": ["Arizona", "Colorado", "Idaho", "Montana", "Nevada", "New Mexico", "Utah", "Wyoming", "Alaska", "California", "Hawaii", "Oregon", "Washington"]}
est2reg = {e: r for r, es in regiones.items() for e in es}
d["region"] = d["Consumer_State"].map(est2reg).fillna("Otro / sin dato")
dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
d["dia"] = d["llamada"].dt.dayofweek.map(lambda i: dias[i])
d["hora"] = d["llamada"].dt.hour
d.to_csv(os.path.join(out, "dnc_limpio.csv"), index=False)

# ---------------- ANALIZAR / SEGMENTAR ----------------
A = R["analisis"] = {}
N = len(d)
# 1. Tipo de llamada
A["pct_tipo_llamada"] = (d["robocall"].value_counts(normalize=True) * 100).round(1).to_dict()
# 2. Temas
t = d.groupby("tema").agg(reclamos=("tema", "size"), pct_auto=("robocall", lambda s: round((s == "Automatizada").mean() * 100, 1)))
t["pct"] = (t["reclamos"] / N * 100).round(1)
t = t.sort_values("reclamos", ascending=False); t.to_csv(os.path.join(out, "seg_tema.csv"))
A["temas_top5"] = t.head(5).to_dict("index")
# 3. Día y hora (solo filas con hora real)
dd = d.groupby("dia").size().reindex(dias); dd.to_csv(os.path.join(out, "seg_dia.csv"))
A["pct_llamadas_fin_de_semana"] = round(d["dia"].isin(["Sábado", "Domingo"]).mean() * 100, 1)
hh = d[d["hora_conocida"]].groupby("hora").size(); hh.to_csv(os.path.join(out, "seg_hora.csv"))
A["pct_llamadas_9_a_17h"] = round(hh.loc[9:16].sum() / hh.sum() * 100, 1)
A["pct_llamadas_antes_8_o_despues_21h"] = round((hh.loc[0:7].sum() + hh.loc[21:23].sum()) / hh.sum() * 100, 1)
A["hora_pico"] = int(hh.idxmax())
# 4. Segmentación de números según cuántos reclamos acumulan
v = d[d["numero_valido"]]
cnt = v.groupby("numero").size()
seg = pd.cut(cnt, [0, 1, 4, 19, 1e9], labels=["1 reclamo", "2 a 4", "5 a 19", "20 o más"])
sn = pd.DataFrame({"numeros": seg.value_counts().sort_index(),
                   "reclamos": cnt.groupby(seg, observed=False).sum()})
sn["pct_numeros"] = (sn["numeros"] / sn["numeros"].sum() * 100).round(1)
sn["pct_reclamos"] = (sn["reclamos"] / sn["reclamos"].sum() * 100).round(1)
sn.to_csv(os.path.join(out, "seg_numeros.csv"))
A["segmento_numeros"] = sn.to_dict("index")
A["top10_numeros"] = cnt.sort_values(ascending=False).head(10).to_dict()
# 5. Intervalo entre reclamos del mismo número (hipótesis: llaman a diario respetando un tiempo mínimo)
rep = v[v["numero"].isin(cnt[cnt >= 5].index) & v["hora_conocida"]].sort_values(["numero", "llamada"])
gap = rep.groupby("numero")["llamada"].diff().dt.total_seconds() / 3600
gap = gap.dropna()
A["intervalo_horas_mediana_numeros_5mas"] = round(gap.median(), 1)
A["pct_intervalos_menos_1h"] = round((gap < 1).mean() * 100, 1)
A["pct_intervalos_menos_24h"] = round((gap < 24).mean() * 100, 1)
dias_activos = rep.groupby("numero")["llamada"].apply(lambda s: s.dt.normalize().nunique())
A["dias_activos_mediana_numeros_5mas"] = float(dias_activos.median())
# 6. Tipo de llamada en números repetidos vs únicos
v2 = v.assign(seg=v["numero"].map(seg))
A["pct_auto_por_segmento"] = v2.groupby("seg", observed=False)["robocall"].apply(lambda s: round((s == "Automatizada").mean() * 100, 1)).to_dict()
# 7. Región
rg = d.groupby("region").size().sort_values(ascending=False); rg.to_csv(os.path.join(out, "seg_region.csv"))
A["pct_region"] = (rg / N * 100).round(1).to_dict()
A["top5_estados"] = d["Consumer_State"].value_counts().head(5).to_dict()
# 8. Tiempo entre la llamada y el reclamo
lag = (d["reclamo"] - d["llamada"]).dt.total_seconds() / 86400
A["pct_reclamo_mismo_dia_o_siguiente"] = round((lag < 2).mean() * 100, 1)

json.dump(R, open(os.path.join(out, "resumen.json"), "w"), ensure_ascii=False, indent=2, default=str)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
