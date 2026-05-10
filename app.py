import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# --- LOGICA CALENDARIO E FESTIVI ---
def get_festivi(year):
    festivi_fissi = [(1, 1), (6, 1), (25, 4), (1, 5), (2, 6), (15, 8), (1, 11), (8, 12), (25, 12), (26, 12)]
    c = calendar.Calendar(firstweekday=calendar.MONDAY)
    # Calcolo Patrono (Lunedì dopo la terza domenica di luglio)
    month_july = c.monthdatescalendar(year, 7)
    sundays = [day for week in month_july for day in week if day.weekday() == 6 and day.month == 7]
    terza_dom_luglio = sundays[2]
    patrono = terza_dom_luglio + timedelta(days=1)
    
    lista = [patrono]
    for m, g in festivi_fissi:
        try: lista.append(datetime(year, m, g).date())
        except: pass
    return lista

def format_giorno(d, m, y, lista_festivi):
    dt = datetime(y, m, d).date()
    nome_giorno = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"][dt.weekday()]
    if dt in lista_festivi or dt.weekday() == 6:
        return f"🔴 {d}/{m} - {nome_giorno}"
    elif dt.weekday() == 5:
        return f"🟡 {d}/{m} - {nome_giorno}"
    else:
        return f"{d}/{m} - {nome_giorno}"

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

# Etichette giorni formattate (con colori/emoji)
giorni_labels = [format_giorno(d, mese_idx, anno, festivi) for d in range(1, num_days + 1)]

# --- STATO DELLA SESSIONE ---
if 'df_turni' not in st.session_state or st.session_state.get('prev_mese') != mese_idx:
    st.session_state.df_turni = pd.DataFrame({
        "Giorno": giorni_labels, "MeCAU 1": "", "MeCAU 2": "", "MeCAU Notte": "", "Bassa Intensità": ""
    })
    st.session_state.df_desid = pd.DataFrame(index=giorni_labels, columns=strutturati).fillna("")
    st.session_state.prev_mese = mese_idx

# --- LOGICA ERRORI ---
def check_errors():
    errs = []
    df = st.session_state.df_turni
    ds = st.session_state.df_desid
    for idx, row in df.iterrows():
        g = row["Giorno"]
        medici_attivi = [m for m in [row["MeCAU 1"], row["MeCAU 2"], row["MeCAU Notte"], row["Bassa Intensità"]] if m != ""]
        # Doppi turni
        if len(medici_attivi) != len(set(medici_attivi)):
            duplicati = set([m for m in medici_attivi if medici_attivi.count(m) > 1])
            for d in duplicati: errs.append(f"🔴 **{g}**: {d} ha troppi incarichi.")
        # Vincoli
        for col in ["MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"]:
            m = row[col]
            if m in strutturati:
                v = ds.at[g, m]
                if v in ["Ferie", "Corso", "Blocco"]: errs.append(f"❌ **{g}**: {m} è in '{v}'.")
                elif v == "No Giorno" and col != "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} ha vincolo 'No Giorno'.")
                elif v == "No Notte" and col == "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} ha vincolo 'No Notte'.")
    return errs

# --- INTERFACCIA ---
tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo"])

with tab1:
    st.subheader("Inserimento Vincoli (Strutturati)")
    st.info("I giorni segnati con 🔴 sono Domeniche o Festivi. I 🟡 sono Sabati.")
    opts = ["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]
    config_des = {m: st.column_config.SelectboxColumn(m, options=opts) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_des, use_container_width=True)

with tab2:
    st.subheader("Compilazione Griglia")
    # Mostra errori veloci qui
    lista_errori = check_errors()
    if lista_errori:
        with st.expander(f"⚠️ Ci sono {len(lista_errori)} errori nella griglia!", expanded=True):
            for e in lista_errori[:5]: st.write(e)
            if len(lista_errori) > 5: st.write("...e altri. Controlla la Tab Riepilogo.")
    
    config_turni = {
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=lista_tutti),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=lista_tutti),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=lista_tutti),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=lista_bassa),
    }
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config=config_turni, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Conteggio Ore e Bilancio PA")
    report = []
    for m in strutturati:
        ore_lav = (st.session_state.df_turni.iloc[:, 1:] == m).sum().sum() * 12
        assente = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum()
        ore_abb = assente * 7.6
        report.append({"Medico": m, "Ore Lavorate": ore_lav, "Abbuono Ferie/Corsi": ore_abb, "Totale": ore_lav + ore_abb, "Bilancio": (ore_lav + ore_abb) - target_ore})
    st.table(pd.DataFrame(report))
    
    if lista_errori:
        st.subheader("⚠️ Dettaglio Errori")
        for e in lista_errori: st.write(e)
