import streamlit as st
import pandas as pd

# Impostazioni pagina
st.set_page_config(page_title="Gestione Medici Susa", layout="wide")
st.title("🏥 Configurazione Liste Medici")

# --- SIDEBAR: GESTIONE DIPENDENTI ---
with st.sidebar:
    st.header("👥 Anagrafica Medici")
    st.info("Modifica i nomi qui sotto per aggiornare le liste in tempo reale.")

    # 1. MEDICI STRUTTURATI
    lista_strutturati = st.text_area(
        "1. Medici Strutturati (MeCAU 1, 2 e Notte)", 
        value="Brancaleoni, Desiderio, Pazè, Sapia",
        help="Inserisci i nomi separati da una virgola"
    )
    strutturati = [s.strip() for s in lista_strutturati.split(",") if s.strip()]

    # 2. MEDICI JOLLY
    lista_jolly = st.text_area(
        "2. Medici Jolly (Supporto MeCAU)", 
        value="Calasso, Melis, Sabbatino, Marsanic, Bruno, Castelli, Guglielmino, Trupja, Carbone, Dipietro, Di Stefano, Gili, Montebro, Ostuni, Palumbo, Ronco, Valobra, Vanoni, Veglio, Molino, Leoncini, Maurino, Tatarciuc, Sivera",
        help="Inserisci i nomi separati da una virgola"
    )
    jolly = [j.strip() for j in lista_jolly.split(",") if j.strip()]

    # 3. MEDICI GETTONISTI
    lista_gettonisti = st.text_area(
        "3. Medici Gettonisti (Solo Bassa Intensità)", 
        value="Borgiotto, Moshkina, Mascalchi, Garrone, Passoni, Sardo",
        help="Inserisci i nomi separati da una virgola"
    )
    gettonisti = [g.strip() for g in lista_gettonisti.split(",") if g.strip()]

# --- VISUALIZZAZIONE DI CONTROLLO ---
st.subheader("Riepilogo categorie")
col1, col2, col3 = st.columns(3)

with col1:
    st.write("**Strutturati:**")
    st.write(strutturati)

with col2:
    st.write("**Jolly:**")
    st.write(jolly)

with col3:
    st.write("**Gettonisti:**")
    st.write(gettonisti)

st.success("✅ Liste caricate correttamente. Dimmi come vuoi procedere con la prossima istruzione.")
