#!/usr/bin/env python3
"""各試合行(flow-styleの teams: [...] を持つ行)に kickoff_local を注入する。

現地キックオフ時刻(local)は Web調査(Wikipedia per-group / knockout, SI等で2社確認)より。
YAMLのコメント・整形を壊さないよう、行テキストの teams:[...] 直後に挿入する。
冪等: 既に kickoff_local がある行はスキップ。
"""
import re

# (date, frozenset(teams)) -> "HH:MM" 現地時刻
K = {}
def add(date, a, b, t): K[(date, frozenset((a, b)))] = t

# --- Round of 32 ---
add("2026-06-28", "Canada", "South Africa", "12:00")
add("2026-06-29", "Brazil", "Japan", "12:00")
add("2026-06-29", "Paraguay", "Germany", "16:30")
add("2026-06-29", "Morocco", "Netherlands", "19:00")
add("2026-06-30", "Norway", "Ivory Coast", "12:00")
add("2026-06-30", "France", "Sweden", "17:00")
add("2026-06-30", "Mexico", "Ecuador", "19:00")
add("2026-07-01", "England", "DR Congo", "12:00")
add("2026-07-01", "Belgium", "Senegal", "13:00")
add("2026-07-01", "USA", "Bosnia and Herzegovina", "17:00")
add("2026-07-02", "Spain", "Austria", "12:00")
add("2026-07-02", "Portugal", "Croatia", "19:00")
add("2026-07-02", "Switzerland", "Algeria", "20:00")
add("2026-07-03", "Egypt", "Australia", "13:00")
add("2026-07-03", "Argentina", "Cape Verde", "18:00")
add("2026-07-03", "Colombia", "Ghana", "20:30")
# --- Group A ---
add("2026-06-11", "Mexico", "South Africa", "13:00")
add("2026-06-11", "South Korea", "Czech Republic", "20:00")
add("2026-06-18", "Czech Republic", "South Africa", "12:00")
add("2026-06-18", "Mexico", "South Korea", "19:00")
add("2026-06-24", "Czech Republic", "Mexico", "19:00")
add("2026-06-24", "South Africa", "South Korea", "19:00")
# --- Group B ---
add("2026-06-12", "Canada", "Bosnia and Herzegovina", "15:00")
add("2026-06-13", "Qatar", "Switzerland", "12:00")
add("2026-06-18", "Switzerland", "Bosnia and Herzegovina", "12:00")
add("2026-06-18", "Canada", "Qatar", "15:00")
add("2026-06-24", "Switzerland", "Canada", "12:00")
add("2026-06-24", "Bosnia and Herzegovina", "Qatar", "12:00")
# --- Group C ---
add("2026-06-13", "Brazil", "Morocco", "18:00")
add("2026-06-13", "Haiti", "Scotland", "21:00")
add("2026-06-19", "Scotland", "Morocco", "18:00")
add("2026-06-19", "Brazil", "Haiti", "20:30")
add("2026-06-24", "Scotland", "Brazil", "18:00")
add("2026-06-24", "Morocco", "Haiti", "18:00")
# --- Group D ---
add("2026-06-12", "USA", "Paraguay", "18:00")
add("2026-06-13", "Australia", "Türkiye", "21:00")
add("2026-06-19", "USA", "Australia", "12:00")
add("2026-06-19", "Türkiye", "Paraguay", "20:00")
add("2026-06-25", "Türkiye", "USA", "19:00")
add("2026-06-25", "Paraguay", "Australia", "19:00")
# --- Group E ---
add("2026-06-14", "Germany", "Curaçao", "12:00")
add("2026-06-14", "Ivory Coast", "Ecuador", "19:00")
add("2026-06-20", "Germany", "Ivory Coast", "16:00")
add("2026-06-20", "Ecuador", "Curaçao", "19:00")
add("2026-06-25", "Curaçao", "Ivory Coast", "16:00")
add("2026-06-25", "Ecuador", "Germany", "16:00")
# --- Group F ---
add("2026-06-14", "Netherlands", "Japan", "15:00")
add("2026-06-14", "Sweden", "Tunisia", "20:00")
add("2026-06-20", "Netherlands", "Sweden", "12:00")
add("2026-06-20", "Tunisia", "Japan", "22:00")
add("2026-06-25", "Japan", "Sweden", "18:00")
add("2026-06-25", "Tunisia", "Netherlands", "18:00")
# --- Group G ---
add("2026-06-15", "Belgium", "Egypt", "12:00")
add("2026-06-15", "Iran", "New Zealand", "18:00")
add("2026-06-21", "Belgium", "Iran", "12:00")
add("2026-06-21", "New Zealand", "Egypt", "18:00")
add("2026-06-26", "Egypt", "Iran", "20:00")
add("2026-06-26", "New Zealand", "Belgium", "20:00")
# --- Group H ---
add("2026-06-15", "Spain", "Cape Verde", "12:00")
add("2026-06-15", "Saudi Arabia", "Uruguay", "18:00")
add("2026-06-21", "Spain", "Saudi Arabia", "12:00")
add("2026-06-21", "Uruguay", "Cape Verde", "18:00")
add("2026-06-26", "Cape Verde", "Saudi Arabia", "19:00")
add("2026-06-26", "Uruguay", "Spain", "18:00")
# --- Group I ---
add("2026-06-16", "France", "Senegal", "15:00")
add("2026-06-16", "Iraq", "Norway", "18:00")
add("2026-06-22", "France", "Iraq", "17:00")
add("2026-06-22", "Norway", "Senegal", "20:00")
add("2026-06-26", "Norway", "France", "15:00")
add("2026-06-26", "Senegal", "Iraq", "15:00")
# --- Group J ---
add("2026-06-16", "Argentina", "Algeria", "20:00")
add("2026-06-16", "Austria", "Jordan", "21:00")
add("2026-06-22", "Argentina", "Austria", "12:00")
add("2026-06-22", "Jordan", "Algeria", "20:00")
add("2026-06-27", "Algeria", "Austria", "21:00")
add("2026-06-27", "Jordan", "Argentina", "21:00")
# --- Group K ---
add("2026-06-17", "Portugal", "DR Congo", "12:00")
add("2026-06-17", "Uzbekistan", "Colombia", "20:00")
add("2026-06-23", "Portugal", "Uzbekistan", "12:00")
add("2026-06-23", "Colombia", "DR Congo", "20:00")
add("2026-06-27", "Colombia", "Portugal", "19:30")
add("2026-06-27", "DR Congo", "Uzbekistan", "19:30")
# --- Group L ---
add("2026-06-17", "England", "Croatia", "15:00")
add("2026-06-17", "Ghana", "Panama", "19:00")
add("2026-06-23", "England", "Ghana", "16:00")
add("2026-06-23", "Panama", "Croatia", "19:00")
add("2026-06-27", "Panama", "England", "17:00")
add("2026-06-27", "Croatia", "Ghana", "17:00")

date_re = re.compile(r"date:\s*(\d{4}-\d{2}-\d{2})")
teams_re = re.compile(r"teams:\s*\[([^\]]*)\]")

def process(path):
    out, injected, missing = [], 0, []
    for line in open(path, encoding="utf-8"):
        tm = teams_re.search(line)
        if not tm or "kickoff_local" in line:
            out.append(line); continue
        dm = date_re.search(line)
        teams = frozenset(t.strip() for t in tm.group(1).split(","))
        key = (dm.group(1), teams)
        if key in K:
            ins = f'{tm.group(0)}, kickoff_local: "{K[key]}"'
            out.append(line.replace(tm.group(0), ins, 1))
            injected += 1
        else:
            out.append(line); missing.append(key)
    open(path, "w", encoding="utf-8").writelines(out)
    return injected, missing

for p in ["bracket.yaml", "group_stage.yaml"]:
    inj, miss = process(p)
    print(f"{p}: injected {inj}", f"| MISSING {miss}" if miss else "| no misses")
