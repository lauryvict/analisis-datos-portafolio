"""
Caso de estudio Bellabeat - Google Data Analytics (Capstone, vía A, caso 2)
Datos: FitBit Fitness Tracker Data (Mobius, Kaggle, CC0).
Uso: python bellabeat_analisis.py <carpeta_fitbit> <carpeta_salida> <sleep_health.csv> <gym_members_exercise_tracking.csv>

Análisis:
  0. General: tendencias de uso de dispositivos inteligentes
  1. App de Bellabeat: adopción de funciones (actividad, sueño, peso)
  2. Leaf: actividad, pasos y sedentarismo
  3. Time: uso continuo (24 h) y sueño
  4. Spring: horas de mayor actividad (cuándo recordar hidratarse) - sin datos de agua
  5. Membresía: segmentos de usuarios para guía personalizada
"""
import sys, os, json, glob
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "raw"
out = sys.argv[2] if len(sys.argv) > 2 else "out"
os.makedirs(out, exist_ok=True)
R = {"limpieza": {}, "general": {}, "app": {}, "leaf": {}, "time": {}, "spring": {}, "membresia": {}}
L = R["limpieza"]


def leer(nombre):
    """Lee todas las copias de un archivo (el zip trae dos períodos) y las une."""
    rutas = sorted(glob.glob(os.path.join(src, "**", nombre), recursive=True))
    if not rutas:
        return None
    df = pd.concat([pd.read_csv(r) for r in rutas], ignore_index=True)
    L[f"filas_{nombre}"] = len(df)
    L[f"archivos_{nombre}"] = len(rutas)
    return df


# ---------------- PREPARAR / PROCESAR ----------------
daily = leer("dailyActivity_merged.csv")
sleep = leer("sleepDay_merged.csv")
hourly = leer("hourlySteps_merged.csv")
weight = leer("weightLogInfo_merged.csv")
if daily is None:
    sys.exit("No encontré dailyActivity_merged.csv")

daily["fecha"] = pd.to_datetime(daily["ActivityDate"], format="%m/%d/%Y")
n = len(daily); daily = daily.drop_duplicates(subset=["Id", "fecha"], keep="last")
L["daily_duplicados_quitados"] = n - len(daily)
daily["min_registrados"] = daily[["VeryActiveMinutes", "FairlyActiveMinutes",
                                  "LightlyActiveMinutes", "SedentaryMinutes"]].sum(axis=1)
# días sin uso: 0 pasos y 1440 min sedentarios (dispositivo encendido pero no usado)
n = len(daily)
daily = daily[~((daily["TotalSteps"] == 0) & (daily["SedentaryMinutes"] >= 1440))]
L["daily_dias_sin_uso_quitados"] = n - len(daily)
L["usuarios"] = int(daily["Id"].nunique())
L["periodo"] = f"{daily['fecha'].min().date()} a {daily['fecha'].max().date()}"
L["dias_usuario_finales"] = len(daily)

if sleep is not None:
    sleep["fecha"] = pd.to_datetime(sleep["SleepDay"], format="%m/%d/%Y %I:%M:%S %p").dt.normalize()
    n = len(sleep); sleep = sleep.drop_duplicates(subset=["Id", "fecha"], keep="last")
    L["sleep_duplicados_quitados"] = n - len(sleep)
if hourly is not None:
    hourly["dt"] = pd.to_datetime(hourly["ActivityHour"], format="%m/%d/%Y %I:%M:%S %p")
    n = len(hourly); hourly = hourly.drop_duplicates(subset=["Id", "dt"], keep="last")
    L["hourly_duplicados_quitados"] = n - len(hourly)
if weight is not None:
    weight["fecha"] = pd.to_datetime(weight["Date"], format="%m/%d/%Y %I:%M:%S %p").dt.normalize()
    n = len(weight); weight = weight.drop_duplicates(subset=["Id", "fecha"], keep="last")
    L["weight_duplicados_quitados"] = n - len(weight)

dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
daily["dia"] = daily["fecha"].dt.dayofweek.map(lambda i: dias[i])

# ---------------- 0. GENERAL ----------------
G = R["general"]
G["pasos_promedio_dia"] = round(daily["TotalSteps"].mean())
G["pct_dias_10000_pasos"] = round((daily["TotalSteps"] >= 10000).mean() * 100, 1)
G["pct_dias_7500_pasos"] = round((daily["TotalSteps"] >= 7500).mean() * 100, 1)
tot = daily[["VeryActiveMinutes", "FairlyActiveMinutes", "LightlyActiveMinutes", "SedentaryMinutes"]].sum()
G["pct_minutos_por_intensidad"] = (tot / tot.sum() * 100).round(1).to_dict()
G["horas_sedentarias_promedio"] = round(daily["SedentaryMinutes"].mean() / 60, 1)
G["corr_pasos_calorias"] = round(daily["TotalSteps"].corr(daily["Calories"]), 2)
pdia = daily.groupby("dia")["TotalSteps"].mean().reindex(dias).round()
pdia.to_csv(os.path.join(out, "pasos_por_dia.csv"))
G["dia_mas_pasos"] = pdia.idxmax(); G["dia_menos_pasos"] = pdia.idxmin()
if hourly is not None:
    phora = hourly.groupby(hourly["dt"].dt.hour)["StepTotal"].mean().round()
    phora.to_csv(os.path.join(out, "pasos_por_hora.csv"))
    G["horas_pico_pasos"] = phora.sort_values(ascending=False).head(3).index.tolist()

# ---------------- 1. APP: adopción de funciones ----------------
# Se mide en el período 12 abr - 12 may 2016, el único que trae todos los archivos (incluido sueño diario).
A = R["app"]
p2 = daily[daily["fecha"] >= "2016-04-12"]
u = int(p2["Id"].nunique())
A["periodo_adopcion"] = f"{p2['fecha'].min().date()} a {p2['fecha'].max().date()}"
A["usuarios_actividad"] = u
s2 = sleep if sleep is not None else pd.DataFrame(columns=["Id", "fecha"])
w2 = weight[weight["fecha"] >= "2016-04-12"] if weight is not None else pd.DataFrame(columns=["Id"])
A["usuarios_sueno"] = int(s2["Id"].nunique())
A["usuarios_peso"] = int(w2["Id"].nunique())
A["pct_registra_sueno"] = round(A["usuarios_sueno"] / u * 100, 1)
A["pct_registra_peso"] = round(A["usuarios_peso"] / u * 100, 1)
if weight is not None:
    A["pct_registros_peso_manuales"] = round(weight["IsManualReport"].astype(str).str.lower().eq("true").mean() * 100, 1)
total_dias = (p2["fecha"].max() - p2["fecha"].min()).days + 1
A["dias_periodo"] = total_dias
dias_por_usuario = p2.groupby("Id")["fecha"].nunique()
seg = pd.cut(dias_por_usuario, bins=[0, 10, 20, 31], labels=["Bajo (1–10 días)", "Medio (11–20 días)", "Alto (21–31 días)"])
A["usuarios_por_nivel_de_uso"] = seg.value_counts().reindex(seg.cat.categories[::-1]).to_dict()
noches = s2.groupby("Id")["fecha"].nunique() if len(s2) else pd.Series(dtype=float)
A["noches_registradas_mediana_por_usuario"] = float(noches.median()) if len(noches) else 0
pd.DataFrame({"usuarios": [A["usuarios_actividad"], A["usuarios_sueno"], A["usuarios_peso"]]},
             index=["Actividad", "Sueño", "Peso"]).to_csv(os.path.join(out, "adopcion_funciones.csv"))

