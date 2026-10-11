#!/usr/bin/env python3
"""Векторные портреты для «Зала славы» из свободных фото Wikimedia Commons.

  python make_portraits.py fetch  <photos_dir>   скачать фото + метаданные (автор, лицензия) -> credits.raw.json
  python make_portraits.py trace  <photos_dir> [id ...]   фото -> маска rembg -> кадр от макушки -> 8 тёплых тонов -> vtracer -> portraits/<id>.svg
  python make_portraits.py inject                вставить SVG и подписи в ../startup-quest.html (между маркерами)

Нужно: Python 3.12/3.13 (vtracer 0.6.15 падает на 3.14), pip install vtracer pillow numpy opencv-python-headless "rembg[cpu]"; curl в PATH.
Сами фото в репозиторий не кладём. credits.json (автор/лицензия) проверен вручную по страницам файлов.
"""
import json, os, re, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "StartupQuestPortraits/1.0 (educational game; contact gkobmax@gmail.com)"
API = "https://commons.wikimedia.org/w/api.php?"
SRC = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))["portraits"]
SIZE = 560          # сторона растрового кадра перед трассировкой
# 8 тонов одной тёплой гаммы, от тёмного к светлому (стиль «векторный постер»), и перцентили яркости лица для порогов
PAL = [(14, 10, 10), (52, 24, 18), (98, 44, 28), (150, 72, 42), (196, 116, 74), (228, 160, 116), (246, 200, 162), (252, 230, 210)]
QS = [7, 17, 30, 44, 59, 74, 89]
TOP = 0.07         # запас над макушкой, доля кадра


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
        if not s.get("file"): continue                    # фото прислал пользователь (не Commons): кладётся в photos_dir руками
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


def person_mask(img):
    """Маска человека нейросетью rembg (u2net_human_seg): волосы не срезаются, фон не прилипает."""
    import cv2, numpy as np
    from PIL import Image
    from rembg import remove, new_session
    h, w = img.shape[:2]; k = min(1.0, 1600 / max(h, w))
    small = Image.fromarray(cv2.cvtColor(cv2.resize(img, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
    m = np.array(remove(small, session=new_session("u2net_human_seg"), only_mask=True).resize((w, h), Image.BILINEAR)) > 128
    return largest(m)


def largest(m):
    """Самая крупная связная область без дырок внутри."""
    import cv2, numpy as np
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    if n > 1: m = lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    cn, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    f = np.zeros(m.shape, np.uint8); cv2.drawContours(f, cn, -1, 1, -1)
    return f.astype(bool)


def tones(crop, m, cxc, s):
    """Яркость -> 8 тонов: сглаженные плоскости + тёмные черты лица (глаза, брови, губы) из детального слоя."""
    import cv2, numpy as np
    N = crop.shape[0]
    L0 = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)[..., 0]
    Ld = cv2.createCLAHE(2.0, (4, 4)).apply(cv2.bilateralFilter(L0, 7, 30, 5))
    L = L0
    if s.get("bgfill"): L = L.copy(); L[~m] = int(np.median(L[m]))     # светлый фон не влияет на выравнивание контраста
    for _ in range(2): L = cv2.bilateralFilter(L, 7, 25, 9)
    L = cv2.createCLAHE(s.get("clahe", 1.8), (2, 2)).apply(L)
    yy, xx = np.mgrid[0:N, 0:N]; yt = np.where(m.any(1))[0][0]
    face = m & (yy > yt + 0.18 * N) & (yy < yt + 0.62 * N) & (np.abs(xx - cxc) < 0.17 * N)   # пороги считаем по лицу
    qreg = m if s.get("qmask") else face                   # малоконтрастное (ретушь) лицо: пороги по всей фигуре
    lvl = np.digitize(L, np.percentile(L[qreg], QS)).astype(np.uint8)
    for k in (5, 3): lvl = cv2.medianBlur(lvl, k)
    det = cv2.medianBlur(np.digitize(Ld, np.percentile(Ld[qreg], [9, 22])).astype(np.uint8), 3)
    lvl = cv2.medianBlur(np.where(det < 2, np.minimum(lvl, det), lvl).astype(np.uint8), 3)
    if "lut" in s: lvl = np.array(s["lut"], np.uint8)[lvl]   # тёмная кожа: сжать тона к тёмной части гаммы
    return np.array(PAL, np.uint8)[lvl]


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


def trace(pdir, only=()):
    import cv2, numpy as np, vtracer
    from PIL import Image
    for pid, s in SRC.items():
        if only and pid not in only: continue
        img = cv2.imread(os.path.join(pdir, pid + ".jpg"))[s.get("trim_top", 0):]   # trim_top: тёмная кромка скриншота
        if "pad" in s:                                    # [верх, право, низ, лево]: дотянуть фон, если голове тесно в кадре
            t_, r_, b_, l_ = s["pad"]; img = cv2.copyMakeBorder(img, t_, b_, l_, r_, cv2.BORDER_REPLICATE)
        H, W = img.shape[:2]
        M = person_mask(img)
        side = int(min(W, H, s["scale"] * W))                     # сторона кадра, доля ширины фото
        yt = np.where(M.any(1))[0][0]                             # макушка
        cols = np.where(M[yt:yt + int(0.3 * side)].any(0))[0]; cx = (cols[0] + cols[-1]) / 2   # центр головы
        y0 = int(max(0, min(H - side, yt - TOP * side))); x0 = int(max(0, min(W - side, cx - side / 2)))
        crop = cv2.resize(img[y0:y0 + side, x0:x0 + side], (SIZE, SIZE), interpolation=cv2.INTER_AREA)
        m = cv2.resize(M[y0:y0 + side, x0:x0 + side].astype(np.uint8) * 255, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
        m = cv2.GaussianBlur(m, (0, 0), SIZE / 250) > 127
        for bx0, by0, bx1, by1 in s.get("bg", ()):                # лишние предметы в кадре (доли кадра)
            m[int(by0 * SIZE):int(by1 * SIZE), int(bx0 * SIZE):int(bx1 * SIZE)] = False
        m = largest(m)
        assert not m[0].any(), (pid, "голова касается верха кадра")
        rgba = np.dstack([tones(crop, m, (cx - x0) * SIZE / side, s), (m * 255).astype(np.uint8)])
        png = os.path.join(pdir, pid + "_q.png"); Image.fromarray(rgba, "RGBA").save(png)
        raw = os.path.join(pdir, pid + "_raw.svg")
        vtracer.convert_image_to_svg_py(png, raw, colormode="color", hierarchical="stacked", mode="spline",
                                        filter_speckle=14, color_precision=8, layer_difference=10,
                                        corner_threshold=50, length_threshold=4.0, max_iterations=10,
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
        c = credits[pid]; cr[pid] = {k: c.get(k, "") for k in ("author", "license", "licenseUrl", "page", "note")}
    ddir = os.path.join(HERE, "drawn")                      # рисованные образы (make_drawn.py): без фото, без подписи автора
    for f in sorted(os.listdir(ddir)) if os.path.isdir(ddir) else ():
        if f.endswith(".svg") and f[:-4] not in pt: pt[f[:-4]] = re.sub(r'^<svg[^>]*>|</svg>$', "", open(os.path.join(ddir, f), encoding="utf-8").read())
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
    elif cmd == "trace": trace(sys.argv[2], sys.argv[3:])
    elif cmd == "inject": inject()
    else: print(__doc__)
