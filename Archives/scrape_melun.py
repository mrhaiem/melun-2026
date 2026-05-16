#!/usr/bin/env python3
"""
scrape_melun.py — Scraper liveffn → melun_meeting_2026.html
Competition 92947 — 13ème Meeting de la Ville de Melun — 16 & 17 Mai 2026

Usage:
    py -3.11 scrape_melun.py              # run once
    py -3.11 scrape_melun.py --loop 120   # boucle toutes les 120s
    py -3.11 scrape_melun.py --loop 120 --push  # + git push
"""
import re, sys, time, subprocess, argparse, shutil, json
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install beautifulsoup4")
    sys.exit(1)

# ── CONFIG ───────────────────────────────────────────────────────────
COMPETITION_ID = 92947
BASE_URL = f"https://www.liveffn.com/cgi-bin/resultats.php?competition={COMPETITION_ID}&langue=fra"
HTML_FILE   = Path(__file__).parent / "melun_meeting_2026.html"
STATE_FILE  = Path(__file__).parent / "scrape_state.json"

# ── MAP ÉPREUVES ─────────────────────────────────────────────────────
# (num_liveffn, event_id_html, label, genre, session, categorie, wr_secondes)
EVENT_MAP = [
    # Session 1 — Samedi matin
    ( 5, 's1_800NL_F',    '800 Nage Libre',   'F', 1, 'demi-fond', 484.79),
    (55, 's1_800NL_H',    '800 Nage Libre',   'H', 1, 'demi-fond', 452.12),
    (13, 's1_200DOS_F',   '200 Dos',          'F', 1, 'sprint',    123.35),
    (63, 's1_200DOS_H',   '200 Dos',          'H', 1, 'sprint',    111.92),
    (22, 's1_100BR_F',    '100 Brasse',       'F', 1, 'sprint',     64.13),
    (72, 's1_100BR_H',    '100 Brasse',       'H', 1, 'sprint',     56.88),
    # Session 2 — Samedi après-midi
    (41, 's2_200_4N_F',   '200 4 Nages',      'F', 2, '4nages',    126.12),
    (91, 's2_200_4N_H',   '200 4 Nages',      'H', 2, '4nages',    114.00),
    (12, 's2_100DOS_F',   '100 Dos',          'F', 2, 'sprint',     57.45),
    (62, 's2_100DOS_H',   '100 Dos',          'H', 2, 'sprint',     51.60),
    (32, 's2_100PA_F',    '100 Papillon',     'F', 2, 'sprint',     55.48),
    (82, 's2_100PA_H',    '100 Papillon',     'H', 2, 'sprint',     49.45),
    ( 3, 's2_200NL_F',    '200 Nage Libre',   'F', 2, 'sprint',    112.98),
    (53, 's2_200NL_H',    '200 Nage Libre',   'H', 2, 'sprint',    102.00),
    (23, 's2_200BR_F',    '200 Brasse',       'F', 2, 'sprint',    138.95),
    (73, 's2_200BR_H',    '200 Brasse',       'H', 2, 'sprint',    125.95),
    (43, 's2_4x100NL_F',  '4x100 NL',         'F', 2, 'relais',      None),
    (93, 's2_4x100NL_H',  '4x100 NL',         'H', 2, 'relais',      None),
    # Session 3 — Dimanche matin
    ( 6, 's3_1500NL_F',   '1500 Nage Libre',  'F', 3, 'demi-fond', 920.48),
    (56, 's3_1500NL_H',   '1500 Nage Libre',  'H', 3, 'demi-fond', 871.02),
    (33, 's3_200PA_F',    '200 Papillon',     'F', 3, 'sprint',    121.81),
    (83, 's3_200PA_H',    '200 Papillon',     'H', 3, 'sprint',    110.73),
    (11, 's3_50DOS_F',    '50 Dos',           'F', 3, 'sprint',     27.06),
    (61, 's3_50DOS_H',    '50 Dos',           'H', 3, 'sprint',     24.00),
    ( 1, 's3_50NL_F',     '50 Nage Libre',    'F', 3, 'sprint',     23.67),
    (51, 's3_50NL_H',     '50 Nage Libre',    'H', 3, 'sprint',     20.91),
    # Session 4 — Dimanche après-midi
    (21, 's4_50BR_F',     '50 Brasse',        'F', 4, 'sprint',     29.40),
    (71, 's4_50BR_H',     '50 Brasse',        'H', 4, 'sprint',     25.95),
    ( 4, 's4_400NL_F',    '400 Nage Libre',   'F', 4, 'demi-fond', 236.40),
    (54, 's4_400NL_H',    '400 Nage Libre',   'H', 4, 'demi-fond', 220.07),
    (31, 's4_50PA_F',     '50 Papillon',      'F', 4, 'sprint',     24.43),
    (81, 's4_50PA_H',     '50 Papillon',      'H', 4, 'sprint',     22.27),
    (42, 's4_400_4N_F',   '400 4 Nages',      'F', 4, '4nages',    266.36),
    (92, 's4_400_4N_H',   '400 4 Nages',      'H', 4, '4nages',    243.84),
    ( 2, 's4_100NL_F',    '100 Nage Libre',   'F', 4, 'sprint',     51.71),
    (52, 's4_100NL_H',    '100 Nage Libre',   'H', 4, 'sprint',     46.91),
    (46, 's4_4x100_4N_F', '4x100 4N',         'F', 4, 'relais',      None),
    (96, 's4_4x100_4N_H', '4x100 4N',         'H', 4, 'relais',      None),
]


