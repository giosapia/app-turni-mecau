import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import io
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
# --- NUOVA FUNZIONE: GENERAZIONE AUTOMATICA (Protocollo 2.1) ---
def genera_turni_automatici():
    # Verifichiamo che la griglia sia già stata inizializzata
    if key_stato not in st.session_state:
        return
        
    df_lavoro = st.session_state[key_stato].copy()
    target = ore_dovute_calcolate
    colonne_auto = ["MeCAU Notte", "MeCAU 1", "MeCAU 2"]
    
    for col in colonne_auto:
        for i in range(len(df_lavoro)):
            # Operiamo solo sulle celle vuote
            if df_lavoro.iloc[i][col] == "" or df_lavoro.iloc[i][col] is None:
                giorno_corrente = i + 1
                dt_corrente = datetime(anno, mese_scelto, giorno_corrente).date()
                
                candidati_validi = []
                for med in strutturati:
                    # --- FILTRI HARD (VINCOLI DI SICUREZZA) ---
                    # 1. Desiderata (Ferie, Corsi, No Notte, ecc.)
                    ha_vincolo = False
                    if med in desiderata_map:
                        for d in desiderata_map[med]:
                            if d["giorno"] == giorno_corrente:
                                if d["tipo"] in ["ferie", "corso", "no tutto il giorno"]: ha_vincolo = True
                                if d["tipo"] == "no diurno" and col in ["MeCAU 1", "MeCAU 2"]: ha_vincolo = True
                                if d["tipo"] == "no notte" and col == "MeCAU Notte": ha_vincolo = True
                    if ha_vincolo: continue

                    # 2. Smonto Notte (X+1)
                    if i > 0 and df_lavoro.at[i-1, "MeCAU Notte"] == med: continue
                    
                    # 3. Limite 4 Notti
                    if col == "MeCAU Notte" and (df_lavoro["MeCAU Notte"] == med).sum() >= 4: continue
                    
                   # 4. Limite 2 Weekend (Hard Constraint)
                    is_wk = dt_corrente.weekday() >= 5
                    if is_wk:
                        # Contiamo quanti giorni di weekend ha già in tabella
                        giorni_wk_lavorati = 0
                        for d_idx in range(len(df_lavoro)):
                            dt_temp = datetime(anno, mese_scelto, d_idx+1).date()
                            if dt_temp.weekday() >= 5:
                                if (df_lavoro.iloc[d_idx][colonne_auto] == med).any():
                                    giorni_wk_lavorati += 1
                        
                        # Se ha già raggiunto i 4 turni (2 weekend), lo escludiamo
                        if giorni_wk_lavorati >= 4: 
                            continue
# 4b. Verifica se il medico è già assegnato ad un'altra sala nello stesso giorno
                    # Questo impedisce i duplicati "Brancaleoni - Brancaleoni" nello stesso giorno
                    if (df_lavoro.iloc[i][["MeCAU 1", "MeCAU 2", "MeCAU Notte"]] == med).any():
                        continue
                    # 5. Stop al raggiungimento Monte Ore
                    # Conteggio turni già assegnati (12h ciascuno)
                    ore_fatte = (df_lavoro == med).sum().sum() * 12
                    # Aggiunta crediti per ferie/corsi
                    if med in desiderata_map:
                        for d in desiderata_map[med]:
                            dt_des = datetime(anno, mese_scelto, d["giorno"]).date()
                            if d["tipo"] in ["ferie", "corso"] and dt_des.weekday() < 5 and dt_des not in festivi_italiani:
                                ore_fatte += 7.6
                    
                    if ore_fatte >= target: continue

                    candidati_validi.append(med)

                if candidati_validi:
                    # Logica Soft: Preferenza per chi ha lavorato meno ore per equità
                    candidati_validi.sort(key=lambda m: (df_lavoro == m).sum().sum())
                    
                    # Logica Soft: Weekend consecutivo (Deroga se necessario)
                    if dt_corrente.weekday() >= 5 and i >= 7:
                        med_scelto = candidati_validi[0]
                        # Controlla se ha lavorato nel weekend precedente (7 giorni fa)
                        ha_lavorato_scorso = (df_lavoro.iloc[max(0, i-7):i][colonne_auto] == med_scelto).any().any()
                        if ha_lavorato_scorso and len(candidati_validi) > 1:
                            med_scelto = candidati_validi[1] 
                        df_lavoro.at[i, col] = med_scelto
                    else:
                        df_lavoro.at[i, col] = candidati_validi[0]

    # Aggiornamento dello stato e refresh
    st.session_state[key_stato] = df_lavoro
    st.rerun()
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

