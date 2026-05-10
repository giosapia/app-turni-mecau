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

# --- SIDEBAR: CONFIGURAZIONE ---
st.sidebar.header("⚙️ Configurazione")
anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=4)

st.sidebar.header("👥 Personale")
strutturati_txt = st.sidebar.text_area("Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia")
jolly_txt = st.sidebar.text_area("Jolly", "Maurino, Leoncini, Trupja, Tatarciuc")
gettonisti_txt = st.sidebar.text_area("Gettonisti", "Moshkina, Mascalchi, Garrone")

strutturati = [x.strip() for x in strutturati_txt.split(",") if x.strip()]
jolly = [x.strip() for x in jolly_txt.split(",") if x.strip()]
gettonisti = [x.strip() for x in gettonisti_txt.split(",") if x.strip()]

lista_tutti = [""] + strutturati + jolly
lista_bassa = [""] + gettonisti

# Calcolo Monte Ore Target
num_days = calendar.monthrange(anno, mese_idx)[1]
festivi = get_festivi(anno)
giorni_feriali = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi)
target_ore = giorni_feriali * 7.6
st.sidebar.metric("Monte Ore Target", f"{target_ore:.1f}h")

# --- STATO DELLA SESSIONE (Per non perdere i dati tra i tab) ---
if 'df_turni' not in st.session_state:
    giorni = [f"{d}/{mese_idx}" for d in range(1, num_days + 1)]
    st.session_state.df_turni = pd.DataFrame({
        "Giorno": giorni, "MeCAU 1": "", "MeCAU 2": "", "MeCAU Notte": "", "Bassa Intensità": ""
    })

if 'df_desid' not in st.session_state:
    giorni = [f"{d}/{mese_idx}" for d in range(1, num_days + 1)]
    st.session_state.df_desid = pd.DataFrame(index=giorni, columns=strutturati).fillna("")

# --- INTERFACCIA A TAB ---
tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo & Buchi"])

with tab1:
    st.subheader("Inserimento Vincoli (Strutturati)")
    opts = ["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]
    config_des = {m: st.column_config.SelectboxColumn(m, options=opts) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_des, use_container_width=True)

with tab2:
    st.subheader("Compilazione Griglia")
    config_turni = {
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=lista_tutti),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=lista_tutti),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=lista_tutti),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=lista_bassa),
    }
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config=config_turni, use_container_width=True, hide_index=True)

with tab3:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Conteggio Ore Strutturati")
        report = []
        for m in strutturati:
            # Conteggio turni (12h l'uno)
            ore_lavorate = (st.session_state.df_turni == m).sum().sum() * 12
            # Conteggio ferie/corsi (7.6h l'uno)
            assente = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum()
            ore_abbuonate = assente * 7.6
            totale = ore_lavorate + ore_abbuonate
            bilancio = totale - target_ore
            
            report.append({
                "Medico": m, "Ore Lavorate": ore_lavorate, 
                "Ferie/Corsi (h)": ore_abbuonate, "Totale": totale, "Bilancio (PA)": bilancio
            })
        
        st.table(pd.DataFrame(report))

    with col2:
        st.subheader("Turni Vacanti")
        v_mec1 = st.session_state.df_turni[st.session_state.df_turni["MeCAU 1"] == ""].Giorno.tolist()
        v_mec2 = st.session_state.df_turni[st.session_state.df_turni["MeCAU 2"] == ""].Giorno.tolist()
        v_notte = st.session_state.df_turni[st.session_state.df_turni["MeCAU Notte"] == ""].Giorno.tolist()
        
        st.warning(f"MeCAU 1 vuoti: {len(v_mec1)}")
        st.warning(f"MeCAU 2 vuoti: {len(v_mec2)}")
        st.error(f"Notti vuote: {len(v_notte)}")