# ---------------- 2. LEAF: actividad ----------------
Lf = R["leaf"]
cat = pd.cut(daily["TotalSteps"], bins=[-1, 4999, 7499, 9999, 12499, 1e9],
             labels=["Sedentario (<5.000)", "Poco activo (5.000–7.499)", "Algo activo (7.500–9.999)",
                     "Activo (10.000–12.499)", "Muy activo (12.500+)"])
Lf["pct_dias_por_nivel"] = (cat.value_counts(normalize=True) * 100).round(1).reindex(cat.cat.categories).to_dict()
Lf["min_muy_activos_promedio"] = round(daily["VeryActiveMinutes"].mean(), 1)
Lf["min_activos_semana_promedio"] = round((daily["VeryActiveMinutes"] + daily["FairlyActiveMinutes"]).mean() * 7)
Lf["pct_dias_150min_semana_equivalente"] = round(((daily["VeryActiveMinutes"] + daily["FairlyActiveMinutes"]) >= 150 / 7).mean() * 100, 1)
pd.Series(Lf["pct_dias_por_nivel"]).to_csv(os.path.join(out, "dias_por_nivel_pasos.csv"))

# ---------------- 3. TIME: uso continuo y sueño ----------------
T = R["time"]
T["pct_dias_24h_registradas"] = round((daily["min_registrados"] >= 1440).mean() * 100, 1)
T["horas_registradas_promedio"] = round(daily["min_registrados"].mean() / 60, 1)
if sleep is not None:
    T["horas_sueno_promedio"] = round(sleep["TotalMinutesAsleep"].mean() / 60, 1)
    T["pct_noches_menos_7h"] = round((sleep["TotalMinutesAsleep"] < 420).mean() * 100, 1)
    T["min_en_cama_sin_dormir_promedio"] = round((sleep["TotalTimeInBed"] - sleep["TotalMinutesAsleep"]).mean())
    ds = daily.merge(sleep, on=["Id", "fecha"], how="inner")
    T["dias_con_actividad_y_sueno"] = len(ds)
    T["pasos_dia_con_sueno_7h_o_mas"] = round(ds.loc[ds["TotalMinutesAsleep"] >= 420, "TotalSteps"].mean())
    T["pasos_dia_con_sueno_menos_7h"] = round(ds.loc[ds["TotalMinutesAsleep"] < 420, "TotalSteps"].mean())
    rango = pd.cut(sleep["TotalMinutesAsleep"] / 60, bins=[0, 5, 6, 7, 8, 9, 24],
                   labels=["<5 h", "5–6 h", "6–7 h", "7–8 h", "8–9 h", "9 h+"])
    (rango.value_counts(normalize=True) * 100).round(1).reindex(rango.cat.categories).to_csv(
        os.path.join(out, "noches_por_horas_sueno.csv"))

# ---------------- 4. SPRING: cuándo recordar hidratarse ----------------
S = R["spring"]
S["nota"] = "Los datos no incluyen consumo de agua; se usan las horas de más actividad como momentos de recordatorio."
if hourly is not None:
    S["horas_mas_activas"] = G["horas_pico_pasos"]
S["calorias_promedio_dia"] = round(daily["Calories"].mean())

# ---------------- 5. MEMBRESÍA: segmentos ----------------
M = R["membresia"]
por_usuario = daily.groupby("Id").agg(pasos=("TotalSteps", "mean"), sed=("SedentaryMinutes", "mean"))
seg_u = pd.cut(por_usuario["pasos"], bins=[-1, 4999, 7499, 9999, 1e9],
               labels=["Sedentaria", "Poco activa", "Algo activa", "Activa"])
M["usuarios_por_segmento"] = seg_u.value_counts().reindex(seg_u.cat.categories).to_dict()
if sleep is not None:
    s_u = sleep.groupby("Id")["TotalMinutesAsleep"].mean()
    M["usuarios_sueno_promedio_menos_7h"] = int((s_u < 420).sum())
M["usuarios_uso_bajo_o_medio"] = int(sum(v for k, v in A["usuarios_por_nivel_de_uso"].items() if not k.startswith("Alto")))
pd.Series(M["usuarios_por_segmento"]).to_csv(os.path.join(out, "usuarios_por_segmento.csv"))

