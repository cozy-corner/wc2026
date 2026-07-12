#!/usr/bin/env python3
"""SF(準決勝)予想 — QFまでの疲労を引き継ぐ。R16/QFは実出場分(bracketのminutes, 延長込み)を使う。

SFの組は予想QF勝者で決まる。各SF出場4チームの
group(3)+R32+R16+QF の累積疲労 + SF会場までの移動 + SF前休養 を算出し、
地力(ln市場価値)+疲労+ホーム のモデルで勝者を予想する。
"""
import math
from datetime import date
import yaml

ns = {}
exec(open("scripts/fatigue.py").read().split("rows = []")[0], ns)
B, V = ns["B"], ns["V"]
hav, heat, alt = ns["haversine"], ns["heat_stress"], ns["alt_stress"]
gmatches, clinched, ROT = ns["group_matches"], ns["clinched_first_after2"], ns["ROT_FACTOR"]
ACCL = ns["ACCLIMATIZED"]
S = yaml.safe_load(open("strength.yaml"))["strength"]
_b = {}
exec(open("scripts/blend.py").read(), _b)
STRENGTH = _b["build_strength"](S)   # 地力 = ln市場価値 と Elo のブレンド

LAMBDA, T, HOME, HOME_ALT = 0.6, 1.3, 0.45, 0.5
HOME_COUNTRY = {"Mexico": "Mexico", "USA": "USA", "Canada": "Canada"}
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

# QFカードを予想R16勝者で解決し、予想QF勝者ごとにQF情報を持つ
qf_by_team = {}
for q in B["quarterfinals"]:
    a, b = r16_win[q["home"]["winner"]], r16_win[q["away"]["winner"]]
    q2 = dict(q); q2["a"], q2["b"] = a, b
    qf_by_team[P[q["id"]]["winner"]] = q2

def accumulate(team, sf_venue, sf_date):
    gm = gmatches(team); rested = clinched(team)
    lastg = max(str(x["date"]) for x in gm)
    h = a = mins = 0.0
    for x in gm:
        f = ROT if (rested and str(x["date"]) == lastg) else 1.0
        h += heat(x["venue"], x["kickoff_local"]) * f
        a += alt(x["venue"], team) * f
        mins += 90 * f
    stages = []
    r32 = r32_by_team[team]
    stages.append((r32["venue"], r32["minutes"], r32["kickoff_local"]))
    r16 = r16_by_team[team]
    stages.append((r16["venue"], r16.get("minutes", 90), et_to_local(r16["kickoff_et"], r16["venue"])))
    qf = qf_by_team[team]
    stages.append((qf["venue"], qf.get("minutes", 90), et_to_local(qf["kickoff_et"], qf["venue"])))
    for v, mn, ko in stages:
        h += heat(v, ko) * (mn / 90)
        a += alt(v, team) * (mn / 90)
        mins += mn
    venues = [x["venue"] for x in gm] + [s[0] for s in stages] + [sf_venue]
    km = sum(hav(venues[i], venues[i + 1]) for i in range(len(venues) - 1))
    rest = (d(sf_date) - d(str(qf["date"]))).days - 1
    return dict(team=team, heat=round(h, 1), alt=round(a, 2), km=round(km),
                mins=round(mins), rest=rest)

# SFカードを予想QF勝者で解決
SF = []
qf_win = {q["id"]: P[q["id"]]["winner"] for q in B["quarterfinals"]}
for s in B["semifinals"]:
    SF.append(dict(id=s["id"], venue=s["venue"], date=str(s["date"]),
                   a=qf_win[s["home"]["winner"]], b=qf_win[s["away"]["winner"]]))

teams = [t for s in SF for t in (s["a"], s["b"])]
acc = {t: accumulate(t, s["venue"], s["date"]) for s in SF for t in (s["a"], s["b"])}

def norm(vals):
    lo, hi = min(vals), max(vals)
    return lambda x: (x - lo) / (hi - lo) if hi > lo else 0.0

nkm = norm([acc[t]["km"] for t in teams]); nh = norm([acc[t]["heat"] for t in teams])
na = norm([acc[t]["alt"] for t in teams]); nm = norm([acc[t]["mins"] for t in teams])
fat = {}
for t in teams:
    r = acc[t]; rest = max(0.0, min(1.0, (4 - r["rest"]) / 2))
    fat[t] = (0.25 * nkm(r["km"]) + 0.25 * nh(r["heat"]) + 0.20 * na(r["alt"])
              + 0.15 * nm(r["mins"]) + 0.15 * rest)

def home_bonus(team, opp, venue):
    v = V[venue]
    if HOME_COUNTRY.get(team) != v["country"]:
        return 0.0
    return HOME + (HOME_ALT if v["elevation_m"] > 1500 and opp not in ACCL else 0.0)

def Q(t, o, v):
    return STRENGTH[t] - LAMBDA * fat[t] + home_bonus(t, o, v)

def logistic(x):
    return 1 / (1 + math.exp(-x))

print(f"パラメータ: λ={LAMBDA}, T={T}  (R16/QFは実出場分=延長込み, SF会場は空調)\n")
winners = []
for s in SF:
    a, b, v = s["a"], s["b"], s["venue"]
    pa = logistic((Q(a, b, v) - Q(b, a, v)) / T)
    win, p = (a, pa) if pa >= 0.5 else (b, 1 - pa)
    winners.append((s["id"], win, p))
    print(f'{s["id"]} @{V[v]["city"]} ({s["date"]}): {a} vs {b}')
    print(f'   地力 €{S[a]["market_value_eur_m"]:.0f}m / €{S[b]["market_value_eur_m"]:.0f}m'
          f'   疲労(累積) {fat[a]:.2f} / {fat[b]:.2f}')
    print(f'   詳細 heat {acc[a]["heat"]}/{acc[b]["heat"]}  alt {acc[a]["alt"]}/{acc[b]["alt"]}'
          f'  km {acc[a]["km"]}/{acc[b]["km"]}  rest {acc[a]["rest"]}/{acc[b]["rest"]}d')
    print(f'   → 予想: {win}  {p*100:.0f}%\n')

print("=== 予想される決勝進出2チーム ===")
print("  " + " / ".join(f"{w} ({p*100:.0f}%)" for _, w, p in winners))
