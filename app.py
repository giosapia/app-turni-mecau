import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random
from fpdf import FPDF

# --- LOGICA DEL CALENDARIO E FESTIVITÀ ---
def get_festivi(year):
    festivi_fissi = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    lista_date = [datetime(year, m, g).date() for m, g in festivi_fissi]
    # Algoritmo di Gauss per la Pasqua
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
    nomi_giorni = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    base = f"{d}/{m} - {nomi_giorni[dt.weekday()]}"
    if dt in festivi or dt.weekday() == 6:
        return f"🔴 {base}"
    elif dt.weekday() == 5:
        return f"🟡 {base}"
    return f"⚪ {base}"

# --- GENERAZIONE DOCUMENTO PDF ---
def genera_pdf(df, anno, mese_idx, festivi):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    nome_mese = calendar.month_name[mese_idx].upper()
    pdf.cell(0, 10, f"PROGRAMMAZIONE TURNI MECAU - {nome_mese} {anno}", ln=True, align="C")
    pdf.ln(5)

    widths = [40, 60, 60, 60, 55]
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(31, 78, 120)
    pdf.set_text_color(255, 255, 255)
    
    headers = ["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Int."]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 10, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)

    for i, row in df.iterrows():
        dt = datetime(anno, mese_idx, i + 1).date()
        if dt in festivi or dt.weekday() == 6: pdf.set_fill_color(255, 220, 220)
        elif dt.weekday() == 5: pdf.set_fill_color(255, 250, 200)
        else: pdf.set_fill_color(255, 255, 255)
        
        label_pulita = row['Giorno'].replace("🔴 ", "").replace("🟡 ", "").replace("⚪ ", "")
        pdf.cell(widths[0], 9, label_pulita, border=1, fill=True)
        pdf.cell(widths[1], 9, str(row['MeCAU 1']), border=1, align="C", fill=True)
        pdf.cell(widths[2], 9, str(row['MeCAU 2']), border=1, align="C", fill=True)
        pdf.cell(widths[3], 9, str(row['MeCAU Notte']), border=1, align="C", fill=True)
        pdf.cell(widths[4], 9, str(row['Bassa Intensità']), border=1, align="C", fill=True)
        pdf.ln()
    return pdf.output()

# --- APPLICAZIONE INTERATTIVA ---
st.set_page_config(page_title="MeCAU Scheduler", layout="wide")
st.title("🏥 Gestione Turni MeCAU")

anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=datetime.now().month - 1)
medici_input = st.sidebar.text_area("Elenco Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia")
strutturati = [x.strip() for x in medici_input.split(",") if x.strip()]

num_giorni = calendar.monthrange(anno, mese_idx)[1]
festivi_list = get_festivi(anno)
target_ore = sum(1 for d in range(1, num_giorni + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi_list) * 7.6
st.sidebar.metric("Target Orario Mensile", f"{target_ore:.1f}h")

if 'session_key' not in st.session_state or st.session_state.session_key != f"{anno}-{mese_idx}":
    etichette = [get_day_label(d, mese_idx, anno, festivi_list) for d in range(1, num_giorni + 1)]
    st.session_state.df_turni = pd.DataFrame("", index=range(num_giorni), columns=["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"])
    st.session_state.df_turni["Giorno"] = etichette
    st.session_state.df_desid = pd.DataFrame("", index=etichette, columns=strutturati)
    st.session_state.session_key = f"{anno}-{mese_idx}"

tab1, tab2, tab3 = st.tabs(["📅 Desiderata e Jolly", "🛠️ Generazione Turni", "📊 Bilancio Ore"])

with tab1:
    st.markdown("### Inserimento Indisponibilità")
    st.caption("Selezionare l'opzione desiderata per ogni medico (es. Ferie, Corso, Blocco).")
    config_colonne = {m: st.column_config.SelectboxColumn(m, options=["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_colonne, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    if col1.button("🪄 Genera Programmazione Ottimizzata", type="primary"):
        df = st.session_state.df_turni.copy()
        ds = st.session_state.df_desid.copy()
        for c in ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]: df[c] = ""
        
        # Algoritmo a due fasi: Notti, poi Giorno
        for turno in ["MeCAU Notte", "MeCAU 1", "MeCAU 2"]:
            for i in range(num_giorni):
                # Ordina i medici per minor carico orario attuale
                candidati = sorted(strutturati, key=lambda m: (df == m).sum().sum())
                for medico in candidati:
                    pref = ds.at[df.at[i, "Giorno"], medico]
                    if pref in ["Ferie", "Corso", "Blocco"]: continue
                    if (pref == "No Giorno" and turno != "MeCAU Notte") or (pref == "No Notte" and turno == "MeCAU Notte"): continue
                    
                    # Vincoli di riposo e sovrapposizione
                    if medico in [df.at[i, "MeCAU 1"], df.at[i, "MeCAU 2"], df.at[i, "MeCAU Notte"]]: continue
                    if i > 0 and df.at[i-1, "MeCAU Notte"] == medico: continue # Riposo post-notte
                    
                    df.at[i, turno] = medico
                    break
        st.session_state.df_turni = df
        st.rerun()

    if col2.button("📥 Esporta in PDF"):
        output_pdf = genera_pdf(st.session_state.df_turni, anno, mese_idx, festivi_list)
        st.download_button("Scarica PDF", output_pdf, f"Programma_Turni_{mese_idx}_{anno}.pdf", "application/pdf")
    
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### Riepilogo Carico Orario")
    dati_bilancio = []
    for m in strutturati:
        ore_lavorate = (st.session_state.df_turni == m).sum().sum() * 12
        ore_abbuono = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum() * 7.6
        totale = ore_lavorate + ore_abbuono
        dati_bilancio.append({"Medico": m, "Ore Lavorate": ore_lavorate, "Abbuono (Ferie/Corsi)": ore_abbuono, "Totale": totale, "Delta": round(totale - target_ore, 1)})
    st.table(pd.DataFrame(dati_bilancio))
