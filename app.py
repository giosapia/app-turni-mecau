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
    
    mese_testo = st.selectbox("Mese", mesi_nomi, index=4) 
    mese_scelto = mesi_nomi.index(mese_testo) + 1

# --- LOGICA FESTIVITÀ CORRETTA (Punto 2) ---
def calcola_festivi(year, month):
    # Formato corretto: (Mese, Giorno)
    fisse = [
        (1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)
    ]
    festivi = [datetime(year, m, g).date() for m, g in fisse]

    # Pasqua e Pasquetta
    a, b, c = year % 19, year // 100, year % 100
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
    festivi.extend([pasqua, pasqua + timedelta(days=1)])

    # Patrono Susa
    if month == 7:
        dom = [datetime(year, 7, d).date() for d in range(1, 32) if datetime(year, 7, d).weekday() == 6]
        if len(dom) >= 3: festivi.append(dom[2] + timedelta(days=1))
    return festivi

festivi_italiani = calcola_festivi(anno, mese_scelto)

# --- 3. LAYOUT GRAFICO E GRIGLIA (Punto 3) ---

# Inizializzazione dati
if 'griglia' not in st.session_state or st.session_state.get('key_mese') != f"{mese_scelto}-{anno}":
    num_days = calendar.monthrange(anno, mese_scelto)[1]
    ita_giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    
    data = []
    for d in range(1, num_days + 1):
        dt = datetime(anno, mese_scelto, d).date()
        data.append({
            "Giorno": f"{d} {ita_giorni[dt.weekday()]}",
            "MeCAU 1": "",
            "MeCAU 2": "",
            "MeCAU Notte": "",
            "Bassa Intensità": ""
        })
    st.session_state.griglia = pd.DataFrame(data)
    st.session_state.key_mese = f"{mese_scelto}-{anno}"

# Definizione liste per i menu
medici_mecau = [""] + strutturati + jolly
medici_bassa = [""] + gettonisti

st.subheader(f"Pianificazione Turni - {mese_testo} {anno}")

# Visualizzazione Editor Grafico
df_editabile = st.data_editor(
    st.session_state.griglia,
    column_config={
        "Giorno": st.column_config.TextColumn("Data", disabled=True, width="medium"),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=medici_mecau, width="medium"),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=medici_mecau, width="medium"),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=medici_mecau, width="medium"),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=medici_bassa, width="medium")
    },
    hide_index=True,
    use_container_width=True,
    key="main_editor"
)

# Aggiornamento stato
st.session_state.griglia = df_editabile
