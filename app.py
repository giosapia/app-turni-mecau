import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# --- LOGICA CALENDARIO E FESTIVI ---
def get_festivi(year):
    festivi_fissi = [(1, 1), (6, 1), (25, 4), (1, 5), (2, 6), (15, 8), (1, 11), (8, 12), (25, 12), (26, 12)]
    c = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_july = c.monthdatescalendar(year, 7)
    sundays = [day for week in month_july for day in week if day.weekday() == 6 and day.month == 7]
    terza_dom_luglio = sundays[2]
    patrono = terza_dom_luglio + timedelta(days=1)
    lista = [patrono]
    for m, g in festivi_fissi:
        try: lista.append(datetime(year, m, g).date())
        except: pass
    return lista

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gestore Turni MeCAU", layout="wide")
st.title("🏥 Gestore Turni MeCAU")

# --- SIDEBAR: GESTIONE ---
st.sidebar.header("⚙️ Configurazione")
anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=4)

st.sidebar.header("👥 Personale")
strutturati_txt = st.sidebar.text_area("Strutturati (separati da virgola)", "Brancaleoni, Desiderio, Pazè, Sapia")
jolly_txt = st.sidebar.text_area("Jolly (separati da virgola)", "Maurino, Leoncini, Trupja, Tatarciuc")
gettonisti_txt = st.sidebar.text_area("Gettonisti (separati da virgola)", "Moshkina, Mascalchi, Garrone")

strutturati = [x.strip() for x in strutturati_txt.split(",") if x.strip()]
jolly = [x.strip() for x in jolly_txt.split(",") if x.strip()]
gettonisti = [x.strip() for x in gettonisti_txt.split(",") if x.strip()]

lista_completa = [""] + strutturati + jolly
lista_bassa_int = [""] + strutturati + jolly + gettonisti

num_days = calendar.monthrange(anno, mese_idx)[1]
festivi = get_festivi(anno)
feriali_count = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi)
st.sidebar.info(f"**Monte Ore Target:** {feriali_count * 7.6:.1f}h")

# --- INTERFACCIA ---
tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo"])

with tab1:
    st.subheader("Inserimento Ferie, Corsi e Blocchi")
    st.markdown("Seleziona il tipo di assenza per ogni giorno. *Le Ferie e i Corsi scalano 7.6h dal monte ore.*")
    
    # Opzioni per i desiderata
    opzioni_desiderata = ["", "Ferie", "Corso", "Blocco (Indisponibile)"]
    
    giorni = [f"{d}/{mese_idx}" for d in range(1, num_days + 1)]
    
    # Creiamo una tabella dove le colonne sono i Medici Strutturati
    df_desiderata = pd.DataFrame(index=giorni, columns=strutturati).fillna("")
    
    config_desid = {medico: st.column_config.SelectboxColumn(medico, options=opzioni_desiderata) for medico in strutturati}
    
    st.data_editor(df_desiderata, column_config=config_desid, use_container_width=True)

with tab2:
    st.subheader("Compilazione Turni MeCAU")
    df_base = pd.DataFrame({
        "Giorno": giorni,
        "MeCAU 1": ["" for _ in giorni],
        "MeCAU 2": ["" for _ in giorni],
        "MeCAU Notte": ["" for _ in giorni],
        "Bassa Intensità": ["" for _ in giorni]
    })
    
    config_turni = {
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=lista_completa),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=lista_completa),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=lista_completa),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=lista_bassa_int),
    }
    
    st.data_editor(df_base, column_config=config_turni, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Riepilogo Ore")
    st.info("I calcoli verranno visualizzati qui una volta completata la logica di conteggio.")

st.success("Tab 'Desiderata' attivata con menu a tendina!")
