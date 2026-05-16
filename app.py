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

# --- 🔄 FUNZIONE GENERATORE AUTOMATICO CORRETTA E BLINDATA SUI VINCOLI SETTIMANALI ---
def genera_turni_automatici():
    if key_stato not in st.session_state:
        return

    df_lavoro = st.session_state[key_stato].copy()
    colonne_auto = ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]
    
    # Rimescolamento per equità di distribuzione iniziale
    medici_random = strutturati.copy()
    random.shuffle(medici_random)

    for i in range(len(df_lavoro)):
        giorno_corrente = i + 1
        dt_corrente = datetime(anno, mese_scelto, giorno_corrente).date()
        sett_corrente = dt_corrente.isocalendar()[1]
        
        for col in colonne_auto:
            if df_lavoro.at[i, col] == "":
                for med in medici_random:
                    
                    # --- 1. FILTRO: SMONTO NOTTE REALE (X+1) ---
                    if i > 0 and df_lavoro.at[i - 1, "MeCAU Notte"] == med:
                        continue
                        
                    # --- 2. FILTRO: ANTI-DUPLICATO NELLO STESSO GIORNO ---
                    if (df_lavoro.iloc[i][colonne_auto] == med).any():
                        continue

                    # --- 3. FILTRO RIGIDO: MASSIMO 4 TURNI PER SETTIMANA SOLARE ---
                    # Scansiona l'intera tabella del mese per contare i turni reali in questa specifica settimana solare
                    turni_settimana_sim = 0
                    for idx_c in range(len(df_lavoro)):
                        dt_c = datetime(anno, mese_scelto, idx_c + 1).date()
                        if dt_c.isocalendar()[1] == sett_corrente:
                            if (df_lavoro.iloc[idx_c][colonne_auto] == med).any():
                                turni_settimana_sim += 1
                                
                    if turni_settimana_sim >= 4:
                        continue  # Salta il medico se ha già raggiunto o superato i 4 turni in questa settimana

                    # --- TEST INSERIMENTO PROVVISORIO ---
                    df_lavoro.at[i, col] = med
                    
                    # --- SIMULAZIONE DEI RESTANTI VINCOLI MENSILI (MONITORAGGIO SPOSTATO) ---
                    valido = True
                    conteggio_notti_sim = {nome: 0 for nome in strutturati}
                    wk_lavorati_sim = {nome: set() for nome in strutturati}
                    
                    for idx_s in range(i + 1):
                        g_s = idx_s + 1
                        dt_s = datetime(anno, mese_scelto, g_s).date()
                        is_weekend_s = dt_s.weekday() >= 5
                        
                        if dt_s.weekday() == 6:
                            id_wk_s = (dt_s - timedelta(days=1)).strftime("%Y-%U")
                        else:
                            id_wk_s = dt_s.strftime("%Y-%U")
                            
                        nomi_giorno_s = [
                            df_lavoro.at[idx_s, "MeCAU 1"],
                            df_lavoro.at[idx_s, "MeCAU 2"],
                            df_lavoro.at[idx_s, "MeCAU Notte"]
                        ]
                        
                        lavoro_oggi_s = [n.replace(" PA", "").strip() for n in nomi_giorno_s if n and isinstance(n, str) and n.strip() != ""]
                        
                        for m_s in lavoro_oggi_s:
                            if m_s in strutturati:
                                # Controllo Weekend Mensili (Massimo 2)
                                if is_weekend_s:
                                    wk_lavorati_sim[m_s].add(id_wk_s)
                                    if len(wk_lavorati_sim[m_s]) > 2:
                                        valido = False
                                        break
                                        
                                # Controllo Notti Mensili (Massimo 4)
                                if df_lavoro.at[idx_s, "MeCAU Notte"] == m_s:
                                    conteggio_notti_sim[m_s] += 1
                                    if conteggio_notti_sim[m_s] > 4:
                                        valido = False
                                        break
                        if not valido:
                            break
                            
                        # --- VERIFICA DESIDERATA ATTIVE ---
                        if med in desiderata_map:
                            for d in desiderata_map[med]:
                                if d["giorno"] == giorno_corrente:
                                    t = d["tipo"]
                                    if t in ["ferie", "corso", "no tutto il giorno", "no giorno"]: valido = False
                                    elif t == "no diurno" and col in ["MeCAU 1", "MeCAU 2"]: valido = False
                                    elif t == "no notte" and col == "MeCAU Notte"]: valido = False
                        if not valido:
                            break

                    if not valido:
                        df_lavoro.at[i, col] = ""
                    else:
                        break

    st.session_state[key_stato] = df_lavoro
    st.rerun()

