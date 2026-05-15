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
    # ... [Sotto alla scelta di mese e anno nella Sidebar] ...
    mese_scelto = mesi_nomi.index(mese_testo) + 1

    # --- NUOVO: CALCOLO DEBITO ORARIO ---
    def conta_feriali(year, month, festivi):
        giorni_nel_mese = calendar.monthrange(year, month)[1]
        feriali = 0
        for d in range(1, giorni_nel_mese + 1):
            dt = datetime(year, month, d).date()
            # Un giorno è feriale se: 
            # 1. Non è Sabato (5) o Domenica (6)
            # 2. Non è tra i festivi nazionali/patronali
            if dt.weekday() < 5 and dt not in festivi:
                feriali += 1
        return feriali

    # Calcoliamo i festivi necessari per il conteggio dei feriali
    festivi_per_conteggio = calcola_festivi(anno, mese_scelto)
    giorni_feriali = conta_feriali(anno, mese_scelto, festivi_per_conteggio)
    ore_dovute = round(giorni_feriali * 7.6, 1)

    st.divider()
    st.sidebar.metric(label="📊 Debito Orario Mensile", value=f"{ore_dovute} h")
    st.sidebar.caption(f"Basato su {giorni_feriali} giorni feriali (7.6h/gg)")

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

medici_mecau = [""] + strutturati + jolly
medici_bassa = [""] + gettonisti

st.subheader(f"Pianificazione Turni - {mese_testo} {anno}")

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

st.session_state[key_stato] = df_editabile

# --- 4. VERIFICA VINCOLI (Punto 6a & 6b) ---
st.divider()
st.subheader("🛡️ Controllo Vincoli e Sicurezza")

errori_rilevati = []
avvisi_carenza = []

# Reset temporaneo delle notti per il ricalcolo coerente della griglia
notti_temp = {}

for index, row in df_editabile.iterrows():
    giorno_corrente = index + 1
    nomi_giorno = {
        "MeCAU 1": row["MeCAU 1"], "MeCAU 2": row["MeCAU 2"],
        "MeCAU Notte": row["MeCAU Notte"], "Bassa Intensità": row["Bassa Intensità"]
    }
    
    lavoro_oggi = []
    for sala, n in nomi_giorno.items():
        if n and isinstance(n, str) and n.strip() != "":
            nome_pulito = n.replace(" PA", "").strip()
            lavoro_oggi.append({"nome": nome_pulito, "sala": sala, "is_pa": " PA" in n})

    # VINCOLO 6a: UNICITÀ GIORNALIERA
    nomi_soli = [d["nome"] for d in lavoro_oggi]
    if len(nomi_soli) != len(set(nomi_soli)):
        duplicati = set([x for x in nomi_soli if nomi_soli.count(x) > 1])
        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {', '.join(duplicati)} duplicato nello stesso giorno!")

    # VINCOLO 6b: REGOLE STRUTTURATI
    for medico in lavoro_oggi:
        m_nome = medico["nome"]
        m_sala = medico["sala"]
        
        if m_nome in strutturati:
            # Esclusività Bassa Intensità
            if m_sala == "Bassa Intensità":
                errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} (Strutturato) non può stare in Bassa Intensità!")

            # Controllo Riposo (X+1 e X+2)
            if not medico["is_pa"]:
                if m_nome in notti_temp:
                    distanza = giorno_corrente - notti_temp[m_nome]
                    
                    if distanza == 1:
                        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} è in SMONTO NOTTE (X+1)!")
                    elif distanza == 2:
                        avvisi_carenza.append(f"🟡 **{row['Giorno']}**: {m_nome} in deroga al riposo (X+2).")
                        # Spostiamo la 'notte virtuale' per proteggere il giorno X+3
                        notti_temp[m_nome] = giorno_corrente - 1

            # Registrazione turno notturno
            if m_sala == "MeCAU Notte" and not medico["is_pa"]:
                notti_temp[m_nome] = giorno_corrente

# Visualizzazione messaggi
if errori_rilevati or avvisi_carenza:
    for err in errori_rilevati: st.error(err)
    for warn in avvisi_carenza: st.warning(warn)
else:
    st.success("✅ Vincoli di sicurezza rispettati.")