# --- 3. AGGIORNAMENTO LISTE PER PA ---
opzioni_strutturati_pa = []
for s in strutturati:
    opzioni_strutturati_pa.append(s)          # Nome standard per monte ore
    opzioni_strutturati_pa.append(f"{s} PA") # Variante per libera professione

medici_mecau = [""] + opzioni_strutturati_pa + jolly
medici_bassa = [""] + gettonisti

st.subheader(f"Pianificazione Turni - {mese_testo} {anno}")

# --- LOGICA DI GESTIONE TABELLA CORRETTA ---

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
    key="main_editor" # Manteniamo questa chiave fissa
)

# Sincronizzazione immediata: questo garantisce che al prossimo 'rerun' 
# lo stato sia già aggiornato al primo colpo.
if not df_editabile.equals(st.session_state[key_stato]):
    st.session_state[key_stato] = df_editabile
    st.rerun()

# --- 4. VERIFICA VINCOLI (Versione Corretta) ---
st.divider()
st.subheader("🛡️ Controllo Vincoli e Sicurezza")

errori_rilevati = []
avvisi_carenza = []

# --- [FASE 1] INIZIALIZZAZIONE CONTATORI ---
conteggio_settimanale = {nome: {} for nome in strutturati}
conteggio_notti_mensili = {nome: 0 for nome in strutturati}
weekend_lavorati = {nome: set() for nome in strutturati} 
ore_contrattuali_mese = {nome: 0 for nome in strutturati}
ore_pa_mese = {nome: 0 for nome in strutturati}
notti_temp = {} 

for index, row in df_editabile.iterrows():
    giorno_corrente = index + 1
    dt_corrente = datetime(anno, mese_scelto, giorno_corrente).date()
    
    is_feriale = dt_corrente.weekday() < 5 and dt_corrente not in festivi_italiani
    is_weekend = dt_corrente.weekday() >= 5 
    
    if dt_corrente.weekday() == 6: # Domenica
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

    # --- [FASE 2] LOGICA SETTIMANALE E VINCOLI ---
    for medico in lavoro_oggi:
        m_nome = medico["nome"]
        m_sala = medico["sala"]
        
        if m_nome in desiderata_map:
            for d in desiderata_map[m_nome]:
                if d["giorno"] == giorno_corrente:
                    tipo = d["tipo"]
                    conf = False
                    if tipo in ["ferie", "corso", "no tutto il giorno", "no giorno"]: conf = True
                    elif tipo == "no diurno" and m_sala in ["MeCAU 1", "MeCAU 2", "Bassa Intensità"]: conf = True
                    elif tipo == "no notte" and m_sala == "MeCAU Notte": conf = True
                    if conf: errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} ha un vincolo '{tipo.upper()}'!")

        if m_nome in strutturati:
            sett_n = dt_corrente.isocalendar()[1]
            if sett_n not in conteggio_settimanale[m_nome]:
                conteggio_settimanale[m_nome][sett_n] = 0
            conteggio_settimanale[m_nome][sett_n] += 1
            
            if medico["is_pa"]:
                ore_pa_mese[m_nome] += 12
            else:
                ore_contrattuali_mese[m_nome] += 12
                if is_weekend: weekend_lavorati[m_nome].add(id_weekend)

            if not medico["is_pa"]:
                if m_nome in notti_temp:
                    dist = giorno_corrente - notti_temp[m_nome]
                    if dist == 1: errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} in SMONTO NOTTE!")
                    elif dist == 2: avvisi_carenza.append(f"🟡 **{row['Giorno']}**: {m_nome} in deroga riposo (X+2).")
                
                if m_sala == "MeCAU Notte":
                    notti_temp[m_nome] = giorno_corrente
                    conteggio_notti_mensili[m_nome] += 1 

    nomi_soli = [d["nome"] for d in lavoro_oggi]
    if len(nomi_soli) != len(set(nomi_soli)):
        duplicati = set([x for x in nomi_soli if nomi_soli.count(x) > 1])
        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {', '.join(duplicati)} duplicato oggi!")

# --- [FASE 3] ANALISI MENSILE ---
for medico, lista_wk in weekend_lavorati.items():
    if len(lista_wk) > 2:
        errori_rilevati.append(f"🚨 **Limite Weekend**: {medico} ha lavorato {len(lista_wk)} weekend (Max: 2)!")

