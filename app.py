import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import random
from fpdf import FPDF

# --- LOGICA CALENDARIO E FESTIVI (Invariata) ---
def get_festivi(year):
    festivi_fissi = [(1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
    lista_date = [datetime(year, m, g).date() for m, g in festivi_fissi]
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
    c_cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_july = c_cal.monthdatescalendar(year, 7)
    sundays = [day for week in month_july for day in week if day.weekday() == 6 and day.month == 7]
    lista_date.append(sundays[2] + timedelta(days=1))
    return lista_date

def format_giorno(d, m, y, lista_festivi):
    dt = datetime(y, m, d).date()
    nome_giorno = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"][dt.weekday()]
    if dt in lista_festivi or dt.weekday() == 6: return f"F {d}/{m} - {nome_giorno}"
    if dt.weekday() == 5: return f"S {d}/{m} - {nome_giorno}"
    return f"{d}/{m} - {nome_giorno}"

# --- NUOVA FUNZIONE PDF (SENZA ERRORI) ---
def crea_pdf_fpdf(df, anno, mese_nome):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Programmazione Turni MeCAU - {mese_nome} {anno}", ln=True, align="C")
    pdf.ln(5)
    
    # Intestazioni
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(31, 78, 120)
    pdf.set_text_color(255, 255, 255)
    cols = ["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Int."]
    widths = [40, 60, 60, 60, 50]
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 10, col, border=1, align="C", fill=True)
    pdf.ln()
    
    # Dati
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(0, 0, 0)
    for _, row in df.iterrows():
        fill = False
        if "F " in str(row['Giorno']):
            pdf.set_fill_color(255, 200, 200)
            fill = True
        elif "S " in str(row['Giorno']):
            pdf.set_fill_color(255, 244, 200)
            fill = True
        
        pdf.cell(widths[0], 8, str(row['Giorno']), border=1, fill=fill)
        pdf.cell(widths[1], 8, str(row['MeCAU 1']), border=1, fill=fill)
        pdf.cell(widths[2], 8, str(row['MeCAU 2']), border=1, fill=fill)
        pdf.cell(widths[3], 8, str(row['MeCAU Notte']), border=1, fill=fill)
        pdf.cell(widths[4], 8, str(row['Bassa Intensità']), border=1, fill=fill)
        pdf.ln()
    
    return pdf.output()

# --- IL RESTO DEL CODICE (MONTE ORE E INTERFACCIA) ---
st.set_page_config(page_title="Gestore Turni MeCAU", layout="wide")
st.title("🏥 Gestore Turni MeCAU")

st.sidebar.header("⚙️ Configurazione")
anno = st.sidebar.number_input("Anno", value=2026)
mese_idx = st.sidebar.selectbox("Mese", range(1, 13), index=datetime.now().month - 1)

strutturati_txt = st.sidebar.text_area("Strutturati", "Brancaleoni, Desiderio, Pazè, Sapia")
jolly_txt = st.sidebar.text_area("Jolly", "Maurino, Leoncini, Trupja, Tatarciuc")
gettonisti_txt = st.sidebar.text_area("Gettonisti", "Moshkina, Mascalchi, Garrone")

strutturati = [x.strip() for x in strutturati_txt.split(",") if x.strip()]
jolly = [x.strip() for x in jolly_txt.split(",") if x.strip()]
gettonisti = [x.strip() for x in gettonisti_txt.split(",") if x.strip()]
lista_tutti = [""] + strutturati + jolly
lista_bassa = [""] + gettonisti

num_days = calendar.monthrange(anno, mese_idx)[1]
festivi = get_festivi(anno)
giorni_feriali = sum(1 for d in range(1, num_days + 1) if datetime(anno, mese_idx, d).weekday() < 5 and datetime(anno, mese_idx, d).date() not in festivi)
target_ore = giorni_feriali * 7.6
st.sidebar.metric("Monte Ore Target", f"{target_ore:.1f}h")

giorni_labels = [format_giorno(d, mese_idx, anno, festivi) for d in range(1, num_days + 1)]

if 'df_turni' not in st.session_state or st.session_state.get('prev_mese') != mese_idx or st.session_state.get('prev_anno') != anno:
    st.session_state.df_turni = pd.DataFrame("", index=range(num_days), columns=["Giorno", "MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"])
    st.session_state.df_turni["Giorno"] = giorni_labels
    st.session_state.df_desid = pd.DataFrame("", index=giorni_labels, columns=strutturati)
    st.session_state.prev_mese = mese_idx
    st.session_state.prev_anno = anno

def check_errors(df_in, ds_in):
    errs = []
    df_c = df_in.fillna("").replace("None", "")
    for idx, row in df_c.iterrows():
        g = row["Giorno"]
        attivi = [str(m) for m in [row["MeCAU 1"], row["MeCAU 2"], row["MeCAU Notte"], row["Bassa Intensità"]] if str(m).strip()]
        if len(attivi) != len(set(attivi)):
            for d in set([m for m in attivi if attivi.count(m) > 1]): errs.append(f"🔴 **{g}**: {d} duplicato.")
        if idx > 0:
            ieri_notte = str(df_c.iloc[idx-1]["MeCAU Notte"])
            if ieri_notte.strip() and ieri_notte in attivi: errs.append(f"😴 **{g}**: {ieri_notte} post-notte.")
        if idx > 2:
            for m in strutturati:
                if any(df_c.iloc[idx-1, 1:] == m) and any(df_c.iloc[idx-2, 1:] == m) and any(df_c.iloc[idx-3, 1:] == m):
                    if any(df_c.iloc[idx, 1:] == m): errs.append(f"⚠️ **{g}**: {m} > 3 turni consecutivi.")
        for col in ["MeCAU 1", "MeCAU 2", "MeCAU Notte", "Bassa Intensità"]:
            m = str(row[col])
            if m in strutturati:
                v = ds_in.at[g, m]
                if v in ["Ferie", "Corso", "Blocco"]: errs.append(f"❌ **{g}**: {m} in {v}.")
                elif v == "No Giorno" and col != "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} No Giorno.")
                elif v == "No Notte" and col == "MeCAU Notte": errs.append(f"🚫 **{g}**: {m} No Notte.")
    return errs

