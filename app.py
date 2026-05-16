import streamlit as st  # Fix #1: 'i' mancante in 'mport'
import pandas as pd
from datetime import datetime, timedelta
import calendar
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import random

# Impostazioni pagina
st.set_page_config(page_title="Gestione Medici Susa", layout="wide")
st.title("🏥 Calendario Turni MeCAU Susa")

# --- 1. SIDEBAR: ANAGRAFICA E DESIDERATA ---
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
    mesi_nomi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                 "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    mese_testo = st.selectbox("Mese", mesi_nomi, index=4)
    mese_scelto = mesi_nomi.index(mese_testo) + 1

    st.divider()

    # --- SEZIONE DESIDERATA E FERIE ---
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
                            except ValueError:
                                pass
                        # Gestione giorno singolo
                        else:
                            try:
                                giorno = int(giorno_str)
                                desiderata_map[med_nome].append({"tipo": tipo, "giorno": giorno})
                            except ValueError:
                                pass

    st.divider()

    # --- SEZIONE VISUALIZZAZIONE LIVE: COUNTDOWN ORE STRUTTURATI ---
    st.header("📊 Resoconto Ore Mese")

    ore_con = st.session_state.get("ore_contrattuali_aggiornate", {m: 0.0 for m in strutturati})
    ore_pa = st.session_state.get("ore_pa_aggiornate", {m: 0.0 for m in strutturati})
    monte_ore_target = st.session_state.get("monte_ore_dinamico", 0.0)

    if monte_ore_target == 0:
        st.info("ℹ️ Inserisci o genera dei turni per calcolare il monte ore.")
    else:
        for med in strutturati:
            ore_fatte = ore_con.get(med, 0.0)
            ore_pa_fatte = ore_pa.get(med, 0.0)
            ore_restanti = monte_ore_target - ore_fatte

            if ore_restanti > 12:
                stato_colore = "🟢"
            elif ore_restanti >= -12:
                stato_colore = "🟡"
            else:
                stato_colore = "🚨"

            titolo_expander = f"{stato_colore} **{med}** ({ore_fatte:.1f}h / {monte_ore_target:.1f}h)"
            with st.expander(titolo_expander):
                st.write(f"⏳ **Ore Contrattuali**: {ore_fatte:.1f} h")
                st.write(f"💼 **Libera Prof. (PA)**: {ore_pa_fatte:.1f} h")
                st.write(f"🎯 **Target Mese**: {monte_ore_target:.1f} h")

                if ore_restanti >= 0:
                    st.write(f"📉 **Mancano**: {ore_restanti:.1f} h al pareggio")
                else:
                    st.write(f"📈 **Esubero**: {abs(ore_restanti):.1f} h")

    st.divider()
# --- FINE INPUT SIDEBAR ---


# --- 2. LOGICA FESTIVITÀ ---
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
        # Fix #6: uso di calendar.monthrange per range sicuro
        giorni_luglio = calendar.monthrange(year, 7)[1]
        dom = [datetime(year, 7, d).date() for d in range(1, giorni_luglio + 1)
               if datetime(year, 7, d).weekday() == 6]
        if len(dom) >= 3:
            festivi.append(dom[2] + timedelta(days=1))
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
# --- FINE LOGICA ORE ---


