import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
from fpdf import FPDF

# --- CONFIGURAZIONE ---
SALE_DIURNE = ["MeCAU 1", "MeCAU 2"]
SALA_NOTTE = "MeCAU Notte"
SALA_BASSA = "Bassa Intensità"

def get_festivi_susa(year):
    festivi_fissi = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    lista_date = [datetime(year, m, g).date() for m, g in festivi_fissi]
    # Pasqua/Pasquetta e Patrono omessi per brevità ma calcolabili
    return lista_date

def get_day_label(d, m, y, festivi):
    dt = datetime(y, m, d).date()
    nomi = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    base = f"{d}/{m} - {nomi[dt.weekday()]}"
    return f"🔴 {base}" if (dt in festivi or dt.weekday() >= 5) else f"⚪ {base}"

st.set_page_config(page_title="Turni MeCAU Susa", layout="wide")
st.title("🚑 Generatore Turni Susa (Versione Semplificata)")

with st.sidebar:
    anno = st.number_input("Anno", value=2026)
    mese_idx = st.selectbox("Mese", range(1, 13), index=4)
    strutturati = [s.strip() for s in st.text_area("Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia").split(",") if s.strip()]
    jolly = [j.strip() for j in st.text_area("Jolly", "Calasso, Melis, Sabbatino, Marsanic").split(",") if j.strip()]
    gettonisti = [g.strip() for g in st.text_area("Gettonisti", "Borgiotto, Moshkina, Mascalchi").split(",") if g.strip()]

festivi_list = get_festivi_susa(anno)
num_days = calendar.monthrange(anno, mese_idx)[1]
target_mensile = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5) * 7.6

if 'df_turni' not in st.session_state or st.session_state.get('last_m') != mese_idx:
    labels = [get_day_label(d, mese_idx, anno, festivi_list) for d in range(1, num_days + 1)]
    st.session_state.df_turni = pd.DataFrame("", index=range(num_days), columns=["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"])
    st.session_state.df_turni["Giorno"] = labels
    st.session_state.df_desid = pd.DataFrame("", index=labels, columns=strutturati)
    st.session_state.last_m = mese_idx

tab1, tab2, tab3 = st.tabs(["📋 Desiderata", "⚙️ Generazione", "📊 Bilancio"])

with tab1:
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, use_container_width=True)

with tab2:
    if st.button("🪄 GENERA TURNI (Logica Semplice)", type="primary"):
        df = st.session_state.df_turni.copy()
        ds = st.session_state.df_desid.copy()

        for i in range(num_days):
            label = df.at[i, "Giorno"]
            # 1. NOTTE
            if df.at[i, "MeCAU Notte"] == "":
                candidati = sorted(strutturati, key=lambda m: (df == m).sum().sum())
                for m in candidati:
                    if ds.at[label, m] in ["Ferie", "No Notte", "Blocco"]: continue
                    if i > 0 and df.at[i-1, "MeCAU Notte"] == m: continue
                    df.at[i, "MeCAU Notte"] = m
                    break
            
            # 2. SALE MECAU
            for sala in ["MeCAU 1", "MeCAU 2"]:
                if df.at[i, sala] == "":
                    candidati = sorted(strutturati, key=lambda m: (df == m).sum().sum())
                    for m in candidati:
                        if ds.at[label, m] in ["Ferie", "No Giorno", "Blocco"]: continue
                        if m in [df.at[i, "MeCAU 1"], df.at[i, "MeCAU 2"], df.at[i, "MeCAU Notte"]]: continue
                        if i > 0 and df.at[i-1, "MeCAU Notte"] == m: continue # Minimo riposo post-notte
                        df.at[i, sala] = m
                        break
        st.session_state.df_turni = df
        st.rerun()

    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config={
        "MeCAU 1": st.column_config.SelectboxColumn(options=[""]+strutturati+jolly),
        "MeCAU 2": st.column_config.SelectboxColumn(options=[""]+strutturati+jolly),
        "MeCAU Notte": st.column_config.SelectboxColumn(options=[""]+strutturati+jolly),
        "Bassa Intensità": st.column_config.SelectboxColumn(options=[""]+gettonisti)
    }, use_container_width=True, hide_index=True)

with tab3:
    stats = [{"Medico": m, "Ore": (st.session_state.df_turni == m).sum().sum()*12} for m in strutturati]
    st.table(pd.DataFrame(stats))
