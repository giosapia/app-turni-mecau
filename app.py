import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random
from fpdf import FPDF

# --- CALCOLO FESTIVI ---
def get_festivi(year):
    festivi_fissi = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    lista_date = [datetime(year, m, g).date() for m, g in festivi_fissi]
    # Calcolo Pasqua (Algoritmo di Gauss)
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

# --- PDF GENERATOR ---
def genera_pdf_sicuro(df, anno, mese_idx, festivi):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"TURNI MECAU - {calendar.month_name[mese_idx].upper()} {anno}", ln=True, align="C")
    pdf.ln(5)
    widths = [40, 60, 60, 60, 55]
    pdf.set_font("Helvetica", "B", 11); pdf.set_fill_color(31, 78, 120); pdf.set_text_color(255, 255, 255)
    headers = ["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Int."]
    for h, w in zip(headers, widths): pdf.cell(w, 10, h, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(0, 0, 0)
    for i, row in df.iterrows():
        dt = datetime(anno, mese_idx, i + 1).date()
        if dt in festivi or dt.weekday() == 6: pdf.set_fill_color(240, 200, 200)
        elif dt.weekday() == 5: pdf.set_fill_color(255, 245, 200)
        else: pdf.set_fill_color(255, 255, 255)
        txt = row['Giorno'].replace("🔴 ", "").replace("🟡 ", "").replace("⚪ ", "")
        pdf.cell(widths[0], 9, txt, border=1, fill=True)
        for j in range(1, 5): pdf.cell(widths[j], 9, str(row.iloc[j]), border=1, align="C", fill=True)
        pdf.ln()
    return pdf.output()

# --- APP ---
st.set_page_config(page_title="MeCAU Scheduler", layout="wide")
st.title("🏥 Gestore Turni MeCAU")

anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=datetime.now().month - 1)
strutturati = [x.strip() for x in st.sidebar.text_area("Lista Medici", "Brancaleoni, Desiderio, Pazè, Sapia").split(",") if x.strip()]

num_days = calendar.monthrange(anno, mese_idx)[1]
festivi_list = get_festivi(anno)
target_h = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi_list) * 7.6

if 'key' not in st.session_state or st.session_state.key != f"{anno}-{mese_idx}":
    labels = [get_day_label(d, mese_idx, anno, festivi_list) for d in range(1, num_days + 1)]
    st.session_state.df_turni = pd.DataFrame("", index=range(num_days), columns=["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"])
    st.session_state.df_turni["Giorno"] = labels
    st.session_state.df_desid = pd.DataFrame("", index=labels, columns=strutturati)
    st.session_state.key = f"{anno}-{mese_idx}"

t1, t2, t3 = st.tabs(["📅 Desiderata & Jolly", "🛠️ Griglia Turni", "📊 Bilancio Ore"])

with t1:
    st.info("Segna Ferie, Corso o Blocco per escludere i medici. Segna No Giorno/No Notte per vincoli specifici.")
    config_des = {m: st.column_config.SelectboxColumn(m, options=["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_des, use_container_width=True)

with t2:
    if st.button("🪄 Genera Bozza (Rispetta Vincoli)", type="primary"):
        df = st.session_state.df_turni.copy()
        ds = st.session_state.df_desid.copy()
        for c in ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]: df[c] = ""
        
        # --- 1. ASSEGNAZIONE NOTTI ---
        for idx in range(num_days):
            random.shuffle(strutturati)
            medici_okay = sorted(strutturati, key=lambda m: (df == m).sum().sum())
            for m in medici_okay:
                pref = ds.at[df.at[idx, "Giorno"], m]
                if pref in ["Ferie", "Corso", "Blocco", "No Notte"]: continue
                if idx > 0 and df.at[idx-1, "MeCAU Notte"] == m: continue # Riposo post-notte
                df.at[idx, "MeCAU Notte"] = m
                break

        # --- 2. ASSEGNAZIONE GIORNI (MeCAU 1 e 2) ---
        for col in ["MeCAU 1", "MeCAU 2"]:
            for idx in range(num_days):
                medici_okay = sorted(strutturati, key=lambda m: (df == m).sum().sum())
                for m in medici_okay:
                    pref = ds.at[df.at[idx, "Giorno"], m]
                    if pref in ["Ferie", "Corso", "Blocco", "No Giorno"]: continue
                    if df.at[idx, "MeCAU Notte"] == m: continue # No Notte + Giorno stesso giorno
                    if idx > 0 and df.at[idx-1, "MeCAU Notte"] == m: continue # Riposo post-notte obbligatorio
                    if m in [df.at[idx, "MeCAU 1"], df.at[idx, "MeCAU 2"]]: continue # No doppione
                    
                    # Controllo ore (con tolleranza)
                    ore = (df == m).sum().sum() * 12 + ds[m].isin(["Ferie","Corso"]).sum() * 7.6
                    if ore >= (target_h + 12): continue 
                    
                    df.at[idx, col] = m
                    break
        st.session_state.df_turni = df
        st.rerun()

    if st.button("📥 Scarica PDF"):
        st.download_button("Download PDF", genera_pdf_sicuro(st.session_state.df_turni, anno, mese_idx, festivi_list), f"Turni_{mese_idx}.pdf", "application/pdf")
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, use_container_width=True, hide_index=True)

with t3:
    rep = []
    for m in strutturati:
        lav = (st.session_state.df_turni == m).sum().sum() * 12
        abb = st.session_state.df_desid[m].isin(["Ferie","Corso"]).sum() * 7.6
        rep.append({"Medico": m, "Ore": lav, "Abbuono": abb, "Totale": lav+abb, "Delta": round(lav+abb-target_h, 1)})
    st.table(pd.DataFrame(rep))
