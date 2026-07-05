#!/usr/bin/env python3
"""得点期待値(Poisson)レンズ — R16の各試合をスコア分布で予想する。

本モデル(地力+疲労+ホーム)とは独立の視点。グループ+R32の得失点だけを使い
(=R16は不使用, ネタバレ/リークなし)、相手の強さで補正した攻撃/守備レートを
反復фитで求め、Poissonでスコア分布・勝分負・想定スコアを出す。

注意: 1チーム4試合の極小サンプル。分散が大きい"参考レンズ"。ホームは非考慮(中立)。
"""
import math
import yaml

G = yaml.safe_load(open("group_stage.yaml"))
B = yaml.safe_load(open("bracket.yaml"))


def goals(score):
    a, b = score.split(" ")[0].split("-")   # "1-1 (pens 4-3)" -> "1-1"
    return int(a), int(b)


# (teamA, gA, teamB, gB) を全部集める(group 72 + R32 16)
matches = []
for grp in G["group_stage"].values():
    for m in grp["matches"]:
        ga, gb = goals(m["score"])
        matches.append((m["teams"][0], ga, m["teams"][1], gb))
for m in B["round_of_32"]:
    ga, gb = goals(m["score"])
    matches.append((m["teams"][0], ga, m["teams"][1], gb))

teams = sorted({t for a, _, b, _ in matches for t in (a, b)})
GF = {t: 0 for t in teams}
GA = {t: 0 for t in teams}
opp = {t: [] for t in teams}
for a, ga, b, gb in matches:
    GF[a] += ga; GA[a] += gb; opp[a].append(b)
    GF[b] += gb; GA[b] += ga; opp[b].append(a)

mu = sum(GF.values()) / sum(len(opp[t]) for t in teams)   # 1試合平均得点

# 反復фит: attack a_i, defense b_i (>1=攻撃/失点が平均超)
# 収縮(shrinkage): 4試合の極小サンプル対策。平均的な相手とのK試合ぶんを擬似的に
# 足し、全レートを平均1.0へ引き戻す(失点0で守備=0になる暴走を防ぐ)。
K = 3.0
att = {t: 1.0 for t in teams}
dfn = {t: 1.0 for t in teams}
for _ in range(50):
    for t in teams:
        den = mu * (sum(dfn[o] for o in opp[t]) + K)
        att[t] = (GF[t] + K * mu) / den
    for t in teams:
        den = mu * (sum(att[o] for o in opp[t]) + K)
        dfn[t] = (GA[t] + K * mu) / den
    ma = sum(att.values()) / len(teams)
    md = sum(dfn.values()) / len(teams)
    for t in teams:
        att[t] /= ma; dfn[t] /= md


def pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def scoreline(a, b, mx=8):
    la = mu * att[a] * dfn[b]
    lb = mu * att[b] * dfn[a]
    pa = [pois(k, la) for k in range(mx + 1)]
    pb = [pois(k, lb) for k in range(mx + 1)]
    win = draw = 0.0
    best, bp = (0, 0), 0.0
    for i in range(mx + 1):
        for j in range(mx + 1):
            p = pa[i] * pb[j]
            if i > j: win += p
            elif i == j: draw += p
            if p > bp: bp, best = p, (i, j)
    return la, lb, win, draw, 1 - win - draw, best


r16_att = sorted(((t, att[t], dfn[t]) for m in B["round_of_16"]
                  for t in (m["home"], m["away"])), key=lambda x: -x[1])
# 攻撃/守備レート(相手補正済み)。予想は下の対戦別 期待得点(相手考慮)で行う。
print("■ R16各チームの攻撃/守備レート (1.0=平均, 攻撃は高い程強/守備は低い程堅い)")
for t, a, d in r16_att:
    print(f"  {t:<12} 攻撃 {a:.2f}  守備 {d:.2f}")

print("\n■ R16スコア予想(Poisson, 中立=ホーム非考慮)")
for m in B["round_of_16"]:
    a, b = m["home"], m["away"]
    la, lb, pa, pd, pb, best = scoreline(a, b)
    print(f"\n{m['id']}: {a} vs {b}")
    print(f"   期待得点 {la:.2f} - {lb:.2f}   想定スコア {best[0]}-{best[1]}")
    print(f"   勝 {pa*100:.0f}% / 分 {pd*100:.0f}% / 負 {pb*100:.0f}%"
          f"   → {'両者拮抗' if abs(pa-pb) < 0.1 else (a if pa > pb else b) + ' 優勢'}")
