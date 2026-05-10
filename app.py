import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random
from fpdf import FPDF

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
    return lista_date

def format_giorno_emoji(d, m, y, festivi):
    dt = datetime(y, m, d).date()
    nome_giorno = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"][dt.weekday()]
    label = f"{d}/{m} - {nome_giorno}"
    if dt in festivi or dt.weekday() == 6:
        return f"🔴 {label}"
    elif dt.weekday() == 5:
        return f"🟡 {label}"
    return f"⚪ {label}"

# --- FUNZIONE PDF (FPDF2) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(31, 78, 120)
        self.cell(0, 10, self.custom_title, ln=True, align='C')
        self.ln(5)

def crea_pdf_finale(df, anno, mese_idx, festivi):
    pdf = PDF(orientation="L", unit="mm", format="A4")
    mese_nome = calendar.month_name[mese_idx].upper()
    pdf.custom_title = f"PROGRAMMAZIONE TURNI MECAU - {mese_nome} {anno}"
    pdf.add_page()
    widths = [40, 60, 60, 60, 55]
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(31, 78, 120)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Int."]):
        pdf.cell(widths[i], 10, col, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    for i, row in df.iterrows():
        dt = datetime(anno, mese_idx, i + 1).date()
        if dt in festivi or dt.weekday() == 6: pdf.set_fill_color(255, 230, 230)
        elif dt.weekday() == 5: pdf.set_fill_color(255, 255, 200)
        else: pdf.set_fill_color(255, 255, 255)
        
        # Pulizia emoji per il PDF (alcuni font PDF non le amano)
        label_pulita = row['Giorno'].replace("🔴 ", "").replace("🟡 ", "").replace("⚪ ", "")
        
        pdf.cell(widths[0], 10, label_pulita, border=1, fill=True)
        pdf.cell(widths[1], 10, str(row['MeCAU 1']), border=1, align="C", fill=True)
        pdf.cell(widths[2], 10, str(row['MeCAU 2']), border=1, align="C", fill=True)
        pdf.cell(widths[3], 10, str(row['MeCAU Notte']), border=1, align="C", fill=True)
        pdf.cell(widths[4], 10, str(row['Bassa Intensità']), border=1, align="C", fill=True)
        pdf.ln()
    return pdf.output()

# --- APP STREAMLIT ---
st.set_page_config(page_title="Gestore Turni MeCAU", layout="wide")
st.title("🏥 Gestore Turni MeCAU")

anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=datetime.now().month - 1)
strutturati = [x.strip() for x in st.sidebar.text_area("Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia").split(",") if x.strip()]

num_days = calendar.monthrange(anno, mese_idx)[1]
festivi = get_festivi(anno)
feriali = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi)
target_ore = feriali * 7.6
st.sidebar.metric("Target Orario", f"{target_ore:.1f}h")

# Reset se cambia mese
if 'prev_mese' not in st.session_state or st.session_state.prev_mese != mese_idx:
    labels = [format_giorno_emoji(d, mese_idx, anno, festivi) for d in range(1, num_days + 1)]
    st.session_state.df_turni = pd.DataFrame("", index=range(num_days), columns=["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"])
    st.session_state.df_turni["Giorno"] = labels
    st.session_state.df_desid = pd.DataFrame("", index=labels, columns=strutturati)
    st.session_state.prev_mese = mese_idx

def suggerisci_turni():
    df = st.session_state.df_turni.copy()
    ds = st.session_state.df_desid.copy()
    for col in ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]: df[col] = ""
    for col in ["MeCAU Notte", "MeCAU 1", "MeCAU 2"]:
        for idx in range(len(df)):
            medici = sorted(strutturati, key=lambda m: (df == m).sum().sum())
            for med in medici:
                pref = ds.at[df.at[idx, "Giorno"], med]
                if pref in ["Ferie", "Corso", "Blocco"]: continue
                if pref == "No Giorno" and col != "MeCAU Notte": continue
                if pref == "No Notte" and col == "MeCAU Notte": continue
                ore = (df == med).sum().sum() * 12
                abb = ds[med].isin(["Ferie", "Corso"]).sum() * 7.6
                if (ore + abb + 12) > target_ore: continue
                if idx > 0 and df.at[idx-1, "MeCAU Notte"] == med: continue
                if med in [df.at[idx, "MeCAU 1"], df.at[idx, "MeCAU 2"], df.at[idx, "MeCAU Notte"]]: continue
                df.at[idx, col] = med
                break
    st.session_state.df_turni = df

# Visualizzazione
t1, t2, t3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Bilancio"])

with t1:
    st.info("🔴 = Domenica/Festivo | 🟡 = Sabato | ⚪ = Feriale")
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, use_container_width=True)

with t2:
    c1, c2 = st.columns(2)
    if c1.button("🪄 Genera Bozza Bilanciata", type="primary"):
        suggerisci_turni()
        st.rerun()
    if c2.button("📥 Scarica PDF"):
        pdf_bytes = crea_pdf_finale(st.session_state.df_turni, anno, mese_idx, festivi)
        st.download_button("Salva PDF", pdf_bytes, f"Turni_{mese_idx}.pdf", "application/pdf")
    
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, use_container_width=True, hide_index=True)

with t3:
    rep = []
    for m in strutturati:
        ore = (st.session_state.df_turni == m).sum().sum() * 12
        abb = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum() * 7.6
        rep.append({"Medico": m, "Ore": ore, "Abbuono": abb, "Bilancio": round(ore+abb-target_ore, 1)})
    st.table(pd.DataFrame(rep))
