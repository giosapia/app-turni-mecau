import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# Impostazioni pagina
st.set_page_config(page_title="Gestione Medici Susa", layout="wide")
st.title("🏥 Calendario Turni MeCAU Susa")

# --- 1. SIDEBAR: ANAGRAFICA (Punto 1 - Congelato con nuovi nomi Jolly) ---
with st.sidebar:
    st.header("👥 Anagrafica Medici")
    lista_strutturati = st.text_area("1. Medici Strutturati", value="Brancaleoni, Desiderio, Pazè, Sapia")
    strutturati = [s.strip() for s in lista_strutturati.split(",") if s.strip()]

    # Aggiunti Vellata e Isidori come richiesto
    lista_jolly = st.text_area("2. Medici Jolly", value="Calasso, Melis, Sabbatino, Marsanic, Bruno, Castelli, Guglielmino, Trupja, Carbone, Dipietro, Di Stefano, Gili, Montebro, Ostuni, Palumbo, Ronco, Valobra, Vanoni, Veglio, Molino, Leoncini, Maurino, Tatarciuc, Sivera, Vellata, Isidori")
    jolly = [j.strip() for j in lista_jolly.split(",") if j.strip()]

    lista_gettonisti = st.text_area("3. Medici Gettonisti", value="Borgiotto, Moshkina, Mascalchi, Garrone, Passoni, Sardo")
    gettonisti = [g.strip() for g in lista_gettonisti.split(",") if g.strip()]

    st.divider()
    
    # --- 2. SIDEBAR: SELEZIONE PERIODO (Punto 2) ---
    st.header("📅 Periodo di Riferimento")
    anno = st.number_input("Anno", min_value=2024, max_value=2030, value=2026)
    mese_scelto = st.selectbox("Mese", range(1, 13), format_func=lambda x: calendar.month_name[x])

# --- LOGICA FESTIVITÀ (Testata) ---
def calcola_festivi(year, month):
    # Feste Fisse Italiane
    fisse = [(1,1), (6,1), (25,4), (1,5), (2,6), (15,8), (1,11), (8,12), (25,12), (26,12)]
    festivi = [datetime(year, m, g).date() for m, g in fisse]

    # Pasqua e Pasquetta
    a = year % 19
    b = year // 100
    c = year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese_p = (h + l - 7 * m + 114) // 31
    giorno_p = ((h + l - 7 * m + 114) % 31) + 1
    pasqua = datetime(year, mese_p, giorno_p).date()
    festivi.extend([pasqua, pasqua + timedelta(days=1)])

    # Patrono Susa (Lunedì dopo 3° domenica di Luglio)
    if month == 7:
        dom = [datetime(year, 7, d).date() for d in range(1, 32) if datetime(year, 7, d).weekday() == 6]
        if len(dom) >= 3: festivi.append(dom[2] + timedelta(days=1))
            
    return festivi

festivi_italiani = calcola_festivi(anno, mese_scelto)

# --- COSTRUZIONE TABELLA ---
num_giorni = calendar.monthrange(anno, mese_scelto)[1]
giorni_data = []
ita_giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

for g in range(1, num_giorni + 1):
    dt = datetime(anno, mese_scelto, g).date()
    tipo = "Feriale"
    if dt in festivi_italiani: tipo = "FESTIVO"
    elif dt.weekday() >= 5: tipo = "WEEKEND"
    
    giorni_data.append({
        "Giorno": f"{g} {ita_giorni[dt.weekday()]}",
        "Tipo": tipo
    })

df_cal = pd.DataFrame(giorni_data)

# Visualizzazione
st.subheader(f"Configurazione Calendario: {calendar.month_name[mese_scelto]} {anno}")

def highlight_days(row):
    color = ''
    if row.Tipo == "FESTIVO": color = 'background-color: #ffcccc' # Rosso
    elif row.Tipo == "WEEKEND": color = 'background-color: #fff2cc' # Giallo
    return [color] * len(row)

st.table(df_cal.style.apply(highlight_days, axis=1))
