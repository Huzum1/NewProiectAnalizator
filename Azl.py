import streamlit as st
import pandas as pd
import json
import time
import random
from collections import Counter

# ==========================================
# 1. CONFIGURARE & STILIZARE (SUPREME UI)
# ==========================================
st.set_page_config(
    page_title="Loto AI - Supreme Architect",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f1f3f5;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a237e; /* Royal Blue */
        color: white;
    }
    .warning-box {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 15px;
        margin-bottom: 10px;
        color: #bf360c;
    }
    .success-box {
        background-color: #e8f5e9;
        border-left: 5px solid #2e7d32;
        padding: 15px;
        margin-bottom: 10px;
        color: #1b5e20;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGICA MATEMATICĂ (CORE ENGINE)
# ==========================================

@st.cache_data
def detecteaza_configuratia(runde_unice):
    """Detectează automat formatul (ex: 6/49, 12/66, 20/80)."""
    if not runde_unice:
        return 66, 12 # Default Safety
    toate_numerele = [num for runda in runde_unice for num in runda]
    max_ball = max(toate_numerele) if toate_numerele else 66
    lungimi = [len(r) for r in runde_unice]
    avg_len = int(sum(lungimi) / len(lungimi)) if lungimi else 12
    return max_ball, avg_len

def get_exposure_limit(max_ball, draw_len):
    """
    Calculează limita matematică de expunere pentru a preveni falimentul.
    Formula: Probabilitate Naturală * 1.8 (Marjă de Siguranță)
    """
    if max_ball == 0: return 1.0
    base_prob = draw_len / max_ball
    limit = base_prob * 1.8 
    # Hard limits pentru a nu bloca tot sau a nu lăsa tot
    return max(0.15, min(limit, 0.60))

def check_portfolio_balance(candidate_nums, current_portfolio, max_exposure_percent):
    """Gardianul Riscului: Respinge variantele care supra-aglomerează un număr."""
    total_size = len(current_portfolio) + 1
    if total_size <= 30: return True # Perioadă de grație la început
    
    all_nums = []
    for p in current_portfolio: all_nums.extend(p['Raw_Set'])
    counts = Counter(all_nums)
    
    for num in candidate_nums:
        curr_count = counts.get(num, 0)
        new_ratio = (curr_count + 1) / total_size
        if new_ratio > max_exposure_percent:
            return False # Respins: Numărul devine prea riscant
    return True

def check_quality_patterns(num_list):
    """
    Poliția Tiparelor: Asigură că variantele sunt 'curate'.
    """
    if len(num_list) < 3: return True
    
    # 1. Fără Triplete Consecutive (ex: 11, 12, 13) - Arată urât și ies rar
    for i in range(len(num_list) - 2):
        if num_list[i+1] == num_list[i] + 1 and num_list[i+2] == num_list[i] + 2:
            return False 
            
    # 2. Distribuție Zonale (Nu toate în aceeași decadă)
    decades = [n // 10 for n in num_list]
    counts = Counter(decades)
    limit = len(num_list) - 1
    if any(c > limit for c in counts.values()):
        return False

    return True

def check_user_constraints(num_list, blacklist, whitelist):
    """Respectă ordinele directe ale utilizatorului."""
    s = set(num_list)
    if not s.isdisjoint(blacklist): return False # Conține număr interzis
    if not whitelist.issubset(s): return False   # Nu conține număr obligatoriu
    return True

def calculeaza_bonusuri_smart(num_list, max_ball):
    """
    Sistemul de Bonificație pentru Strategia 'Balanced'.
    Premiază variantele care acoperă bine tabla.
    """
    bonus = 0
    if not num_list: return 0
    
    # 1. Echilibru Mic/Mare
    mid_point = max_ball / 2
    mici = len([n for n in num_list if n <= mid_point])
    mari = len([n for n in num_list if n > mid_point])
    
    # Diferență mică = Echilibru bun
    diff = abs(mici - mari)
    if diff <= 1: bonus += 40 
    
    # 2. Spread (Distanța dintre Min și Max)
    # O variantă bună 'respiră', nu e înghesuită într-un colț
    spread = max(num_list) - min(num_list)
    if spread > (max_ball * 0.5): 
        bonus += 30
        
    return bonus

def calculeaza_scor_variant(varianta_set, runde_sets_ponderate, tip_joc_len, max_ball):
    """
    Motorul de Scoring Hibrid: Istoric + Matematică.
    """
    scor_total = 0
    palmares = {4: 0, 3: 0, 2: 0}
    surse_atinse = set()
    
    variant_len = len(varianta_set)
    
    # Grilă Punctaj Adaptivă (Prioritate 4/4)
    if variant_len == 4: pct_map = {4: 100, 3: 20, 2: 5}
    elif variant_len == 3: pct_map = {3: 100, 2: 15}
    elif tip_joc_len <= 7: pct_map = {6: 500, 5: 250, 4: 100, 3: 15, 2: 2} 
    else: pct_map = {10: 500, 9: 200, 8: 100, 7: 50, 6: 20, 5: 5, 4: 2} 

    # A. Puncte din Backtesting (Frecvență)
    for runda_obj in runde_sets_ponderate:
        runda_set = runda_obj['set']
        intersectie = len(varianta_set.intersection(runda_set))
        
        if intersectie in pct_map:
            points = pct_map[intersectie] * runda_obj['weight']
            scor_total += points
            
            if intersectie >= 4: palmares[4] += 1
            elif intersectie == 3: palmares[3] += 1
            elif intersectie == 2: palmares[2] += 1
            surse_atinse.add(runda_obj['sursa'])

    # B. Puncte din Structură (Doar dacă varianta e vie)
    if scor_total > 0:
        bonus = calculeaza_bonusuri_smart(sorted(list(varianta_set)), max_ball)
        scor_total += bonus

    return scor_total, palmares, len(surse_atinse)

def generator_genesis(runde_engine, max_ball, draw_len, count=500, whitelist=set(), strategy="balanced"):
    """
    CREATORUL: Generează variante de la zero.
    strategy='balanced': Împarte tabla în sectoare (Stabilitate).
    strategy='frequency': Folosește urna ponderată (Formă de moment).
    """
    generated = []
    
    # Pregătire Urnă pentru Frequency Mode
    population_freq = []
    if strategy == "frequency":
        freq = Counter()
        for r in runde_engine:
            for num in r['set']: freq[num] += r['weight']
        for num, weight in freq.items():
            reps = int(weight * 10)
            population_freq.extend([num] * reps)
    
    attempts = 0
    # Safety break: Nu încercăm la infinit dacă constrângerile sunt imposibile
    while len(generated) < count and attempts < (count * 50):
        attempts += 1
        current_var = set(whitelist)
        needed = draw_len - len(current_var)
        
        if needed > 0:
            try:
                if strategy == "balanced":
                    # STRATEGIA SECTOARE (GARANTEAZĂ SPREAD)
                    sector_size = max_ball // needed
                    for i in range(needed):
                        # Definim sectorul i
                        start = (i * sector_size) + 1
                        end = min((i + 1) * sector_size, max_ball)
                        if start > end: start = end # Safety
                        
                        # Alegem un număr din sector
                        pick = random.randint(start, end)
                        current_var.add(pick)
                    
                    # Completăm dacă set-ul a eliminat duplicate
                    while len(current_var) < draw_len:
                        current_var.add(random.randint(1, max_ball))
                        
                else:
                    # STRATEGIA FRECVENȚĂ (HOT NUMBERS)
                    if population_freq:
                        extracted = set(random.sample(population_freq, needed + 5)) # Luăm un buffer
                        for x in extracted:
                            if x not in current_var:
                                current_var.add(x)
                            if len(current_var) == draw_len: break
                    else:
                         # Fallback dacă nu avem istoric
                         while len(current_var) < draw_len:
                            current_var.add(random.randint(1, max_ball))

            except: continue
        
        # Tăiem la lungimea corectă (safety)
        if len(current_var) > draw_len:
            current_var = set(list(current_var)[:draw_len])
            
        if len(current_var) != draw_len: continue
        
        var_list = sorted(list(current_var))
        
        # VERIFICARE FINALĂ CALITATE
        if check_quality_patterns(var_list):
            generated.append({
                'id': f"GEN_{random.randint(10000,99999)}",
                'numere': current_var,
                'numere_raw': var_list
            })
            
    return generated

def worker_analiza_hibrida(variante_brute, runde_config, top_n=100, evo_count=15, use_strict_filters=True, blacklist=set(), whitelist=set(), strategy="balanced"):
    """
    MANAGERUL DE PROCES: Coordonează Filtrarea, Scoring-ul și Evoluția.
    """
    # 1. Construcție Engine Istoric
    runde_engine = []
    total_surse_active = 0
    for i in range(1, 14):
        sursa_key = f"sursa_{i}"
        if sursa_key in runde_config and runde_config[sursa_key]:
            weight = 0.5 + (0.05 * i) # Ponderare Temporală
            total_surse_active += 1
            for runda in runde_config[sursa_key]:
                runde_engine.append({'set': set(runda), 'sursa': i, 'weight': min(weight, 1.2)})
    
    max_ball, draw_len = detecteaza_configuratia([r['set'] for r in runde_engine])
    
    # Contoare Diagnostic
    rejected_sum = 0
    rejected_pattern = 0 
    rejected_zombie = 0
    rejected_user = 0
    
    candidati_procesati = []
    
    # 2. Procesare Variante Candidate (RAW)
    for var in variante_brute:
        v_list = var['numere_raw']
        variant_len = len(v_list)
        
        # A. Filtre Utilizator
        if not check_user_constraints(v_list, blacklist, whitelist):
            rejected_user += 1
            continue
        
        # B. Filtre Stricte (Logică)
        if use_strict_filters:
            # Filtru Sumă (Relaxat dar prezent)
            ideal_sum = (variant_len * (max_ball + 1)) / 2
            suma_min = ideal_sum * 0.30
            suma_max = ideal_sum * 1.70
            if not (suma_min <= sum(v_list) <= suma_max): 
                rejected_sum += 1
                continue
            
            # Filtru Tipare
            if not check_quality_patterns(v_list):
                rejected_pattern += 1
                continue

        # C. Scoring
        scor, stats, coverage = calculeaza_scor_variant(var['numere'], runde_engine, draw_len, max_ball)
        
        # D. Filtru Zombie (Trebuie să fi mișcat ceva, undeva)
        if use_strict_filters and total_surse_active > 5 and coverage == 0 and scor == 0:
             rejected_zombie += 1
             continue

        candidati_procesati.append({
            'ID': var['id'], 'Numere': str(v_list), 'Scor': int(scor),
            'Acoperire': f"{coverage}/{total_surse_active}", 'Stats': stats,
            'Raw_Set': v_list, 'Tip': 'RAW', 'set': var['numere']
        })
    
    # Sortăm candidații umani
    candidati_procesati.sort(key=lambda x: x['Scor'], reverse=True)
    
    # 3. Evoluție Genetică (AI)
    # Folosim ACEEAȘI strategie ca și generatorul pentru consistență
    copii_evoluti = []
    if candidati_procesati:
        # Generăm copii noi folosind logica selectată (Balanced/Frequency)
        # Folosim lungimea primului candidat ca referință
        ref_len = len(candidati_procesati[0]['set'])
        copii_evoluti = generator_genesis(runde_engine, max_ball, ref_len, count=evo_count, whitelist=whitelist, strategy=strategy)
        
        # Scorăm copiii
        for c in copii_evoluti:
             s, st, cv = calculeaza_scor_variant(c['numere'], runde_engine, draw_len, max_ball)
             c['Scor'] = int(s)
             c['Acoperire'] = f"{cv}/{total_surse_active}"
             c['Stats'] = st
             c['Tip'] = '🧬 EVO'

    # 4. Fuziune și Finalizare
    copii_evoluti.sort(key=lambda x: x['Scor'], reverse=True)
    
    # Umplem lista finală: întâi cei mai buni copii, apoi cei mai buni raw
    raw_needed = max(0, top_n - len(copii_evoluti))
    best_raw = candidati_procesati[:raw_needed]
    
    rezultat_final = copii_evoluti + best_raw
    rezultat_final.sort(key=lambda x: x['Scor'], reverse=True)
    
    diagnostics = {
        'sum': rejected_sum,
        'pattern': rejected_pattern,
        'zombie': rejected_zombie,
        'user': rejected_user,
        'config': f"{draw_len}/{max_ball}",
        'runde_engine': runde_engine
    }
    
    return rezultat_final, len(copii_evoluti), max_ball, draw_len, diagnostics

def elimina_redundanta(portofoliu):
    """Cluster Analysis: Șterge variantele aproape identice."""
    if not portofoliu: return []
    sorted_p = sorted(portofoliu, key=lambda x: x['Scor'], reverse=True)
    keep = []
    for current in sorted_p:
        is_redundant = False
        curr_set = set(current['Raw_Set'])
        for kept in keep:
            kept_set = set(kept['Raw_Set'])
            # Dacă diferă doar printr-un singur număr, e redundantă
            if len(curr_set.intersection(kept_set)) >= (len(curr_set) - 1):
                is_redundant = True
                break
        if not is_redundant: keep.append(current)
    return keep

def ruleaza_backtest(portofoliu, runde_test):
    """Simulare Istorică: Verifică profitabilitatea."""
    stats = {'Total Câștiguri': 0, 'Hits 4': 0, 'Hits 3': 0, 'Hits 2': 0}
    variant_scores = []
    
    for var in portofoliu:
        var_hits = 0
        v_set = set(var['Raw_Set'])
        
        for runda in runde_test:
            r_set = set(runda)
            matches = len(v_set.intersection(r_set))
            
            if matches >= 2:
                var_hits += 1
                stats['Total Câștiguri'] += 1
                if matches >= 4: stats['Hits 4'] += 1
                elif matches == 3: stats['Hits 3'] += 1
                elif matches == 2: stats['Hits 2'] += 1
        
        # Etichetare Performanță
        label = ""
        if var_hits > 0:
            if stats['Hits 4'] > 0: label = "*** GOLD ***" # A prins jackpot în test
            elif var_hits >= 3: label = "** SILVER **"   # A prins des
            else: label = "* BRONZE *"
        
        variant_scores.append({
            'ID': var['ID'],
            'Label': label,
            'Backtest Hits': var_hits
        })
        
    return stats, variant_scores

# ==========================================
# 3. INTERFAȚA (UI)
# ==========================================

if 'portfolio' not in st.session_state: st.session_state.portfolio = []
if 'runde_db' not in st.session_state: st.session_state.runde_db = {}
if 'blacklist' not in st.session_state: st.session_state.blacklist = set()
if 'whitelist' not in st.session_state: st.session_state.whitelist = set()

def main():
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🎛️ Panou Control")
        with st.expander("⛔ Reguli Personale", expanded=True):
            bl_input = st.text_input("Blacklist (Interzise)", placeholder="Ex: 13, 66")
            wl_input = st.text_input("Fixed Numbers (Obligatorii)", placeholder="Ex: 7")
            try:
                st.session_state.blacklist = {int(x.strip()) for x in bl_input.split(',') if x.strip().isdigit()}
                st.session_state.whitelist = {int(x.strip()) for x in wl_input.split(',') if x.strip().isdigit()}
            except: pass
            if st.session_state.blacklist: st.caption(f"🚫 Blocate: {sorted(list(st.session_state.blacklist))}")
            if st.session_state.whitelist: st.caption(f"✅ Fixate: {sorted(list(st.session_state.whitelist))}")

        st.divider()
        st.header("💾 Manager Proiect")
        if st.session_state.runde_db or st.session_state.portfolio:
            project_data = {'ts': time.time(), 'runde_db': st.session_state.runde_db, 'portfolio': st.session_state.portfolio}
            st.download_button("💾 Salvează JSON", json.dumps(project_data, default=str), f"loto_master_{int(time.time())}.json", "application/json")
        
        up = st.file_uploader("Încarcă JSON", type=['json'])
        if up:
            try:
                d = json.load(up)
                st.session_state.runde_db = d.get('runde_db', {})
                st.session_state.portfolio = d.get('portfolio', [])
                st.success("Proiect Restaurat!"); time.sleep(1); st.rerun()
            except: st.error("Fișier corupt.")

    st.title("🧬 Loto AI - Supreme Architect")
    
    tab1, tab2, tab3, tab4 = st.tabs(["1. 📂 SURSE", "2. ⛏️ GENERATOR", "3. 💰 PORTOFOLIU", "4. 🧪 LABORATOR TEST"])

    # === TAB 1: SURSE ===
    with tab1:
        st.info("Încarcă istoricul (13 Surse). Sistemul va elimina automat duplicatele.")
        tabs_surse = st.tabs([f"Sursa {i}" for i in range(1, 14)])
        
        all_rounds_flat = []
        for i, t in enumerate(tabs_surse, 1):
            with t:
                key = f"sursa_{i}"
                col_imp, col_man = st.columns([1, 2], gap="large")
                with col_imp:
                    st.write(f"📂 **Import Sursa {i}**")
                    uploaded_file = st.file_uploader(f"Fișier (Sursa {i})", type=['txt', 'csv'], key=f"up_{i}")
                    if uploaded_file is not None:
                        try:
                            content = uploaded_file.read().decode("utf-8")
                            parsed_imp = []
                            for l in content.split('\n'):
                                try:
                                    nums = sorted([int(n) for n in l.replace(';',',').replace(' ', ',').split(',') if n.strip().isdigit()])
                                    if len(nums) > 1: parsed_imp.append(nums)
                                except: pass
                            if parsed_imp:
                                st.session_state.runde_db[key] = parsed_imp
                                st.success(f"✅ Importat: {len(parsed_imp)} runde!")
                        except Exception as e: st.error(f"Eroare: {e}")

                with col_man:
                    st.write(f"✍️ **Editare Manuală**")
                    ex = st.session_state.runde_db.get(key, [])
                    val_show = ""
                    if ex:
                        val_show = "\n".join([",".join(map(str,r)) for r in ex[:50]])
                        if len(ex) > 50: val_show += f"\n... (+ {len(ex)-50} runde)"
                    txt = st.text_area(f"Conținut Sursa {i}", height=150, key=f"t_{i}", value=val_show)
                    if txt and txt != val_show:
                        parsed = []
                        for l in txt.split('\n'):
                            if "..." in l: continue
                            try:
                                nums = sorted([int(n) for n in l.replace(';',',').replace(' ', ',').split(',') if n.strip().isdigit()])
                                if len(nums) > 1: parsed.append(nums)
                            except: pass
                        if parsed: 
                            st.session_state.runde_db[key] = parsed
                            all_rounds_flat.extend(parsed)
                    elif ex: all_rounds_flat.extend(ex)
        
        # --- CHECK DUPLICATE GLOBAL ---
        if all_rounds_flat:
            initial_count = len(all_rounds_flat)
            unique_rounds_set = set(tuple(r) for r in all_rounds_flat)
            deduped_rounds = [list(x) for x in unique_rounds_set]
            final_count = len(deduped_rounds)
            removed_count = initial_count - final_count
            
            # Update pentru Engine
            all_rounds_flat = deduped_rounds
            
            if removed_count > 0:
                st.markdown(f"""<div class="warning-box"><b>⚠️ Curățenie:</b> Au fost eliminate <b>{removed_count}</b> duplicate. Analiză pe {final_count} runde unice.</div>""", unsafe_allow_html=True)
            
            mb, dl = detecteaza_configuratia(all_rounds_flat)
            limit_pct = get_exposure_limit(mb, dl)
            
            st.markdown("### 🔥 Matrix Heatmap")
            flat_nums = [n for r in all_rounds_flat for n in r]
            counts = Counter(flat_nums)
            heatmap_cols = st.columns(10)
            for num in range(1, mb + 1):
                count = counts.get(num, 0)
                max_c = max(counts.values()) if counts else 1
                intensity = count / max_c
                if intensity > 0.8: color = "#2e7d32" 
                elif intensity > 0.4: color = "#66bb6a" 
                else: color = "#e0e0e0" 
                with heatmap_cols[(num-1)%10]:
                    st.markdown(f"""<div style="background-color:{color}; padding:5px; border-radius:5px; text-align:center; margin:2px; font-weight:bold; color:{'white' if intensity>0.4 else 'black'}">{num}<br><span style="font-size:10px">{count}x</span></div>""", unsafe_allow_html=True)

    # === TAB 2: GENERATOR ===
    with tab2:
        mode = st.radio("Mod de Lucru:", ["🏭 Generator Automat", "✍️ Input Manual & Fișier"], horizontal=True)
        brute_input = []
        
        if mode == "✍️ Input Manual & Fișier":
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.subheader("Import Variante")
                uploaded_vars = st.file_uploader("Încarcă .txt/.csv", type=['txt', 'csv'])
                inv = st.text_area("Sau scrie manual (Paste)", height=200, placeholder="ID, 1 2 3 4")
                
                # Procesare Upload
                if uploaded_vars:
                    try:
                        content = uploaded_vars.read().decode("utf-8")
                        for l in content.split('\n'):
                            parts = l.replace(',', ' ').split()
                            nums = [int(n) for n in parts if n.strip().isdigit()]
                            if len(nums) >= 2:
                                # Luăm ultimele n numere ca variantă, ignorăm ID-ul din față
                                # Presupunem că ID-ul e primul element dacă e text sau număr
                                # Pentru siguranță, luăm tot ce e număr, dar în engine se va curăța
                                brute_input.append({'id': f"IMP_{random.randint(1000,9999)}", 'numere': set(nums), 'numere_raw': sorted(nums)})
                        st.info(f"Fișier: {len(brute_input)} variante detectate.")
                    except: st.error("Format fișier invalid.")
                
                # Procesare Text Area
                if inv:
                    for l in inv.split('\n'):
                        parts = l.replace(',', ' ').split()
                        nums = [int(n) for n in parts if n.strip().isdigit()]
                        if len(nums) >= 2:
                            brute_input.append({'id': f"MAN_{random.randint(1000,9999)}", 'numere': set(nums), 'numere_raw': sorted(nums)})

        else:
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.subheader("🏭 Configurare Genesis")
                strat = st.radio("Strategie:", ["Stabilitate (Balanced/Spread)", "Frecvență (Hot Numbers)"])
                strat_code = "balanced" if "Stabilitate" in strat else "frequency"
                
                gen_count = st.slider("Câte variante?", 100, 2000, 500)
                bilet_len = st.number_input("Lungime Bilet", min_value=1, max_value=20, value=4)
                
                if st.button("🤖 START GENESIS", type="primary", use_container_width=True):
                    temp_engine = []
                    for i in range(1, 14):
                        k = f"sursa_{i}"
                        if k in st.session_state.runde_db:
                            w = 0.5 + (0.05 * i)
                            for r in st.session_state.runde_db[k]:
                                temp_engine.append({'set': set(r), 'weight': min(w, 1.2), 'sursa':i})
                    if temp_engine:
                        mb_gen, _ = detecteaza_configuratia([r['set'] for r in temp_engine])
                        # Pasăm strategia selectată
                        generated_list = generator_genesis(temp_engine, mb_gen, bilet_len, count=gen_count, whitelist=st.session_state.whitelist, strategy=strat_code)
                        brute_input = generated_list
                        st.success(f"Generat {len(brute_input)} variante ({strat})!")
                    else: st.error("Nu ai runde încărcate!")

        with c2:
            st.subheader("Rezultate Analiză")
            if brute_input:
                st.caption(f"Total Variante de Procesat: {len(brute_input)}")
                if 'top_n' not in st.session_state: st.session_state.top_n = 100
                st.session_state.top_n = st.slider("Top N (Cele mai bune)", 10, 200, 100, key="sld_top")
                st.session_state.evo_n = st.slider("🧬 Genetic Boost", 0, 50, 15, key="sld_evo")
                use_filters = st.checkbox("Filtre Stricte (Anti-Aglomerare)", value=True)
                
                # Determinăm strategia pentru evoluție bazată pe UI (dacă e generator) sau default balanced
                current_strat = "balanced"
                if 'strat' in locals() and "Frecvență" in strat: current_strat = "frequency"

                with st.spinner("Analizez..."):
                    res, n_evo, mb, dl, diag = worker_analiza_hibrida(
                        brute_input, st.session_state.runde_db, 
                        st.session_state.top_n, st.session_state.evo_n, 
                        use_strict_filters=use_filters,
                        blacklist=st.session_state.blacklist,
                        whitelist=st.session_state.whitelist,
                        strategy=current_strat # Transmitem strategia la worker
                    )
                
                if not res and use_filters:
                    st.warning(f"Totul filtrat! User Blocked: {diag['user']} | Pattern: {diag['pattern']} | Sum: {diag['sum']}")
                else:
                    st.success(f"Găsite: {len(res)} (Genetic: {n_evo})")
                    df = pd.DataFrame(res)
                    if not df.empty:
                        df['Palmares'] = df['Stats'].apply(lambda x: f"4x:{x[4]}|3x:{x[3]}")
                        st.dataframe(df[['Tip', 'ID', 'Numere', 'Scor', 'Acoperire', 'Palmares']], use_container_width=True, hide_index=True)
                        st.session_state.temp = res
                        st.session_state.game_params = (mb, dl)

            if 'temp' in st.session_state:
                st.divider()
                if st.button("📥 ADAUGĂ ÎN SEIF", use_container_width=True):
                    mb, dl = st.session_state.get('game_params', (49, 6))
                    limit_pct = get_exposure_limit(mb, dl)
                    added, rejected = 0, 0
                    exist_ids = {v['ID'] for v in st.session_state.portfolio}
                    exist_sets = {tuple(v['Raw_Set']) for v in st.session_state.portfolio}
                    work_portfolio = list(st.session_state.portfolio)
                    for r in st.session_state.temp:
                        r_tup = tuple(r['Raw_Set'])
                        if r['ID'] not in exist_ids and r_tup not in exist_sets:
                            if check_portfolio_balance(r['Raw_Set'], work_portfolio, limit_pct):
                                st.session_state.portfolio.append(r)
                                work_portfolio.append(r) 
                                added += 1
                                exist_ids.add(r['ID'])
                            else: rejected += 1
                    st.toast(f"✅ +{added} adăugate! (⛔ {rejected} risc)")
                    del st.session_state.temp
                    st.rerun()

    # === TAB 3: PORTOFOLIU ===
    with tab3:
        st.header(f"💰 Tezaur: {len(st.session_state.portfolio)} Variante")
        c_act, c_view = st.columns([1, 3])
        with c_act:
            if st.button("🔍 Elimină Redundanța", type="secondary"):
                clean = elimina_redundanta(st.session_state.portfolio)
                rm = len(st.session_state.portfolio) - len(clean)
                st.session_state.portfolio = clean
                st.success(f"Optimizat! -{rm}"); st.rerun()
            st.divider()
            if st.button("🗑️ Golește Tot"): st.session_state.portfolio = []; st.rerun()
            
            if st.session_state.portfolio:
                txt_output = ""
                for v in st.session_state.portfolio:
                    label = v.get('Label', "")
                    nums_str = " ".join(map(str, v['Raw_Set']))
                    txt_output += f"{v['ID']}, {nums_str} {label}\n"

                st.download_button(
                    label="💾 Export .TXT (Etichetat)",
                    data=txt_output,
                    file_name="Loto_Variante.txt",
                    mime="text/plain",
                    type="primary"
                )

        with c_view:
            if st.session_state.portfolio:
                cols = ['Tip', 'ID', 'Numere', 'Scor', 'Acoperire']
                # Afișăm coloanele de test doar dacă există date
                if 'Label' in st.session_state.portfolio[0]: cols.append('Label')
                if 'Backtest Hits' in st.session_state.portfolio[0]: cols.append('Backtest Hits')
                
                df_p = pd.DataFrame(st.session_state.portfolio)
                # Asigurăm că există coloanele înainte de afișare
                for c in ['Label', 'Backtest Hits']:
                    if c not in df_p.columns: df_p[c] = ""
                
                st.dataframe(df_p[cols], use_container_width=True)
                st.divider()
                all_n = [n for v in st.session_state.portfolio for n in v['Raw_Set']]
                if all_n: st.bar_chart(pd.Series(all_n).value_counts().sort_index())

    # === TAB 4: LABORATOR ===
    with tab4:
        st.header("🧪 Laborator de Testare (Backtesting)")
        st.info("Verifică eficiența variantelor împotriva unor runde reale.")
        
        test_input = st.text_area("Paste Runde pentru Testare (ex: Ultimele 20 extrageri)", height=150)
        
        if st.button("🔬 Rulează Testul", type="primary"):
            if not st.session_state.portfolio:
                st.error("Tezaurul e gol!")
            elif not test_input:
                st.error("Introdu runde pentru testare!")
            else:
                runde_test = []
                for l in test_input.split('\n'):
                    try:
                        nums = sorted([int(n) for n in l.replace(';',',').replace(' ', ',').split(',') if n.strip().isdigit()])
                        if len(nums) > 1: runde_test.append(nums)
                    except: pass
                
                if runde_test:
                    stats, scored_vars = ruleaza_backtest(st.session_state.portfolio, runde_test)
                    
                    # Update Portofoliu
                    for i, p in enumerate(st.session_state.portfolio):
                        # Match după ID ca să fim siguri (deși ordinea e păstrată)
                        for sv in scored_vars:
                            if sv['ID'] == p['ID']:
                                p['Label'] = sv['Label']
                                p['Backtest Hits'] = sv['Backtest Hits']
                                break
                    
                    st.markdown(f"""
                    <div class="success-box">
                        <h3>📊 Rezultate Test pe {len(runde_test)} Runde</h3>
                        <ul>
                            <li><b>Total Bilete Câștigătoare (minim 2 nr):</b> {stats['Total Câștiguri']}</li>
                            <li><b>Jackpot-uri (4 nr):</b> {stats['Hits 4']} 🏆</li>
                            <li><b>Câștiguri Medii (3 nr):</b> {stats['Hits 3']}</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    st.success("Etichete actualizate! Verifică Tab-ul 3.")
                else:
                    st.error("Format invalid.")

if __name__ == "__main__":
    main()