json.dump(R, open(os.path.join(out, "resumen.json"), "w"), ensure_ascii=False, indent=2, default=str)
print(json.dumps(R, ensure_ascii=False, indent=2, default=str))


# =====================================================================
# 6. FITBIT - ANÁLISIS ADICIONALES (todos los archivos)
#    sueño por minuto de ambos períodos, fin de semana, hora de dormir,
#    frecuencia cardíaca, perfil horario e índice de masa corporal
# =====================================================================
X = R["fitbit_extra"] = {}
ms = leer("minuteSleep_merged.csv")
if ms is not None:
    ms["dt"] = pd.to_datetime(ms["date"], format="%m/%d/%Y %I:%M:%S %p")
    ms = ms.drop_duplicates(["Id", "dt"])
    ses = ms.groupby(["Id", "logId"]).agg(ini=("dt", "min"), fin=("dt", "max"),
                                          dormido=("value", lambda v: (v == 1).sum()))
    ses["fecha"] = ses["fin"].dt.normalize()
    noc = ses.groupby(["Id", "fecha"]).agg(dormido=("dormido", "sum"), ini=("ini", "min")).reset_index()
    noc = noc[noc["dormido"] >= 60]          # se descartan siestas o registros < 1 hora
    X["sueno_usuarios"] = int(noc["Id"].nunique()); X["sueno_noches"] = len(noc)
    X["sueno_horas_promedio"] = round(noc["dormido"].mean() / 60, 2)
    X["pct_noches_menos_7h"] = round((noc["dormido"] < 420).mean() * 100, 1)
    noc["fds"] = noc["fecha"].dt.dayofweek >= 5
    X["sueno_horas_semana_vs_fds"] = (noc.groupby("fds")["dormido"].mean() / 60).round(2).rename({False: "semana", True: "fin_de_semana"}).to_dict()
    h = noc["ini"].dt.hour + noc["ini"].dt.minute / 60
    h = h.where(h > 12, h + 24)
    X["hora_mediana_dormirse"] = round(h.median() % 24, 2)
daily["fds"] = daily["fecha"].dt.dayofweek >= 5
X["pasos_semana_vs_fds"] = daily.groupby("fds")["TotalSteps"].mean().round().rename({False: "semana", True: "fin_de_semana"}).to_dict()
hr = leer("heartrate_seconds_merged.csv")
if hr is not None:
    X["usuarios_con_pulso"] = int(hr["Id"].nunique())
    X["pct_usuarios_con_pulso"] = round(hr["Id"].nunique() / daily["Id"].nunique() * 100, 1)
if hourly is not None:
    hs = hourly[hourly["StepTotal"] > 0].copy(); hs["h"] = hs["dt"].dt.hour
    centro = hs.groupby("Id").apply(lambda g: (g["h"] * g["StepTotal"]).sum() / g["StepTotal"].sum())
    X["perfil_horario"] = {"mañana (antes de 13 h)": int((centro < 13).sum()),
                           "mediodía (13 a 15 h)": int(((centro >= 13) & (centro < 15)).sum()),
                           "tarde (15 h o después)": int((centro >= 15).sum())}
if weight is not None:
    imc = weight.groupby("Id")["BMI"].mean()
    X["imc_usuarios"] = pd.cut(imc, [0, 18.5, 25, 30, 99], labels=["bajo", "normal", "sobrepeso", "obesidad"]).value_counts().to_dict()