# ── STATE (résultats déjà scrapés) ───────────────────────────────────
def load_state():
    """Charge les résultats déjà scrapés depuis le fichier état."""
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding='utf-8'))
            print(f"  ✓ État chargé — {len(data)} épreuves déjà scrapées")
            return data  # { event_id: [[eid,rank,name,...], ...] }
        except:
            pass
    return {}

def save_state(state):
    """Sauvegarde l'état des résultats."""
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

def reset_state():
    """Réinitialise l'état (utile en début de journée)."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("  ✓ État réinitialisé")

# ── HELPERS ──────────────────────────────────────────────────────────
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

def compute_points(wr, secs):
    if not wr or not secs or secs <= 0:
        return 0
    return round(1000 * (wr / secs) ** 3)


# ── FILTRE TEMPOREL ──────────────────────────────────────────────────
# Sessions Melun 92947 — horaires officiels
# Session 1 : Samedi matin    → épreuves 1-6   (début 10h00)
# Session 2 : Samedi APM      → épreuves 7-18  (début 15h30)
# Session 3 : Dimanche matin  → épreuves 19-26 (début 10h00)
# Session 4 : Dimanche APM    → épreuves 27-38 (début 15h00)

SESSION_SCHEDULE = {
    1: ('samedi',   10, 30),   # jour, heure_debut, buffer_minutes
    2: ('samedi',   15, 45),
    3: ('dimanche', 10, 30),
    4: ('dimanche', 15, 30),
}

def session_has_started(session_num):
    """Retourne True si la session a démarré (heure actuelle > début + buffer)."""
    now = datetime.now()
    weekday = now.weekday()  # 5=samedi, 6=dimanche
    day, start_h, buffer_min = SESSION_SCHEDULE[session_num]

    if day == 'samedi'   and weekday != 5: return False
    if day == 'dimanche' and weekday != 6: return False

    start_minutes = start_h * 60 + buffer_min
    now_minutes   = now.hour * 60 + now.minute
    return now_minutes >= start_minutes

def get_sessions_to_scrape():
    sessions = [s for s in [1,2,3,4] if session_has_started(s)]
    return sessions

# ── FETCH via curl.exe ───────────────────────────────────────────────
def fetch_html(event_num, retries=3):
    url = f"{BASE_URL}&go=epreuve&epreuve={event_num}"
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ['curl.exe', '-s', '-L', '--max-time', '15',
                 '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0',
                 url],
                capture_output=True, timeout=20
            )
            html = result.stdout.decode('utf-8', errors='replace')
            if html and 'class="place"' in html:
                return html
            if html and len(html) > 3000:
                return "NO_RESULTS"
            if attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
        except Exception:
            if attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
    return ''  # Connexion échouée''

# ── PARSE RÉSULTATS ──────────────────────────────────────────────────
def parse_event(html, eid, label, cat, wr):
    is_relay = cat == 'relais'
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

        time_td = (tr.find('td', class_='temps_sans_tps_passage') or
                   tr.find('td', class_='temps'))
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
            pts = compute_points(wr, secs)

        results.append((eid, rank, name, year, club, time_str, pts))

    # Dédoublonner + top 6
    seen, out = set(), []
    for r in sorted(results, key=lambda x: x[1]):
        if r[1] not in seen:
            seen.add(r[1])
            out.append(r)
    return out  # Tous les résultats

# ── BUILD JS RESULTS ─────────────────────────────────────────────────
def build_results_js(all_results):
    lines = []
    for r in all_results:
        eid, rank, name, year, club, time_str, pts = r
        name_e = name.replace("'", "\\'")
        club_e = club.replace("'", "\\'")
        if club == '':  # relay
            lines.append(f"  ['{eid}',{rank},'{name_e}','','','{time_str}',{pts}]")
        else:
            lines.append(f"  ['{eid}',{rank},'{name_e}',{year},'{club_e}','{time_str}',{pts}]")
    return "const RESULTS = [\n" + ",\n".join(lines) + "\n];"

# ── INJECT HTML ──────────────────────────────────────────────────────
def inject_html(all_results):
    content = HTML_FILE.read_text(encoding='utf-8')
    new_js  = build_results_js(all_results)
    new_content = re.sub(r'const RESULTS = \[.*?\];', new_js, content, flags=re.DOTALL)
    ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    new_content = re.sub(
        r'(En attente des résultats|Dernière mise à jour.*?)— natvision\.fr',
        f'Dernière mise à jour : {ts} — natvision.fr',
        new_content
    )
    if new_content == content:
        print("  ⚠ Aucun changement")
        return False
    HTML_FILE.write_text(new_content, encoding='utf-8')
    print(f"  ✓ HTML mis à jour — {len(all_results)} résultats")
    return True

# ── GIT PUSH ─────────────────────────────────────────────────────────
def git_push():
    try:
        subprocess.run(['git', 'add', str(HTML_FILE)], check=True, capture_output=True)
        index_file = HTML_FILE.parent / "index.html"
        if index_file.exists():
            subprocess.run(['git', 'add', str(index_file)], check=True, capture_output=True)
        msg = f"update {datetime.now().strftime('%H:%M:%S')}"
        subprocess.run(['git', 'commit', '-m', msg], check=True, capture_output=True)
        subprocess.run(['git', 'push'], check=True, capture_output=True)
        print("  ✓ git push → GitHub Pages")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ git push échoué : {e.stderr.decode()[:100] if e.stderr else ''}")

# ── RUN ONCE ─────────────────────────────────────────────────────────
def run_once(do_push=False):
    print(f"\n{'='*50}")
    print(f"  {datetime.now().strftime('%H:%M:%S')} — Competition {COMPETITION_ID}")
    print(f"{'='*50}")

    # Charger l'état existant — résultats déjà scrapés
    state = load_state()
    # Reconstruire all_results depuis le state complet (toutes sessions)
    all_results = [row for rows in state.values() for row in rows]
    failed      = []

    # Filtrer sur les sessions déjà commencées
    active_sessions = get_sessions_to_scrape()
    if active_sessions:
        print(f"  Sessions actives : {active_sessions}")
    else:
        print("  ⚠ Aucune session démarrée — attente")

    to_scrape = [e for e in EVENT_MAP if e[4] in active_sessions]
    print(f"  → {len(to_scrape)}/{len(EVENT_MAP)} épreuves à scraper\n")

    if not to_scrape:
        print("  Rien à scraper pour l'instant.")
        return

    # Passe 1
    for num, eid, label, genre, sess, cat, wr in to_scrape:
        print(f"  Épreuve {num:2d} — {label} {genre}... ", end='', flush=True)
        html = fetch_html(num)
        if not html:
            # Connexion échouée → retry
            print("↻ retry queue")
            failed.append((num, eid, label, genre, sess, cat, wr))
        elif 'survol' not in html:
            # HTML reçu mais pas de résultats → épreuve future, ne pas retenter
            print("⏳ pas encore disponible")
        else:
            rows = parse_event(html, eid, label, cat, wr)
            if rows:
                all_results.extend(rows)
                print(f"{len(rows)} résultats")
            else:
                print("⚠ retry queue")
                failed.append((num, eid, label, genre, sess, cat, wr))
        time.sleep(4.0)

    # Passe 2
    if failed:
        print(f"\n  Passe 2 — {len(failed)} épreuves (délai 5s)")
        still_failed = []
        for num, eid, label, genre, sess, cat, wr in failed:
            print(f"  ↺ {num:2d} — {label} {genre}... ", end='', flush=True)
            html = fetch_html(num, retries=5)
            if not html:
                print("⚠")
                still_failed.append((num, eid, label, genre, sess, cat, wr))
            else:
                rows = parse_event(html, eid, label, cat, wr)
                if rows:
                    all_results.extend(rows)
                    print(f"{len(rows)} résultats")
                else:
                    print("⚪ pas encore disponible")
            time.sleep(5.0)

        # Passe 3
        if still_failed:
            print(f"\n  Passe 3 — {len(still_failed)} épreuves (délai 10s)")
            for num, eid, label, genre, sess, cat, wr in still_failed:
                print(f"  ↺↺ {num:2d} — {label} {genre}... ", end='', flush=True)
                html = fetch_html(num, retries=5)
                if html:
                    rows = parse_event(html, eid, label, cat, wr)
                    if rows:
                        all_results.extend(rows)
                        state[eid] = rows
                        save_state(state)
                        print(f"{len(rows)} résultats")
                    else:
                        print("⚪ pas encore disponible")
                else:
                    print("❌ abandon")
                time.sleep(10.0)

    # Résumé
    events_ok = len(set(r[0] for r in all_results))
    print(f"\n  → {events_ok}/{len(EVENT_MAP)} épreuves — {len(all_results)} lignes")

    # Sauvegarder l'état complet avant injection
    save_state(state)

    if all_results:
        changed = inject_html(all_results)
        if changed:
            # Copier vers index.html pour GitHub Pages
            index_file = HTML_FILE.parent / "index.html"
            shutil.copy(HTML_FILE, index_file)
            print(f"  ✓ Copié → index.html")
        if changed and do_push:
            git_push()
    else:
        print("  → Aucun résultat — HTML non modifié")

# ── MAIN ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--loop', type=int, default=0)
    parser.add_argument('--push', action='store_true')
    parser.add_argument('--reset', action='store_true', help='Réinitialiser l\'état (nouveau jour)')
    args = parser.parse_args()

    if args.reset:
        reset_state()
    if args.loop > 0:
        print(f"Mode boucle toutes les {args.loop}s — Ctrl+C pour arrêter")
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
