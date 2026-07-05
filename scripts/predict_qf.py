#!/usr/bin/env python3
"""QF(準々決勝)予想 — R16までの疲労を引き継ぐ。R16は延長なし(全90分)前提。

QFの組は bracket.yaml の予想R16勝者で決まる。各QF出場8チームについて
group(3)+R32+R16 の累積疲労 + QF会場までの移動 + QF前休養 を算出し、
R16と同じ 地力(ln市場価値) + 疲労 + ホーム のモデルで勝者を予想する。
"""
import io
import contextlib
import math
from datetime import date
import yaml

# --- fatigue.py のヘルパ/データを再利用 ---
ns = {}
exec(open("scripts/fatigue.py").read().split("rows = []")[0], ns)
B, G, V = ns["B"], ns["G"], ns["V"]
hav, heat, alt = ns["haversine"], ns["heat_stress"], ns["alt_stress"]
gmatches, clinched, ROT = ns["group_matches"], ns["clinched_first_after2"], ns["ROT_FACTOR"]
ACCL = ns["ACCLIMATIZED"]
S = yaml.safe_load(open("strength.yaml"))["strength"]
_b = {}
exec(open("scripts/blend.py").read(), _b)
STRENGTH = _b["build_strength"](S)   # 地力 = ln市場価値 と Elo のブレンド

LAMBDA, T, HOME, HOME_ALT = 0.6, 1.3, 0.45, 0.5
HOME_COUNTRY = {"Mexico": "Mexico", "USA": "USA", "Canada": "Canada"}

# 会場のET差(local = ET + offset時間)
ET_OFF = {"houston": -1, "philadelphia": 0, "new_jersey": 0, "mexico_city": -2,
          "arlington": -1, "seattle": -3, "atlanta": 0, "vancouver": -3, "boston": 0,
          "los_angeles": -3, "miami": 0, "kansas_city": -1, "monterrey": -2,
          "santa_clara": -3, "toronto": 0, "guadalajara": -2}

def et_to_local(et, venue):
    h, m = et.split(":")
    return f"{int(h) + ET_OFF[venue]:02d}:{m}"

def d(s):
    y, mo, dd = map(int, str(s).split("-"))
    return date(y, mo, dd)

P = yaml.safe_load(open("predictions.yaml"))["predictions"]   # 予想は別ファイル
r16_by_team = {P[m["id"]]["winner"]: m for m in B["round_of_16"]}
r32_by_team = {m["winner"]: m for m in B["round_of_32"]}
r16_win = {m["id"]: P[m["id"]]["winner"] for m in B["round_of_16"]}


def accumulate(team, qf_venue, qf_date):
    gm = gmatches(team)
    rested = clinched(team)
    lastg = max(str(x["date"]) for x in gm)
    h = a = mins = 0.0
    for x in gm:
        f = ROT if (rested and str(x["date"]) == lastg) else 1.0
        h += heat(x["venue"], x["kickoff_local"]) * f
        a += alt(x["venue"], team) * f
        mins += 90 * f
    r32 = r32_by_team[team]
    h += heat(r32["venue"], r32["kickoff_local"]) * (r32["minutes"] / 90)
    a += alt(r32["venue"], team) * (r32["minutes"] / 90)
    mins += r32["minutes"]
    r16 = r16_by_team[team]
    ko = et_to_local(r16["kickoff_et"], r16["venue"])
    h += heat(r16["venue"], ko)            # R16は90分(延長なし)
    a += alt(r16["venue"], team)
    mins += 90
    venues = [x["venue"] for x in gm] + [r32["venue"], r16["venue"], qf_venue]
    km = sum(hav(venues[i], venues[i + 1]) for i in range(len(venues) - 1))
    rest = (d(qf_date) - d(str(r16["date"]))).days - 1
    return dict(team=team, heat=round(h, 1), alt=round(a, 2), km=round(km),
                mins=round(mins), rest=rest, r16_venue=r16["venue"])


# QFカードを予想R16勝者で解決
QF = []
for q in B["quarterfinals"]:
    a = r16_win[q["home"]["winner"]]
    b = r16_win[q["away"]["winner"]]
    QF.append(dict(id=q["id"], venue=q["venue"], date=str(q["date"]), a=a, b=b))

teams = [t for q in QF for t in (q["a"], q["b"])]
acc = {}
for q in QF:
    for t in (q["a"], q["b"]):
        acc[t] = accumulate(t, q["venue"], q["date"])


def norm(vals):
    lo, hi = min(vals), max(vals)
    return lambda x: (x - lo) / (hi - lo) if hi > lo else 0.0

nkm = norm([acc[t]["km"] for t in teams])
nh = norm([acc[t]["heat"] for t in teams])
na = norm([acc[t]["alt"] for t in teams])
nm = norm([acc[t]["mins"] for t in teams])
fat = {}
for t in teams:
    r = acc[t]
    rest = max(0.0, min(1.0, (4 - r["rest"]) / 2))
    fat[t] = (0.25 * nkm(r["km"]) + 0.25 * nh(r["heat"]) + 0.20 * na(r["alt"])
              + 0.15 * nm(r["mins"]) + 0.15 * rest)

def home_bonus(team, opp, venue):
    v = V[venue]
    if HOME_COUNTRY.get(team) != v["country"]:
        return 0.0
    b = HOME
    if v["elevation_m"] > 1500 and opp not in ACCL:
        b += HOME_ALT
    return b

def Q(team, opp, venue):
    return STRENGTH[team] - LAMBDA * fat[team] + home_bonus(team, opp, venue)

def logistic(x):
    return 1 / (1 + math.exp(-x))

print(f"パラメータ: λ={LAMBDA}, T={T}, ホーム+{HOME}, 高地+{HOME_ALT}  (R16延長なし=90分)\n")
winners = []
for q in QF:
    a, b, v = q["a"], q["b"], q["venue"]
    qa, qb = Q(a, b, v), Q(b, a, v)
    pa = logistic((qa - qb) / T)
    win, p = (a, pa) if pa >= 0.5 else (b, 1 - pa)
    winners.append(win)
    hb = home_bonus(a, b, v) or home_bonus(b, a, v)
    tag = f'  ［{a if home_bonus(a,b,v) else b} ホーム補正］' if hb else ""
    print(f'{q["id"]} @{V[v]["city"]} ({q["date"]}): {a} vs {b}')
    print(f'   地力 €{S[a]["market_value_eur_m"]:.0f}m / €{S[b]["market_value_eur_m"]:.0f}m'
          f'   疲労(累積) {fat[a]:.2f} / {fat[b]:.2f}')
    print(f'   詳細 heat {acc[a]["heat"]}/{acc[b]["heat"]}  alt {acc[a]["alt"]}/{acc[b]["alt"]}'
          f'  km {acc[a]["km"]}/{acc[b]["km"]}  rest {acc[a]["rest"]}/{acc[b]["rest"]}d')
    print(f'   → 予想: {win}  {p*100:.0f}%{tag}\n')

print("=== 予想される準決勝進出4チーム ===")
print("  " + ", ".join(winners))