# =====================================================================
# 7. MUJERES Y HOMBRES - Sleep Health and Lifestyle Dataset (Kaggle)
#    Uso: python bellabeat_analisis.py raw out <sleep_health.csv> <gym.csv>
#    OJO: 242 de 374 filas se repiten y las mujeres son ~10 años mayores.
# =====================================================================
if len(sys.argv) > 3:
    Z = R["sexo_sueno_estres"] = {}
    s = pd.read_csv(sys.argv[3], keep_default_na=False)   # "None" = sin trastorno, no es un vacío
    s["BMI Category"] = s["BMI Category"].replace({"Normal Weight": "Normal"})  # categoría duplicada
    Z["filas"] = len(s); Z["filas_repetidas_sin_id"] = int(s.drop(columns="Person ID").duplicated().sum())
    Z["personas_por_sexo"] = s["Gender"].value_counts().to_dict()
    Z["edad_promedio_por_sexo"] = s.groupby("Gender")["Age"].mean().round(1).to_dict()
    Z["promedios_por_sexo"] = s.groupby("Gender").agg(
        horas_sueno=("Sleep Duration", "mean"), calidad_sueno=("Quality of Sleep", "mean"),
        estres=("Stress Level", "mean"), pasos=("Daily Steps", "mean")).round(2).to_dict("index")
    Z["pct_trastorno_sueno"] = (pd.crosstab(s["Gender"], s["Sleep Disorder"], normalize="index") * 100).round(1).to_dict("index")
    Z["pct_imc"] = (pd.crosstab(s["Gender"], s["BMI Category"], normalize="index") * 100).round(1).to_dict("index")
    s["edad"] = pd.cut(s["Age"], [0, 39, 49, 99], labels=["Menos de 40", "40 a 49", "50 o más"])
    t = s.groupby(["edad", "Gender"], observed=True).agg(n=("Age", "size"), horas_sueno=("Sleep Duration", "mean"),
                                                        calidad=("Quality of Sleep", "mean"), estres=("Stress Level", "mean")).round(2)
    t.to_csv(os.path.join(out, "sueno_estres_por_edad_y_sexo.csv"))
    Z["sueno_por_nivel_estres"] = s.groupby("Stress Level")[["Sleep Duration", "Quality of Sleep"]].mean().round(2).to_dict("index")
    Z["corr_estres_horas_sueno"] = round(s["Stress Level"].corr(s["Sleep Duration"]), 2)
    Z["corr_estres_calidad_sueno"] = round(s["Stress Level"].corr(s["Quality of Sleep"]), 2)

# =====================================================================
# 8. AGUA Y EJERCICIO - Gym Members Exercise Dataset (Kaggle)
#    OJO: el agua de mujeres nunca pasa de 2,7 L y la de hombres va de 2,0 a 3,7 L:
#    patrón de datos generados por reglas (probablemente simulados).
# =====================================================================
if len(sys.argv) > 4:
    W = R["agua_ejercicio"] = {}
    g = pd.read_csv(sys.argv[4])
    W["filas"] = len(g); W["duplicados"] = int(g.duplicated().sum())
    W["personas_por_sexo"] = g["Gender"].value_counts().to_dict()
    W["agua_litros_por_sexo"] = g.groupby("Gender")["Water_Intake (liters)"].agg(["mean", "min", "max"]).round(2).to_dict("index")
    W["frecuencia_dias_semana_por_sexo"] = g.groupby("Gender")["Workout_Frequency (days/week)"].mean().round(2).to_dict()
    a = g.pivot_table(index="Workout_Frequency (days/week)", columns="Gender", values="Water_Intake (liters)", aggfunc="mean").round(2)
    a.to_csv(os.path.join(out, "agua_por_frecuencia_y_sexo.csv"))
    W["agua_por_frecuencia"] = a.to_dict("index")
    W["pct_tipo_ejercicio_por_sexo"] = (pd.crosstab(g["Gender"], g["Workout_Type"], normalize="index") * 100).round(1).to_dict("index")

json.dump(R, open(os.path.join(out, "resumen.json"), "w"), ensure_ascii=False, indent=2, default=str)
print(json.dumps({k: R[k] for k in R if k in ("fitbit_extra", "sexo_sueno_estres", "agua_ejercicio")}, ensure_ascii=False, indent=1, default=str)[:3500])
