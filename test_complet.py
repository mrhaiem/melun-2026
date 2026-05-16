#!/usr/bin/env python3
"""
test_complet.py — Test complet scrape + classements sur Cayenne 93699
Scrape toutes les épreuves, calcule les 3 challenges, génère test_cayenne.html
Usage : python test_complet.py
"""
import subprocess, re, time, sys, os, webbrowser
from bs4 import BeautifulSoup

COMPETITION = 93699
BASE_URL = f"https://www.liveffn.com/cgi-bin/resultats.php?competition={COMPETITION}&langue=fra"

# ── MAP ÉPREUVES ─────────────────────────────────────────────────────
# (eid_html, label, genre, cat, wr_secondes)
# cat: sprint | demi-fond | 4nages | relais
EVENTS = [
    ('e_50NL_F',     1, '50 NL',        'F', 'sprint',    23.67),
    ('e_50NL_H',    51, '50 NL',        'H', 'sprint',    20.91),
    ('e_200NL_F',    3, '200 NL',       'F', 'sprint',   112.98),
    ('e_200NL_H',   53, '200 NL',       'H', 'sprint',   102.00),
    ('e_400NL_F',    4, '400 NL',       'F', 'demi-fond', 236.40),
    ('e_400NL_H',   54, '400 NL',       'H', 'demi-fond', 220.07),
    ('e_50DOS_F',   11, '50 Dos',       'F', 'sprint',    27.06),
    ('e_50DOS_H',   61, '50 Dos',       'H', 'sprint',    24.00),
    ('e_100DOS_F',  12, '100 Dos',      'F', 'sprint',    57.45),
    ('e_100DOS_H',  62, '100 Dos',      'H', 'sprint',    51.60),
    ('e_200DOS_F',  13, '200 Dos',      'F', 'sprint',   123.35),
    ('e_200DOS_H',  63, '200 Dos',      'H', 'sprint',   111.92),
    ('e_50BR_F',    21, '50 Brasse',    'F', 'sprint',    29.40),
    ('e_50BR_H',    71, '50 Brasse',    'H', 'sprint',    25.95),
    ('e_100BR_F',   22, '100 Brasse',   'F', 'sprint',    64.13),
    ('e_100BR_H',   72, '100 Brasse',   'H', 'sprint',    56.88),
    ('e_200BR_F',   23, '200 Brasse',   'F', 'sprint',   138.95),
    ('e_200BR_H',   73, '200 Brasse',   'H', 'sprint',   125.95),
    ('e_50PA_F',    31, '50 Papillon',  'F', 'sprint',    24.43),
    ('e_50PA_H',    81, '50 Papillon',  'H', 'sprint',    22.27),
    ('e_100PA_F',   32, '100 Papillon', 'F', 'sprint',    55.48),
    ('e_100PA_H',   82, '100 Papillon', 'H', 'sprint',    49.45),
    ('e_200PA_H',   83, '200 Papillon', 'H', 'sprint',   110.73),
    ('e_200_4N_F',  41, '200 4 Nages',  'F', '4nages',   126.12),
    ('e_200_4N_H',  91, '200 4 Nages',  'H', '4nages',   114.00),
    ('e_4x50NL_F',  47, '4x50 NL',     'F', 'relais',    None),
    ('e_4x50NL_H',  97, '4x50 NL',     'H', 'relais',    None),
]

# ── SCRAPING ─────────────────────────────────────────────────────────
def fetch_html(url, retries=3):
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ['curl.exe', '-s', '-L', '--max-time', '15',
                 '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0',
                 url],
                capture_output=True, timeout=20
            )
            html = result.stdout.decode('utf-8', errors='replace')
            if html and '<tr' in html:
                return html
            if attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
        except:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    return ''

def time_to_seconds(t):
    t = t.strip()
    if not t or t in ('DSQ','DNS','DNF','ABD','NP'):
        return None
    try:
        if ':' in t:
            p = t.split(':')
            return int(p[0]) * 60 + float(p[1])
        return float(t)
    except:
        return None

def compute_pts(wr, secs):
    if not wr or not secs or secs <= 0:
        return 0
    return round(1000 * (wr / secs) ** 3)

