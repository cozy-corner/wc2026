#!/usr/bin/env python3
"""全48チームの市場価値 と 到達段階(グループ敗退/R32敗退/R16進出)の相関を見る。

stage: 0=グループ敗退, 1=R32敗退, 2=R16進出。
Spearman順位相関で「地力(市場価値)がどれだけ結果を説明したか」を評価する。
"""
import yaml

B = yaml.safe_load(open("bracket.yaml"))
G = yaml.safe_load(open("group_stage.yaml"))
S = yaml.safe_load(open("strength.yaml"))["strength"]

r16 = {t for m in B["round_of_16"] for t in (m["home"], m["away"])}
r32 = {t for m in B["round_of_32"] for t in m["teams"]}
all_teams = [s["team"] for g in G["group_stage"].values() for s in g["standings"]]

def stage(t):
    return 2 if t in r16 else (1 if t in r32 else 0)

data = [(t, S[t]["market_value_eur_m"], stage(t)) for t in all_teams]


def ranks(vals):
    """平均順位(タイ補正)。大きいほど高順位=大きい順位値。"""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    vx = sum((a - mx) ** 2 for a in x) ** 0.5
    vy = sum((b - my) ** 2 for b in y) ** 0.5
    return cov / (vx * vy)


vals = [d[1] for d in data]
stages = [d[2] for d in data]
rho = pearson(ranks(vals), ranks(stages))
print(f"Spearman順位相関 (市場価値 × 到達段階): rho = {rho:.3f}  (n=48)")

# Elo(2026-07-01=グループ終了時)の相関も見て、ブレンド重みを決める
elos = [S[t]["elo"] for t in all_teams]
rho_elo = pearson(ranks(elos), ranks(stages))
print(f"Spearman順位相関 (Elo    × 到達段階): rho = {rho_elo:.3f}  (n=48)")
w_mv, w_elo = rho / (rho + rho_elo), rho_elo / (rho + rho_elo)
print(f"相関ベースの推奨ブレンド重み → 市場価値 {w_mv:.2f} / Elo {w_elo:.2f}\n")

# 段階別の平均・中央値市場価値
for st, name in [(2, "R16進出"), (1, "R32敗退"), (0, "グループ敗退")]:
    vs = sorted(d[1] for d in data if d[2] == st)
    med = vs[len(vs) // 2]
    print(f"  {name:<8} n={len(vs):2}  平均€{sum(vs)/len(vs):6.1f}m  中央€{med:6.1f}m  "
          f"範囲€{vs[0]:.0f}–{vs[-1]:.0f}m")

# 市場価値トップ16のうち何チームがR16へ？
by_val = sorted(data, key=lambda d: -d[1])
top16 = by_val[:16]
print(f"\n市場価値トップ16のうちR16進出: {sum(1 for _,_,s in top16 if s==2)}/16")
print(f"市場価値ボトム16のうちR16進出: {sum(1 for _,_,s in by_val[-16:] if s==2)}/16")

# 番狂わせ: 価値順位 vs 段階の乖離
val_rank = {d[0]: i + 1 for i, d in enumerate(by_val)}  # 1=最高価値
print("\n■ 過大達成(格安なのに勝ち上がり) — 価値ランク低いのにR16")
over = sorted((d for d in data if d[2] == 2), key=lambda d: -val_rank[d[0]])
for t, v, s in over[:5]:
    print(f"  {t:<14} €{v:6.1f}m  価値{val_rank[t]:>2}位 → R16")
print("■ 過小達成(高額なのに早期敗退) — 価値ランク高いのに非R16")
under = sorted((d for d in data if d[2] < 2), key=lambda d: val_rank[d[0]])
for t, v, s in under[:6]:
    lbl = "R32敗退" if s == 1 else "グループ敗退"
    print(f"  {t:<14} €{v:6.1f}m  価値{val_rank[t]:>2}位 → {lbl}")
