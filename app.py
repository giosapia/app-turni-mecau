import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random
from fpdf import FPDF

# --- CONFIGURAZIONE E COSTANTI ---
SALE_DIURNE = ["MeCAU 1", "MeCAU 2"]
SALA_NOTTE = "MeCAU Notte"
SALA_BASSA = "Bassa Intensità"
SALE_TUTTE = SALE_DIURNE + [SALA_NOTTE, SALA_BASSA]

OPZIONI_DESIDERATA = ["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]

# --- LOGICA CALENDARIO E FESTIVI ---
def get_festivi_susa(year):
    festivi_fissi = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    lista_date = [datetime(year, m, g).date() for m, g in festivi_fissi]
    
    # Pasqua e Pasquetta
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
    
    # Patrono Susa: Lunedì dopo la terza domenica di luglio
    luglio = [datetime(year, 7, d).date() for d in range(1, 32)]
    domeniche = [d for d in luglio if d.weekday() == 6]
    if len(domeniche) >= 3:
        lista_date.append(domeniche[2] + timedelta(days=1))
    return lista_date

def get_day_label(d, m, y, festivi):
    dt = datetime(y, m, d).date()
    nomi = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    base = f"{d}/{m} - {nomi[dt.weekday()]}"
    if dt in festivi or dt.weekday() == 6: return f"🔴 {base}"
    elif dt.weekday() == 5: return f"🟡 {base}"
    return f"⚪ {base}"

# --- ESPORTAZIONE PDF ---
def crea_pdf_susa(df, anno, mese_idx, festivi):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    mese_n = list(calendar.month_name)[mese_idx].upper()
    pdf.cell(0, 15, f"TURNI PRONTO SOCCORSO SUSA - {mese_n} {anno}", ln=True, align="C")
    
    headers = ["GIORNO", "MeCAU 1", "MeCAU 2", "NOTTE", "BASSA INT."]
    widths = [35, 60, 60, 60, 60]
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    for h, w in zip(headers, widths):
        pdf.cell(w, 10, h, border=1, align="C", fill=True)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 10)
    for i, row in df.iterrows():
        dt = datetime(anno, mese_idx, i + 1).date()
        fill = (dt in festivi or dt.weekday() >= 5)
        pdf.set_fill_color(240, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
        
        pdf.cell(widths[0], 9, row["Giorno"].split(" ", 1)[1], border=1, fill=fill)
        pdf.cell(widths[1], 9, str(row["MeCAU 1"]), border=1, align="C", fill=fill)
        pdf.cell(widths[2], 9, str(row["MeCAU 2"]), border=1, align="C", fill=fill)
        pdf.cell(widths[3], 9, str(row["MeCAU Notte"]), border=1, align="C", fill=fill)
        pdf.cell(widths[4], 9, str(row["Bassa Intensità"]), border=1, align="C", fill=fill)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Turni MeCAU Susa", layout="wide")
st.title("🚑 Gestione Turni PS Susa")

with st.sidebar:
    st.header("👥 Liste Medici")
    anno = st.number_input("Anno", value=2026)
    mese_idx = st.selectbox("Mese", range(1, 13), index=4)
    strutturati = [s.strip() for s in st.text_area("Strutturati (Solo MeCAU)", "Brancaleoni, Desiderio, Pazè, Sapia").split(",") if s.strip()]
    jolly = [j.strip() for j in st.text_area("Jolly (No Bassa Int.)", "Calasso, Melis, Sabbatino, Marsanic, Bruno, Castelli, Guglielmino, Trupja, Carbone, Dipietro, Di Stefano, Gili, Montebro, Ostuni, Palumbo, Ronco, Valobra, Vanoni, Veglio, Molino, Leoncini, Maurino, Tatarciuc, Sivera").split(",") if j.strip()]
    gettonisti = [g.strip() for g in st.text_area("Gettonisti (Solo Bassa Int.)", "Borgiotto, Moshkina, Mascalchi, Garrone, Passoni, Sardo").split(",") if g.strip()]

festivi_list = get_festivi_susa(anno)
num_days = calendar.monthrange(anno, mese_idx)[1]
giorni_feriali = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi_list)
target_mensile = giorni_feriali * 7.6

if 'session_id' not in st.session_state or st.session_state.session_id != f"{anno}-{mese_idx}":
    labels = [get_day_label(d, mese_idx, anno, festivi_list) for d in range(1, num_days + 1)]
    st.session_state.df_turni = pd.DataFrame("", index=range(num_days), columns=["Giorno"] + SALE_TUTTE)
    st.session_state.df_turni["Giorno"] = labels
    st.session_state.df_desid = pd.DataFrame("", index=labels, columns=strutturati)
    st.session_state.session_id = f"{anno}-{mese_idx}"

tab1, tab2, tab3 = st.tabs(["📋 Desiderata", "⚙️ Generazione", "📊 Bilancio"])

with tab1:
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, use_container_width=True, key="editor_desid")

