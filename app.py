import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random
from fpdf import FPDF

# --- LOGICA CALENDARIO ---
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
    return lista_date

def get_day_label(d, m, y, festivi):
    dt = datetime(y, m, d).date()
    nomi = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    base = f"{d}/{m} - {nomi[dt.weekday()]}"
    if dt in festivi or dt.weekday() == 6: return f"🔴 {base}"
    elif dt.weekday() == 5: return f"🟡 {base}"
    return f"⚪ {base}"

# --- APP ---
st.set_page_config(page_title="MeCAU Scheduler", layout="wide")
st.title("🏥 Gestione Turni MeCAU")

anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=4) 
medici_input = st.sidebar.text_area("Elenco Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia")
strutturati = [x.strip() for x in medici_input.split(",") if x.strip()]

num_giorni = calendar.monthrange(anno, mese_idx)[1]
festivi_list = get_festivi(anno)
target_ore = sum(1 for d in range(1, num_giorni + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi_list) * 7.6

if 'session_key' not in st.session_state or st.session_state.session_key != f"{anno}-{mese_idx}":
    labels = [get_day_label(d, mese_idx, anno, festivi_list) for d in range(1, num_giorni + 1)]
    st.session_state.df_turni = pd.DataFrame("", index=range(num_giorni), columns=["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"])
    st.session_state.df_turni["Giorno"] = labels
    st.session_state.df_desid = pd.DataFrame("", index=labels, columns=strutturati)
    st.session_state.session_key = f"{anno}-{mese_idx}"

tab1, tab2, tab3 = st.tabs(["📅 Desiderata & Jolly", "🛠️ Griglia Turni", "📊 Bilancio"])

with tab1:
    st.markdown("### ⚙️ Configurazione Jolly")
    # CONFIGURAZIONE BOX SELEZIONE PER DESIDERATA
    config_jolly = {m: st.column_config.SelectboxColumn(m, options=["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_jolly, use_container_width=True)

with tab2:
    if st.button("🪄 Genera Turni", type="primary"):
        df, ds = st.session_state.df_turni.copy(), st.session_state.df_desid.copy()
        for c in ["MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"]: df[c] = ""

        for i in range(num_giorni):
            giorno_label = df.at[i, "Giorno"]
            # 1. NOTTE
            cand = sorted(strutturati, key=lambda m: (df == m).sum().sum())
            for m in cand:
                if ds.at[giorno_label, m] in ["Ferie", "Corso", "Blocco", "No Notte"]: continue
                if i > 0 and df.at[i-1, "MeCAU Notte"] == m: continue 
                df.at[i, "MeCAU Notte"] = m; break
            # 2. ALTRI TURNI (Inclusa Bassa Intensità)
            for t in ["MeCAU 1", "MeCAU 2", "Bassa Intensità"]:
                cand_g = sorted(strutturati, key=lambda m: (df == m).sum().sum())
                for m in cand_g:
                    if ds.at[giorno_label, m] in ["Ferie", "Corso", "Blocco", "No Giorno"]: continue
                    if m in [df.at[i, "MeCAU 1"], df.at[i, "MeCAU 2"], df.at[i, "MeCAU Notte"], df.at[i, "Bassa Intensità"]]: continue
                    if i > 0 and df.at[i-1, "MeCAU Notte"] == m: continue 
                    df.at[i, t] = m; break
        st.session_state.df_turni = df; st.rerun()

    # CONFIGURAZIONE BOX SELEZIONE PER GRIGLIA TURNI
    config_griglia = {
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=[""] + strutturati),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=[""] + strutturati),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=[""] + strutturati),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=[""] + strutturati),
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True)
    }
    
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config=config_griglia, use_container_width=True, hide_index=True)

with tab3:
    bilancio = []
    for m in strutturati:
        lav = (st.session_state.df_turni == m).sum().sum() * 12
        abb = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum() * 7.6
        bilancio.append({"Medico": m, "Ore": lav, "Abbuono": abb, "Totale": lav+abb, "Delta": round(lav+abb-target_ore, 1)})
    st.table(pd.DataFrame(bilancio))