def suggerisci_turni():
    df = st.session_state.df_turni.fillna("").replace("None", "").copy()
    ds = st.session_state.df_desid.fillna("").replace("None", "").copy()
    for idx in range(len(df)):
        for col in ["MeCAU Notte", "MeCAU 1", "MeCAU 2"]:
            if not str(df.at[idx, col]).strip():
                if col == "MeCAU Notte":
                    medici_shuffled = sorted(strutturati, key=lambda m: (df["MeCAU Notte"] == m).sum())
                else:
                    medici_shuffled = strutturati.copy()
                    random.shuffle(medici_shuffled)
                for med in medici_shuffled:
                    ore_attuali = (df == med).sum().sum() * 12
                    assente = ds[med].isin(["Ferie", "Corso"]).sum() if med in ds.columns else 0
                    abbuono = assente * 7.6
                    if (ore_attuali + abbuono + 12) > (target_ore + 6): continue
                    
                    start_7d = max(0, idx - 6)
                    ore_sett = (df.iloc[start_7d:idx+1] == med).sum().sum() * 12
                    consecutivi = 0
                    if idx > 0 and any(df.iloc[idx-1, 1:] == med): consecutivi += 1
                    if idx > 1 and any(df.iloc[idx-2, 1:] == med): consecutivi += 1
                    post_weekend = False
                    if idx >= 1:
                        fatto_sab = any(df.iloc[idx-2, 1:] == med) if idx >= 2 else False
                        fatto_dom = any(df.iloc[idx-1, 1:] == med)
                        if fatto_sab and fatto_dom and (idx % 7 in [0, 1]): post_weekend = True

                    if (ore_sett + 12) <= 48 and consecutivi < 3 and not post_weekend:
                        df.at[idx, col] = med
                        if check_errors(df, ds): df.at[idx, col] = ""
                        else: break
    st.session_state.df_turni = df

tab1, tab2, tab3 = st.tabs(["📅 Desiderata", "🛠️ Griglia Turni", "📊 Riepilogo"])

with tab1:
    config_des = {m: st.column_config.SelectboxColumn(m, options=["", "Ferie", "Corso", "Blocco", "No Giorno", "No Notte"]) for m in strutturati}
    st.session_state.df_desid = st.data_editor(st.session_state.df_desid.fillna("").replace("None", ""), column_config=config_des, use_container_width=True)

with tab2:
    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        if st.button("🪄 Genera bozza turni", type="primary"):
            suggerisci_turni()
            st.rerun()
    with col_bt2:
        if st.button("📥 Scarica PDF"):
            pdf_out = crea_pdf_fpdf(st.session_state.df_turni, anno, calendar.month_name[mese_idx])
            st.download_button(label="Clicca qui per il PDF", data=pdf_out, file_name=f"Turni_{mese_idx}.pdf", mime="application/pdf")
    
    lista_errori = check_errors(st.session_state.df_turni, st.session_state.df_desid)
    if lista_errori:
        with st.expander(f"⚠️ {len(lista_errori)} conflitti", expanded=True):
            for e in lista_errori: st.write(e)
    
    config_turni = {
        "Giorno": st.column_config.TextColumn("Giorno", disabled=True),
        "MeCAU 1": st.column_config.SelectboxColumn("MeCAU 1", options=lista_tutti),
        "MeCAU 2": st.column_config.SelectboxColumn("MeCAU 2", options=lista_tutti),
        "MeCAU Notte": st.column_config.SelectboxColumn("MeCAU Notte", options=lista_tutti),
        "Bassa Intensità": st.column_config.SelectboxColumn("Bassa Intensità", options=lista_bassa),
    }
    st.session_state.df_turni = st.data_editor(st.session_state.df_turni.fillna("").replace("None", ""), column_config=config_turni, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📊 Riepilogo Ore")
    df_v = st.session_state.df_turni.fillna("").replace("None", "")
    report = []
    for m in strutturati:
        ore_lav = (df_v.iloc[:, 1:] == m).sum().sum() * 12
        notti_fatte = (df_v["MeCAU Notte"] == m).sum()
        assente = st.session_state.df_desid[m].isin(["Ferie", "Corso"]).sum() if m in st.session_state.df_desid.columns else 0
        ore_abb = assente * 7.6
        bilancio = round((ore_lav + ore_abb) - target_ore, 1)
        extra = bilancio if bilancio > 0 else 0
        report.append({"Medico": m, "Ore Totali": ore_lav, "Notti": notti_fatte, "Abbuono": ore_abb, "Target": round(target_ore, 1), "Bilancio": bilancio, "di cui PA": extra})
    st.table(pd.DataFrame(report))
