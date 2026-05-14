#!/usr/bin/env python3
"""
scrape_melun.py — Scraper liveffn → melun_meeting_2026.html
Compétition 92947 — 13ème Meeting de la Ville de Melun — 16 & 17 Mai 2026

Usage:
    python scrape_melun.py              # run once
    python scrape_melun.py --loop 120   # boucle toutes les 120s
    python scrape_melun.py --push       # git push après chaque update

Dépendances : pip install requests beautifulsoup4
"""

import re, sys, time, json, subprocess, argparse
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install requests beautifulsoup4")
    sys.exit(1)

# ============================================================
# CONFIG
# ============================================================
COMPETITION_ID = 92947
BASE_URL = f"https://www.liveffn.com/cgi-bin/resultats.php?competition={COMPETITION_ID}&langue=fra"
HTML_FILE = Path(__file__).parent / "melun_meeting_2026.html"

# World records (LCM 50m) pour recalcul points si absent de liveffn
WR = {
    's1_800NL_F': 484.79,   's1_800NL_H': 452.12,
    's1_200DOS_F': 123.35,  's1_200DOS_H': 111.92,
    's1_100BR_F': 64.13,    's1_100BR_H': 56.88,
    's2_200_4N_F': 126.12,  's2_200_4N_H': 114.00,
    's2_100DOS_F': 57.45,   's2_100DOS_H': 51.60,
    's2_100PA_F': 55.48,    's2_100PA_H': 49.45,
    's2_200NL_F': 112.98,   's2_200NL_H': 102.00,
    's2_200BR_F': 138.95,   's2_200BR_H': 125.95,
    's2_4x100NL_F': 215.73, 's2_4x100NL_H': 198.80,
    's3_1500NL_F': 920.48,  's3_1500NL_H': 871.02,
    's3_200PA_F': 121.81,   's3_200PA_H': 110.73,
    's3_50DOS_F': 27.06,    's3_50DOS_H': 24.00,
    's3_50NL_F': 23.67,     's3_50NL_H': 20.91,
    's4_50BR_F': 29.40,     's4_50BR_H': 25.95,
    's4_400NL_F': 236.40,   's4_400NL_H': 220.07,
    's4_50PA_F': 24.43,     's4_50PA_H': 22.27,
    's4_400_4N_F': 266.36,  's4_400_4N_H': 243.84,
    's4_100NL_F': 51.71,    's4_100NL_H': 46.91,
    's4_4x100_4N_F': 233.78,'s4_4x100_4N_H': 214.76,
}

# Mapping numéro épreuve liveffn → event_id du HTML
# Ordre extrait du programme liveffn (séquentiel par session)
EVENT_MAP = {
     1: ('s1_800NL_F',    '800 Nage Libre',   'F', 1, 'demi-fond'),
     2: ('s1_800NL_H',    '800 Nage Libre',   'H', 1, 'demi-fond'),
     3: ('s1_200DOS_F',   '200 Dos',          'F', 1, 'sprint'),
     4: ('s1_200DOS_H',   '200 Dos',          'H', 1, 'sprint'),
     5: ('s1_100BR_F',    '100 Brasse',       'F', 1, 'sprint'),
     6: ('s1_100BR_H',    '100 Brasse',       'H', 1, 'sprint'),
     7: ('s2_200_4N_F',   '200 4 Nages',      'F', 2, '4nages'),
     8: ('s2_200_4N_H',   '200 4 Nages',      'H', 2, '4nages'),
     9: ('s2_100DOS_F',   '100 Dos',          'F', 2, 'sprint'),
    10: ('s2_100DOS_H',   '100 Dos',          'H', 2, 'sprint'),
    11: ('s2_100PA_F',    '100 Papillon',     'F', 2, 'sprint'),
    12: ('s2_100PA_H',    '100 Papillon',     'H', 2, 'sprint'),
    13: ('s2_200NL_F',    '200 Nage Libre',   'F', 2, 'sprint'),
    14: ('s2_200NL_H',    '200 Nage Libre',   'H', 2, 'sprint'),
    15: ('s2_200BR_F',    '200 Brasse',       'F', 2, 'sprint'),
    16: ('s2_200BR_H',    '200 Brasse',       'H', 2, 'sprint'),
    17: ('s2_4x100NL_F',  '4×100 NL',        'F', 2, 'relais'),
    18: ('s2_4x100NL_H',  '4×100 NL',        'H', 2, 'relais'),
    19: ('s3_1500NL_F',   '1500 Nage Libre',  'F', 3, 'demi-fond'),
    20: ('s3_1500NL_H',   '1500 Nage Libre',  'H', 3, 'demi-fond'),
    21: ('s3_200PA_F',    '200 Papillon',     'F', 3, 'sprint'),
    22: ('s3_200PA_H',    '200 Papillon',     'H', 3, 'sprint'),
    23: ('s3_50DOS_F',    '50 Dos',           'F', 3, 'sprint'),
    24: ('s3_50DOS_H',    '50 Dos',           'H', 3, 'sprint'),
    25: ('s3_50NL_F',     '50 Nage Libre',    'F', 3, 'sprint'),
    26: ('s3_50NL_H',     '50 Nage Libre',    'H', 3, 'sprint'),
    27: ('s4_50BR_F',     '50 Brasse',        'F', 4, 'sprint'),
    28: ('s4_50BR_H',     '50 Brasse',        'H', 4, 'sprint'),
    29: ('s4_400NL_F',    '400 Nage Libre',   'F', 4, 'demi-fond'),
    30: ('s4_400NL_H',    '400 Nage Libre',   'H', 4, 'demi-fond'),
    31: ('s4_50PA_F',     '50 Papillon',      'F', 4, 'sprint'),
    32: ('s4_50PA_H',     '50 Papillon',      'H', 4, 'sprint'),
    33: ('s4_400_4N_F',   '400 4 Nages',      'F', 4, '4nages'),
    34: ('s4_400_4N_H',   '400 4 Nages',      'H', 4, '4nages'),
    35: ('s4_100NL_F',    '100 Nage Libre',   'F', 4, 'sprint'),
    36: ('s4_100NL_H',    '100 Nage Libre',   'H', 4, 'sprint'),
    37: ('s4_4x100_4N_F', '4×100 4N',        'F', 4, 'relais'),
    38: ('s4_4x100_4N_H', '4×100 4N',        'H', 4, 'relais'),
}

