#!/usr/bin/env python3
"""R16勝者予想 — 地力(市場価値) と 疲労 の2軸。

地力: s = ln(市場価値). 価値は乗算的に効くので対数を取る。
疲労: fatigue.py の累積疲労スコア(0-1, 高い=疲労大)を減点として使う。
  R32分析で地力は結果をよく説明(rho 0.66)・疲労は弱い(9/16)ため、疲労は従属の重み。

実効クオリティ Q = ln(value) - LAMBDA * fatigue
勝率 P(i>j) = logistic( (Qi - Qj) / T )
"""
import io
import contextlib
import math
import yaml

LAMBDA = 0.6   # 疲労の重み(ln-value単位換算)。地力より小さく設定=疲労は従
T = 1.3        # ロジスティックの温度(小さいほど大差=決定的)
HOME = 0.45      # 自国会場ボーナス(Q=ln-value単位)
HOME_ALT = 0.5   # ホーム×高地(>1500m)で非順応の相手を苦しめる追加分

B = yaml.safe_load(open("bracket.yaml"))
S = yaml.safe_load(open("strength.yaml"))["strength"]
V = B["venues"]

# 開催国の代表 -> 国名(会場のcountryと突合してホーム判定)
HOME_COUNTRY = {"Mexico": "Mexico", "USA": "USA", "Canada": "Canada"}
ACCLIMATIZED = {"Mexico", "Colombia"}  # 高地順応(相手なら高地ボーナス無効)

def home_bonus(team, opp, venue):
    v = V[venue]
    if HOME_COUNTRY.get(team) != v["country"]:
        return 0.0
    b = HOME
    if v["elevation_m"] > 1500 and opp not in ACCLIMATIZED:
        b += HOME_ALT
    return b

# fatigue.py を実行して累積疲労スコアを取得(標準出力は抑制)
ns = {}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open("scripts/fatigue.py").read(), ns)
FAT = {r["team"]: r["score"] for r in ns["rows"]}

HOSTS = {"Mexico", "USA", "Canada"}  # 開催国(モデル外の補正候補として注記)

def Q(team):
    return math.log(S[team]["market_value_eur_m"]) - LAMBDA * FAT[team]

def logistic(x):
    return 1 / (1 + math.exp(-x))

print(f"パラメータ: 疲労重みλ={LAMBDA}, 温度T={T}, ホーム+{HOME}, 高地追加+{HOME_ALT}\n")
winners = []
for m in B["round_of_16"]:
    a, b = m["home"], m["away"]
    ha, hb = home_bonus(a, b, m["venue"]), home_bonus(b, a, m["venue"])
    qa, qb = Q(a) + ha, Q(b) + hb
    pa = logistic((qa - qb) / T)
    win, p = (a, pa) if pa >= 0.5 else (b, 1 - pa)
    winners.append(win)
    tag = ""
    if ha or hb:
        who = a if ha else b
        alt = "＋高地" if (ha and ha > HOME) or (hb and hb > HOME) else ""
        tag = f'  ［{who} ホーム{alt}補正］'
    print(f'{m["id"]}: {a} vs {b}  @{V[m["venue"]]["city"]}')
    print(f'   地力 €{S[a]["market_value_eur_m"]:.0f}m / €{S[b]["market_value_eur_m"]:.0f}m'
          f'   疲労 {FAT[a]:.2f} / {FAT[b]:.2f}  (高=疲労大)')
    print(f'   → 予想: {win}  {p*100:.0f}%{tag}\n')

print("=== 予想されるQF進出8チーム ===")
print("  " + ", ".join(winners))
