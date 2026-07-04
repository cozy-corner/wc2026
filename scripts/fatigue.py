#!/usr/bin/env python3
"""R16各チームの累積疲労を算出する。

疲労は「初戦からの全試合」で積み上がるという前提で、各試合ごとに
  出場時間(分) × その試合の暑熱ストレス(キックオフ時刻で気温補正)
を積算する。さらに全行程の移動距離、R32→R16の休養も加味する。
合成スコアは相対比較の目安。
"""
import math
import yaml

B = yaml.safe_load(open("bracket.yaml"))
G = yaml.safe_load(open("group_stage.yaml"))
V = B["venues"]


def haversine(a, b):
    (la1, lo1), (la2, lo2) = V[a]["coords"], V[b]["coords"]
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


# 日周変化: 日中平均最高気温からの差(°C)。ピークは15-16時、夜に向け低下。
_ANCHORS = {6: -6, 10: -5, 11: -3, 12: -2, 13: -1, 14: -0.5, 15: 0, 16: 0,
            17: -1.5, 18: -3, 19: -4.5, 20: -6, 21: -7, 22: -8, 23: -9}
def diurnal_offset(hour):
    keys = sorted(_ANCHORS)
    if hour <= keys[0]:
        return _ANCHORS[keys[0]]
    if hour >= keys[-1]:
        return _ANCHORS[keys[-1]]
    for i in range(len(keys) - 1):
        lo, hi = keys[i], keys[i + 1]
        if lo <= hour <= hi:
            t = (hour - lo) / (hi - lo)
            return _ANCHORS[lo] + t * (_ANCHORS[hi] - _ANCHORS[lo])


def kickoff_hour(s):
    h, m = s.split(":")
    return int(h) + int(m) / 60.0


def heat_stress(venue_key, kickoff):
    """試合1つあたりの暑熱ストレス強度。空調ありは屋内快適で0扱い。
    体感 = (気温-快適20°C)超過分 × 湿度係数。"""
    v = V[venue_key]
    if v["air_conditioned"]:
        return 0.0
    temp = v["july_avg_high_c"] + diurnal_offset(kickoff_hour(kickoff))
    return max(0.0, temp - 20.0) * (v["july_humidity_pct"] / 100.0)


# 高地順応国: 本拠地が高地でパフォーマンス低下が小さい
ACCLIMATIZED = {"Mexico", "Colombia"}  # メキシコ(本拠地)/コロンビア(アンデス)

def alt_stress(venue_key, team):
    """標高疲労強度。~1000m超で酸素負荷。順応国は割引。"""
    elev = V[venue_key]["elevation_m"]
    base = max(0.0, elev - 1000) / 1000.0   # 1560m=0.56, 2240m=1.24
    if team in ACCLIMATIZED:
        base *= 0.3
    return base


# MD2(2戦目)終了時点で首位が確定 → 第3戦は主力を休ませられる。
# 2連勝でも同組の他チームに勝点で追い越される可能性が残るなら休めない
# (例: France/Norwayは同組2連勝だが直接対決が残り首位未定 → 休めない)。
ROT_FACTOR = 0.4  # 第3戦の主力負荷(出場時間・暑熱)の残存割合(ローテ想定)

POINTS = {"W": 3, "D": 1, "L": 0}
TEAM_GROUP = {s["team"]: gl for gl, grp in G["group_stage"].items()
              for s in grp["standings"]}

def _result(team, m):
    gf, ga = (int(x) for x in m["score"].split(" ")[0].split("-"))
    mine, opp = (gf, ga) if team == m["teams"][0] else (ga, gf)
    return "W" if mine > opp else ("D" if mine == opp else "L")

def group_matches(team):
    ms = [m for grp in G["group_stage"].values() for m in grp["matches"]
          if team in m["teams"]]
    ms.sort(key=lambda m: str(m["date"]))
    return ms

def pts_after2(team):
    return sum(POINTS[_result(team, m)] for m in group_matches(team)[:2])

def clinched_first_after2(team):
    """MD2終了時点で誰も勝点で追い越せない(タイは上位GDで確保)= 首位確定。"""
    mates = [s["team"] for s in G["group_stage"][TEAM_GROUP[team]]["standings"]]
    p = {x: pts_after2(x) for x in mates}
    return all(p[x] + 3 <= p[team] for x in mates if x != team)

