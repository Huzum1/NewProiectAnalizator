import streamlit as st
from collections import Counter

st.set_page_config(
    page_title="Verificare Loterie Latvia Keno 20/62",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 Verificare Variante — Latvia Keno 20/62")
st.caption("Variante de 6 numere din 62 • Runde cu 20 numere extrase")
st.divider()

# ==============================
# FUNCȚII
# ==============================

@st.cache_data(show_spinner=False)
def parse_runde_bulk(text):
    """
    Accepta formate:
    - Tab-separated: 1\t01.01.2025\t10:00 (R)\t1, 2, 4, 11, ...   (format latvia_keno.txt)
    - Simplu:        1, 2, 4, 11, 16, 18, ...                       (format latvia_numere.txt)
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
            runde.append(sorted(set(nums)))
        elif len(nums) > 0 and len(nums) != 20:
            pass  # ignora linii incomplete
    return runde

@st.cache_data(show_spinner=False)
def parse_variante_bulk(text):
    """
    Accepta formate:
    - 1, 3 7 15 22 44 55       (ID urmat de 6 numere)
    - 1,3,7,15,22,44,55        (ID + numere cu virgula)
    - 3 7 15 22 44 55          (fara ID - se genereaza automat)
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
        nums = sorted(set(nums))
        if len(nums) == 6:
            # primul token e ID sau numar din varianta?
            first = tokens[0].rstrip(',')
            try:
                first_int = int(first)
                # daca primul nu e in lista finala de 6, e ID
                if first_int not in nums:
                    vid = first
                else:
                    vid = str(auto_id)
            except:
                vid = str(auto_id)
            variante.append({"id": vid, "numere": nums})
            auto_id += 1
        elif len(nums) == 7:
            # primul e ID, restul 6 sunt numerele
            vid = tokens[0].rstrip(',')
            variante.append({"id": vid, "numere": nums[1:]})
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
    st.header("🎲 Variante (6 numere din 62)")
    text_variante = st.text_area(
        "Format: ID, n1 n2 n3 n4 n5 n6  sau  n1 n2 n3 n4 n5 n6",
        height=150,
        key="input_variante",
        placeholder="1, 3 7 15 22 44 55\n2, 1 9 18 33 47 61\n..."
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

    minim = st.slider(
        "Numere minime potrivite (match) din 6:",
        min_value=3,
        max_value=6,
        value=6,
        key="slider_minim"
    )

    st.caption(f"Cauti variante cu **{minim}/6** numere potrivite în cele 20 extrase")

    # ==============================
    # CALCUL
    # ==============================
    variant_stats  = {v["id"]: 0 for v in st.session_state.variante}
    runde_acoperite = 0
    total_hits      = 0
    match_distribution = Counter()  # distributie 3/4/5/6 match-uri

    for runda in st.session_state.runde:
        rset = set(runda)
        hit_in_runda = False

        for v in st.session_state.variante:
            mc = len(set(v["numere"]) & rset)
            match_distribution[mc] += 1
            if mc >= minim:
                variant_stats[v["id"]] += 1
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
    st.subheader("📊 Distribuție match-uri (toate variantele × toate rundele)")
    dcols = st.columns(7)
    for i, label in enumerate(["0/6","1/6","2/6","3/6","4/6","5/6","6/6"]):
        cnt = match_distribution.get(i, 0)
        total_checks = len(st.session_state.runde) * len(st.session_state.variante)
        pct = cnt / total_checks * 100 if total_checks > 0 else 0
        dcols[i].metric(label, cnt, f"{pct:.2f}%")

    # ==============================
    # TOP VARIANTE
    # ==============================
    st.divider()
    st.subheader(f"📈 Top variante după hit-uri ({minim}/6)")
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
        st.warning(f"Nicio variantă nu a atins {minim}/6 în rundele analizate.")

    # ==============================
    # DETALII PE RUNDE
    # ==============================
    st.divider()
    st.subheader("📋 Detalii pe fiecare rundă")
    with st.container(height=350):
        for i, runda in enumerate(st.session_state.runde, 1):
            rset = set(runda)
            hits_runda = [(v["id"], len(set(v["numere"]) & rset), v["numere"])
                          for v in st.session_state.variante
                          if len(set(v["numere"]) & rset) >= minim]
            if hits_runda:
                st.markdown(f"**Runda {i}** `{runda}` → **{len(hits_runda)} variante câștigătoare**")
                for vid, mc, vnums in hits_runda[:5]:
                    st.text(f"    Varianta #{vid} {vnums} → {mc}/6 ✅")
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
            "\n".join(", ".join(map(str, r)) for r in st.session_state.runde),
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
        runde_fara_hit = [
            runda for runda in st.session_state.runde
            if not any(
                len(set(v["numere"]) & set(runda)) >= minim
                for v in st.session_state.variante
            )
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
        st.info("➡️ Introdu variantele tale de 6 numere.")
