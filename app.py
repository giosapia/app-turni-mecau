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

def format_giorno(d, m, y):
    dt = datetime(y, m, d).date()
    nome_giorno = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"][dt.weekday()]
    return f"{d}/{m} - {nome_giorno}"

# --- FUNZIONE PDF ---
def crea_pdf_fpdf(df, anno, mese_idx, lista_festivi):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    mese_nome = calendar.month_name[mese_idx].upper()
    pdf.cell(0, 10, f"PROGRAMMAZIONE TURNI MECAU - {mese_nome} {anno}", ln=True, align="C")
    pdf.ln(5)
    cols = ["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Int."]
    widths = [40, 60, 60, 60, 55]
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(31, 78, 120)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 10, col, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    for i, row in df.iterrows():
        d = i + 1
        dt = datetime(anno, mese_idx, d).date()
        pdf.set_fill_color(255, 255, 255)
        fill = False
        if dt in lista_festivi or dt.weekday() == 6:
            pdf.set_fill_color(255, 200, 200)
            fill = True
        elif dt.weekday() == 5:
            pdf.set_fill_color(255, 255, 180)
            fill = True
        pdf.cell(widths[0], 8, str(row['Giorno']), border=1, fill=fill)
        pdf.cell(widths[1], 8, str(row['MeCAU 1']), border=1, fill=fill)
        pdf.cell(widths[2], 8, str(row['MeCAU 2']), border=1, fill=fill)
        pdf.cell(widths[3], 8, str(row['MeCAU Notte']), border=1, fill=fill)
        pdf.cell(widths[4], 8, str(row['Bassa Intensità']), border=1, fill=fill)
        pdf.ln()
    return pdf.output()

# --- APP ---
st.set_page_config(page_title="Gestore Turni MeCAU", layout="wide")
st.title("🏥 Gestore Turni MeCAU")

anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=datetime.now().month - 1)
strutturati = [x.strip() for x in st.sidebar.text_area("Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia").split(",") if x.strip()]
jolly = [x.strip() for x in st.sidebar.text_area("Jolly", "Maurino, Leoncini, Trupja, Tatarciuc").split(",") if x.strip()]
gettonisti = [x.strip() for x in st.sidebar.text_area("Gettonisti", "Moshkina, Mascalchi, Garrone").split(",") if x.strip()]

num_days = calendar.monthrange(anno, mese_idx)[1]
festivi = get_festivi(anno)
feriali_count = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi)
target_ore = feriali_count * 7.6
st.sidebar.metric("Target Orario", f"{target_ore:.1f}h")

giorni_labels = [format_giorno(d, mese_idx, anno) for d in range(1, num_days + 1)]

if 'df_turni' not in st.session_state or st.session_state.get('prev_mese') != mese_idx:
    st.session_state.df_turni = pd.DataFrame("", index=range(num_days), columns=["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"])
    st.session_state.df_turni["Giorno"] = giorni_labels
    st.session_state.df_desid = pd.DataFrame("", index=giorni_labels, columns=strutturati)
    st.session_state.prev_mese = mese_idx

def suggerisci_turni():
    df = st.session_state.df_turni.fillna("").copy()
    ds = st.session_state.df_desid.fillna("").copy()
    for idx in range(len(df)):
        for col in ["MeCAU Notte", "MeCAU 1", "MeCAU 2"]:
            if not str(df.at[idx, col]).strip():
                medici_shuffled = sorted(strutturati, key=lambda m: (df["MeCAU Notte"] == m).sum()) if col == "MeCAU Notte" else random.sample(strutturati, len(strutturati))
                for med in medici_shuffled:
                    ore_tot = (df == med).sum().sum() * 12
                    abb = ds[med].isin(["Ferie", "Corso", "Blocco"]).sum() * 7.6
                    if (ore_tot + abb + 12) > target_ore: continue
                    if idx > 0 and str(df.at[idx-1, "MeCAU Notte"]) == med: continue
                    start_7d = max(0, idx - 6)
                    if ((df.iloc[start_7d:idx+1] == med).sum().sum() * 12) + 12 > 48: continue
                    df.at[idx, col] = med
                    break
    st.session_state.df_turni = df

tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo"])

with tab1:
    # RIPRISTINO MENU A TENDINA DESIDERATA
    config_des = {m: st.column_config.SelectboxColumn(m, options=["", "Ferie", "Corso", "Blocco"]) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_des, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Genera Bozza (Contrattuale)", type="primary"):
            suggerisci_turni()
            st.rerun()
    with c2:
        if st.button("Scarica PDF"):
            pdf_data = crea_pdf_fpdf(st.session_state.df_turni, anno, mese_idx, festivi)
            st.download_button("Salva PDF", pdf_data, f"Turni_{mese_idx}.pdf", "application/pdf")
    
    lista_tutti = [""] + strutturati + jolly
    lista_bassa = [""] + gettonisti
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config={
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn(options=lista_tutti),
        "MeCAU 2": st.column_config.SelectboxColumn(options=lista_tutti),
        "MeCAU Notte": st.column_config.SelectboxColumn(options=lista_tutti),
        "Bassa Intensità": st.column_config.SelectboxColumn(options=lista_bassa),
    }, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📊 Bilancio Ore")
    report = []
    for m in strutturati:
        ore_l = (st.session_state.df_turni.iloc[:, 1:] == m).sum().sum() * 12
        abb = st.session_state.df_desid[m].isin(["Ferie", "Corso", "Blocco"]).sum() * 7.6
        diff = round((ore_l + abb) - target_ore, 1)
        report.append({"Medico": m, "Ore Lavorate": ore_l, "Abbuono": abb, "Target": round(target_ore, 1), "Differenza": diff})
    st.table(pd.DataFrame(report))
