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
    /* Stil pentru mesaje de eroare/succes compacte */
    .element-container { margin-bottom: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGICA MATEMATICĂ (ENGINE)
# ==========================================

@st.cache_data
def detecteaza_configuratia(runde_unice):
    """Auto-calibrare: Determină tipul de joc (6/49, 20/80 etc.)"""
    if not runde_unice:
        return 49, 6
    toate_numerele = [num for runda in runde_unice for num in runda]
    max_ball = max(toate_numerele) if toate_numerele else 49
    lungimi = [len(r) for r in runde_unice]
    avg_len = int(sum(lungimi) / len(lungimi)) if lungimi else 6
    return max_ball, avg_len

def get_exposure_limit(max_ball, draw_len):
    """Calculează AUTOMAT limita de expunere a unui număr."""
    if max_ball == 0: return 1.0
    base_prob = draw_len / max_ball
    limit = base_prob * 1.5
    # Limita minimă 15%, maximă 50% (pentru Keno)
    return max(0.15, min(limit, 0.50))

def check_portfolio_balance(candidate_nums, current_portfolio, max_exposure_percent):
    """
    Verifică riscul. Include 'Grace Period' pentru primele 20 variante.
    """
    total_size = len(current_portfolio) + 1
    
    # PERIOADA DE GRAȚIE: Nu aplicăm filtre stricte la început
    if total_size <= 20:
        return True
    
    # Numărăm frecvențele actuale
    all_nums = []
    for p in current_portfolio:
        all_nums.extend(p['Raw_Set'])
    counts = Counter(all_nums)
    
    # Verificăm ipotetic numerele noi
    for num in candidate_nums:
        curr_count = counts.get(num, 0)
        # Calculăm noua pondere dacă am adăuga această variantă
        new_ratio = (curr_count + 1) / total_size
        
        if new_ratio > max_exposure_percent:
            return False # Respins: Risc de supra-expunere
            
    return True

def calculeaza_scor_variant(varianta_set, runde_sets_ponderate, tip_joc_len):
    scor_total = 0
    palmares = {4: 0, 3: 0, 2: 0}
    surse_atinse = set()
    
    # Punctaj Dinamic
    if tip_joc_len <= 7:
        # Loto Clasic
        pct_map = {6: 500, 5: 250, 4: 100, 3: 15, 2: 2} 
    else: 
        # Keno
        pct_map = {10: 500, 9: 200, 8: 100, 7: 50, 6: 20, 5: 5} 

    for runda_obj in runde_sets_ponderate:
        runda_set = runda_obj['set']
        intersectie = len(varianta_set.intersection(runda_set))
        
        if intersectie in pct_map:
            points = pct_map[intersectie] * runda_obj['weight']
            scor_total += points
            
            # Palmares simplificat pentru afișare
            if intersectie >= 4: palmares[4] += 1
            elif intersectie == 3: palmares[3] += 1
            elif intersectie == 2: palmares[2] += 1
            
            surse_atinse.add(runda_obj['sursa'])

    return scor_total, palmares, len(surse_atinse)

def evolueaza_variante(parinti, runde_engine, draw_len, max_ball, target_count=15):
    copii = []
    attempts = 0
    max_attempts = target_count * 20
    
    if len(parinti) < 2: return []

    while len(copii) < target_count and attempts < max_attempts:
        attempts += 1
        p1, p2 = random.sample(parinti, 2)
        union = list(p1['set'].union(p2['set']))
        
        # Dacă părinții sunt prea diferiți și nu au destule numere comune, încercăm din nou
        if len(union) < draw_len: continue
        
        # Crossover
        child_nums = set(random.sample(union, draw_len))
        
        # Mutație (15% șansă)
        if random.random() < 0.15: 
            child_list = list(child_nums)
            child_list[random.randint(0, draw_len-1)] = random.randint(1, max_ball)
            child_nums = set(child_list)
        
        if len(child_nums) != draw_len: continue
        
        scor, stats, coverage = calculeaza_scor_variant(child_nums, runde_engine, draw_len)
        if scor > 0:
            # ID Unic bazat pe timp pentru a evita coliziuni
            unique_id = f"EVO_{int(time.time())}_{random.randint(100,999)}"
            copii.append({
                'ID': unique_id,
                'Numere': str(sorted(list(child_nums))),
                'Scor': int(scor),
                'Acoperire': str(coverage),
                'Stats': stats,
                'Raw_Set': sorted(list(child_nums)),
                'Tip': '🧬 EVO',
                'set': child_nums
            })

    copii.sort(key=lambda x: x['Scor'], reverse=True)
    return copii[:target_count]

def worker_analiza_hibrida(variante_brute, runde_config, top_n=100, evo_count=15):
    # Pregătire engine
    runde_engine = []
    total_surse_active = 0
    for i in range(1, 11):
        sursa_key = f"sursa_{i}"
        if sursa_key in runde_config and runde_config[sursa_key]:
            # Ponderare Temporală: Sursa 10 (1.0) vs Sursa 1 (0.55)
            weight = 0.5 + (0.05 * i)
            total_surse_active += 1
            for runda in runde_config[sursa_key]:
                runde_engine.append({'set': set(runda), 'sursa': i, 'weight': min(weight, 1.2)})
    
    max_ball, draw_len = detecteaza_configuratia([r['set'] for r in runde_engine])
    
    # Procesare RAW
    candidati_procesati = []
    for var in variante_brute:
        v_list = var['numere_raw']
        
        # Filtre de bază (Gaussian Sum + Parity)
        suma_min = (draw_len * (max_ball + 1) / 2) * 0.5 # Toleranță largă
        suma_max = (draw_len * (max_ball + 1) / 2) * 1.5
        if not (suma_min <= sum(v_list) <= suma_max): continue
        
        # Filtru Par/Impar (exclude tot par sau tot impar)
        pari = len([n for n in v_list if n % 2 == 0])
        if pari == 0 or pari == len(v_list): continue

        scor, stats, coverage = calculeaza_scor_variant(var['numere'], runde_engine, draw_len)
        
        # Filtru Anti-Zombie: Trebuie să aibă activitate în surse multiple
        if total_surse_active > 3 and coverage == 0: continue

        candidati_procesati.append({
            'ID': var['id'], 'Numere': str(v_list), 'Scor': int(scor),
            'Acoperire': f"{coverage}/{total_surse_active}", 'Stats': stats,
            'Raw_Set': v_list, 'Tip': 'RAW', 'set': var['numere']
        })
    
    candidati_procesati.sort(key=lambda x: x['Scor'], reverse=True)
    
    # Evoluție
    parinti = candidati_procesati[:40] # Luăm o bază mai largă de părinți
    copii_evoluti = evolueaza_variante(parinti, runde_engine, draw_len, max_ball, target_count=evo_count)
    
    raw_needed = top_n - len(copii_evoluti)
    best_raw = candidati_procesati[:raw_needed]
    
    rezultat_final = copii_evoluti + best_raw
    rezultat_final.sort(key=lambda x: x['Scor'], reverse=True)
    
    return rezultat_final, len(copii_evoluti), max_ball, draw_len

def elimina_redundanta(portofoliu):
    if not portofoliu: return []
    # Păstrăm variantele cu scor mare
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

# ==========================================
# 3. INTERFAȚA (UI)
# ==========================================

if 'portfolio' not in st.session_state: st.session_state.portfolio = []
if 'runde_db' not in st.session_state: st.session_state.runde_db = {}

def main():
    # SIDEBAR - MANAGER PROIECT
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

    # === TAB 1: INPUT DATE ===
    with tab1:
        st.info("Sistemul detectează automat tipul de joc și ajustează algoritmii.")
        tabs_surse = st.tabs([f"Sursa {i}" for i in range(1, 11)])
        
        all_rounds_flat = []
        for i, t in enumerate(tabs_surse, 1):
            with t:
                k = f"sursa_{i}"
                ex = st.session_state.runde_db.get(k, [])
                # Afișare inteligentă: Dacă sunt date, arată primele 10 linii + count
                val_show = "\n".join([",".join(map(str,r)) for r in ex[:20]]) if ex else ""
                
                txt = st.text_area(f"Paste Runde Sursa {i}", height=100, key=f"t_{i}", value=val_show)
                
                if txt and txt != val_show: # Procesăm doar dacă s-a schimbat
                    parsed = []
                    for l in txt.split('\n'):
                        try:
                            nums = sorted([int(n) for n in l.replace(';',',').replace(' ', ',').split(',') if n.strip().isdigit()])
                            if len(nums) > 1: parsed.append(nums)
                        except: pass
                    if parsed: 
                        st.session_state.runde_db[k] = parsed
                        st.success(f"✅ {len(parsed)} runde actualizate")
                    all_rounds_flat.extend(parsed)
                elif ex:
                    st.caption(f"ℹ️ {len(ex)} runde în memorie.")
                    all_rounds_flat.extend(ex)
        
        # Feedback Calibrare
        if all_rounds_flat:
            mb, dl = detecteaza_configuratia(all_rounds_flat)
            limit_pct = get_exposure_limit(mb, dl)
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Format Detectat", f"{dl} din {mb}")
            c2.metric("Limită Expunere", f"{int(limit_pct*100)}%", help="Limita automată de risc per număr.")
            c3.metric("Total Istoric", len(all_rounds_flat))

    # === TAB 2: MINERIT ===
    with tab2:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("Input & Config")
            inv = st.text_area("Variante Brute (Paste aici)", height=250, placeholder="ID, 1 2 3 4 5 6")
            
            # Parametrii salvati in sesiune pentru a nu se reseta la rerun
            if 'top_n' not in st.session_state: st.session_state.top_n = 100
            if 'evo_n' not in st.session_state: st.session_state.evo_n = 15
            
            st.session_state.top_n = st.slider("Mărime Lot", 50, 200, st.session_state.top_n)
            st.session_state.evo_n = st.slider("🧬 Generare Genetică", 0, 50, st.session_state.evo_n)
            
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
                    with st.spinner("⚙️ Procesare: Filtre -> Scoring -> Evoluție Genetică..."):
                        res, n_evo, mb, dl = worker_analiza_hibrida(brute, st.session_state.runde_db, st.session_state.top_n, st.session_state.evo_n)
                    
                    st.success(f"Analiză completă! {len(res)} variante (Genetic: {n_evo})")
                    
                    df = pd.DataFrame(res)
                    if not df.empty:
                        df['Palmares'] = df['Stats'].apply(lambda x: f"4x:{x[4]}|3x:{x[3]}")
                        st.dataframe(df[['Tip', 'ID', 'Numere', 'Scor', 'Acoperire', 'Palmares']], use_container_width=True, hide_index=True)
                        st.session_state.temp = res
                        st.session_state.game_params = (mb, dl)
                    else:
                        st.warning("Nicio variantă nu a trecut filtrele stricte.")

            if 'temp' in st.session_state:
                st.divider()
                if st.button("📥 ADAUGĂ CU FILTRU DE RISC AUTOMAT", use_container_width=True):
                    mb, dl = st.session_state.get('game_params', (49, 6))
                    limit_pct = get_exposure_limit(mb, dl)
                    
                    added, rejected = 0, 0
                    exist_ids = {v['ID'] for v in st.session_state.portfolio}
                    exist_sets = {tuple(v['Raw_Set']) for v in st.session_state.portfolio}
                    
                    work_portfolio = list(st.session_state.portfolio)
                    
                    for r in st.session_state.temp:
                        r_tup = tuple(r['Raw_Set'])
                        # 1. Unicitate
                        if r['ID'] not in exist_ids and r_tup not in exist_sets:
                            # 2. Risk Check
                            if check_portfolio_balance(r['Raw_Set'], work_portfolio, limit_pct):
                                st.session_state.portfolio.append(r)
                                work_portfolio.append(r) # Update local pt urmatorul check
                                added += 1
                                exist_ids.add(r['ID']) # Prevent duplicates within same batch
                            else:
                                rejected += 1
                    
                    st.toast(f"✅ +{added} adăugate! (⛔ {rejected} oprite de filtrul de risc)")
                    del st.session_state.temp
                    st.rerun()

    # === TAB 3: PORTOFOLIU ===
    with tab3:
        st.header(f"💰 Tezaur: {len(st.session_state.portfolio)} Variante")
        
        c_act, c_view = st.columns([1, 3])
        with c_act:
            st.write("Instrumente:")
            if st.button("🔍 Elimină Redundanța (Cluster)", type="secondary"):
                clean = elimina_redundanta(st.session_state.portfolio)
                rm = len(st.session_state.portfolio) - len(clean)
                st.session_state.portfolio = clean
                st.success(f"Optimizat! -{rm} redundante."); st.rerun()
            
            st.divider()
            if st.button("🗑️ Golește Tot"): st.session_state.portfolio = []; st.rerun()
            
            if st.session_state.portfolio:
                df_exp = pd.DataFrame(st.session_state.portfolio)[['ID', 'Numere', 'Scor', 'Acoperire', 'Stats', 'Tip']]
                st.download_button("💾 Export CSV", df_exp.to_csv(index=False).encode('utf-8'), "Master_Portfolio.csv", "text/csv", type="primary")

        with c_view:
            if st.session_state.portfolio:
                df_p = pd.DataFrame(st.session_state.portfolio)
                st.dataframe(df_p[['Tip', 'ID', 'Numere', 'Scor', 'Acoperire']], use_container_width=True)
                
                st.divider()
                st.caption("📊 Balanța Riscului (Distribuția Numerelor)")
                all_n = [n for v in st.session_state.portfolio for n in v['Raw_Set']]
                if all_n:
                    chart_data = pd.Series(all_n).value_counts().sort_index()
                    st.bar_chart(chart_data)

if __name__ == "__main__":
    main()
