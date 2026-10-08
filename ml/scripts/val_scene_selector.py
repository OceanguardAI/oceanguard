import csv, re, collections
rows = list(csv.DictReader(open(r"D:\Main\OceanGuard\labels\validation.csv", newline="", encoding="utf-8")))
cnt = collections.Counter(r["scene_id"] for r in rows if r["is_vessel"]=="True" and r["confidence"] in ("HIGH","MEDIUM") and r["scene_id"] != "590dd08f71056cacv")
lines = open(r"D:\Main\OceanGuard\train_out\validation.txt", encoding="utf-8").read().splitlines()
avail = {}
for i, ln in enumerate(lines):
    m = re.match(r"https://.*/validation/([0-9a-f]+v)\.tar\.gz", ln)
    if m: avail[m.group(1)] = (ln, lines[i+1])
pick = ["b1844cde847a3942v"] + [s for s, _ in cnt.most_common() if s in avail and s != "b1844cde847a3942v"][:2]
print("picked", [(s, cnt[s]) for s in pick])
with open(r"D:\Main\OceanGuard\val2_links.txt", "w", encoding="utf-8") as f:
    for s in pick: f.write(avail[s][0] + "\n" + avail[s][1] + "\n")
sel = [r for r in rows if r["scene_id"] in pick and r["is_vessel"]=="True" and r["confidence"] in ("HIGH","MEDIUM")]
with open(r"D:\Main\OceanGuard\labels\val2_labels.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(sel)
print("label rows", len(sel))
