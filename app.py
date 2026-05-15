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
    
    # CORREZIONE: Abbiamo rimosso il calcolo da qui perché le funzioni non sono ancora state definite.
    # La metrica verrà visualizzata in fondo alla sidebar tramite il comando st.sidebar.metric 
    # posizionato dopo il Punto 2.

  # --- FINE INPUT SIDEBAR ---
    # Nota: Il calcolo del debito orario è stato spostato nel Mainframe
    # subito dopo la definizione della funzione calcola_festivi per evitare NameError.
    
    st.divider()
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
# --- LOGICA CALCOLO ORE (Sostituisce il vecchio blocco sidebar) ---

def conta_feriali(year, month, lista_festivi):
    giorni_nel_mese = calendar.monthrange(year, month)[1]
    feriali = 0
    for d in range(1, giorni_nel_mese + 1):
        dt = datetime(year, month, d).date()
        # Un giorno è feriale se non è weekend e non è festivo
        if dt.weekday() < 5 and dt not in lista_festivi:
            feriali += 1
    return feriali

# Usiamo 'festivi_italiani' che è la variabile corretta definita appena sopra
giorni_f = conta_feriali(anno, mese_scelto, festivi_italiani)
ore_dovute_calcolate = round(giorni_f * 7.6, 1)

# Visualizzazione "iniettata" nella Sidebar
st.sidebar.metric(label="📊 Debito Orario Mensile", value=f"{ore_dovute_calcolate} h")
st.sidebar.caption(f"Basato su {giorni_f} giorni feriali (7.6h/gg)")

# --- FINE LOGICA ORE ---
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

# --- 4. VERIFICA VINCOLI (Punto 6a & 6b + Integrazione Settimanale/PA) ---
st.divider()
st.subheader("🛡️ Controllo Vincoli e Sicurezza")

errori_rilevati = []
avvisi_carenza = []

# Reset temporaneo delle notti per il ricalcolo coerente della griglia
notti_temp = {}

# --- [FASE 1] INIZIALIZZAZIONE CONTATORI ---
conteggio_settimanale = {nome: {} for nome in strutturati}
ore_contrattuali_mese = {nome: 0 for nome in strutturati}
ore_pa_mese = {nome: 0 for nome in strutturati}

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
            is_pa = " PA" in n
            lavoro_oggi.append({"nome": nome_pulito, "sala": sala, "is_pa": is_pa})

    # --- [FASE 2] LOGICA SETTIMANALE E CONTEGGIO ORE (DENTRO IL CICLO) ---
    for medico in lavoro_oggi:
        m_nome = medico["nome"]
        m_sala = medico["sala"]
        
        if m_nome in strutturati:
            # Identificazione settimana (ISO calendar)
            giorno_dt = datetime(anno, mese_scelto, giorno_corrente).date()
            sett_n = giorno_dt.isocalendar()[1]
            
            # Conteggio turni per settimana
            if sett_n not in conteggio_settimanale[m_nome]:
                conteggio_settimanale[m_nome][sett_n] = 0
            conteggio_settimanale[m_nome][sett_n] += 1
            
            # Conteggio Ore Mensili (Separazione PA)
            if medico["is_pa"]:
                ore_pa_mese[m_nome] += 12
            else:
                ore_contrattuali_mese[m_nome] += 12

            # --- VINCOLI PREESISTENTI (SMONTO/RIPOSO/BASSA INTENSITÀ) ---
            if m_sala == "Bassa Intensità":
                errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} (Strutturato) non può stare in Bassa Intensità!")

            if not medico["is_pa"]:
                if m_nome in notti_temp:
                    distanza = giorno_corrente - notti_temp[m_nome]
                    if distanza == 1:
                        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} è in SMONTO NOTTE (X+1)!")
                    elif distanza == 2:
                        avvisi_carenza.append(f"🟡 **{row['Giorno']}**: {m_nome} in deroga al riposo (X+2).")
                        notti_temp[m_nome] = giorno_corrente - 1

            if m_sala == "MeCAU Notte" and not medico["is_pa"]:
                notti_temp[m_nome] = giorno_corrente

    # VINCOLO 6a: UNICITÀ GIORNALIERA
    nomi_soli = [d["nome"] for d in lavoro_oggi]
    if len(nomi_soli) != len(set(nomi_soli)):
        duplicati = set([x for x in nomi_soli if nomi_soli.count(x) > 1])
        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {', '.join(duplicati)} duplicato nello stesso giorno!")

# --- [FASE 3] ANALISI SETTIMANALE E SIDEBAR (FUORI DAL CICLO) ---
for medico, settimane in conteggio_settimanale.items():
    for sett, n_turni in settimane.items():
        # Limite esteso a 5 se il medico ha turni PA nel mese
        limite_max = 5 if ore_pa_mese[medico] > 0 else 4
        
        if n_turni > 5:
            errori_rilevati.append(f"🚨 **Settimana {sett}**: {medico} ha superato il limite massimo assoluto ({n_turni} turni)!")
        elif n_turni > 4 and ore_pa_mese[medico] == 0:
            errori_rilevati.append(f"🚨 **Settimana {sett}**: {medico} ha {n_turni} turni senza PA. Max consentito: 4.")
        elif n_turni < 3 and n_turni > 0:
            avvisi_carenza.append(f"🔵 **Settimana {sett}**: {medico} ha solo {n_turni} turni. Minimo richiesto: 3.")

# Consuntivo in Sidebar
st.sidebar.divider()
st.sidebar.subheader("📈 Bilancio Ore Strutturati")
for medico in strutturati:
    fatte = ore_contrattuali_mese[medico]
    pa = ore_pa_mese[medico]
    delta = fatte - ore_dovute_calcolate
    colore = "green" if delta >= 0 else "orange"
    
    st.sidebar.markdown(f"**{medico}**")
    st.sidebar.write(f"Contrattuali: {fatte} / {ore_dovute_calcolate}h (:{colore}[{delta:+.1f}h])")
    if pa > 0:
        st.sidebar.write(f"✨ Ore in PA: **{pa} h**")

# Visualizzazione messaggi nel mainframe
if errori_rilevati or avvisi_carenza:
    for err in errori_rilevati: st.error(err)
    for warn in avvisi_carenza: st.warning(warn)
else:
    st.success("✅ Vincoli di sicurezza rispettati.")
