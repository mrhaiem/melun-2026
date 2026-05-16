#!/usr/bin/env python3
"""
discover_events.py — Extrait les IDs depuis les onclick JavaScript du programme liveffn
"""
import subprocess, re

COMPETITION = 92947

def curl(url):
    r = subprocess.run(
        ['curl.exe', '-s', '-L', '--max-time', '20',
         '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0', url],
        capture_output=True, timeout=25
    )
    return r.stdout.decode('utf-8', errors='replace')

url = f"https://www.liveffn.com/cgi-bin/programme.php?competition={COMPETITION}&langue=fra"
html = curl(url)
print(f"HTML: {len(html)} chars\n")

# Pattern : &epr_id='+' N '+'&typ_id ... suivi du nom de l'épreuve
# Exemple : '&epr_id='+'5'+'&typ_id='+60 ... 800 Nage Libre Dames Séries
pattern = r"epr_id='\+'(\d+)'\+.*?>\s*([\w\s]+(?:Nage Libre|Dos|Brasse|Papillon|4 Nages|Nages|Relais)[^\n<]*)"
matches = re.findall(pattern, html, re.DOTALL)

found = {}
for num, label in matches:
    label_clean = re.sub(r'\s+', ' ', label).strip()
    label_clean = label_clean.split('Séries')[0].split('Finales')[0].strip()
    if num not in found:
        found[num] = label_clean

# Aussi chercher pattern alternatif
pattern2 = r"epr_id='\+'(\d+)'"
all_ids = re.findall(pattern2, html)

# Associer IDs aux noms en cherchant le contexte
for id_str in set(all_ids):
    if id_str not in found:
        idx = html.find(f"epr_id='+'{ id_str }'+")
        if idx > 0:
            chunk = html[idx:idx+500]
            # Chercher le texte après le onclick
            m = re.search(r'>([\w\s]+(?:Nage Libre|Dos|Brasse|Papillon|Nages|Relais)[^<\n]{0,40})', chunk)
            if m:
                label = re.sub(r'\s+', ' ', m.group(1)).strip()
                found[id_str] = label

print(f"{len(found)} épreuves trouvées :\n")
for num, label in sorted(found.items(), key=lambda x: int(x[0])):
    print(f"  epreuve={num:>3} : {label[:60]}")

# Résumé mapping
print("\n=== MAPPING EVENT_MAP SUGGÉRÉ ===")
MAP = {
    '800 Nage Libre Dames':    ('s1_800NL_F',    1, 'demi-fond', 484.79),
    '800 Nage Libre Messieurs':('s1_800NL_H',    1, 'demi-fond', 452.12),
    '200 Dos Dames':           ('s1_200DOS_F',   1, 'sprint',    123.35),
    '200 Dos Messieurs':       ('s1_200DOS_H',   1, 'sprint',    111.92),
    '100 Brasse Dames':        ('s1_100BR_F',    1, 'sprint',     64.13),
    '100 Brasse Messieurs':    ('s1_100BR_H',    1, 'sprint',     56.88),
    '200 4 Nages Dames':       ('s2_200_4N_F',   2, '4nages',    126.12),
    '200 4 Nages Messieurs':   ('s2_200_4N_H',   2, '4nages',    114.00),
    '100 Dos Dames':           ('s2_100DOS_F',   2, 'sprint',     57.45),
    '100 Dos Messieurs':       ('s2_100DOS_H',   2, 'sprint',     51.60),
    '100 Papillon Dames':      ('s2_100PA_F',    2, 'sprint',     55.48),
    '100 Papillon Messieurs':  ('s2_100PA_H',    2, 'sprint',     49.45),
    '200 Nage Libre Dames':    ('s2_200NL_F',    2, 'sprint',    112.98),
    '200 Nage Libre Messieurs':('s2_200NL_H',    2, 'sprint',    102.00),
    '200 Brasse Dames':        ('s2_200BR_F',    2, 'sprint',    138.95),
    '200 Brasse Messieurs':    ('s2_200BR_H',    2, 'sprint',    125.95),
    '4x100 Nage Libre Dames':  ('s2_4x100NL_F',  2, 'relais',      None),
    '4x100 Nage Libre Messieurs':('s2_4x100NL_H',2, 'relais',      None),
    '1500 Nage Libre Dames':   ('s3_1500NL_F',   3, 'demi-fond', 920.48),
    '1500 Nage Libre Messieurs':('s3_1500NL_H',  3, 'demi-fond', 871.02),
    '200 Papillon Dames':      ('s3_200PA_F',    3, 'sprint',    121.81),
    '200 Papillon Messieurs':  ('s3_200PA_H',    3, 'sprint',    110.73),
    '50 Dos Dames':            ('s3_50DOS_F',    3, 'sprint',     27.06),
    '50 Dos Messieurs':        ('s3_50DOS_H',    3, 'sprint',     24.00),
    '50 Nage Libre Dames':     ('s3_50NL_F',     3, 'sprint',     23.67),
    '50 Nage Libre Messieurs': ('s3_50NL_H',     3, 'sprint',     20.91),
    '50 Brasse Dames':         ('s4_50BR_F',     4, 'sprint',     29.40),
    '50 Brasse Messieurs':     ('s4_50BR_H',     4, 'sprint',     25.95),
    '400 Nage Libre Dames':    ('s4_400NL_F',    4, 'demi-fond', 236.40),
    '400 Nage Libre Messieurs':('s4_400NL_H',    4, 'demi-fond', 220.07),
    '50 Papillon Dames':       ('s4_50PA_F',     4, 'sprint',     24.43),
    '50 Papillon Messieurs':   ('s4_50PA_H',     4, 'sprint',     22.27),
    '400 4 Nages Dames':       ('s4_400_4N_F',   4, '4nages',    266.36),
    '400 4 Nages Messieurs':   ('s4_400_4N_H',   4, '4nages',    243.84),
    '100 Nage Libre Dames':    ('s4_100NL_F',    4, 'sprint',     51.71),
    '100 Nage Libre Messieurs':('s4_100NL_H',    4, 'sprint',     46.91),
    '4x100 4 Nages Dames':     ('s4_4x100_4N_F', 4, 'relais',      None),
    '4x100 4 Nages Messieurs': ('s4_4x100_4N_H', 4, 'relais',      None),
}

event_map_lines = []
for num, label in sorted(found.items(), key=lambda x: int(x[0])):
    for key, val in MAP.items():
        if key.lower() in label.lower() or label.lower() in key.lower():
            eid, sess, cat, wr = val
            genre = 'F' if 'Dames' in label else 'H'
            wr_s = str(wr) if wr else 'None'
            line = f"    ({int(num):>3}, '{eid}', '{key}', '{genre}', {sess}, '{cat}', {wr_s}),"
            print(line)
            event_map_lines.append((int(num), line))
            break