for medico, n_notti in conteggio_notti_mensili.items():
    if n_notti > 4:
        errori_rilevati.append(f"🚨 **Limite Notti**: {medico} ha troppe notti ({n_notti}/4)!")

for medico, settimane in conteggio_settimanale.items():
    for sett, n_turni in settimane.items():
        if n_turni > 4:
            errori_rilevati.append(f"🚨 **Settimana {sett}**: {medico} ha {n_turni} turni (Max: 4)!")

if errori_rilevati or avvisi_carenza:
    for err in errori_rilevati: st.error(err)
    for warn in avvisi_carenza: st.warning(warn)
else:
    st.success("✅ Vincoli di sicurezza rispettati.")
    
# --- 5. FUNZIONE GENERAZIONE PDF E PULSANTE ---
st.divider()
st.subheader("🖨️ Esportazione")

def genera_pdf_mecau(df, mese_nome, anno_scelto):
    # Creazione di un buffer di memoria per il file
    buffer = io.BytesIO()
    
    # Margini del foglio ridotti a 15pt
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
    
    # Configurazione Titolo
    stile_titolo = styles['Title']
    stile_titolo.fontSize = 14
    titolo = f"Programmazione Turni MeCAU Susa - {mese_nome} {anno_scelto}"
    elementi.append(Paragraph(titolo, stile_titolo))
    elementi.append(Spacer(1, 6))

    # Conversione DataFrame per ReportLab
    dati_per_tabella = [df.columns.tolist()] + df.values.tolist()

    # Definizione larghezza colonne
    tabella = Table(dati_per_tabella, colWidths=[60, 185, 185, 185, 185])
    
    # Stile della tabella
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
    
    # Colorazione righe: Weekend e Festivi in GIALLO
    for i, riga in enumerate(dati_per_tabella[1:], start=1):
        giorno_str = str(riga[0]).lower()
        
        # Evidenziazione in giallo per sabato, domenica e festivi (🔴)
        if "🔴" in giorno_str or "dom" in giorno_str or "sab" in giorno_str:
            stile.add('BACKGROUND', (0, i), (-1, i), colors.yellow)

    tabella.setStyle(stile)
    elementi.append(tabella)
    
    # Costruzione finale del PDF
    doc.build(elementi)
    buffer.seek(0)
    return buffer

# Creazione effettiva del file pronto al download
try:
    file_pdf = genera_pdf_mecau(df_editabile, mese_testo, anno)
    
    st.download_button(
        label="📥 Scarica Turni in PDF",
        data=file_pdf,
        file_name=f"Turni_MeCAU_Susa_{mese_testo}_{anno}.pdf",
        mime="application/pdf",
    )
except Exception as e:
    st.error(f"Errore nella generazione del PDF: {e}")

# --- NUOVA FUNZIONE: RESET SELETTIVO ---
def reset_solo_strutturati():
    if key_stato in st.session_state:
        df_reset = st.session_state[key_stato].copy()
        colonne_da_pulire = ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]
        
        # Creiamo una lista di nomi da rimuovere (sia standard che " PA")
        nomi_da_rimuovere = strutturati + [f"{s} PA" for s in strutturati]
        
        for col in colonne_da_pulire:
            # Sostituiamo con stringa vuota solo se il nome è tra gli strutturati
            df_reset[col] = df_reset[col].apply(lambda x: "" if x in nomi_da_rimuovere else x)
        
        st.session_state[key_stato] = df_reset
        st.rerun()

# --- AGGIORNAMENTO LAYOUT PULSANTI ---
st.divider()
st.info("💡 **Suggerimento**: Inserisci prima i turni fissi, poi usa la generazione. Se il risultato non ti soddisfa, usa 'Svuota Strutturati' e riprova.")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🗑️ Svuota Solo Strutturati", use_container_width=True):
        reset_solo_strutturati()

with col_btn2:
    if st.button("🤖 Genera Automatica", use_container_width=True, type="primary"):
        genera_turni_automatici()

# --- 6. PULSANTE DI GENERAZIONE AUTOMATICA (POSIZIONE FINALE) ---
st.divider()
st.info("💡 **Suggerimento**: Inserisci prima i turni fissi o le preferenze a mano nella tabella sopra, poi usa il tasto qui sotto per completare i turni mancanti dei medici strutturati.")

col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    if st.button("🤖 Genera Automatica Turni Strutturati", use_container_width=True, type="primary"):
        genera_turni_automatici()
