import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random

# --- LOGICA CALENDARIO E FESTIVI ---
def get_festivi(year):
    festivi_fissi = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    lista_date = [datetime(year, m, g).date() for m, g in festivi_fissi]
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
    lista_date.extend([pasqua, pasqua + timedelta(days=1)])
    c_cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_july = c_cal.monthdatescalendar(year, 7)
    sundays = [day for week in month_july for day in week if day.weekday() == 6 and day.month == 7]
    lista_date.append(sundays[2] + timedelta(days=1))
    return lista_date

def format_giorno(d, m, y, lista_festivi):
    dt = datetime(y, m, d).date()
    nome_giorno = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"][dt.weekday()]
    if dt in lista_festivi or dt.weekday() == 6: return f"🔴 {d}/{m} - {nome_giorno}"
    if dt.weekday() == 5: return f"🟡 {d}/{m} - {nome_giorno}"
    return f"{d}/{m} - {nome_giorno}"

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Gestore Turni MeCAU", layout="wide")
st.title("🏥 Gestore Turni MeCAU")

st.sidebar.header("⚙️ Configurazione")
anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=4)

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

giorni_labels = [format_giorno(d, mese_idx, anno, festivi) for d in range(1, num_days + 1)]

# INIZIALIZZAZIONE SESSION STATE PULITA (Corretta per evitare None)
if 'df_turni' not in st.session_state or st.session_state.get('prev_mese') != mese_idx:
    st.session_state.df_turni = pd.DataFrame({
        "Giorno": giorni_labels, "MeCAU 1": "", "MeCAU 2": "", "MeCAU Notte": "", "Bassa Intensità": ""
    }).fillna("")
    # Creiamo il DataFrame desiderata e forziamo tutte le celle a stringa vuota
    st.session_state.df_desid = pd.DataFrame("", index=giorni_labels, columns=strutturati)
    st.session_state.prev_mese = mese_idx

# --- LOGICA ERRORI ---
def check_errors(df_in, ds_in):
    errs = []
    df_clean = df_in.fillna("")
    ds_clean = ds_in.fillna("")
    
    for idx, row in df_clean.iterrows():
        g = row["Giorno"]
        attivi = [str(m) for m in [row["MeCAU 1"], row["MeCAU 2"], row["MeCAU Notte"], row["Bassa Intensità"]] if m and str(m).strip() != "" and str(m) != "None"]
        
        if len(attivi) != len(set(attivi)):
            duplicati = set([m for m in attivi if attivi.count(m) > 1])
            for d in duplicati: errs.append(f"🔴 **{g}**: {d} ha duplicati.")
        
        if idx > 0:
            ieri_notte = str(df_clean.iloc[idx-1]["MeCAU Notte"])
            if ieri_notte and ieri_notte != "" and ieri_notte != "None" and ieri_notte in attivi:
                errs.append(f"😴 **{g}**: {ieri_notte} post-notte.")
        
        for col in ["MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"]:
            m = str(row[col])
            if m in strutturati:
                # Usiamo .get() o controlliamo se l'indice esiste per evitare errori con "None"
                try:
                    v = ds_clean.at[g, m]
                    if v in ["Ferie", "Corso", "Blocco"]: errs.append(f"❌ **{g}**: {m} in {v}.")
                    elif v == "No Giorno" and col != "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} No Giorno.")
                    elif v == "No Notte" and col == "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} No Notte.")
                except: pass
    return errs

# --- FUNZIONE DI SUGGERIMENTO ---
def suggerisci_turni():
    df = st.session_state.df_turni.fillna("").copy()
    ds = st.session_state.df_desid.fillna("").copy()
    colonne_ordine = ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]
    
    for idx, row in df.iterrows():
        for col in colonne_ordine:
            valore_cella = str(df.at[idx, col])
            if valore_cella == "" or valore_cella == "None":
                medici_shuffled = strutturati.copy()
                random.shuffle(medici_shuffled)
                for med in medici_shuffled:
                    ore_fatte = (df == med).sum().sum() * 12
                    abbuono = (ds[med].isin(["Ferie", "Corso"])).sum() * 7.6
                    if (ore_fatte + abbuono) < target_ore:
                        df.at[idx, col] = med
                        if check_errors(df, ds):
                            df.at[idx, col] = ""
                        else:
                            break
    st.session_state.df_turni = df

# --- INTERFACCIA ---
tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo"])

with tab1:
    st.subheader("Inserimento Vincoli (Strutturati)")
    config_des = {m: st.column_config.SelectboxColumn(m, options=["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]) for m in strutturati}
    # Forziamo il riempimento dei vuoti con "" prima di mostrare l'editor
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid.fillna(""), column_config=config_des, use_container_width=True)

with tab2:
    if st.button("🪄 Suggerisci Turni (Bozza)"):
        suggerisci_turni()
        st.rerun()
    
    lista_errori = check_errors(st.session_state.df_turni, st.session_state.df_desid)
    if lista_errori:
        with st.expander(f"⚠️ {len(lista_errori)} conflitti rilevati", expanded=True):
            for e in lista_errori: st.write(e)
    
    config_turni = {
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=lista_tutti),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=lista_tutti),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=lista_tutti),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=lista_bassa),
    }
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni.fillna(""), column_config=config_turni, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Bilancio Ore")
    df_c = st.session_state.df_turni.fillna("")
    ds_c = st.session_state.df_desid.fillna("")
    report = []
    for m in strutturati:
        ore_lav = (df_c.iloc[:, 1:] == m).sum().sum() * 12
        assente = ds_c[m].isin(["Ferie", "Corso"]).sum() if m in ds_c.columns else 0
        ore_abb = assente * 7.6
        tot = ore_lav + ore_abb
        report.append({"Medico": m, "Ore Lav.": ore_lav, "Abbuono (h)": ore_abb, "Totale": round(tot,1), "Bilancio (PA)": round(tot - target_ore,1)})
    st.table(pd.DataFrame(report))