# --- FUNZIONE GENERAZIONE AUTOMATICA ---
def genera_turni_automatici():
    if key_stato not in st.session_state:
        return

    df_lavoro = st.session_state[key_stato].copy()
    colonne_auto = ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]
    
    # Mischiamo i medici per garantire un'equa rotazione di partenza
    medici_random = strutturati.copy()
    random.shuffle(medici_random)

    for i in range(len(df_lavoro)):
        giorno_corrente = i + 1
        dt_corrente = datetime(anno, mese_scelto, giorno_corrente).date()
        
        # Identificazione ID Weekend (Stessa identica logica del Punto 4)
        if dt_corrente.weekday() == 6: # Domenica
            id_wk_corrente = (dt_corrente - timedelta(days=1)).strftime("%Y-%U")
        else:
            id_wk_corrente = dt_corrente.strftime("%Y-%U")
            
        sett_corrente = dt_corrente.isocalendar()[1]

        for col in colonne_auto:
            # Procediamo all'assegnazione solo se la cella è vuota
            if df_lavoro.at[i, col] == "":
                for med in medici_random:
                    
                    # --- FILTRO 1: DESIDERATA ---
                    skip = False
                    if med in desiderata_map:
                        for d in desiderata_map[med]:
                            if d["giorno"] == giorno_corrente:
                                t = d["tipo"]
                                if t in ["ferie", "corso", "no tutto il giorno", "no giorno"]: skip = True
                                elif t == "no diurno" and col in ["MeCAU 1", "MeCAU 2"]: skip = True
                                elif t == "no notte" and col == "MeCAU Notte": skip = True
                    if skip: continue

                    # --- FILTRO 2: SMONTO NOTTE (X+1) ---
                    if i > 0:
                        if df_lavoro.at[i-1, "MeCAU Notte"] == med:
                            continue

                    # --- FILTRO 3: ANTI-DUPLICATO (Nello stesso giorno) ---
                    if (df_lavoro.iloc[i][colonne_auto] == med).any():
                        continue

                    # --- FILTRO 4: LIMITE TURNI SETTIMANALI SOLARI (MAX 4) ---
                    # Sincronizzato sul calcolo ISO-calendar del Punto 4
                    turni_questa_settimana = 0
                    for d_idx in range(len(df_lavoro)):
                        dt_controllo = datetime(anno, mese_scelto, d_idx + 1).date()
                        # Contiamo solo i turni della settimana solare corrente
                        if dt_controllo.isocalendar()[1] == sett_corrente:
                            # Verifichiamo se il medico è presente in una delle colonne dei turni
                            if (df_lavoro.iloc[d_idx][colonne_auto] == med).any():
                                turni_questa_settimana += 1
                    
                    if turni_questa_settimana >= 4:
                        continue # Salta questo medico, ha già raggiunto i 4 turni settimanali

                    # --- FILTRO 5: LIMITE WEEKEND (MAX 2) ---
                    if dt_corrente.weekday() >= 5:
                        wk_lavorati = set()
                        for d_idx in range(len(df_lavoro)):
                            dt_temp = datetime(anno, mese_scelto, d_idx+1).date()
                            if dt_temp.weekday() >= 5:
                                if (df_lavoro.iloc[d_idx][colonne_auto] == med).any():
                                    if dt_temp.weekday() == 6:
                                        id_w = (dt_temp - timedelta(days=1)).strftime("%Y-%U")
                                    else:
                                        id_w = dt_temp.strftime("%Y-%U")
                                    wk_lavorati.add(id_w)
                        
                        if len(wk_lavorati) >= 2 and id_wk_corrente not in wk_lavorati:
                            continue

                    # --- FILTRO 6: LIMITE NOTTI MENSILI (MAX 4) ---
                    if col == "MeCAU Notte":
                        notti_fatte = (df_lavoro["MeCAU Notte"] == med).sum()
                        if notti_fatte >= 4:
                            continue

                    # Se supera indenne tutti i blocchi del "Tetris", assegna il turno!
                    df_lavoro.at[i, col] = med
                    break

    st.session_state[key_stato] = df_lavoro
    st.rerun()


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

# --- AGGIORNAMENTO LISTE PER PA ---
opzioni_strutturati_pa = []
for s in strutturati:
    opzioni_strutturati_pa.append(s)
    opzioni_strutturati_pa.append(f"{s} PA")

medici_mecau = [""] + opzioni_strutturati_pa + jolly
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

if not df_editabile.equals(st.session_state[key_stato]):
    st.session_state[key_stato] = df_editabile
    st.rerun()


# --- 4. VERIFICA VINCOLI ---
st.divider()
st.subheader("🛡️ Controllo Vincoli e Sicurezza")

errori_rilevati = []
avvisi_carenza = []

# Fix #5: inizializzazione con float invece di int
conteggio_settimanale = {nome: {} for nome in strutturati}
conteggio_notti_mensili = {nome: 0 for nome in strutturati}
weekend_lavorati = {nome: set() for nome in strutturati}
ore_contrattuali_mese = {nome: 0.0 for nome in strutturati}
ore_pa_mese = {nome: 0.0 for nome in strutturati}
notti_temp = {}