with tab2:
    if st.button("🪄 Genera Turni Strutturati", type="primary"):
        df = st.session_state.df_turni.copy()
        ds = st.session_state.df_desid.copy()

        def calcola_ore_attuali(medico, temp_df):
            ferie_h = sum(7.6 for i, v in enumerate(ds[medico]) if v in ["Ferie", "Corso"] and datetime(anno, mese_idx, i+1).date().weekday() < 5 and datetime(anno, mese_idx, i+1).date() not in festivi_list)
            return (temp_df == medico).sum().sum() * 12 + ferie_h

        # 1. NOTTI (Priorità assoluta, max 4)
        for i in range(num_days):
            if df.at[i, SALA_NOTTE] != "": continue
            label = df.at[i, "Giorno"]
            candidati = sorted(strutturati, key=lambda m: calcola_ore_attuali(m, df))
            for m in candidati:
                if ds.at[label, m] in ["Ferie", "Corso", "Blocco", "No Notte"]: continue
                if (df[SALA_NOTTE] == m).sum() >= 4: continue
                if i > 0 and (df.at[i-1, SALA_NOTTE] == m): continue
                if i > 1 and (df.at[i-2, SALA_NOTTE] == m): continue
                if calcola_ore_attuali(m, df) + 12 > target_mensile + 12: continue
                df.at[i, SALA_NOTTE] = m; break

        # 2. GIORNO (MeCAU 1 e 2) con ritmo umano
        for i in range(num_days):
            label = df.at[i, "Giorno"]
            dt_curr = datetime(anno, mese_idx, i+1).date()
            # Shuffle per ruotare tra MeCAU 1 e 2
            sale_giorno = SALE_DIURNE.copy()
            random.shuffle(sale_giorno)
            
            for sala in sale_giorno:
                if df.at[i, sala] != "": continue
                candidati = sorted(strutturati, key=lambda m: calcola_ore_attuali(m, df))
                for m in candidati:
                    # Vincoli base
                    if ds.at[label, m] in ["Ferie", "Corso", "Blocco", "No Giorno"]: continue
                    if m in [df.at[i, s] for s in SALE_TUTTE if s != sala]: continue
                    # Riposo post-notte (almeno 2 giorni)
                    if i > 0 and df.at[i-1, SALA_NOTTE] == m: continue
                    if i > 1 and df.at[i-2, SALA_NOTTE] == m: continue
                    
                    # LOGICA RITMO UMANO (Evitare troppi giorni consecutivi)
                    # Controllo ultimi 3 giorni: se ha lavorato 2 volte su 3, oggi riposa (schema G-R-G o G-G-R)
                    lavorati_recenti = 0
                    for check_idx in range(max(0, i-3), i):
                        if (df.iloc[check_idx] == m).any(): lavorati_recenti += 1
                    if lavorati_recenti >= 2: continue

                    # Controllo Spalmatura: se siamo a metà mese e ha già fatto il 60% delle ore, frena
                    progressione_mese = (i + 1) / num_days
                    if calcola_ore_attuali(m, df) > (target_mensile * progressione_mese) + 12: continue
                    
                    df.at[i, sala] = m; break
        
        st.session_state.df_turni = df
        st.rerun()

    if st.button("📥 Esporta PDF"):
        pdf_bytes = crea_pdf_susa(st.session_state.df_turni, anno, mese_idx, festivi_list)
        st.download_button("Scarica PDF", data=pdf_bytes, file_name=f"Turni_Susa_{mese_idx}_{anno}.pdf", mime="application/pdf")

    # Editor principale
    opzioni_editor = [""] + strutturati + jolly + [f"{s} PA" for s in strutturati]
    opzioni_bassa = [""] + gettonisti + jolly
    
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config={
        "Giorno": st.column_config.TextColumn(disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn(options=opzioni_editor),
        "MeCAU 2": st.column_config.SelectboxColumn(options=opzioni_editor),
        "MeCAU Notte": st.column_config.SelectboxColumn(options=opzioni_editor),
        "Bassa Intensità": st.column_config.SelectboxColumn(options=opzioni_bassa)
    }, use_container_width=True, hide_index=True, key="main_grid")

with tab3:
    stats = []
    for m in strutturati:
        ore_l = (st.session_state.df_turni.isin([m])).sum().sum() * 12
        pa_h = (st.session_state.df_turni.isin([f"{m} PA"])).sum().sum() * 12
        ferie_h = sum(7.6 for i, v in enumerate(st.session_state.df_desid[m]) if v in ["Ferie", "Corso"] and datetime(anno, mese_idx, i+1).date().weekday() < 5 and datetime(anno, mese_idx, i+1).date() not in festivi_list)
        notti = (st.session_state.df_turni[SALA_NOTTE] == m).sum()
        stats.append({
            "Medico": m, 
            "Ore Tot (incl. Ferie)": ore_l + ferie_h, 
            "Delta": round(ore_l + ferie_h - target_mensile, 1),
            "di cui PA (h)": pa_h,
            "Notti": notti
        })
    st.table(pd.DataFrame(stats))