def parse_event(html, eid, label, gender, cat, wr, is_relay=False):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for tr in soup.find_all('tr', class_='survol'):
        tds = tr.find_all('td')
        if len(tds) < 5:
            continue
        place_td = tr.find('td', class_='place')
        if not place_td:
            continue
        rank_m = re.match(r'^(\d+)', place_td.get_text(strip=True))
        if not rank_m:
            continue
        rank = int(rank_m.group(1))

        if is_relay:
            name  = tds[1].get_text(strip=True)
            year, club = '', ''
        else:
            name      = tds[1].get_text(strip=True)
            year_text = tds[2].get_text(strip=True)
            year      = int(year_text) if year_text.isdigit() else 0
            club      = tds[4].get_text(strip=True) if len(tds) > 4 else ''

        time_td = tr.find('td', class_='temps_sans_tps_passage') or tr.find('td', class_='temps')
        if time_td:
            raw = time_td.get_text(strip=True)
            m   = re.match(r'^(\d+:\d{2}\.\d{2}|\d+\.\d{2})', raw)
            time_str = m.group(1) if m else ''
        else:
            time_str = ''

        pts_td   = tr.find('td', class_='points')
        pts_text = pts_td.get_text(strip=True) if pts_td else '0'
        pts_m    = re.search(r'(\d+)', pts_text)
        pts      = int(pts_m.group(1)) if pts_m else 0

        secs = time_to_seconds(time_str)
        if not time_str or secs is None:
            continue
        if pts == 0 and wr:
            pts = compute_pts(wr, secs)

        results.append([eid, rank, name, year, club, time_str, pts])

    seen, out = set(), []
    for r in sorted(results, key=lambda x: x[1]):
        if r[1] not in seen:
            seen.add(r[1])
            out.append(r)
    return out[:6]

# ── CHALLENGES ───────────────────────────────────────────────────────
def challenge_nageurs(all_results, gender):
    best = {}
    for r in all_results:
        eid, rank, name, year, club, time_str, pts = r
        ev = next((e for e in EVENTS if e[0] == eid), None)
        if not ev or ev[3] != gender or ev[4] == 'relais':
            continue
        if name not in best or pts > best[name]['pts']:
            best[name] = {'name': name, 'year': year, 'club': club,
                          'pts': pts, 'event': ev[2], 'time': time_str}
    return sorted(best.values(), key=lambda x: -x['pts'])[:6]

def challenge_coachs(all_results, gender):
    # Pas de coaches définis pour Cayenne → on simule par club
    nageurs = challenge_nageurs(all_results, gender)
    coach_best = {}
    for s in nageurs:
        club = s['club']
        if club not in coach_best or s['pts'] > coach_best[club]['pts']:
            coach_best[club] = {**s, 'coach': f"Coach {club[:15]}"}
    return sorted(coach_best.values(), key=lambda x: -x['pts'])[:3]

def challenge_clubs(all_results):
    club_data = {}
    for r in all_results:
        eid, rank, name, year, club, time_str, pts = r
        ev = next((e for e in EVENTS if e[0] == eid), None)
        if not ev:
            continue
        is_relay = ev[4] == 'relais'
        cid = name if is_relay else club
        if not cid:
            continue
        if cid not in club_data:
            club_data[cid] = {'indiv': [], 'relay4N': None, 'relayNL': None}
        if is_relay:
            key = 'relay4N' if '4N' in ev[2] else 'relayNL'
            if not club_data[cid][key] or pts > club_data[cid][key]['pts']:
                club_data[cid][key] = {'pts': pts, 'event': ev[2]}
        else:
            club_data[cid]['indiv'].append({'swimmer': name, 'pts': pts, 'cat': ev[4], 'event': ev[3]})

    scores = []
    for cid, data in club_data.items():
        indiv = data['indiv']
        # Meilleure perf par nageur
        swimmer_best = {}
        for p in indiv:
            sw = p['swimmer']
            if sw not in swimmer_best or p['pts'] > swimmer_best[sw]['pts']:
                swimmer_best[sw] = p
        # Sélection : 1 4N + 1 fond + 4 libres (6 nageurs différents)
        used, chosen = set(), []
        for cat_req in ['4nages', 'demi-fond']:
            best_p, best_sw = None, None
            for sw, p in swimmer_best.items():
                if sw not in used and p['cat'] == cat_req:
                    if not best_p or p['pts'] > best_p['pts']:
                        best_p, best_sw = p, sw
            if best_p:
                chosen.append(best_p)
                used.add(best_sw)
        remaining = sorted(
            [(sw, p) for sw, p in swimmer_best.items() if sw not in used],
            key=lambda x: -x[1]['pts']
        )
        for sw, p in remaining[:6 - len(chosen)]:
            chosen.append(p)
            used.add(sw)
        # Relais
        for key in ['relayNL', 'relay4N']:
            if data[key]:
                chosen.append(data[key])
        total = sum(c['pts'] for c in chosen)
        scores.append({'club': cid, 'total': total, 'count': len(chosen), 'detail': chosen})
    # Filtrer les entrées qui ressemblent à des noms de nageurs (pas de clubs)
    real_clubs = [s for s in scores if len(s['club']) > 4 and ' ' not in s['club'][:3]]
    # Si club contient espace au début c'est probablement un vrai club
    all_clubs = [s for s in scores if s['count'] >= 2]  # au moins 2 perfs = vrai club
    return sorted(all_clubs if all_clubs else scores, key=lambda x: -x['total'])[:6]

