import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random
from fpdf import FPDF

# --- COSTANTI E CONFIGURAZIONE ---
SALE = ["MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"]
OPZIONI_JOLLY = ["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]

# --- LOGICA CALENDARIO E FESTIVI ---
def get_festivi_susa(year):
    # Festivi fissi italiani
    festivi_fissi = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    lista_date = [datetime(year, m, g).date() for m, g in festivi_fissi]
    
    # Pasqua e Pasquetta (Algoritmo di Gauss)
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
    
    # Santo Patrono Susa: Lunedì dopo la terza domenica di Luglio
    luglio = [datetime(year, 7, d).date() for d in range(1, 32)]
    domeniche_luglio = [d for d in luglio if d.weekday() == 6]
    patrono = domeniche_luglio[2] + timedelta(days=1)
    lista_date.append(patrono)
    
    return lista_date

def get_day_label(d, m, y, festivi):
    dt = datetime(y, m, d).date()
    nomi = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    base = f"{d}/{m} - {nomi[dt.weekday()]}"
    if dt in festivi or dt.weekday() == 6: return f"🔴 {base}"
    elif dt.weekday() == 5: return f"🟡 {base}"
    return f"⚪ {base}"

# --- FUNZIONE PDF ---
def crea_pdf_susa(df, anno, mese_idx, festivi):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    # Intestazione specifica richiesta
    mese_nome = list(calendar.month_name)[mese_idx].capitalize()
    pdf.cell(0, 15, f"Turni Pronto Soccorso di Susa {mese_nome} {anno}", ln=True, align="C")
    pdf.ln(5)
    
    # Ordine colonne: MECAU 1, MECAU 2, NOTTE, BASSA INTENSITÀ
    headers = ["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Int."]
    widths = [35, 60, 60, 60, 60]
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200) # Grigio chiaro per stampa B/N
    for h, w in zip(headers, widths):
        pdf.cell(w, 10, h, border=1, align="C", fill=True)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 10)
    for i, row in df.iterrows():
        dt = datetime(anno, mese_idx, i + 1).date()
        # Colore sfondo celle festivi/weekend per B/N
        fill = False
        if dt in festivi or dt.weekday() >= 5:
            pdf.set_fill_color(240, 240, 240)
            fill = True
        
        pdf.cell(widths[0], 9, row["Giorno"].split(" ")[1] + " " + row["Giorno"].split(" ")[2], border=1, fill=fill)
        pdf.cell(widths[1], 9, str(row["MeCAU 1"]), border=1, align="C", fill=fill)
        pdf.cell(widths[2], 9, str(row["MeCAU 2"]), border=1, align="C", fill=fill)
        pdf.cell(widths[3], 9, str(row["MeCAU Notte"]), border=1, align="C", fill=fill)
        pdf.cell(widths[4], 9, str(row["Bassa Intensità"]), border=1, align="C", fill=fill)
        pdf.ln()
        
    return pdf.output()

# --- APP STREAMLIT ---
st.set_page_config(page_title="Turni MeCAU Susa", layout="wide")
st.title("🏥 Gestione Turni Pronto Soccorso Susa")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurazioni")
    anno = st.number_input("Anno", value=2026)
    mese_idx = st.selectbox("Mese", range(1, 13), index=4)
    
    strutturati = st.text_area("Lista Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia").split(",")
    strutturati = [s.strip() for s in strutturati if s.strip()]
    
    jolly_list = st.text_area("Lista Jolly", "Calasso, Melis, Sabbatino, Marsanic, Bruno, Castelli, Guglielmino, Trupja, Carbone, Dipietro, Di Stefano, Gili, Montebro, Ostuni, Palumbo, Ronco, Valobra, Vanoni, Veglio, Molino, Leoncini, Maurino, Tatarciuc, Sivera").split(",")
    jolly_list = [j.strip() for j in jolly_list if j.strip()]
    
    gettonisti = st.text_area("Lista Gettonisti", "Borgiotto, Moshkina, Mascalchi, Garrone, Passoni, Sardo").split(",")
    gettonisti = [g.strip() for g in gettonisti if g.strip()]

# Calcoli Iniziali
festivi_list = get_festivi_susa(anno)
num_days = calendar.monthrange(anno, mese_idx)[1]
giorni_feriali = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi_list)
target_mensile = giorni_feriali * 7.6

# Session State
if 'session_id' not in st.session_state or st.session_state.session_id != f"{anno}-{mese_idx}":
    labels = [get_day_label(d, mese_idx, anno, festivi_list) for d in range(1, num_days + 1)]
    st.session_state.df_turni = pd.DataFrame("", index=range(num_days), columns=["Giorno"] + SALE)
    st.session_state.df_turni["Giorno"] = labels
    st.session_state.df_desid = pd.DataFrame("", index=labels, columns=strutturati)
    st.session_state.session_id = f"{anno}-{mese_idx}"

