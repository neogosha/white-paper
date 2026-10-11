#!/usr/bin/env python3
"""Векторные портреты для «Зала славы» из свободных фото Wikimedia Commons.

  python make_portraits.py fetch  <photos_dir>   скачать фото + метаданные (автор, лицензия) -> credits.raw.json
  python make_portraits.py trace  <photos_dir>   фото -> вырезание фона -> постеризация -> vtracer -> portraits/<id>.svg
  python make_portraits.py inject                вставить SVG и подписи в ../startup-quest.html (между маркерами)

Нужно: Python 3.12/3.13 (vtracer 0.6.15 падает на 3.14), pip install vtracer pillow numpy opencv-python-headless; curl в PATH.
Сами фото в репозиторий не кладём. credits.json (автор/лицензия) проверен вручную по страницам файлов.
"""
import json, os, re, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "StartupQuestPortraits/1.0 (educational game; contact gkobmax@gmail.com)"
API = "https://commons.wikimedia.org/w/api.php?"
SRC = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))["portraits"]
SIZE = 300          # сторона растрового кадра перед трассировкой
COLORS = 9          # цветов в постеризации лица/одежды


def curl(url, out=None):
    cmd = ["curl", "-s", "-L", "-m", "120", "-A", UA] + (["-o", out] if out else []) + [url]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def api(**p):
    p["format"] = "json"
    return json.loads(curl(API + urllib.parse.urlencode(p)))