def reset_griglia():
    if key_stato in st.session_state:
        del st.session_state[key_stato]
    st.rerun()

# Layout pulsanti di controllo
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("⚡ Generazione Automatica Strutturati", use_container_width=True):
        genera_turni_automatici()
with col_btn2:
    if st.button("🗑️ Svuota e Reset Tabella", use_container_width=True):
        reset_griglia()

# --- INTERFACCIA EDITING TABELLA ---
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

if not df_editabile.equals(st.session_state[key_stato]):
    st.session_state[key_stato] = df_editabile
    st.rerun()

# --- 4. VERIFICA VINCOLI ---
st.divider()
st.subheader("🛡️ Controllo Vincoli e Sicurezza")

errori_rilevati = []
avvisi_carenza = []
notti_temp = {}

# --- [FASE 1] INIZIALIZZAZIONE CONTATORI ---
conteggio_settimanale = {nome: {} for nome in strutturati}
conteggio_notti_mensili = {nome: 0 for nome in strutturati}
weekend_lavorati = {nome: set() for nome in strutturati} 
ore_contrattuali_mese = {nome: 0 for nome in strutturati}
ore_pa_mese = {nome: 0 for nome in strutturati}

for index, row in df_editabile.iterrows():
    giorno_corrente = index + 1
    dt_corrente = datetime(anno, mese_scelto, giorno_corrente).date()
    
    is_feriale = dt_corrente.weekday() < 5 and dt_corrente not in festivi_italiani
    is_weekend = dt_corrente.weekday() >= 5 
    
    if dt_corrente.weekday() == 6: 
        id_weekend = (dt_corrente - timedelta(days=1)).strftime("%Y-%U")
    else:
        id_weekend = dt_corrente.strftime("%Y-%U")
    
    for med, lista_des in desiderata_map.items():
        if med in strutturati and is_feriale:
            for d in lista_des:
                if d["giorno"] == giorno_corrente and d["tipo"] in ["ferie", "corso"]:
                    ore_contrattuali_mese[med] += 7.6

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

    # --- [FASE 2] LOGICA SETTIMANALE, ORE E VINCOLI ---
    for medico in lavoro_oggi:
        m_nome = medico["nome"]
        m_sala = medico["sala"]
        
        if m_nome in desiderata_map:
            for d in desiderata_map[m_nome]:
                if d["giorno"] == giorno_corrente:
                    tipo = d["tipo"]
                    conflitto = False
                    if tipo in ["ferie", "corso", "no tutto il giorno", "no giorno"]:
                        conflitto = True
                    elif tipo == "no diurno" and m_sala in ["MeCAU 1", "MeCAU 2", "Bassa Intensità"]:
                        conflitto = True
                    elif tipo == "no notte" and m_sala == "MeCAU Notte":
                        conflitto = True
                    if conflitto:
                        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} ha un vincolo '{tipo.upper()}'!")

        if m_nome in strutturati:
            sett_n = dt_corrente.isocalendar()[1]
            if sett_n not in conteggio_settimanale[m_nome]:
                conteggio_settimanale[m_nome][sett_n] = 0
            conteggio_settimanale[m_nome][sett_n] += 1
            
            if medico["is_pa"]:
                ore_pa_mese[m_nome] += 12
            else:
                ore_contrattuali_mese[m_nome] += 12
                if is_weekend:
                    weekend_lavorati[m_nome].add(id_weekend)

            if m_sala == "Bassa Intensità":
                errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} (Strutturato) non può stare in Bassa Intensità!")

            if not medico["is_pa"]:
                if m_nome in notti_temp:
                    distanza = giorno_corrente - notti_temp[m_nome]
                    if distanza == 1:
                        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} è in SMONTO NOTTE (X+1)!")
                    elif distanza == 2:
                        avvisi_carenza.append(f"🟡 **{row['Giorno']}**: {m_nome} in deroga al riposo (X+2).")
                
                if m_sala == "MeCAU Notte":
                    notti_temp[m_nome] = giorno_corrente
                    conteggio_notti_mensili[m_nome] += 1 

    nomi_soli = [d["nome"] for d in lavoro_oggi]
    if len(nomi_soli) != len(set(nomi_soli)):
        duplicati = set([x for x in nomi_soli if nomi_soli.count(x) > 1])
        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {', '.join(duplicati)} duplicato nello stesso giorno!")