# ── MAIN ─────────────────────────────────────────────────────────────
print("=" * 65)
print(f"  TEST COMPLET — Meeting Cayenne #{COMPETITION}")
print(f"  Scrape + Challenges Nageurs / Coachs / Clubs")
print("=" * 65)

all_results = []
failed = []  # épreuves à retenter

# ── PASSE 1 ──────────────────────────────────────────────
print("  PASSE 1 — Scraping initial (délai 4s)")
for ev_tuple in EVENTS:
    eid, enum, label, gender, cat, wr = ev_tuple
    is_relay = cat == 'relais'
    print(f"  ▶ {label:15} {gender}...", end=' ', flush=True)
    url  = f"{BASE_URL}&go=epreuve&epreuve={enum}"
    html = fetch_html(url)
    if not html:
        print("❌  → retry queue")
        failed.append(ev_tuple)
    else:
        rows = parse_event(html, eid, label, gender, cat, wr, is_relay)
        if rows:
            all_results.extend(rows)
            print(f"✅ {len(rows)}")
        else:
            print(f"⚠  0 résultat → retry queue")
            failed.append(ev_tuple)
    time.sleep(2.0)

# ── PASSE 2 — retry avec délai 5s ────────────────────────
if failed:
    print(f"\n  PASSE 2 — {len(failed)} épreuves à retenter (délai 5s)")
    still_failed = []
    for ev_tuple in failed:
        eid, enum, label, gender, cat, wr = ev_tuple
        is_relay = cat == 'relais'
        print(f"  ↺ {label:15} {gender}...", end=' ', flush=True)
        url  = f"{BASE_URL}&go=epreuve&epreuve={enum}"
        html = fetch_html(url, retries=5)
        if not html:
            print("❌")
            still_failed.append(ev_tuple)
        else:
            rows = parse_event(html, eid, label, gender, cat, wr, is_relay)
            if rows:
                all_results.extend(rows)
                print(f"✅ {len(rows)}")
            else:
                print(f"⚠  0")
                still_failed.append(ev_tuple)
        time.sleep(5.0)

    # ── PASSE 3 — dernière chance avec délai 10s ──────────
    if still_failed:
        print(f"\n  PASSE 3 — {len(still_failed)} épreuves (délai 10s, dernière chance)")
        for ev_tuple in still_failed:
            eid, enum, label, gender, cat, wr = ev_tuple
            is_relay = cat == 'relais'
            print(f"  ↺↺ {label:15} {gender}...", end=' ', flush=True)
            url  = f"{BASE_URL}&go=epreuve&epreuve={enum}"
            html = fetch_html(url, retries=5)
            rows = []
            if html:
                rows = parse_event(html, eid, label, gender, cat, wr, is_relay)
            if rows:
                all_results.extend(rows)
                print(f"✅ {len(rows)}")
            else:
                # Vérifier si l'épreuve est vraiment vide (pas de <tr class="survol">)
                if html and 'survol' not in html and len(html) > 5000:
                    print("⚪ épreuve sans participants (normal)")
                else:
                    print("❌ abandon (rate limit persistant)")
            time.sleep(10.0)

ok_count = len(set(r[0] for r in all_results))
print(f"\n  → {ok_count}/{len(EVENTS)} épreuves — {len(all_results)} lignes totales\n")

# ── AFFICHAGE CLASSEMENTS ─────────────────────────────────────────────
prizes_clubs = [1600, 1200, 800, 500, 300, 100]

for gender in ['F', 'H']:
    gname = 'Dames' if gender == 'F' else 'Messieurs'
    print(f"{'='*65}")
    print(f"  ⚡ CHALLENGE NAGEURS — {gname}")
    print(f"{'='*65}")
    nageurs = challenge_nageurs(all_results, gender)
    if nageurs:
        for i, n in enumerate(nageurs):
            print(f"  {i+1}. {n['name']:<30} {n['club'][:25]:<25} {n['event']:>12}  {n['pts']:>5} pts")
    else:
        print("  Aucune donnée")