giorni_feriali_totali = 0

for index, row in df_editabile.iterrows():
    giorno_corrente = index + 1
    dt_corrente = datetime(anno, mese_scelto, giorno_corrente).date()

    is_feriale = dt_corrente.weekday() < 5 and dt_corrente not in festivi_italiani
    is_weekend = dt_corrente.weekday() >= 5

    if is_feriale:
        giorni_feriali_totali += 1

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

    for medico in lavoro_oggi:
        m_nome = medico["nome"]
        m_sala = medico["sala"]

        if m_nome in desiderata_map:
            for d in desiderata_map[m_nome]:
                if d["giorno"] == giorno_corrente:
                    tipo = d["tipo"]
                    conf = False
                    if tipo in ["ferie", "corso", "no tutto il giorno", "no giorno"]:
                        conf = True
                    elif tipo == "no diurno" and m_sala in ["MeCAU 1", "MeCAU 2", "Bassa Intensità"]:
                        conf = True
                    elif tipo == "no notte" and m_sala == "MeCAU Notte":
                        conf = True
                    if conf:
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

            if not medico["is_pa"]:
                if m_nome in notti_temp:
                    dist = giorno_corrente - notti_temp[m_nome]
                    if dist == 1:
                        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {m_nome} in SMONTO NOTTE!")
                    elif dist == 2:
                        avvisi_carenza.append(f"🟡 **{row['Giorno']}**: {m_nome} in deroga riposo (X+2).")

                if m_sala == "MeCAU Notte":
                    notti_temp[m_nome] = giorno_corrente
                    conteggio_notti_mensili[m_nome] += 1

    nomi_soli = [d["nome"] for d in lavoro_oggi]
    if len(nomi_soli) != len(set(nomi_soli)):
        duplicati = set([x for x in nomi_soli if nomi_soli.count(x) > 1])
        errori_rilevati.append(f"🔴 **{row['Giorno']}**: {', '.join(duplicati)} duplicato oggi!")

# --- ANALISI MENSILE ---
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

# --- SALVATAGGIO ORE DINAMICHE PER SIDEBAR ---
monte_ore_mese = giorni_feriali_totali * 7.6

st.session_state["ore_contrattuali_aggiornate"] = ore_contrattuali_mese
st.session_state["ore_pa_aggiornate"] = ore_pa_mese
st.session_state["monte_ore_dinamico"] = monte_ore_mese

# --- VISUALIZZAZIONE ERRORI ---
if errori_rilevati or avvisi_carenza:
    for err in errori_rilevati:
        st.error(err)
    for warn in avvisi_carenza:
        st.warning(warn)
else:
    st.success("✅ Vincoli di sicurezza rispettati.")


# --- 5. ESPORTAZIONE PDF ---
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
            stile.add('BACKGROUND', (0, i), (-1, i), colors.yellow)

    tabella.setStyle(stile)
    elementi.append(tabella)

    doc.build(elementi)
    buffer.seek(0)
    return buffer


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


# --- RESET SELETTIVO ---
def reset_solo_strutturati():
    if key_stato in st.session_state:
        df_reset = st.session_state[key_stato].copy()
        colonne_da_pulire = ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]
        nomi_da_rimuovere = strutturati + [f"{s} PA" for s in strutturati]

        for col in colonne_da_pulire:
            df_reset[col] = df_reset[col].apply(lambda x: "" if x in nomi_da_rimuovere else x)

        st.session_state[key_stato] = df_reset
        st.rerun()


# --- 6. PULSANTI AZIONE (Fix #3 e #4: rimosso il blocco duplicato) ---
st.divider()
st.info("💡 **Suggerimento**: Inserisci prima i turni fissi o le preferenze a mano nella tabella sopra, poi usa i tasti qui sotto per completare o svuotare i turni degli strutturati.")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🗑️ Svuota Solo Strutturati", use_container_width=True):
        reset_solo_strutturati()

with col_btn2:
    if st.button("🤖 Genera Automatica Turni Strutturati", use_container_width=True, type="primary"):
        genera_turni_automatici()
