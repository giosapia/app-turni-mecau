import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random
from weasyprint import HTML

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

# --- NUOVA FUNZIONE PDF CON WEASYPRINT (BELLA E STABILE) ---
def genera_pdf_weasy(df, anno, mese_idx, festivi):
    mese_nome = calendar.month_name[mese_idx].upper()
    rows_html = ""
    for i, row in df.iterrows():
        dt = datetime(anno, mese_idx, i + 1).date()
        row_style = ""
        dot = ""
        if dt in festivi or dt.weekday() == 6:
            row_style = 'background-color: #ffeaea;'
            dot = '<span style="height:10px;width:10px;background-color:#ff4d4d;border-radius:50%;display:inline-block;margin-right:5px;"></span>'
        elif dt.weekday() == 5:
            row_style = 'background-color: #fff9e6;'
            dot = '<span style="height:10px;width:10px;background-color:#ffcc00;border-radius:50%;display:inline-block;margin-right:5px;"></span>'
        
        rows_html += f"""
        <tr style="{row_style}">
            <td style="border:1px solid #ddd;padding:8px;text-align:left;">{dot} {row['Giorno']}</td>
            <td style="border:1px solid #ddd;padding:8px;">{row['MeCAU 1']}</td>
            <td style="border:1px solid #ddd;padding:8px;">{row['MeCAU 2']}</td>
            <td style="border:1px solid #ddd;padding:8px;">{row['MeCAU Notte']}</td>
            <td style="border:1px solid #ddd;padding:8px;">{row['Bassa Intensità']}</td>
        </tr>"""

    html_content = f"""
    <html>
    <body style="font-family:sans-serif;margin:20px;">
        <h1 style="text-align:center;color:#1f4e78;">TURNI MECAU - {mese_nome} {anno}</h1>
        <table style="width:100%;border-collapse:collapse;text-align:center;">
            <thead>
                <tr style="background-color:#1f4e78;color:white;">
                    <th style="padding:10px;border:1px solid #ddd;">Giorno</th>
                    <th style="padding:10px;border:1px solid #ddd;">MeCAU 1</th>
                    <th style="padding:10px;border:1px solid #ddd;">MeCAU 2</th>
                    <th style="padding:10px;border:1px solid #ddd;">MeCAU Notte</th>
                    <th style="padding:10px;border:1px solid #ddd;">Bassa Int.</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </body>
    </html>"""
    return HTML(string=html_content).write_pdf()

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Gestore Turni MeCAU", layout="wide")
st.title("🏥 Gestore Turni MeCAU")

# Sidebar
anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=datetime.now().month - 1)
strutturati = [x.strip() for x in st.sidebar.text_area("Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia").split(",") if x.strip()]
jolly = [x.strip() for x in st.sidebar.text_area("Jolly", "Maurino, Leoncini, Trupja, Tatarciuc").split(",") if x.strip()]

num_days = calendar.monthrange(anno, mese_idx)[1]
festivi = get_festivi(anno)
feriali = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi)
target_ore = feriali * 7.6
st.sidebar.metric("Target Orario Mensile", f"{target_ore:.1f}h")

if 'df_turni' not in st.session_state or st.session_state.get('prev_mese') != mese_idx:
    st.session_state.df_turni = pd.DataFrame("", index=range(num_days), columns=["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"])
    st.session_state.df_turni["Giorno"] = [format_giorno(d, mese_idx, anno) for d in range(1, num_days + 1)]
    st.session_state.df_desid = pd.DataFrame("", index=st.session_state.df_turni["Giorno"], columns=strutturati)
    st.session_state.prev_mese = mese_idx

def suggerisci_turni():
    df = st.session_state.df_turni.copy()
    ds = st.session_state.df_desid.copy()
    for col in ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]: df[col] = ""

    for idx in range(len(df)):
        turni = ["MeCAU Notte", "MeCAU 1", "MeCAU 2"]
        random.shuffle(turni)
        for t in turni:
            medici = sorted(strutturati, key=lambda m: (df == m).sum().sum())
            for med in medici:
                pref = ds.at[df.at[idx, "Giorno"], med]
                if pref in ["Ferie", "Corso", "Blocco"]: continue
                if pref == "No Giorno" and t != "MeCAU Notte": continue
                if pref == "No Notte" and t == "MeCAU Notte": continue
                
                ore = (df == med).sum().sum() * 12
                abb = ds[med].isin(["Ferie", "Corso"]).sum() * 7.6
                if (ore + abb + 12) > target_ore: continue
                if idx > 0 and df.at[idx-1, "MeCAU Notte"] == med: continue
                if med in [df.at[idx, "MeCAU 1"], df.at[idx, "MeCAU 2"], df.at[idx, "MeCAU Notte"]]: continue
                
                df.at[idx, t] = med
                break
    st.session_state.df_turni = df

# Tab
t1, t2, t3 = st.tabs(["📅 Desiderata", "🛠️ Griglia", "📊 Bilancio"])

with t1:
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, use_container_width=True)

with t2:
    c1, c2 = st.columns(2)
    if c1.button("🪄 Genera Bozza Bilanciata", type="primary"):
        suggerisci_turni()
        st.rerun()
    if c2.button("📥 Scarica PDF con Pallini"):
        pdf = genera_pdf_weasy(st.session_state.df_turni, anno, mese_idx, festivi)
        st.download_button("Salva PDF", pdf, f"Turni_{mese_idx}.pdf", "application/pdf")
    
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, use_container_width=True, hide_index=True)

with t3:
    rep = []
    for m in strutturati:
        ore = (st.session_state.df_turni == m).sum().sum() * 12
        abb = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum() * 7.6
        rep.append({"Medico": m, "Ore": ore, "Abbuono": abb, "Diff": round(ore+abb-target_ore, 1)})
    st.table(pd.DataFrame(rep))
