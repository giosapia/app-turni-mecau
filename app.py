import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

# --- LOGICA CALENDARIO E FESTIVI ITALIANI COMPLETI ---
def get_festivi(year):
    # 1. Festività Fisse Nazionali
    festivi_fissi = [
        (1, 1),   # Capodanno
        (1, 6),   # Epifania
        (4, 25),  # Liberazione
        (5, 1),   # Festa del Lavoro
        (6, 2),   # Festa della Repubblica
        (8, 15),  # Ferragosto
        (11, 1),  # Ognissanti
        (12, 8),  # Immacolata
        (12, 25), # Natale
        (12, 26)  # S. Stefano
    ]
    
    lista_date = []
    for m, g in festivi_fissi:
        lista_date.append(datetime(year, m, g).date())
    
    # 2. Calcolo Pasqua e Pasquetta (Algoritmo di Gauss)
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
    pasquetta = pasqua + timedelta(days=1)
    lista_date.extend([pasqua, pasquetta])
    
    # 3. Calcolo Patrono (Lunedì dopo la 3° domenica di Luglio)
    c_cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_july = c_cal.monthdatescalendar(year, 7)
    sundays = [day for week in month_july for day in week if day.weekday() == 6 and day.month == 7]
    terza_dom_luglio = sundays[2]
    patrono = terza_dom_luglio + timedelta(days=1)
    lista_date.append(patrono)
    
    return lista_date

def format_giorno(d, m, y, lista_festivi):
    dt = datetime(y, m, d).date()
    settimana = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    nome_giorno = settimana[dt.weekday()]
    
    # Un giorno è rosso se è Domenica O se è nella lista dei festivi
    if dt in lista_festivi or dt.weekday() == 6:
        return f"🔴 {d}/{m} - {nome_giorno}"
    # Un giorno è giallo se è Sabato (e non è un festivo)
    elif dt.weekday() == 5:
        return f"🟡 {d}/{m} - {nome_giorno}"
    else:
        return f"{d}/{m} - {nome_giorno}"

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gestore Turni MeCAU", layout="wide")
st.title("🏥 Gestore Turni MeCAU")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configurazione")
anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=datetime.now().month - 1)

st.sidebar.header("👥 Personale")
strutturati_txt = st.sidebar.text_area("Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia")
jolly_txt = st.sidebar.text_area("Jolly", "Maurino, Leoncini, Trupja, Tatarciuc")
gettonisti_txt = st.sidebar.text_area("Gettonisti", "Moshkina, Mascalchi, Garrone")

strutturati = [x.strip() for x in strutturati_txt.split(",") if x.strip()]
jolly = [x.strip() for x in jolly_txt.split(",") if x.strip()]
gettonisti = [x.strip() for x in gettonisti_txt.split(",") if x.strip()]

lista_tutti = [""] + strutturati + jolly
lista_bassa = [""] + gettonisti

# Calcolo giorni feriali effettivi
num_days = calendar.monthrange(anno, mese_idx)[1]
festivi = get_festivi(anno)
giorni_feriali_count = 0
for d in range(1, num_days + 1):
    dt = datetime(anno, mese_idx, d).date()
    # Feriale = non è sabato, non è domenica, non è festivo
    if dt.weekday() < 5 and dt not in festivi:
        giorni_feriali_count += 1

target_ore = giorni_feriali_count * 7.6
st.sidebar.metric("Monte Ore Target", f"{target_ore:.1f}h")
st.sidebar.caption(f"Basato su {giorni_feriali_count} giorni feriali (LUN-VEN no festivi)")

giorni_labels = [format_giorno(d, mese_idx, anno, festivi) for d in range(1, num_days + 1)]

# --- STATO DELLA SESSIONE ---
if 'df_turni' not in st.session_state or st.session_state.get('prev_mese') != mese_idx or st.session_state.get('prev_anno') != anno:
    st.session_state.df_turni = pd.DataFrame({
        "Giorno": giorni_labels, "MeCAU 1": "", "MeCAU 2": "", "MeCAU Notte": "", "Bassa Intensità": ""
    })
    st.session_state.df_desid = pd.DataFrame(index=giorni_labels, columns=strutturati).fillna("")
    st.session_state.prev_mese = mese_idx
    st.session_state.prev_anno = anno

# --- LOGICA ERRORI ---
def check_errors():
    errs = []
    df = st.session_state.df_turni
    ds = st.session_state.df_desid
    for idx, row in df.iterrows():
        g = row["Giorno"]
        medici_attivi = [m for m in [row["MeCAU 1"], row["MeCAU 2"], row["MeCAU Notte"], row["Bassa Intensità"]] if m != ""]
        if len(medici_attivi) != len(set(medici_attivi)):
            duplicati = set([m for m in medici_attivi if medici_attivi.count(m) > 1])
            for d in duplicati: errs.append(f"🔴 **{g}**: {d} ha incarichi duplicati.")
        for col in ["MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"]:
            m = row[col]
            if m in strutturati:
                v = ds.at[g, m]
                if v in ["Ferie", "Corso", "Blocco"]: errs.append(f"❌ **{g}**: {m} è in '{v}'.")
                elif v == "No Giorno" and col != "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} ha vincolo 'No Giorno'.")
                elif v == "No Notte" and col == "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} ha vincolo 'No Notte'.")
    return errs

# --- INTERFACCIA ---
tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo & Jolly"])

with tab1:
    st.subheader("Inserimento Vincoli (Strutturati)")
    opts = ["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]
    config_des = {m: st.column_config.SelectboxColumn(m, options=opts) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid, column_config=config_des, use_container_width=True)

with tab2:
    st.subheader("Compilazione Griglia")
    lista_errori = check_errors()
    if lista_errori:
        with st.expander(f"⚠️ Attenzione: {len(lista_errori)} conflitti rilevati", expanded=True):
            for e in lista_errori[:5]: st.write(e)
    
    config_turni = {
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=lista_tutti),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=lista_tutti),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=lista_tutti),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=lista_bassa),
    }
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni, column_config=config_turni, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Riepilogo Ore e PA")
    report_data = []
    for m in strutturati:
        ore_lav = (st.session_state.df_turni.iloc[:, 1:] == m).sum().sum() * 12
        assente = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum()
        ore_abb = assente * 7.6
        tot = ore_lav + ore_abb
        bilancio = tot - target_ore
        report_data.append({"Medico": m, "Ore Lav.": ore_lav, "Abbuono (h)": ore_abb, "Totale": round(tot, 1), "Bilancio (PA)": round(bilancio, 1)})
    
    st.table(pd.DataFrame(report_data))
    
    st.divider()
    col_v, col_e = st.columns(2)
    with col_v:
        st.subheader("📌 Turni Vacanti")
        vacanti = []
        for idx, row in st.session_state.df_turni.iterrows():
            for col in ["MeCAU 1", "MeCAU 2", "MeCAU Notte"]:
                if row[col] == "":
                    vacanti.append({"Giorno": row["Giorno"], "Postazione": col})
        if vacanti:
            df_vacanti = pd.DataFrame(vacanti)
            st.dataframe(df_vacanti, use_container_width=True, hide_index=True)
            csv = df_vacanti.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica Elenco Vacanti (CSV)", csv, "turni_vacanti.csv", "text/csv")
        else:
            st.success("Griglia coperta!")

    with col_e:
        if lista_errori:
            st.subheader("⚠️ Dettaglio Errori")
            for e in lista_errori: st.write(e)
        else:
            st.success("Nessun errore rilevato.")
