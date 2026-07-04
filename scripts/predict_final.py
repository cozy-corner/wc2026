#!/usr/bin/env python3
"""決勝予想 — SFまでの疲労を引き継ぐ。R16/QF/SFは延長なし(90分)前提。

決勝カードは予想SF勝者で決まる。2チームだけなので min-max 正規化は使わず、
大会全体の高値を基準にした固定分母でスケール(効果は従来round同等になるよう設定)。
"""
import math
from datetime import date
import yaml

ns = {}
exec(open("scripts/fatigue.py").read().split("rows = []")[0], ns)
B, V = ns["B"], ns["V"]
hav, heat, alt = ns["haversine"], ns["heat_stress"], ns["alt_stress"]
gmatches, clinched, ROT = ns["group_matches"], ns["clinched_first_after2"], ns["ROT_FACTOR"]
S = yaml.safe_load(open("strength.yaml"))["strength"]

LAMBDA, T = 0.6, 1.3
ET_OFF = {"houston": -1, "philadelphia": 0, "new_jersey": 0, "mexico_city": -2,
          "arlington": -1, "seattle": -3, "atlanta": 0, "vancouver": -3, "boston": 0,
          "los_angeles": -3, "miami": 0, "kansas_city": -1, "monterrey": -2,
          "santa_clara": -3, "toronto": 0, "guadalajara": -2}
# 固定基準(大会高値の目安)。fatigue_index=各成分/基準の加重和
KM_REF, HEAT_REF, ALT_REF, MIN_REF = 11000, 35, 1.3, 660

def et_to_local(et, v):
    h, m = et.split(":")
    return f"{int(h) + ET_OFF[v]:02d}:{m}"

def d(s):
    y, mo, dd = map(int, str(s).split("-"))
    return date(y, mo, dd)

P = yaml.safe_load(open("predictions.yaml"))["predictions"]   # 予想は別ファイル
r16_by_team = {P[m["id"]]["winner"]: m for m in B["round_of_16"]}
r32_by_team = {m["winner"]: m for m in B["round_of_32"]}
qf_by_team = {P[q["id"]]["winner"]: dict(q) for q in B["quarterfinals"]}
sf_by_team = {P[s["id"]]["winner"]: dict(s) for s in B["semifinals"]}

F = B["final"]
FIN_V, FIN_D = F["venue"], str(F["date"])

def accumulate(team):
    gm = gmatches(team); rested = clinched(team)
    lastg = max(str(x["date"]) for x in gm)
    h = a = mins = 0.0
    for x in gm:
        f = ROT if (rested and str(x["date"]) == lastg) else 1.0
        h += heat(x["venue"], x["kickoff_local"]) * f
        a += alt(x["venue"], team) * f
        mins += 90 * f
    r32 = r32_by_team[team]
    stages = [(r32["venue"], r32["minutes"], r32["kickoff_local"])]
    for st in (r16_by_team[team], qf_by_team[team], sf_by_team[team]):
        stages.append((st["venue"], 90, et_to_local(st["kickoff_et"], st["venue"])))
    for v, mn, ko in stages:
        h += heat(v, ko) * (mn / 90)
        a += alt(v, team) * (mn / 90)
        mins += mn
    venues = [x["venue"] for x in gm] + [s[0] for s in stages] + [FIN_V]
    km = sum(hav(venues[i], venues[i + 1]) for i in range(len(venues) - 1))
    rest = (d(FIN_D) - d(str(sf_by_team[team]["date"]))).days - 1
    idx = (0.25 * min(1, km / KM_REF) + 0.25 * min(1, h / HEAT_REF)
           + 0.20 * min(1, a / ALT_REF) + 0.15 * min(1, mins / MIN_REF)
           + 0.15 * max(0, min(1, (4 - rest) / 2)))
    return dict(team=team, heat=round(h, 1), alt=round(a, 2), km=round(km),
                mins=round(mins), rest=rest, fatigue=round(idx, 3))

A = P["SF-1"]["winner"]   # SF-1勝者
Bt = P["SF-2"]["winner"]  # SF-2勝者
accA, accB = accumulate(A), accumulate(Bt)

def Q(acc):
    return math.log(S[acc["team"]]["market_value_eur_m"]) - LAMBDA * acc["fatigue"]

pa = 1 / (1 + math.exp(-(Q(accA) - Q(accB)) / T))
win, p = (A, pa) if pa >= 0.5 else (Bt, 1 - pa)

print(f"決勝 @{V[FIN_V]['city']} ({FIN_D}, {V[FIN_V]['july_avg_high_c']}°C 屋外)\n")
for acc in (accA, accB):
    print(f'  {acc["team"]:<8} 地力€{S[acc["team"]]["market_value_eur_m"]:.0f}m  '
          f'疲労{acc["fatigue"]}  [heat {acc["heat"]}, alt {acc["alt"]}, '
          f'km {acc["km"]}, mins {acc["mins"]}, rest {acc["rest"]}d]')
print(f'\n★ 優勝予想: {win}  {p*100:.0f}%   (相手 {100-p*100:.0f}%)')
