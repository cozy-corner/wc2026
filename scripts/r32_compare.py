#!/usr/bin/env python3
"""ラウンド32の結果 と 「R32突入時点(グループ3戦終了時)までの疲労」を比較する。

R32前疲労 = グループ3試合の(出場時間×暑熱/標高) + R32会場までの移動 + R32前の休養。
より疲労していた側が負けたか(=疲労が効いたか)を各試合で見る。
"""
from datetime import date

# fatigue.py のヘルパ・データを再利用(main実行部の手前まで)
src = open("scripts/fatigue.py").read().split("rows = []")[0]
ns = {}
exec(src, ns)
B, G, V = ns["B"], ns["G"], ns["V"]
hav, heat_stress, alt_stress = ns["haversine"], ns["heat_stress"], ns["alt_stress"]
group_matches, clinched = ns["group_matches"], ns["clinched_first_after2"]
ROT = ns["ROT_FACTOR"]


def d(s):
    y, m, dd = map(int, s.split("-"))
    return date(y, m, dd)


# R32の全32チーム -> そのR32試合(会場/日付)
r32_of = {}
for m in B["round_of_32"]:
    for t in m["teams"]:
        r32_of[t] = m


def pre_r32(team):
    gm = group_matches(team)                 # 3試合(日付順)
    rested = clinched(team)
    last_g = max(str(x["date"]) for x in gm)
    heat = alt = mins = 0.0
    for x in gm:
        f = ROT if (rested and str(x["date"]) == last_g) else 1.0
        heat += heat_stress(x["venue"], x["kickoff_local"]) * f
        alt += alt_stress(x["venue"], team) * f
        mins += 90 * f
    # 移動: グループ会場列 + R32会場まで
    venues = [x["venue"] for x in gm] + [r32_of[team]["venue"]]
    km = sum(hav(venues[i], venues[i + 1]) for i in range(len(venues) - 1))
    rest = (d(str(r32_of[team]["date"])) - d(last_g)).days
    return dict(team=team, heat=round(heat, 1), alt=round(alt, 2),
                km=round(km), mins=round(mins), rest=rest, rested=rested)


teams = list(r32_of)
pre = {t: pre_r32(t) for t in teams}


def norm(vals):
    lo, hi = min(vals), max(vals)
    return lambda x: (x - lo) / (hi - lo) if hi > lo else 0.0

nkm = norm([p["km"] for p in pre.values()])
nh = norm([p["heat"] for p in pre.values()])
na = norm([p["alt"] for p in pre.values()])
nm = norm([p["mins"] for p in pre.values()])
for p in pre.values():
    rest = max(0.0, min(1.0, (4 - p["rest"]) / 2))
    p["score"] = round(0.25 * nkm(p["km"]) + 0.25 * nh(p["heat"])
                       + 0.20 * na(p["alt"]) + 0.15 * nm(p["mins"])
                       + 0.15 * rest, 3)

print(f'{"R32 match (勝者*)":<34}{"疲労(勝)":>8}{"疲労(負)":>8}  結果   疲労で不利だったのは？')
print("-" * 92)
hit = 0
for m in B["round_of_32"]:
    w = m["winner"]
    l = [t for t in m["teams"] if t != w][0]
    fw, fl = pre[w]["score"], pre[l]["score"]
    who = "勝者が高疲労" if fw > fl else "敗者が高疲労"
    if fl > fw:
        hit += 1
    et = "" if m["decided_by"] == "regulation" else f'({m["decided_by"]})'
    label = f'{w}* vs {l}'
    print(f'{label:<34}{fw:>8}{fl:>8}  {m["score"]:>6}{et:<12} {who}')
print("-" * 92)
print(f'より疲労していた側が敗退: {hit}/16 試合')
