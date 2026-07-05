"""地力(strength)を 市場価値 と Elo のブレンドで返す。

既存モデルは Q を ln(市場価値) 単位で校正済み(λ, ホーム, 停止)。
そこでEloを ln(市場価値) と同じ平均・分散に写して合成し、単位を保つ。
  z_elo = (elo - mean_elo)/sd_elo
  elo_as_lv = mean_lv + z_elo * sd_lv
  strength = w_mv * ln(mv) + w_elo * elo_as_lv
統計量は全48チーム固定 → ラウンドに依らず各チームの地力は一定。
重みは strength_corr.py の相関ベース(市場価値0.48 / Elo0.52)。
"""
import math
import statistics


def build_strength(S, w_mv=0.48, w_elo=0.52):
    teams = list(S)
    lv = {t: math.log(S[t]["market_value_eur_m"]) for t in teams}
    elo = {t: S[t]["elo"] for t in teams}
    mlv, slv = statistics.mean(lv.values()), statistics.pstdev(lv.values())
    melo, selo = statistics.mean(elo.values()), statistics.pstdev(elo.values())
    out = {}
    for t in teams:
        elo_as_lv = mlv + (elo[t] - melo) / selo * slv
        out[t] = w_mv * lv[t] + w_elo * elo_as_lv
    return out
