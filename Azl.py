import streamlit as st
import pandas as pd
import json
import time
import random
from collections import Counter

# ==========================================
# 1. CONFIGURARE & STILIZARE
# ==========================================
st.set_page_config(
    page_title="Loto AI Master Architect",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4b7bff; 
        color: white;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        margin-bottom: 10px;
        color: #856404;
    }
    .element-container { margin-bottom: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGICA MATEMATICĂ (ENGINE)
# ==========================================

@st.cache_data
def detecteaza_configuratia(runde_unice):
    if not runde_unice:
        return 49, 6
    toate_numerele = [num for runda in runde_unice for num in runda]
    max_ball = max(toate_numerele) if toate_numerele else 49
    lungimi = [len(r) for r in runde_unice]
    avg_len = int(sum(lungimi) / len(lungimi)) if lungimi else 6
    return max_ball, avg_len

def get_exposure_limit(max_ball, draw_len):
    if max_ball == 0: return 1.0
    base_prob = draw_len / max_ball
    limit = base_prob * 1.5
    return max(0.15, min(limit, 0.50))

def check_portfolio_balance(candidate_nums, current_portfolio, max_exposure_percent):
    total_size = len(current_portfolio) + 1
    if total_size <= 20: return True
    
    all_nums = []
    for p in current_portfolio: all_nums.extend(p['Raw_Set'])
    counts = Counter(all_nums)
    
    for num in candidate_nums:
        curr_count = counts.get(num, 0)
        new_ratio = (curr_count + 1) / total_size
        if new_ratio > max_exposure_percent: return False
    return True

def check_quality_patterns(num_list):
    if len(num_list) < 3: return True
    for i in range(len(num_list) - 2):
        if num_list[i+1] == num_list[i] + 1 and num_list[i+2] == num_list[i] + 2:
            return False 
    pari = len([n for n in num_list if n % 2 == 0])
    if pari == 0 or pari == len(num_list):
        return False
    return True

# --- NEW: CALCULATOR DE BONUSURI SMART ---
def calculeaza_bonusuri_smart(num_list, max_ball):
    """Acordă puncte extra pentru estetica matematică."""
    bonus = 0
    if not num_list: return 0
    
    # 1. Echilibru Mic/Mare (High/Low)
    mid_point = max_ball / 2
    mici = len([n for n in num_list if n <= mid_point])
    mari = len([n for n in num_list if n > mid_point])
    
    # Dacă e echilibrat (diferență mică între count-uri), bonus mare
    diff = abs(mici - mari)
    if diff <= 1: 
        bonus += 50 # Perfect echilibrat (ex: 2 mici, 2 mari)
    elif diff <= 2:
        bonus += 20 # Acceptabil
        
    # 2. Spread (Acoperire)
    # Vrem ca diferența dintre Max și Min să fie măcar 40% din plajă
    spread = max(num_list) - min(num_list)
    if spread > (max_ball * 0.4):
        bonus += 30
        
    # 3. Diversitate Decade
    decade = {n // 10 for n in num_list}
    if len(decade) >= (len(num_list) - 1): # Ex: 4 numere în 3 sau 4 decade
        bonus += 20
        
    return bonus

def calculeaza_scor_variant(varianta_set, runde_sets_ponderate, tip_joc_len, max_ball):
    scor_total = 0
    palmares = {4: 0, 3: 0, 2: 0}
    surse_atinse = set()
    
    variant_len = len(varianta_set)
    
    # Grilă Punctaj
    if variant_len == 4:
        pct_map = {4: 100, 3: 20, 2: 5}
    elif variant_len == 3:
        pct_map = {3: 100, 2: 15}
    elif tip_joc_len <= 7:
        pct_map = {6: 500, 5: 250, 4: 100, 3: 15, 2: 2} 
    else: 
        pct_map = {10: 500, 9: 200, 8: 100, 7: 50, 6: 20, 5: 5, 4: 2} 

    # 1. Puncte din Istoric (Backtesting)
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
    
    # 2. Puncte din Bonificații Smart (Matematică)
    # Se aplică doar dacă varianta are minim un mic succes în istoric (nu punctăm morții)
    if scor_total > 0:
        bonus = calculeaza_bonusuri_smart(sorted(list(varianta_set)), max_ball)
        scor_total += bonus

    return scor_total, palmares, len(surse_atinse)

def evolueaza_variante(parinti, runde_engine, draw_len, max_ball, target_count=15):
    copii = []
    attempts = 0
    max_attempts = target_count * 50
    if len(parinti) < 2: return []
    
    child_len = len(parinti[0]['set']) 

    while len(copii) < target_count and attempts < max_attempts:
        attempts += 1
        p1, p2 = random.sample(parinti, 2)
        union = list(p1['set'].union(p2['set']))
        if len(union) < child_len: continue
        
        child_nums = set(random.sample(union, child_len))
        if random.random() < 0.15: 
            child_list = list(child_nums)
            child_list[random.randint(0, child_len-1)] = random.randint(1, max_ball)
            child_nums = set(child_list)
        
        if len(child_nums) != child_len: continue
        
        child_sorted = sorted(list(child_nums))
        if not check_quality_patterns(child_sorted):
            continue

        scor, stats, coverage = calculeaza_scor_variant(child_nums, runde_engine, draw_len, max_ball)
        if scor > 0:
            unique_id = f"EVO_{int(time.time())}_{random.randint(100,999)}"
            copii.append({
                'ID': unique_id, 'Numere': str(child_sorted),
                'Scor': int(scor), 'Acoperire': str(coverage),
                'Stats': stats, 'Raw_Set': sorted(list(child_nums)),
                'Tip': '🧬 EVO', 'set': child_nums
            })

    copii.sort(key=lambda x: x['Scor'], reverse=True)
    return copii[:target_count]

def worker_analiza_hibrida(variante_brute, runde_config, top_n=100, evo_count=15, use_strict_filters=True):
    runde_engine = []
    total_surse_active = 0
    for i in range(1, 14):
        sursa_key = f"sursa_{i}"
        if sursa_key in runde_config and runde_config[sursa_key]:
            weight = 0.5 + (0.05 * i)
            total_surse_active += 1
            for runda in runde_config[sursa_key]:
                runde_engine.append({'set': set(runda), 'sursa': i, 'weight': min(weight, 1.2)})
    
    max_ball, draw_len = detecteaza_configuratia([r['set'] for r in runde_engine])
    
    rejected_sum = 0
    rejected_pattern = 0 
    rejected_zombie = 0
    
    candidati_procesati = []
    for var in variante_brute:
        v_list = var['numere_raw']
        variant_len = len(v_list)
        
        if use_strict_filters:
            ideal_sum = (variant_len * (max_ball + 1)) / 2
            suma_min = ideal_sum * 0.25 
            suma_max = ideal_sum * 1.75
            if not (suma_min <= sum(v_list) <= suma_max): 
                rejected_sum += 1
                continue
            
            if not check_quality_patterns(v_list):
                rejected_pattern += 1
                continue

        scor, stats, coverage = calculeaza_scor_variant(var['numere'], runde_engine, draw_len, max_ball)
        
        if use_strict_filters and total_surse_active > 0 and coverage == 0:
             rejected_zombie += 1
             continue

        candidati_procesati.append({
            'ID': var['id'], 'Numere': str(v_list), 'Scor': int(scor),
            'Acoperire': f"{coverage}/{total_surse_active}", 'Stats': stats,
            'Raw_Set': v_list, 'Tip': 'RAW', 'set': var['numere']
        })
    
    candidati_procesati.sort(key=lambda x: x['Scor'], reverse=True)
    
    copii_evoluti = []
    if candidati_procesati:
        parinti = candidati_procesati[:40] 
        copii_evoluti = evolueaza_variante(parinti, runde_engine, draw_len, max_ball, target_count=evo_count)
    
    raw_needed = top_n - len(copii_evoluti)
    best_raw = candidati_procesati[:raw_needed]
    
    rezultat_final = copii_evoluti + best_raw
    rezultat_final.sort(key=lambda x: x['Scor'], reverse=True)
    
    diagnostics = {
        'sum': rejected_sum,
        'pattern': rejected_pattern,
        'zombie': rejected_zombie,
        'config': f"{draw_len}/{max_ball}"
    }
    
    return rezultat_final, len(copii_evoluti), max_ball, draw_len, diagnostics

def elimina_redundanta(portofoliu):
    if not portofoliu: return []
    sorted_p = sorted(portofoliu, key=lambda x: x['Scor'], reverse=True)
    keep = []
    for current in sorted_p:
        is_redundant = False
        curr_set = set(current['Raw_Set'])
        for kept in keep:
            kept_set = set(kept['Raw_Set'])
            if len(curr_set.intersection(kept_set)) >= (len(curr_set) - 1):
                is_redundant = True
                break
        if not is_redundant: keep.append(current)
    return keep

# ==========================================
# 3. INTERFAȚA (UI)
# ==========================================

if 'portfolio' not in st.session_state: st.session_state.portfolio = []
if 'runde_db' not in st.session_state: st.session_state.runde_db = {}

def main():
    with st.sidebar:
        st.header("💾 Manager Proiect")
        if st.session_state.runde_db or st.session_state.portfolio:
            project_data = {'ts': time.time(), 'runde_db': st.session_state.runde_db, 'portfolio': st.session_state.portfolio}
            st.download_button("💾 Salvează JSON", json.dumps(project_data, default=str), f"loto_ai_{int(time.time())}.json", "application/json")
        
        up = st.file_uploader("Încarcă JSON", type=['json'])
        if up:
            try:
                d = json.load(up)
                st.session_state.runde_db = d.get('runde_db', {})
                st.session_state.portfolio = d.get('portfolio', [])
                st.success("Proiect Restaurat!"); time.sleep(1); st.rerun()
            except: st.error("Fișier corupt.")

    st.title("🧬 Loto AI Master Architect")
    
    tab1, tab2, tab3 = st.tabs(["1. 📂 SURSE & CALIBRARE", "2. ⛏️ MINERIT INTELIGENT", "3. 💰 PORTOFOLIU & BALANS"])

    with tab1:
        st.info("Sistemul detectează automat tipul de joc.")
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
        
        if all_rounds_flat:
            mb, dl = detecteaza_configuratia(all_rounds_flat)
            limit_pct = get_exposure_limit(mb, dl)
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Format Detectat", f"{dl} din {mb}")
            c2.metric("Limită Risc", f"{int(limit_pct*100)}%")
            c3.metric("Runde Totale", len(all_rounds_flat))

    with tab2:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("Configurare Minerit")
            inv = st.text_area("Variante Brute (Paste)", height=200, placeholder="ID, 1 2 3 4 5 6")
            
            if 'top_n' not in st.session_state: st.session_state.top_n = 100
            if 'evo_n' not in st.session_state: st.session_state.evo_n = 15
            
            st.session_state.top_n = st.slider("Mărime Lot", 50, 200, st.session_state.top_n)
            st.session_state.evo_n = st.slider("🧬 Genetic", 0, 50, st.session_state.evo_n)
            
            st.markdown("---")
            use_filters = st.checkbox("Activează Filtre Stricte (Tipare/Sumă)", value=True)
            
            run = st.button("🚀 ANALIZĂ HIBRIDĂ", type="primary", use_container_width=True)

        with c2:
            st.subheader("Rezultate")
            if run and inv:
                brute = []
                for l in inv.split('\n'):
                    if ',' in l:
                        p = l.split(',', 1)
                        try:
                            nums = [int(n) for n in p[1].split() if n.strip().isdigit()]
                            if nums: brute.append({'id': p[0].strip(), 'numere': set(nums), 'numere_raw': sorted(nums)})
                        except: pass
                
                if brute:
                    with st.spinner("⚙️ Procesare..."):
                        res, n_evo, mb, dl, diag = worker_analiza_hibrida(
                            brute, st.session_state.runde_db, 
                            st.session_state.top_n, st.session_state.evo_n, 
                            use_strict_filters=use_filters
                        )
                    
                    if not res and use_filters:
                        st.markdown(f"""
                        <div class="warning-box">
                            <h4>⚠️ Variante filtrate!</h4>
                            <ul>
                                <li><b>Tipare Interzise:</b> {diag['pattern']}</li>
                                <li><b>Sumă Incorectă:</b> {diag['sum']}</li>
                                <li><b>Zombie:</b> {diag['zombie']}</li>
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.success(f"Găsite: {len(res)} variante (Genetic: {n_evo})")
                        df = pd.DataFrame(res)
                        if not df.empty:
                            df['Palmares'] = df['Stats'].apply(lambda x: f"4x:{x[4]}|3x:{x[3]}")
                            st.dataframe(df[['Tip', 'ID', 'Numere', 'Scor', 'Acoperire', 'Palmares']], use_container_width=True, hide_index=True)
                            st.session_state.temp = res
                            st.session_state.game_params = (mb, dl)

            if 'temp' in st.session_state:
                st.divider()
                if st.button("📥 ADAUGĂ ÎN SEIF (Cu Filtru Risc)", use_container_width=True):
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
                    
                    st.toast(f"✅ +{added} adăugate! (⛔ {rejected} risc mare)")
                    del st.session_state.temp
                    st.rerun()

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
                    nums_str = " ".join(map(str, v['Raw_Set']))
                    txt_output += f"{v['ID']}, {nums_str}\n"

                st.download_button(
                    label="💾 Export .TXT (Format ID, Numere)",
                    data=txt_output,
                    file_name="Loto_Variante.txt",
                    mime="text/plain",
                    type="primary"
                )

        with c_view:
            if st.session_state.portfolio:
                df_p = pd.DataFrame(st.session_state.portfolio)
                st.dataframe(df_p[['Tip', 'ID', 'Numere', 'Scor', 'Acoperire']], use_container_width=True)
                st.divider()
                all_n = [n for v in st.session_state.portfolio for n in v['Raw_Set']]
                if all_n: st.bar_chart(pd.Series(all_n).value_counts().sort_index())

if __name__ == "__main__":
    main()