# --- [FASE 3] ANALISI MENSILE E SIDEBAR ---
for medico, lista_wk in weekend_lavorati.items():
    n_wk = len(lista_wk)
    if n_wk > 2:
        errori_rilevati.append(f"🚨 **Limite Weekend**: {medico} ha lavorato {n_wk} weekend (Max: 2)!")

for medico, n_notti in conteggio_notti_mensili.items():
    if n_notti > 4:
        errori_rilevati.append(f"🚨 **Limite Notti**: {medico} ha troppe notti contrattuali ({n_notti}/4)!")

for medico, settimane in conteggio_settimanale.items():
    for sett, n_turni in settimane.items():
        limite_max = 5 if ore_pa_mese[medico] > 0 else 4
        if n_turni > limite_max:
            errori_rilevati.append(f"🚨 **Settimana {sett}**: {medico} ha troppi turni ({n_turni}). Max: {limite_max}")
        elif 0 < n_turni < 3:
            avvisi_carenza.append(f"🔵 **Settimana {sett}**: {medico} ha solo {n_turni} turni. Minimo richiesto: 3.")

# Sidebar
st.sidebar.divider()
st.sidebar.subheader("📈 Bilancio Ore Strutturati")
for medico in strutturati:
    fatte = ore_contrattuali_mese[medico]
    pa = ore_pa_mese[medico]
    delta = fatte - ore_dovute_calcolate
    colore = "green" if delta >= 0 else "orange"
    st.sidebar.markdown(f"**{medico}**")
    st.sidebar.write(f"Contrattuali: {fatte:.1f} / {ore_dovute_calcolate}h (:{colore}[{delta:+.1f}h])")
    if pa > 0: st.sidebar.write(f"✨ Ore in PA: **{pa} h**")

if errori_rilevati or avvisi_carenza:
    for err in errori_rilevati: st.error(err)
    for warn in avvisi_carenza: st.warning(warn)
else:
    st.success("✅ Vincoli di sicurezza rispettati.")
    
# --- 5. FUNZIONE GENERAZIONE PDF ---
st.divider()
st.subheader("🖨️ Esportazione")

def genera_pdf_mecau(df, mese_nome, anno_scelto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        rightMargin=15, 
        leftMargin=15, 
        topMargin=15, 
        bottomMargin=15
    )
    
    elementi = []
    styles = getSampleStyleSheet()
    
    stile_titolo = styles['Title']
    stile_titolo.fontSize = 14
    titolo = f"Programmazione Turni MeCAU Susa - {mese_nome} {anno_scelto}"
    elementi.append(Paragraph(titolo, stile_titolo))
    elementi.append(Spacer(1, 6))

    dati_per_tabella = [df.columns.tolist()] + df.values.tolist()
    tabella = Table(dati_per_tabella, colWidths=[60, 185, 185, 185, 185])
    
    stile = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 1.8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.8),
    ])
    
    for i, riga in enumerate(dati_per_tabella[1:], start=1):
        giorno_str = str(riga[0]).lower()
        if "🔴" in giorno_str or "dom" in giorno_str or "sab" in giorno_str:
            stile.add('BACKGROUND', (0, i),
