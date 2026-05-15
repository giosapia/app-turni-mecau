import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# Impostazioni pagina
st.set_page_config(page_title="Gestione Medici Susa", layout="wide")
st.title("🏥 Calendario Turni MeCAU Susa")

# --- 1. SIDEBAR: ANAGRAFICA (CONGELATO) ---
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

st.subheader(f"Pianificazione Turni - {mese_testo} {anno}")

# --- 3. EDITOR GRAFICO ---
df_editabile = st.data_editor(
    st.session_state[key_stato],
    column_config={
        "Giorno": st.column_config.TextColumn("Data", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=medici_mecau),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=medici_mecau),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=medici_mecau),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=medici_bassa)
    },
    hide_index=True,
    use_container_width=True,
    key="main_editor"
)

# Salvataggio immediato nello stato
st.session_state[key_stato] = df_editabile

# --- 4. VERIFICA VINCOLI (Punto 6a & 6b) ---
st.divider()
st.subheader("🛡️ Controllo Vincoli e Sicurezza")

errori_rilevati = []
avvisi_carenza = []
# Dizionario temporaneo per tracciare il riposo durante la scansione delle righe
riposo_dovuto = {} 

for index, row in df_editabile.iterrows():
    giorno_corrente = index + 1
    nomi_giorno = {
        "MeCAU 1": row["MeCAU 1"],
        "MeCAU 2": row["MeCAU 2"],
        "MeCAU Notte": row["MeCAU Notte"],
        "Bassa Intensità": row["Bassa Intensità"]
    }
    
    lavoro_oggi = []
    for sala, n in nomi_giorno.items():
        if n and isinstance(n, str) and n.strip() != "":
            nome_pulito = n.replace(" PA", "").strip()
            is_pa = " PA" in n
            lavoro_oggi.append({"nome": nome_pulito, "sala": sala, "is_pa": is_pa})

    # --- VINCOLO 6a: UNICITÀ GIORNALIERA ---
    nomi_soli = [d["nome"] for d in lavoro_oggi]
    if len(nomi_soli) != len(set(nomi_soli)):
        duplicati = set([x for x in nomi_soli if nomi_soli.count(x) > 1])
        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {', '.join(duplicati)} è inserito in più sale!")

    # --- VINCOLO 6b: REGOLE STRUTTURATI ---
    for medico in lavoro_oggi:
        m_nome = medico["nome"]
        m_sala = medico["sala"]
        
        if m_nome in strutturati:
            # 1. Esclusività Bassa Intensità
            if m_sala == "Bassa Intensità":
                errori_rilevati.append(f"🔴 **{row['Giorno']}**: Lo strutturato {m_nome} non può stare in Bassa Intensità!")

            # 2. Controllo Riposo (X+1, X+2)
            if m_nome in riposo_dovuto and riposo_dovuto[m_nome] <= giorno_corrente:
                if not medico["is_pa"]:
                    # Recuperiamo quando ha fatto l'ultima notte
                    ultima_notte = st.session_state.get(f"notte_{m_nome}", -10)
                    distanza = giorno_corrente - ultima_notte
                    
                    if distanza == 1:
                        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} è in SMONTO NOTTE (X+1). Vietato!")
                    elif distanza == 2:
                        avvisi_carenza.append(f"🟡 **{row['Giorno']}**: {m_nome} lavora in deroga al riposo (X+2). Recupero necessario domani.")
                        riposo_dovuto[m_nome] = giorno_corrente + 1 # Slitta al giorno X+3
                
            # 3. Se fa la NOTTE, imposta scadenza riposo
            if m_sala == "MeCAU Notte" and not medico["is_pa"]:
                st.session_state[f"notte_{m_nome}"] = giorno_corrente
                riposo_dovuto[m_nome] = giorno_corrente + 2 # Il riposo copre X+1 e X+2

# Visualizzazione finale dei messaggi
if errori_rilevati or avvisi_carenza:
    for err in errori_rilevati: st.error(err)
    for warn in avvisi_carenza: st.warning(warn)
else:
    st.success("✅ Vincoli di sicurezza rispettati.")