tab1, tab2, tab3 = st.tabs(["📅 Desiderata e Jolly", "🛠️ Generazione Turni", "📊 Bilancio Ore"])

with tab1:
    st.subheader("Inserimento Indisponibilità e Jolly")
    config_des = {m: st.column_config.SelectboxColumn(m, options=OPZIONI_JOLLY) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_des, use_container_width=True)

with tab2:
    col_btn1, col_btn2 = st.columns(2)
    
    if col_btn1.button("🪄 Genera Programmazione Ottimizzata", type="primary"):
        df = st.session_state.df_turni.copy()
        ds = st.session_state.df_desid.copy()
        for c in SALE: df[c] = "" # Reset

        # 1. NOTTI (Priorità Massima)
        for i in range(num_days):
            label = df.at[i, "Giorno"]
            cand = sorted(strutturati, key=lambda m: (df == m).sum().sum())
            for m in cand:
                if ds.at[label, m] in ["Ferie", "Corso", "Blocco", "No Notte"]: continue
                # Vincolo Riposo Post-Notte (2 giorni obbligatori)
                if i > 0 and (df.at[i-1, "MeCAU Notte"] == m): continue
                if i > 1 and (df.at[i-2, "MeCAU Notte"] == m): continue
                # Limite 4 notti
                if (df["MeCAU Notte"] == m).sum() >= 4: continue
                df.at[i, "MeCAU Notte"] = m; break

        # 2. DIURNI MeCAU 1 e 2
        for t in ["MeCAU 1", "MeCAU 2"]:
            for i in range(num_days):
                label = df.at[i, "Giorno"]
                cand = sorted(strutturati, key=lambda m: (df == m).sum().sum())
                for m in cand:
                    if ds.at[label, m] in ["Ferie", "Corso", "Blocco", "No Giorno"]: continue
                    if m in [df.at[i, "MeCAU 1"], df.at[i, "MeCAU 2"], df.at[i, "MeCAU Notte"]]: continue
                    # Smonto notte
                    if i > 0 and (df.at[i-1, "MeCAU Notte"] == m): continue
                    if i > 1 and (df.at[i-2, "MeCAU Notte"] == m): continue
                    # Target orario
                    ore = (df == m).sum().sum() * 12 + ds[m].isin(["Ferie", "Corso"]).sum() * 7.6
                    if ore >= target_mensile + 12: continue
                    
                    df.at[i, t] = m; break
        
        # 3. BASSA INTENSITÀ (Solo Gettonisti)
        for i in range(num_days):
            if gettonisti: df.at[i, "Bassa Intensità"] = random.choice(gettonisti)

        st.session_state.df_turni = df
        st.rerun()

    if col_btn2.button("📥 Esporta in PDF"):
        pdf_out = crea_pdf_susa(st.session_state.df_turni, anno, mese_idx, festivi_list)
        st.download_button("Scarica PDF", pdf_out, f"Turni_Susa_{mese_idx}_{anno}.pdf", "application/pdf")

    # Editor Manuale con liste a discesa
    lista_completa = [""] + strutturati + jolly_list + [f"{s} PA" for s in strutturati]
    config_griglia = {
        "Giorno": st.column_config.TextColumn(disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn(options=lista_completa),
        "MeCAU 2": st.column_config.SelectboxColumn(options=lista_completa),
        "MeCAU Notte": st.column_config.SelectboxColumn(options=lista_completa),
        "Bassa Intensità": st.column_config.SelectboxColumn(options=[""] + gettonisti)
    }
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config=config_griglia, use_container_width=True, hide_index=True)

with tab3:
    st.subheader(f"Statistiche Mensili (Target: {target_mensile:.1f}h)")
    metrics = []
    for m in strutturati:
        # Conteggi
        ore_lavorate = (st.session_state.df_turni.isin([m])).sum().sum() * 12
        n_pa = (st.session_state.df_turni.isin([f"{m} PA"])).sum().sum()
        n_notti = (st.session_state.df_turni["MeCAU Notte"] == m).sum()
        
        # Abbuono ferie (Solo feriali)
        ferie_feriali = 0
        for i, val in enumerate(st.session_state.df_desid[m]):
            dt = datetime(anno, mese_idx, i+1).date()
            if val in ["Ferie", "Corso"] and dt.weekday() < 5 and dt not in festivi_list:
                ferie_feriali += 7.6
        
        totale = ore_lavorate + ferie_feriali
        delta = round(totale - target_mensile, 1)
        
        metrics.append({
            "Medico": m, "Ore Lav.": ore_lavorate, "Abbuono": ferie_feriali, 
            "Totale": totale, "Delta": delta, "Notti": n_notti, "PA": n_pa
        })
    st.dataframe(pd.DataFrame(metrics), use_container_width=True)
