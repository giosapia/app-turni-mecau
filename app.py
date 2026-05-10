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

# --- SIDEBAR ---
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

num_days = calendar.monthrange(anno, mese_idx)[1]
festivi = get_festivi(anno)
giorni_feriali = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi)
target_ore = giorni_feriali * 7.6
st.sidebar.metric("Monte Ore Target", f"{target_ore:.1f}h")

# --- STATO DELLA SESSIONE ---
if 'df_turni' not in st.session_state:
    giorni = [f"{d}/{mese_idx}" for d in range(1, num_days + 1)]
    st.session_state.df_turni = pd.DataFrame({
        "Giorno": giorni, "MeCAU 1": "", "MeCAU 2": "", "MeCAU Notte": "", "Bassa Intensità": ""
    })
if 'df_desid' not in st.session_state:
    giorni = [f"{d}/{mese_idx}" for d in range(1, num_days + 1)]
    st.session_state.df_desid = pd.DataFrame(index=giorni, columns=strutturati).fillna("")

# --- INTERFACCIA ---
tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo & Errori"])

with tab1:
    st.subheader("Inserimento Vincoli")
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
    col_ore, col_errori = st.columns([1.5, 1])
    
    with col_ore:
        st.subheader("Conteggio Ore")
        report = []
        for m in strutturati:
            ore_lavorate = (st.session_state.df_turni.iloc[:, 1:] == m).sum().sum() * 12
            assente = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum()
            ore_abbuonate = assente * 7.6
            totale = ore_lavorate + ore_abbuonate
            report.append({"Medico": m, "Ore Lavorate": ore_lavorate, "Ferie/Corsi (h)": ore_abbuonate, "Totale": totale, "Bilancio": totale - target_ore})
        st.table(pd.DataFrame(report))

    with col_errori:
        st.subheader("⚠️ Errori Riscontrati")
        errori = []
        df = st.session_state.df_turni
        ds = st.session_state.df_desid
        
        for idx, row in df.iterrows():
            giorno = row["Giorno"]
            medici_giorno = [row["MeCAU 1"], row["MeCAU 2"], row["MeCAU Notte"], row["Bassa Intensità"]]
            medici_attivi = [m for m in medici_giorno if m != ""]
            
            # 1. Controllo Doppi Turni
            if len(medici_attivi) != len(set(medici_attivi)):
                duplicati = set([m for m in medici_attivi if medici_attivi.count(m) > 1])
                for d in duplicati:
                    errori.append(f"🔴 **{giorno}**: {d} è segnato in più turni lo stesso giorno.")
            
            # 2. Controllo Desiderata
            for col_name in ["MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"]:
                m = row[col_name]
                if m in strutturati:
                    vincolo = ds.at[giorno, m]
                    if vincolo in ["Ferie", "Corso", "Blocco"]:
                        errori.append(f"❌ **{giorno}**: {m} è in {col_name} ma è segnato in '{vincolo}'.")
                    elif vincolo == "No Giorno" and col_name != "MeCAU Notte":
                        errori.append(f"🚫 **{giorno}**: {m} è in {col_name} ma ha il vincolo 'No Giorno'.")
                    elif vincolo == "No Notte" and col_name == "MeCAU Notte":
                        errori.append(f"🚫 **{giorno}**: {m} è in Notte ma ha il vincolo 'No Notte'.")

        if errori:
            for e in errori: st.write(e)
        else:
            st.success("Nessun conflitto rilevato!")
