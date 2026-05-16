import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import io
import random  
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Impostazioni pagina
st.set_page_config(page_title="Gestione Medici Susa", layout="wide")
st.title("🏥 Calendario Turni MeCAU Susa")

# --- 1. SIDEBAR: ANAGRAFICA E DESIDERATA (Aggiornato) ---
with st.sidebar:
    st.header("👥 Anagrafica Medici")
    
    lista_strutturati = st.text_area("1. Medici Strutturati", value="Brancaleoni, Desiderio, Pazè, Sapia")
    strutturati = [s.strip() for s in lista_strutturati.split(",") if s.strip()]

    lista_jolly = st.text_area("2. Medici Jolly", value="Calasso, Melis, Sabbatino, Marsanic, Bruno, Castelli, Guglielmino, Trupja, Carbone, Dipietro, Di Stefano, Gili, Montebro, Ostuni, Palumbo, Ronco, Valobra, Vanoni, Veglio, Molino, Leoncini, Maurino, Tatarciuc, Sivera, Vellata, Isidori")
    jolly = [j.strip() for j in lista_jolly.split(",") if j.strip()]

    lista_gettonisti = st.text_area("3. Medici Gettonisti", value="Borgiotto, Moshkina, Mascalchi, Garrone, Passoni, Sardo")
    gettonisti = [g.strip() for g in lista_gettonisti.split(",") if g.strip()]

    st.divider()
    
    st.header("📅 Periodo di Riferimento")
    anno = st.number_input("Anno", min_value=2024, max_value=2030, value=2026)
    mesi_nomi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_testo = st.selectbox("Mese", mesi_nomi, index=4) 
    mese_scelto = mesi_nomi.index(mese_testo) + 1
    
    st.divider()

    # --- NUOVA SEZIONE: DESIDERATA E FERIE (Con supporto Range 1-31) ---
    st.header("🚫 Desiderata e Ferie")
    st.caption("Tipi: Ferie, Corso, No Diurno, No Notte, No Tutto il Giorno")
    st.caption("Esempi: Sapia: No Notte 1-31; Brancaleoni: Ferie 10-15, Corso 20")
    testo_desiderata = st.text_area("Inserisci Desiderata (separa i medici con ';')", value="")
    
    desiderata_map = {}
    if testo_desiderata:
        for riga in testo_desiderata.split(";"):
            if ":" in riga:
                med, istruzioni = riga.split(":")
                med_nome = med.strip()
                desiderata_map[med_nome] = []
                for istruzione in istruzioni.split(","):
                    parti = istruzione.strip().split()
                    if len(parti) >= 2:
                        tipo = " ".join(parti[:-1]).lower().strip()
                        giorno_str = parti[-1]
                        
                        # Gestione del Range (es. 1-15)
                        if "-" in giorno_str:
                            try:
                                inizio, fine = map(int, giorno_str.split("-"))
                                for g in range(inizio, fine + 1):
                                    desiderata_map[med_nome].append({"tipo": tipo, "giorno": g})
                            except ValueError: pass
                        # Gestione giorno singolo
                        else:
                            try:
                                giorno = int(giorno_str)
                                desiderata_map[med_nome].append({"tipo": tipo, "giorno": giorno})
                            except ValueError: pass

    st.divider()
# --- FINE INPUT SIDEBAR ---

# --- 2. LOGICA FESTIVITÀ (CONGELATO) ---
def calcola_festivi(year, month):
    fisse = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    festivi = [datetime(year, m, g).date() for m, g in fisse]
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
    festivi.extend([pasqua, pasqua + timedelta(days=1)])
    if month == 7:
        dom = [datetime(year, 7, d).date() for d in range(1, 32) if datetime(year, 7, d).weekday() == 6]
        if len(dom) >= 3: festivi.append(dom[2] + timedelta(days=1))
    return festivi

festivi_italiani = calcola_festivi(anno, mese_scelto)

# --- LOGICA CALCOLO ORE ---
def conta_feriali(year, month, lista_festivi):
    giorni_nel_mese = calendar.monthrange(year, month)[1]
    feriali = 0
    for d in range(1, giorni_nel_mese + 1):
        dt = datetime(year, month, d).date()
        if dt.weekday() < 5 and dt not in lista_festivi:
            feriali += 1
    return feriali

giorni_f = conta_feriali(anno, mese_scelto, festivi_italiani)
ore_dovute_calcolate = round(giorni_f * 7.6, 1)

st.sidebar.metric(label="📊 Debito Orario Mensile", value=f"{ore_dovute_calcolate} h")
st.sidebar.caption(f"Basato su {giorni_f} giorni feriali (7.6h/gg)")

# --- 3. LAYOUT GRAFICO E GRIGLIA ---
key_stato = f"griglia_{mese_scelto}_{anno}_v3_final"

if key_stato not in st.session_state:
    num_days = calendar.monthrange(anno, mese_scelto)[1]
    ita_giorni = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    
    data = []
    for d in range(1, num_days + 1):
        dt = datetime(anno, mese_scelto, d).date()
        if dt in festivi_italiani:
            pref = "🔴"
        elif dt.weekday() >= 5:
            pref = "🟡"
        else:
            pref = "⚪"
            
        data.append({
            "Giorno": f"{pref} {d} {ita_giorni[dt.weekday()]}",
            "MeCAU 1": "", "MeCAU 2": "", "MeCAU Notte": "", "Bassa Intensità": ""
        })
    st.session_state[key_stato] = pd.DataFrame(data)

# --- 3. AGGIORNAMENTO LISTE PER PA ---
opzioni_strutturati_pa = []
for s in strutturati:
    opzioni_strutturati_pa.append(s)          
    opzioni_strutturati_pa.append(f"{s} PA") 

medici_mecau = [""] + opzioni_strutturati_pa + jolly
medici_bassa = [""] + gettonisti

st.subheader(f"Pianificazione Turni - {mese_testo} {anno}")

# --- 🔄 FUNZIONE GENERATORE AUTOM