# 全試合(group+R32+R16)を集める: team -> [(stage, date, venue, minutes, kickoff)]
def matches_for(team):
    out = []
    for m in group_matches(team):
        out.append(("group", str(m["date"]), m["venue"], 90, m["kickoff_local"]))
    for m in B["round_of_32"]:
        if team in m["teams"]:
            out.append(("R32", str(m["date"]), m["venue"], m["minutes"], m["kickoff_local"]))
    for m in B["round_of_16"]:
        if team in (m["home"], m["away"]):
            out.append(("R16", str(m["date"]), m["venue"], None, None))  # 未消化
    out.sort(key=lambda x: x[1])
    return out


r16_teams = [t for m in B["round_of_16"] for t in (m["home"], m["away"])]
r32_min = {m["winner"]: m["minutes"] for m in B["round_of_32"]}
r32_rest = {m["winner"]: m["days_to_R16"] - 1 for m in B["round_of_32"]}

rows = []
for t in r16_teams:
    seq = matches_for(t)
    rested = clinched_first_after2(t)
    last_group_date = max((d for st, d, *_ in seq if st == "group"), default=None)
    venues = [v for _, _, v, _, _ in seq]
    km = sum(haversine(venues[i], venues[i + 1]) for i in range(len(venues) - 1))
    cum_heat = 0.0
    cum_alt = 0.0
    tot_min = 0.0
    hottest = 0.0
    for st, d, v, mins, ko in seq:
        if mins is None:
            continue  # R16は未消化
        # 2連勝で早期突破 → 第3戦(最終グループ戦)は主力ローテで負荷減
        f = ROT_FACTOR if (rested and st == "group" and d == last_group_date) else 1.0
        tot_min += mins * f
        cum_heat += heat_stress(v, ko) * (mins / 90.0) * f
        cum_alt += alt_stress(v, t) * (mins / 90.0) * f
        hottest = max(hottest, heat_stress(v, ko) * f)
    rows.append({
        "team": t, "km": round(km), "cum_heat": round(cum_heat, 1),
        "cum_alt": round(cum_alt, 2), "tot_min": round(tot_min),
        "hottest": round(hottest, 1), "r32_min": r32_min[t],
        "rest": r32_rest[t], "rested_g3": rested,
    })


def norm(vals):
    lo, hi = min(vals), max(vals)
    return lambda x: (x - lo) / (hi - lo) if hi > lo else 0.0


nkm = norm([r["km"] for r in rows])
nheat = norm([r["cum_heat"] for r in rows])
nmin = norm([r["tot_min"] for r in rows])
nalt = norm([r["cum_alt"] for r in rows])
for r in rows:
    travel = nkm(r["km"])
    heat = nheat(r["cum_heat"])
    load = nmin(r["tot_min"])              # 総出場時間(延長分)
    alt = nalt(r["cum_alt"])               # 累積標高負荷(順応国は割引済み)
    rest = max(0.0, min(1.0, (4 - r["rest"]) / 2))  # 休養2日=1, 4日=0
    r["score"] = round(0.25 * travel + 0.25 * heat + 0.15 * load
                       + 0.15 * rest + 0.20 * alt, 3)

rows.sort(key=lambda r: -r["score"])

hdr = (f'{"#":>2} {"team":<12}{"score":>6} | {"cumHeat":>7} {"cumAlt":>6} '
       f'{"km":>6} {"totMin":>7} {"rest":>5} {"G3休":>4}')
print(hdr); print("-" * len(hdr))
for i, r in enumerate(rows, 1):
    print(f'{i:>2} {r["team"]:<12}{r["score"]:>6} | {r["cum_heat"]:>7} {r["cum_alt"]:>6} '
          f'{r["km"]:>6} {r["tot_min"]:>7} {r["rest"]:>5} {"✓" if r["rested_g3"] else "":>4}')

print("\n■ 最も疲労が溜まっていそうな4チーム")
for r in rows[:4]:
    print(f'  {r["team"]}  (score {r["score"]})')
print("■ 疲労が少なそうな4チーム")
for r in rows[-4:][::-1]:
    print(f'  {r["team"]}  (score {r["score"]})')