print()
for gender in ['F', 'H']:
    gname = 'Dames' if gender == 'F' else 'Messieurs'
    print(f"{'='*65}")
    print(f"  🎯 CHALLENGE COACHS — {gname}")
    print(f"{'='*65}")
    coachs = challenge_coachs(all_results, gender)
    prizes = ['300€', '200€', '100€']
    for i, c in enumerate(coachs):
        print(f"  {i+1}. {c['club'][:35]:<35} {c['pts']:>5} pts  ({c['event']} — {c['name']})  {prizes[i] if i < 3 else ''}")

print()
print(f"{'='*65}")
print(f"  🏆 CHALLENGE CLUBS")
print(f"{'='*65}")
clubs = challenge_clubs(all_results)
for i, c in enumerate(clubs):
    prize = f"{prizes_clubs[i]}€" if i < len(prizes_clubs) else ''
    print(f"  {i+1}. {c['club'][:35]:<35} {c['total']:>5} pts  {prize}")
    detail = ', '.join(f"{d['event']}:{d['pts']}" for d in sorted(c['detail'], key=lambda x:-x['pts'])[:4])
    print(f"     ({c['count']} perfs) {detail}")

# ── INJECTION DANS LE HTML ────────────────────────────────────────────
import re as re_mod

# Construire le JS EVENTS pour Cayenne
events_js_lines = []
for eid, enum, label, gender, cat, wr in EVENTS:
    wrs = wr if wr else 'null'
    events_js_lines.append(
        f"  {{id:'{eid}', l:'{label}', g:'{gender}', sess:1, cat:'{cat}', wrs:{wrs}}}"
    )
new_events_js = "const EVENTS = [\n" + ",\n".join(events_js_lines) + "\n];"


html_source = 'melun_meeting_2026.html'
html_dest   = 'test_cayenne.html'

if not os.path.exists(html_source):
    print(f"\n⚠  {html_source} introuvable dans ce dossier — copie le depuis le repo.")
    sys.exit(0)

with open(html_source, encoding='utf-8') as f:
    html_content = f.read()

# Construire le JS RESULTS
lines = []
for r in all_results:
    eid, rank, name, year, club, time_str, pts = r
    ev = next((e for e in EVENTS if e[0] == eid), None)
    if not ev:
        continue
    is_relay = ev[4] == 'relais'
    name_e = name.replace("'", "\\'")
    club_e = club.replace("'", "\\'")
    if is_relay:
        lines.append(f"  ['{eid}',{rank},'{name_e}','','','{time_str}',{pts}]")
    else:
        lines.append(f"  ['{eid}',{rank},'{name_e}',{year},'{club_e}','{time_str}',{pts}]")

new_results = "const RESULTS = [\n" + ",\n".join(lines) + "\n];"

# Construire CLUBS dynamiquement depuis les données scrapées
clubs_seen = {}
for r in all_results:
    eid, rank, name, year, club, time_str, pts = r
    ev = next((e for e in EVENTS if e[0] == eid), None)
    if not ev or ev[4] == 'relais' or not club:
        continue
    if club not in clubs_seen:
        short = club[:12] if len(club) > 12 else club
        clubs_seen[club] = f"  '{club}': {{ name: '{club}', short: '{short}', coach: 'Coach {club[:20]}' }}"

clubs_js_body = ",\n".join(clubs_seen.values())
new_clubs_js = f"const CLUBS = {{\n{clubs_js_body}\n}};"

new_content = re_mod.sub(r'const RESULTS = \[.*?\];', new_results, html_content, flags=re_mod.DOTALL)
new_content = re_mod.sub(r'const EVENTS = \[.*?\];', new_events_js, new_content, flags=re_mod.DOTALL)
new_content = re_mod.sub(r'const CLUBS = \{.*?\};', new_clubs_js, new_content, flags=re_mod.DOTALL)
new_content = new_content.replace('En attente des résultats — natvision.fr',
                                  f'TEST — Meeting Cayenne #{COMPETITION} — natvision.fr')

with open(html_dest, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"\n  ✅ Fichier généré : {html_dest}")
print(f"  → Ouverture dans le navigateur...")
webbrowser.open(os.path.abspath(html_dest))
