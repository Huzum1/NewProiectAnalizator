import streamlit as st
from collections import Counter

st.set_page_config(
    page_title="Verificare Loterie Latvia Keno 20/62",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 Verificare Variante — Latvia Keno 20/62")
st.caption("Variante de 4, 5, 6, 7 sau 8 numere din 62 • Runde cu 20 numere extrase")
st.divider()

# ==============================
# FUNCȚII
# ==============================

@st.cache_data(show_spinner=False)
def parse_runde_bulk(text):
    """
    Accepta formate:
    - Tab-separated: 1\t01.01.2025\t10:00 (R)\t1, 2, 4, 11, ...   (format latvia_keno.txt)
    - Simplu:        1, 2, 4, 11, 16, 18, ...                        (format latvia_numere.txt)
    """
    runde = []
    for linie in text.splitlines():
        linie = linie.strip()
        if not linie:
            continue
        # detecta format tab (latvia_keno.txt)
        if '\t' in linie:
            parts = linie.split('\t')
            if len(parts) >= 4:
                linie = parts[3]  # coloana cu numerele
        # extrage numerele
        nums = []
        for tok in linie.replace(',', ' ').split():
            try:
                n = int(tok)
                if 1 <= n <= 62:
                    nums.append(n)
            except:
                pass
        if len(nums) == 20:
            # Optimizare: Salvează direct ca set() pre-calculat pentru viteză masivă
            runde.append(set(nums))
        elif len(nums) > 0 and len(nums) != 20:
            pass  # ignora linii incomplete
    return runde

@st.cache_data(show_spinner=False)
def parse_variante_bulk(text):
    """
    Accepta variante flexibile de 4, 5, 6, 7 sau 8 numere, cu sau fara ID inclus.
    """
    variante = []
    auto_id = 1
    for linie in text.splitlines():
        linie = linie.strip()
        if not linie:
            continue
        tokens = linie.replace(',', ' ').split()
        nums = []
        for tok in tokens:
            try:
                n = int(tok)
                if 1 <= n <= 62:
                    nums.append(n)
            except:
                pass
        
        # Eliminăm duplicatele din numerele liniei curente menținând ordinea
        unique_nums = sorted(set(nums))
        lungime_numere = len(unique_nums)
        
        if lungime_numere == 0:
            continue
            
        first_token = tokens[0].rstrip(',')
        is_first_token_id = False
        
        try:
            first_int = int(first_token)
            # Dacă primul număr din text nu se regăsește în setul de numere extrase valid, este ID
            if first_int not in unique_nums:
                is_first_token_id = True
        except:
            # Dacă primul token nu e numeric (ex: "V1"), e clar un ID
            is_first_token_id = True

        # Extragere dinamică numere și ID în funcție de structura detectată
        if is_first_token_id:
            vid = first_token
            # Filtrăm primul token din lista totală de numere valide dacă a fost parsat din greșeală
            try:
                first_int = int(first_token)
                lista_numere = [n for n in unique_nums if n != first_int]
            except:
                lista_numere = unique_nums
        else:
            vid = str(auto_id)
            lista_numere = unique_nums

        # Validăm ca lungimea finală a variantei să fie între limitele permise (4/4 până la 8/8)
        if 4 <= len(lista_numere) <= 8:
            variante.append({
                "id": vid, 
                "numere": sorted(lista_numere), 
                "numere_set": set(lista_numere)
            })
            auto_id += 1
            
    return variante

# ==============================
# SESSION STATE
# ==============================
st.session_state.setdefault("runde", [])
st.session_state.setdefault("variante", [])

# ==============================
# INPUT
# ==============================
col1, col2 = st.columns(2)

with col1:
    st.header("📋 Runde (20 numere din 62)")
    uploaded = st.file_uploader(
        "Upload latvia_keno.txt sau latvia_numere.txt",
        type=["txt"],
        key="upload_runde"
    )
    if uploaded:
        continut = uploaded.read().decode("utf-8")
        runde_parsed = parse_runde_bulk(continut)
        if runde_parsed:
            st.session_state.runde = runde_parsed
            st.success(f"✅ {len(runde_parsed)} runde incarcate din fisier")

    text_runde = st.text_area(
        "Sau paste direct (o rundă pe linie, 20 numere):",
        height=150,
        key="input_runde",
        placeholder="1, 2, 4, 11, 16, 18, 26, 29, 33, 38, 40, 43, 44, 47, 53, 54, 57, 58, 60, 62"
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("➕ Adaugă Runde", type="primary", use_container_width=True):
            noi = parse_runde_bulk(text_runde)
            st.session_state.runde += noi
            st.success(f"+{len(noi)} runde")
            st.rerun()
    with col_b:
        if st.button("🗑️ Șterge Runde", use_container_width=True):
            st.session_state.runde = []
            st.rerun()

    if st.session_state.runde:
        st.info(f"📊 **{len(st.session_state.runde)} runde** incarcate")

with col2:
    st.header("🎲 Variante (4 până la 8 numere)")
    text_variante = st.text_area(
        "Format: ID, n1 n2 n3 n4 ... sau  n1 n2 n3 n4 ...",
        height=150,
        key="input_variante",
        placeholder="1, 5 12 23 45\n2, 1 9 18 33 47 51 55 60\n..."
    )
    col_c, col_d = st.columns(2)
    with col_c:
        if st.button("➕ Adaugă Variante", type="primary", use_container_width=True):
            noi = parse_variante_bulk(text_variante)
            st.session_state.variante += noi
            st.success(f"+{len(noi)} variante")
            st.rerun()
    with col_d:
        if st.button("🗑️ Șterge Variante", use_container_width=True):
            st.session_state.variante = []
            st.rerun()

    if st.session_state.variante:
        st.info(f"🎲 **{len(st.session_state.variante)} variante** incarcate")

# ==============================
# REZULTATE
# ==============================
st.divider()
st.header("🏆 Rezultate")

if st.session_state.runde and st.session_state.variante:

    # Determinăm dinamic lungimea maximă a variantelor încărcate (4, 5, 6, 7 sau 8)
    max_dim_variante = max(len(v["numere"]) for v in st.session_state.variante)

    minim = st.slider(
        f"Numere minime potrivite (match) din {max_dim_variante}:",
        min_value=3 if max_dim_variante >= 3 else max_dim_variante,
        max_value=max_dim_variante,
        value=max_dim_variante,
        key="slider_minim"
    )

    st.caption(f"Cauti variante cu **{minim}/{max_dim_variante}** numere potrivite în cele 20 extrase")

    # ==============================
    # CALCUL OPTIMIZAT
    # ==============================
    variant_stats  = {v["id"]: 0 for v in st.session_state.variante}
    runde_acoperite = 0
    total_hits      = 0
    match_distribution = Counter()  # distributie match-uri

    # Optimizare buclă: Extragerea referințelor direct în variabile locale
    variante_active = [(v["id"], v["numere_set"]) for v in st.session_state.variante]

    for rset in st.session_state.runde:
        hit_in_runda = False

        for vid, vset in variante_active:
            mc = len(vset & rset) # Intersecție de seturi pre-calculate ultra rapidă
            match_distribution[mc] += 1
            if mc >= minim:
                variant_stats[vid] += 1
                total_hits += 1
                if not hit_in_runda:
                    hit_in_runda = True

        if hit_in_runda:
            runde_acoperite += 1

    # ==============================
    # METRICS
    # ==============================
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Runde", len(st.session_state.runde))
    c2.metric("Variante", len(st.session_state.variante))
    c3.metric("Runde cu hit", f"{runde_acoperite} ({runde_acoperite/len(st.session_state.runde)*100:.1f}%)")
    c4.metric("Total hit-uri", total_hits)
    c5.metric("Hit-uri per rundă", f"{total_hits/len(st.session_state.runde):.2f}")

    # ==============================
    # DISTRIBUTIE MATCH-URI
    # ==============================
    st.divider()
    st.subheader(f"📊 Distribuție match-uri (toate variantele × toate rundele)")
    
    # Generăm etichetele dinamic în funcție de dimensiunea maximă detectată
    labels = [f"{i}/{max_dim_variante}" for i in range(max_dim_variante + 1)]
    dcols = st.columns(len(labels))
    
    for i, label in enumerate(labels):
        cnt = match_distribution.get(i, 0)
        total_checks = len(st.session_state.runde) * len(st.session_state.variante)
        pct = cnt / total_checks * 100 if total_checks > 0 else 0
        dcols[i].metric(label, cnt, f"{pct:.2f}%")

    # ==============================
    # TOP VARIANTE
    # ==============================
    st.divider()
    st.subheader(f"📈 Top variante după hit-uri ({minim}/{max_dim_variante})")
    sorted_variants = sorted(variant_stats.items(), key=lambda x: x[1], reverse=True)
    
    # afiseaza top 30
    top_nonzero = [(vid, cnt) for vid, cnt in sorted_variants if cnt > 0]
    if top_nonzero:
        for vid, count in top_nonzero[:30]:
            pct = count / len(st.session_state.runde) * 100
            nums = next((v["numere"] for v in st.session_state.variante if v["id"] == vid), [])
            bar = "█" * min(count, 40)
            st.text(f"#{vid:>5}  [{' '.join(f'{n:2d}' for n in nums)}]  →  {count:>3} hit-uri ({pct:.1f}%)  {bar}")
    else:
        st.warning(f"Nicio variantă nu a atins {minim}/{max_dim_variante} în rundele analizate.")

    # ==============================
    # DETALII PE RUNDE
    # ==============================
    st.divider()
    st.subheader("📋 Detalii pe fiecare rundă")
    with st.container(height=350):
        for i, rset in enumerate(st.session_state.runde, 1):
            runda_ordonata = sorted(list(rset))
            
            hits_runda = [(v["id"], len(v["numere_set"] & rset), v["numere"])
                          for v in st.session_state.variante
                          if len(v["numere_set"] & rset) >= minim]
            if hits_runda:
                st.markdown(f"**Runda {i}** `{runda_ordonata}` → **{len(hits_runda)} variante câștigătoare**")
                for vid, mc, vnums in hits_runda[:5]:
                    st.text(f"    Varianta #{vid} {vnums} → {mc}/{max_dim_variante} ✅")
            else:
                st.text(f"Runda {i:>4} → 0 variante")

    # ==============================
    # DOWNLOAD
    # ==============================
    st.divider()
    st.subheader("⬇️ Download")
    d1, d2, d3, d4, d5 = st.columns(5)

    with d1:
        st.download_button(
            "📄 Runde",
            "\n".join(", ".join(map(str, sorted(list(r)))) for r in st.session_state.runde),
            "runde.txt"
        )
    with d2:
        st.download_button(
            "🎲 Variante",
            "\n".join(f"{v['id']}, {' '.join(map(str, v['numere']))}" for v in st.session_state.variante),
            "variante.txt"
        )
    with d3:
        castiguri = "\n".join(
            f"{v['id']}, {' '.join(map(str, v['numere']))}"
            for v in st.session_state.variante if variant_stats[v["id"]] > 0
        )
        st.download_button("🏆 Variante cu hit-uri", castiguri, "castiguri.txt")
    with d4:
        top_txt = "\n".join(f"{vid}, {count}" for vid, count in sorted_variants)
        st.download_button("📊 Top variante", top_txt, "top_variante.txt")
    with d5:
        # Optimizat filtrarea rundelor fără hit
        runde_fara_hit = [
            sorted(list(rset)) for rset in st.session_state.runde
            if not any(len(v["numere_set"] & rset) >= minim for v in st.session_state.variante)
        ]
        fara_hit_txt = "\n".join(", ".join(map(str, r)) for r in runde_fara_hit)
        st.download_button(
            f"❌ Runde fără hit ({len(runde_fara_hit)})",
            fara_hit_txt,
            "runde_fara_hit.txt"
        )

else:
    if not st.session_state.runde:
        st.info("➡️ Încarcă fișierul `latvia_keno.txt` sau `latvia_numere.txt` pentru runde.")
    if not st.session_state.variante:
        st.info("➡️ Introdu variantele tale (sunt suportate lungimi de 4, 5, 6, 7 sau 8 numere).")