# ============================================================
# HELPERS
# ============================================================
def time_to_seconds(t: str) -> float | None:
    """'1:02.34' → 62.34 / '52.34' → 52.34 / 'DSQ' → None"""
    t = t.strip()
    if not t or t in ('DSQ', 'DNS', 'DNF', 'ABD', 'NP', '—', '-'):
        return None
    try:
        if ':' in t:
            parts = t.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return float(t)
    except ValueError:
        return None

def compute_points(event_id: str, seconds: float) -> int:
    wr = WR.get(event_id)
    if not wr or seconds <= 0:
        return 0
    return round(1000 * (wr / seconds) ** 3)

def clean_name(s: str) -> str:
    return ' '.join(s.split())

def fetch_event(event_num: int) -> list[dict]:
    """Scrape une épreuve liveffn et retourne liste de résultats."""
    url = f"{BASE_URL}&go=epreuve&epreuve={event_num}"
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
    except Exception as e:
        print(f"  ⚠ Erreur fetch épreuve {event_num}: {e}")
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    event_id, label, gender, sess, cat = EVENT_MAP[event_num]
    is_relay = cat == 'relais'

    results = []

    # liveffn structure: table.resultat ou table avec class liée
    # Cherche toutes les tables de résultats
    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue

            # Détection rang : premier td contient un nombre
            rank_text = clean_name(cells[0].get_text())
            if not rank_text.isdigit():
                continue
            rank = int(rank_text)

            if is_relay:
                # Format relais: rang | club | temps | points
                club = clean_name(cells[1].get_text())
                time_str = clean_name(cells[2].get_text()) if len(cells) > 2 else ''
                pts_raw = clean_name(cells[3].get_text()) if len(cells) > 3 else ''
            else:
                # Format individuel liveffn typique:
                # rang | nom | prénom | annee | club | temps | [pts]
                # ou: rang | nom prénom | annee | club | temps | [pts]
                # On adapte selon le nombre de colonnes
                if len(cells) >= 6:
                    # nom + prenom séparés
                    nom = clean_name(cells[1].get_text())
                    prenom = clean_name(cells[2].get_text())
                    name = f"{nom} {prenom}".strip()
                    year_text = clean_name(cells[3].get_text())
                    club = clean_name(cells[4].get_text())
                    time_str = clean_name(cells[5].get_text())
                    pts_raw = clean_name(cells[6].get_text()) if len(cells) > 6 else ''
                elif len(cells) >= 4:
                    # nom prénom dans une seule cellule
                    name = clean_name(cells[1].get_text())
                    year_text = clean_name(cells[2].get_text()) if len(cells) > 2 else ''
                    club = clean_name(cells[3].get_text()) if len(cells) > 3 else ''
                    time_str = clean_name(cells[4].get_text()) if len(cells) > 4 else ''
                    pts_raw = clean_name(cells[5].get_text()) if len(cells) > 5 else ''
                else:
                    continue

                # Extraire l'année (4 chiffres)
                year = 0
                for c in [year_text] + [clean_name(x.get_text()) for x in cells]:
                    m = re.search(r'\b(19|20)\d{2}\b', c)
                    if m:
                        year = int(m.group())
                        break

            # Temps
            seconds = time_to_seconds(time_str)
            if seconds is None:
                continue

            # Points: liveffn les affiche parfois, sinon on recalcule
            pts = 0
            if pts_raw and pts_raw.isdigit():
                pts = int(pts_raw)
            elif pts_raw:
                m = re.search(r'\d+', pts_raw)
                if m:
                    pts = int(m.group())
            if pts == 0:
                pts = compute_points(event_id, seconds)

            if is_relay:
                results.append({
                    'event': event_id, 'rank': rank,
                    'name': club, 'year': '', 'club': '',
                    'time': time_str, 'pts': pts, 'relay': True
                })
            else:
                results.append({
                    'event': event_id, 'rank': rank,
                    'name': name, 'year': year, 'club': club,
                    'time': time_str, 'pts': pts, 'relay': False
                })

    # Dédoublonner par rang (parfois liveffn répète les lignes)
    seen = set()
    dedup = []
    for r in results:
        key = r['rank']
        if key not in seen:
            seen.add(key)
            dedup.append(r)

    return dedup[:6]  # top 6

