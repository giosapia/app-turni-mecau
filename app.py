import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# Impostazioni pagina
st.set_page_config(page_title="Gestione Medici Susa", layout="wide")
st.title("🏥 Calendario Turni MeCAU Susa")

# --- 1. SIDEBAR: ANAGRAFICA (Punto 1 - Congelato) ---
with st.sidebar:
    st.header("👥 Anagrafica Medici")
    
    lista_strutturati = st.text_area("1. Medici Strutturati", 
                                   value="Brancaleoni, Desiderio, Pazè, Sapia")
    strutturati = [s.strip() for s in lista_strutturati.split(",") if s.strip()]

    lista_jolly = st.text_area("2. Medici Jolly", 
                               value="Calasso, Melis, Sabbatino, Marsanic, Bruno, Castelli, Guglielmino, Trupja, Carbone, Dipietro, Di Stefano, Gili, Montebro, Ostuni, Palumbo, Ronco, Valobra, Vanoni, Veglio, Molino, Leoncini, Maurino, Tatarciuc, Sivera, Vellata, Isidori")
    jolly = [j.strip() for j in lista_jolly.split(",") if j.strip()]

    lista_gettonisti = st.text_area("3. Medici Gettonisti", 
                                   value="Borgiotto, Moshkina, Mascalchi, Garrone, Passoni, Sardo")
    gettonisti = [g.strip() for g in lista_gettonisti.split(",") if g.strip()]

    st.divider()
    
    # --- 2. SIDEBAR: SELEZIONE PERIODO (Punto 2) ---
    st.header("📅 Periodo di Riferimento")
    anno = st.number_input("Anno", min_value=2024, max_value=2030, value=2026)
    
    mesi_nomi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", 
                 "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    
    mese_testo = st.selectbox("Mese", mesi_nomi, index=4) # Default Maggio
    mese_scelto = mesi_nomi.index(mese_testo) + 1

# --- LOGICA FESTIVITÀ CORRETTA ---
def calcola_festivi(year, month):
    # Feste Fisse Italiane (Mese, Giorno)
    fisse = [
        (1, 1),   # Capodanno
        (1, 6),   # Epifania
        (4, 25),  # Liberazione
        (5, 1),   # Lavoro
        (6, 2),   # Repubblica
        (8, 15),  # Ferragosto
        (11, 1),  # Ognissanti
        (12, 8),  # Immacolata
        (12, 25), # Natale
        (12, 26)  # S. Stefano
    ]
    
    festivi = []
    for m, g in fisse:
        festivi.append(datetime(year, m, g).date())

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
    m_gauss = (a + 11 * h + 22 * l) // 451
    mese_p = (h + l - 7 * m_gauss + 114) // 31
    giorno_p = ((h + l - 7 * m_gauss + 114) % 31) + 1
    pasqua = datetime(year, mese_p, giorno_p).date()
    festivi.append(pasqua)
    festivi.append(pasqua + timedelta(days=1)) # Pasquetta

    # Patrono Susa (Lunedì dopo 3° domenica di Luglio)
    if month == 7:
        domeniche = [datetime(year, 7, d).date() for d in range(1, 32) 
                     if datetime(year, 7, d).weekday() == 6]
        if len(domeniche) >= 3:
            festivi.append(domeniche[2] + timedelta(days=1))
            
    return festivi

# Calcolo effettivo
try:
    festivi_italiani = calcola_festivi(anno, mese_scelto)
except Exception as e:
    st.error(f"Errore nel calcolo festivi: {e}")
    festivi_italiani = []

# --- COSTRUZIONE TABELLA ---
num_giorni = calendar.monthrange(anno, mese_scelto)[1]
giorni_data = []
ita_nomi_giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

for g in range(1, num_giorni + 1):
    dt = datetime(anno, mese_scelto, g).date()
    tipo = "Feriale"
    if dt in festivi_italiani:
        tipo = "FESTIVO"
    elif dt.weekday() >= 5:
        tipo = "WEEKEND"
    
    giorni_data.append({
        "Giorno": f"{g} {ita_nomi_giorni[dt.weekday()]}",
        "Tipo": tipo
    })

df_cal = pd.DataFrame(giorni_data)

# --- VISUALIZZAZIONE ---
st.subheader(f"Calendario Turni: {mese_testo} {anno}")

def highlight_days(row):
    color = ''
    if row.Tipo == "FESTIVO":
        color = 'background-color: #ffcccc' # Rosso
    elif row.Tipo == "WEEKEND":
        color = 'background-color: #fff2cc' # Giallo
    return [color] * len(row)

st.table(df_cal.style.apply(highlight_days, axis=1))
