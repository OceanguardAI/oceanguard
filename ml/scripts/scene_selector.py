import csv, re, collections
used = {"05bc615a9b0e1159t","2899cfb18883251bt","72dba3e82f782f67t","cbe4ad26fe73f118t","e98ca5aba8849b06t"}
rows = list(csv.DictReader(open(r"D:\Main\OceanGuard\labels\train.csv", newline="", encoding="utf-8")))
cnt = collections.Counter(r["scene_id"] for r in rows if r["is_vessel"]=="True" and r["confidence"] in ("HIGH","MEDIUM") and r["scene_id"] not in used)
lines = open(r"D:\Main\OceanGuard\train_out\train.txt", encoding="utf-8").read().splitlines()
avail = {}
for i, ln in enumerate(lines):
    m = re.match(r"https://.*/train/([0-9a-f]+t)\.tar\.gz", ln)
    if m: avail[m.group(1)] = (ln, lines[i+1])
pick = [s for s, _ in cnt.most_common() if s in avail][:8]
print("available", len(avail), "picked", [(s, cnt[s]) for s in pick])
with open(r"D:\Main\OceanGuard\train2_links.txt", "w", encoding="utf-8") as f:
    for s in pick: f.write(avail[s][0] + "\n" + avail[s][1] + "\n")
sel = [r for r in rows if r["scene_id"] in pick and r["is_vessel"]=="True" and r["confidence"] in ("HIGH","MEDIUM")]
with open(r"D:\Main\OceanGuard\labels\train2_labels.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(sel)
print("label rows", len(sel))