# ============================================================
# INJECTION DANS LE HTML
# ============================================================
def build_results_js(all_results: list[dict]) -> str:
    """Construit le tableau RESULTS JavaScript."""
    lines = []
    for r in all_results:
        if r['relay']:
            # relay : name = clubId, year et club vides
            name = r['name'].replace("'", "\\'")
            line = f"  ['{r['event']}',{r['rank']},'{name}','','','{r['time']}',{r['pts']}]"
        else:
            name = r['name'].replace("'", "\\'")
            club = r['club'].replace("'", "\\'")
            line = f"  ['{r['event']}',{r['rank']},'{name}',{r['year']},'{club}','{r['time']}',{r['pts']}]"
        lines.append(line)
    return "const RESULTS = [\n" + ",\n".join(lines) + "\n];"

def inject_into_html(all_results: list[dict], html_path: Path) -> bool:
    """Remplace le bloc RESULTS dans le HTML."""
    content = html_path.read_text(encoding='utf-8')
    new_js = build_results_js(all_results)

    # Remplace entre "const RESULTS = [" et "];"
    pattern = r'const RESULTS = \[.*?\];'
    new_content = re.sub(pattern, new_js, content, flags=re.DOTALL)

    if new_content == content:
        print("  ⚠ Aucun changement détecté dans le HTML")
        return False

    # Injecter timestamp de dernière mise à jour
    ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    new_content = re.sub(
        r'Données de démonstration — natvision\.fr',
        f'Dernière mise à jour : {ts} — natvision.fr',
        new_content
    )

    html_path.write_text(new_content, encoding='utf-8')
    print(f"  ✓ HTML mis à jour ({len(all_results)} résultats)")
    return True

# ============================================================
# GIT PUSH
# ============================================================
def git_push():
    try:
        subprocess.run(['git', 'add', str(HTML_FILE)], check=True, capture_output=True)
        msg = f"update resultats {datetime.now().strftime('%H:%M:%S')}"
        subprocess.run(['git', 'commit', '-m', msg], check=True, capture_output=True)
        subprocess.run(['git', 'push'], check=True, capture_output=True)
        print("  ✓ git push OK → natvision.fr")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ git push échoué: {e.stderr.decode()[:200]}")

# ============================================================
# MAIN
# ============================================================
def run_once(do_push: bool = False):
    print(f"\n{'='*50}")
    print(f"  {datetime.now().strftime('%H:%M:%S')} — Scraping competition {COMPETITION_ID}")
    print(f"{'='*50}")

    all_results = []
    events_scraped = 0
    events_with_data = 0

    for num, info in EVENT_MAP.items():
        event_id, label, gender, sess, cat = info
        print(f"  Épreuve {num:2d} — {label} {gender}... ", end='', flush=True)
        rows = fetch_event(num)
        if rows:
            all_results.extend(rows)
            events_with_data += 1
            print(f"{len(rows)} résultats")
        else:
            print("pas encore disponible")
        events_scraped += 1
        time.sleep(0.3)  # politesse serveur

    print(f"\n  → {events_with_data}/{events_scraped} épreuves avec résultats")
    print(f"  → {len(all_results)} lignes total")

    if all_results:
        changed = inject_into_html(all_results, HTML_FILE)
        if changed and do_push:
            git_push()
    else:
        print("  → Aucun résultat disponible, HTML non modifié")

def main():
    parser = argparse.ArgumentParser(description='Scraper liveffn → Melun Meeting HTML')
    parser.add_argument('--loop', type=int, default=0,
                        help='Intervalle en secondes pour la boucle (0 = run once)')
    parser.add_argument('--push', action='store_true',
                        help='git push après chaque mise à jour')
    args = parser.parse_args()

    if args.loop > 0:
        print(f"Mode boucle : refresh toutes les {args.loop}s — Ctrl+C pour arrêter")
        while True:
            try:
                run_once(do_push=args.push)
                print(f"\n  ⏳ Prochain refresh dans {args.loop}s...\n")
                time.sleep(args.loop)
            except KeyboardInterrupt:
                print("\n  Arrêt.")
                break
    else:
        run_once(do_push=args.push)

if __name__ == '__main__':
    main()
