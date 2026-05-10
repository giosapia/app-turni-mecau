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
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=datetime.now().month - 1)

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

if 'df_turni' not in st.session_state or st.session_state.get('prev_mese') != mese_idx:
    st.session_state.df_turni = pd.DataFrame({"Giorno": giorni_labels, "MeCAU 1": "", "MeCAU 2": "", "MeCAU Notte": "", "Bassa Intensità": ""})
    st.session_state.df_desid = pd.DataFrame(index=giorni_labels, columns=strutturati).fillna("")
    st.session_state.prev_mese = mese_idx

# --- LOGICA ERRORI ---
def check_errors(df_in, ds_in):
    errs = []
    for idx, row in df_in.iterrows():
        g = row["Giorno"]
        attivi = [m for m in [row["MeCAU 1"], row["MeCAU 2"], row["MeCAU Notte"], row["Bassa Intensità"]] if m != ""]
        if len(attivi) != len(set(attivi)):
            for d in set([m for m in attivi if attivi.count(m) > 1]):
                errs.append(f"🔴 **{g}**: {d} ha duplicati.")
        if idx > 0:
            ieri_notte = df_in.iloc[idx-1]["MeCAU Notte"]
            if ieri_notte != "" and ieri_notte in attivi:
                errs.append(f"😴 **{g}**: {ieri_notte} post-notte.")
        for col in ["MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"]:
            m = row[col]
            if m in strutturati:
                v = ds_in.at[g, m]
                if v in ["Ferie", "Corso", "Blocco"]: errs.append(f"❌ **{g}**: {m} in {v}.")
                elif v == "No Giorno" and col != "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} No Giorno.")
                elif v == "No Notte" and col == "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} No Notte.")
    return errs

# --- FUNZIONE DI SUGGERIMENTO ---
def suggerisci_turni():
    df = st.session_state.df_turni.copy()
    ds = st.session_state.df_desid
    
    # Reset per sicurezza se vuoi una bozza pulita (opzionale)
    # df.iloc[:, 1:] = "" 

    # Ordine colonne per priorità diurna come richiesto
    colonne_ordine = ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]
    
    for idx, row in df.iterrows():
        giorno = row["Giorno"]
        for col in colonne_ordine:
            if df.at[idx, col] == "": # Se la cella è vuota
                # Prova a metterci uno strutturato che deve ancora fare ore
                random.shuffle(strutturati) # Mischia per equità
                for med in strutturati:
                    # Calcolo ore attuali
                    ore_fatte = (df == med).sum().sum() * 12
                    abbuono = ds[med].isin(["Ferie", "Corso"]).sum() * 7.6
                    if (ore_fatte + abbuono) < target_ore:
                        # Verifica se può lavorare (no doppi, no post-notte, no desiderata)
                        df.at[idx, col] = med
                        if check_errors(df, ds): # Se crea errore, annulla
                            df.at[idx, col] = ""
                        else:
                            break # Trovato, passa alla prossima colonna
    
    st.session_state.df_turni = df

# --- INTERFACCIA ---
tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo"])

with tab1:
    config_des = {m: st.column_config.SelectboxColumn(m, options=["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_des, use_container_width=True)

with tab2:
    col_btn, col_err = st.columns([1, 3])
    with col_btn:
        if st.button("🪄 Suggerisci Turni (Bozza)"):
            suggerisci_turni()
            st.rerun()
    
    lista_errori = check_errors(st.session_state.df_turni, st.session_state.df_desid)
    if lista_errori:
        with st.expander(f"⚠️ {len(lista_errori)} conflitti", expanded=False):
            for e in lista_errori[:10]: st.write(e)
    
    config_turni = {
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=lista_tutti),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=lista_tutti),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=lista_tutti),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=lista_bassa),
    }
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config=config_turni, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Bilancio Ore")
    report = []
    for m in strutturati:
        ore_lav = (st.session_state.df_turni.iloc[:, 1:] == m).sum().sum() * 12
        assente = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum()
        ore_abb = assente * 7.6
        tot = ore_lav + ore_abb
        report.append({"Medico": m, "Ore Lav.": ore_lav, "Abbuono (h)": ore_abb, "Totale": round(tot,1), "Bilancio (PA)": round(tot - target_ore,1)})
    st.table(pd.DataFrame(report))