def strip(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(pdir):
    os.makedirs(pdir, exist_ok=True)
    credits = {}
    for pid, s in SRC.items():
        d = api(action="query", titles="File:" + s["file"], prop="imageinfo", iiprop="url|extmetadata", iiurlwidth=2400)
        pg = list(d["query"]["pages"].values())[0]
        ii = pg["imageinfo"][0]; m = ii["extmetadata"]
        lic = m.get("LicenseShortName", {}).get("value", "")
        assert re.match(r"(CC0|Public domain|CC BY)", lic), (pid, lic)  # только свободные лицензии
        artist = strip(m.get("Artist", {}).get("value"))
        credits[pid] = {"person": s["person"], "file": pg["title"], "page": ii["descriptionurl"], "author": artist,
                        "license": lic, "licenseUrl": m.get("LicenseUrl", {}).get("value", "")}
        curl(ii.get("thumburl") or ii["url"], os.path.join(pdir, pid + ".jpg"))
        print(pid, lic, artist)
    json.dump(credits, open(os.path.join(HERE, "credits.raw.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cutout(img, face, bg=(), erode=1):
    """GrabCut с подсказками: лицо — точно передний план, верх и бока — точно фон."""
    import cv2, numpy as np
    h, w = img.shape[:2]
    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, rx, ry = face
    ell = lambda k: ((xx / w - cx) / (rx * k)) ** 2 + ((yy / h - cy) / (ry * k)) ** 2 <= 1
    mask[ell(2.2)] = cv2.GC_PR_FGD                      # голова с волосами
    mask[(yy / h > 0.80) & (np.abs(xx / w - 0.5) < 0.42)] = cv2.GC_PR_FGD  # плечи
    mask[ell(0.55)] = cv2.GC_FGD                        # ядро лица
    b = max(2, int(0.025 * w))
    mask[:b, :] = cv2.GC_BGD; mask[: int(h * .6), :b] = cv2.GC_BGD; mask[: int(h * .6), -b:] = cv2.GC_BGD
    for x0, y0, x1, y1 in bg:                         # доп. прямоугольники точного фона
        mask[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = cv2.GC_BGD
    bgd = np.zeros((1, 65)); fgd = np.zeros((1, 65))
    cv2.grabCut(img, mask, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    m = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        m = (lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    k = max(3, w // 60) | 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), w / 100) > 0.5       # сглаженный контур
    # дырки внутри (блики на лице) заливаем
    cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros(m.shape, np.uint8); cv2.drawContours(filled, cnts, -1, 1, -1)
    e = max(1, w // 150) * erode                                  # съесть ореол фона по краю
    return cv2.erode(filled, np.ones((2 * e + 1, 2 * e + 1), np.uint8)).astype(bool)


def posterize(img, mask, colors, chroma=0.85):
    import cv2, numpy as np
    img = cv2.pyrMeanShiftFiltering(img, 6, 14)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l = lab[..., 0].astype(np.float32)                   # растянуть контраст (тёмные фото)
    lo, hi = np.percentile(l[mask], [1, 99])
    lab[..., 0] = np.clip((l - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
    lab[..., 1:] = np.clip(128 + (lab[..., 1:].astype(np.float32) - 128) * chroma, 0, 255).astype(np.uint8)   # приглушить цветовой оттенок съёмки
    pts = lab[mask].reshape(-1, 3).astype(np.float32)
    cv2.setRNGSeed(7)
    _, lbl, ctr = cv2.kmeans(pts, colors, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    out = np.zeros_like(lab); out[mask] = ctr[lbl.ravel()].astype(np.uint8)
    return cv2.medianBlur(cv2.cvtColor(out, cv2.COLOR_LAB2BGR), 5)


def bake(svg):
    """vtracer кладёт translate() на каждый path; вшиваем его в координаты и округляем до целых."""
    paths = []
    for m in re.finditer(r'<path d="([^"]+)" fill="(#[0-9a-fA-F]{6})" transform="translate\(([-\d.]+),([-\d.]+)\)"', svg):
        d, fill, tx, ty = m.group(1), m.group(2).lower(), float(m.group(3)), float(m.group(4))
        out = []
        for seg in re.finditer(r"([MCLZ])([^MCLZ]*)", d):
            cmd, nums = seg.group(1), [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", seg.group(2))]
            vals = [round(nums[i] + (tx if i % 2 == 0 else ty)) for i in range(len(nums))]
            out.append(cmd + " ".join(map(str, vals)))
        paths.append((fill, "".join(out)))
    merged = []   # подряд идущие path одного цвета склеиваем (в stacked-режиме порядок слоёв важен)
    for f, d in paths:
        if merged and merged[-1][0] == f: merged[-1] = (f, merged[-1][1] + d)
        else: merged.append((f, d))
    return "".join(f'<path fill="{f}" d="{d}"/>' for f, d in merged)


def trace(pdir):
    import cv2, numpy as np, vtracer
    from PIL import Image
    for pid, s in SRC.items():
        img = cv2.imread(os.path.join(pdir, pid + ".jpg"))
        H, W = img.shape[:2]; x0f, y0f, sf = s["crop"]
        side = int(sf * W); x0, y0 = int(x0f * W), int(y0f * H)
        crop = img[y0:y0 + side, x0:x0 + side]
        assert crop.shape[0] > 0 and crop.shape[1] > 0, pid
        crop = cv2.resize(crop, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
        mask = cutout(crop, s["face"], s.get("bg", ()), s.get("erode", 1))
        post = posterize(crop, mask, s.get("colors", COLORS), s.get("chroma", 0.85))
        rgba = np.dstack([cv2.cvtColor(post, cv2.COLOR_BGR2RGB), (mask * 255).astype(np.uint8)])
        png = os.path.join(pdir, pid + "_q.png"); Image.fromarray(rgba, "RGBA").save(png)
        raw = os.path.join(pdir, pid + "_raw.svg")
        vtracer.convert_image_to_svg_py(png, raw, colormode="color", hierarchical="stacked", mode="spline",
                                        filter_speckle=s.get("speckle", 18), color_precision=6, layer_difference=8,
                                        corner_threshold=60, length_threshold=6.0, max_iterations=10,
                                        splice_threshold=45, path_precision=1)
        body = bake(open(raw, encoding="utf-8").read())
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}">{body}</svg>'
        open(os.path.join(HERE, pid + ".svg"), "w", encoding="utf-8").write(svg)
        print(pid, len(svg) // 1024, "KB")


def inject():
    credits = json.load(open(os.path.join(HERE, "credits.json"), encoding="utf-8"))
    pt, cr = {}, {}
    for pid in SRC:
        svg = open(os.path.join(HERE, pid + ".svg"), encoding="utf-8").read()
        pt[pid] = re.sub(r'^<svg[^>]*>|</svg>$', "", svg)
        c = credits[pid]; cr[pid] = {k: c[k] for k in ("author", "license", "licenseUrl", "page")}
    js = ("/* PORTRAITS:BEGIN (генерируется portraits/make_portraits.py inject; руками не править) */\n"
          "const PORTRAIT_SIZE = %d;\nconst PORTRAITS = %s;\nconst PORTRAIT_CREDITS = %s;\n/* PORTRAITS:END */"
          % (SIZE, json.dumps(pt, ensure_ascii=False, separators=(",", ":")), json.dumps(cr, ensure_ascii=False, indent=1)))
    path = os.path.join(HERE, "..", "startup-quest.html")
    html = open(path, encoding="utf-8", newline="").read()
    if "\r\n" in html: js = js.replace("\n", "\r\n")        # рабочая копия в CRLF (autocrlf)
    pat = re.compile(r"/\* PORTRAITS:BEGIN.*?PORTRAITS:END \*/", re.S)
    assert pat.search(html), "маркеры PORTRAITS не найдены в startup-quest.html"
    open(path, "w", encoding="utf-8", newline="").write(pat.sub(lambda _: js, html))
    print("inject ok", len(js) // 1024, "KB")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch": fetch(sys.argv[2])
    elif cmd == "trace": trace(sys.argv[2])
    elif cmd == "inject": inject()
    else: print(__doc__)
