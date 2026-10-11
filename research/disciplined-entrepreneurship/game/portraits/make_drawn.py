#!/usr/bin/env python3
"""Рисованные образы для героев без подходящего свободного фото (стиль и палитра — как у векторных портретов).

  python make_drawn.py      -> portraits/drawn/<id>.svg

Лицо мультяшное, как у прежних аватаров, — не портретное сходство; узнаются по причёске и детали. В игре подписано «Рисованный образ».
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = ["#0e0a0a", "#341812", "#622c1c", "#96482a", "#c4744a", "#e4a074", "#f6c8a2", "#fce6d2"]   # = PAL в make_portraits.py
S = 560


FIG = 'transform="translate(-42 -46) scale(1.15)"'   # фигура крупно, как голова на фото-портретах


SKIN = {"light": (P[5], P[4], P[6]), "dark": (P[3], P[2], P[4])}   # основной тон, тень, блик


def base(hair, skin):
    """Плечи в тёмной одежде, голова мультяшная (как у прежних аватаров), тени и блики — тонами палитры."""
    s, sh, hi = SKIN[skin]
    return (
        f'<g {FIG}><path fill="{P[1]}" d="M30 560C40 470 120 430 205 412L355 412C440 430 520 470 530 560Z"/>'
        f'<path fill="{P[0]}" d="M300 412L355 412C440 430 520 470 530 560L300 560Z"/>'
        f'<path fill="{P[3]}" d="M205 412C130 428 52 466 34 548L48 548C64 480 132 446 214 424Z"/>'
        f'<path fill="{s}" d="M236 300L324 300L324 414C300 428 260 428 236 414Z"/><path fill="{sh}" d="M286 300L324 300L324 414C312 420 298 424 286 424Z"/>'
        f'<path fill="{sh}" d="M236 330C256 346 304 346 324 330L324 360C304 372 256 372 236 360Z"/>'
        f'<ellipse fill="{s}" cx="180" cy="222" rx="18" ry="28"/><ellipse fill="{sh}" cx="380" cy="222" rx="18" ry="28"/>'
        f'<path fill="{s}" d="M178 214C178 140 224 96 280 96C336 96 382 140 382 214C382 290 336 336 280 336C224 336 178 290 178 214Z"/>'
        f'<path fill="{sh}" d="M300 98C350 108 382 150 382 214C382 290 336 336 280 336C318 312 336 268 334 214C332 160 322 124 300 98Z"/>'
        f'<path fill="{hi}" d="M200 168C192 186 190 204 192 222C196 256 210 280 230 296C214 270 208 240 208 214C208 196 204 180 200 168Z"/>'
        # лицо: брови, глаза с бликом, нос, улыбка, румянец
        f'<path fill="none" stroke="{P[0]}" stroke-width="9" stroke-linecap="round" d="M222 186Q242 172 262 184M300 184Q320 172 340 186"/>'
        f'<ellipse fill="{P[0]}" cx="242" cy="214" rx="11" ry="14"/><ellipse fill="{P[0]}" cx="320" cy="214" rx="11" ry="14"/>'
        f'<circle fill="{P[7]}" cx="246" cy="209" r="4"/><circle fill="{P[7]}" cx="324" cy="209" r="4"/>'
        f'<path fill="{sh}" d="M282 222C288 244 296 256 298 262C290 268 278 268 270 264C276 256 280 240 282 222Z"/>'
        f'<path fill="{P[1]}" d="M246 284C266 306 300 306 318 284C302 292 264 292 246 284Z"/>'
        f'<path fill="{P[1]}" d="M246 284C262 312 302 312 318 284C298 298 266 298 246 284Z"/>'
        f'<ellipse fill="{sh}" cx="226" cy="262" rx="16" ry="9" opacity=".7"/><ellipse fill="{sh}" cx="338" cy="262" rx="16" ry="9" opacity=".7"/>'
        + hair + "</g>")


HAIR = {
    "short": f'<path fill="{P[0]}" d="M176 206C170 140 214 86 282 84C350 84 392 134 386 206C372 168 350 146 318 140C286 152 236 152 206 142C190 160 182 180 176 206Z"/>'
             f'<path fill="none" stroke="{P[2]}" stroke-width="5" d="M214 116C244 100 290 96 330 108"/>',
    "curly": "".join(f'<circle fill="{P[0]}" cx="{x}" cy="{y}" r="{r}"/>' for x, y, r in
                     [(200, 150, 44), (240, 112, 46), (290, 98, 48), (338, 116, 44), (370, 156, 38), (186, 196, 26), (382, 198, 24)])
             + "".join(f'<path fill="none" stroke="{P[2]}" stroke-width="5" d="M{x - 14} {y + 4}C{x - 8} {y - 12} {x + 8} {y - 12} {x + 14} {y + 4}"/>'
                       for x, y in [(206, 140), (244, 104), (292, 92), (336, 108)]),
    "bun": "".join(f'<circle fill="{P[0]}" cx="{x}" cy="{y}" r="{r}"/>' for x, y, r in
                   [(250, 58, 30), (284, 46, 32), (316, 60, 28), (262, 84, 26), (304, 86, 26)])
           + f'<path fill="{P[0]}" d="M180 204C176 140 222 94 280 92C338 94 384 140 380 204C362 164 330 144 280 142C230 144 198 164 180 204Z"/>'
           + "".join(f'<path fill="none" stroke="{P[2]}" stroke-width="5" d="M{x} 104C{x + 8} 120 {x + 8} 136 {x} 150"/>' for x in (222, 252, 282, 312)),
    "bob": f'<path fill="{P[0]}" d="M166 300C150 220 160 120 230 92C266 80 306 80 340 94C404 122 412 220 394 300C380 286 370 260 372 220C352 176 316 156 270 152C236 160 206 180 190 220C192 262 182 288 166 300Z"/>'
           f'<path fill="none" stroke="{P[2]}" stroke-width="5" d="M196 130C222 104 262 96 300 100"/>',
}


def on_body(svg):
    """Деталь, приклеенная к фигуре (воротник, бусы, шляпка), — в координатах силуэта."""
    return f"<g {FIG}>{svg}</g>"


def bow_tie():   # Мозайя Бриджес: воротник рубашки и галстук-бабочка
    stripes = "".join(f'<path fill="{P[3]}" d="M{x} {y}l18 -10l6 10l-18 10Z"/>' for x, y in [(206, 446), (234, 432), (318, 436), (346, 450)])
    return on_body(f'<path fill="{P[7]}" d="M232 398L280 452L328 398L356 412L300 476L280 470L260 476L204 412Z"/>'
                   f'<path fill="{P[5]}" d="M280 452L196 416C184 444 184 476 196 500ZM280 452L364 416C376 444 376 476 364 500Z"/>' + stripes +
                   f'<path fill="{P[4]}" d="M280 452L196 500L206 478L270 452ZM280 452L364 500L354 478L290 452Z"/>'
                   f'<rect fill="{P[4]}" x="262" y="434" width="36" height="38" rx="9"/><rect fill="{P[3]}" x="266" y="452" width="28" height="20" rx="6"/>')


def bee_lemonade():   # Микайла Улмер: пчела у головы и стакан лимонада впереди
    return (f'<path fill="{P[7]}" d="M324 412L420 412L408 524L336 524Z"/>'
            f'<path fill="{P[6]}" d="M328 452L416 452L408 524L336 524Z"/>'
            f'<path fill="{P[5]}" d="M328 452L416 452L414 470L330 470Z"/>'
            f'<circle fill="{P[5]}" cx="392" cy="424" r="22"/><circle fill="{P[6]}" cx="392" cy="424" r="14"/>'
            f'<path stroke="{P[2]}" stroke-width="8" d="M352 360L368 452"/>'
            '<g transform="translate(446 170) rotate(-18) scale(.9)">'
            f'<ellipse fill="{P[7]}" cx="-6" cy="-34" rx="22" ry="30" opacity=".85"/><ellipse fill="{P[7]}" cx="22" cy="-30" rx="18" ry="26" opacity=".85"/>'
            f'<ellipse fill="{P[5]}" cx="0" cy="0" rx="46" ry="30"/>'
            f'<path fill="{P[0]}" d="M-22 -28C-14 -10 -14 10 -22 28L-8 30C0 10 0 -10 -8 -30ZM6 -30C14 -10 14 10 6 30L20 26C26 10 26 -10 20 -26Z"/>'
            f'<circle fill="{P[0]}" cx="-40" cy="-4" r="16"/><path fill="{P[0]}" d="M44 0l18 -6l-4 12Z"/></g>')


def hat_pearls():   # Эсте Лаудер: шляпка с узором и жемчуг
    dots = "".join(f'<circle fill="{P[4]}" cx="{x}" cy="{y}" r="7"/>' for x, y in
                   [(214, 120), (246, 100), (282, 92), (318, 100), (350, 120), (230, 150), (266, 136), (302, 136), (338, 150)])
    pearls = "".join(f'<circle fill="{P[7]}" cx="{280 + dx}" cy="{y}" r="12"/><circle fill="{P[6]}" cx="{284 + dx}" cy="{y + 4}" r="6"/>'
                     for dx, y in [(-96, 418), (-72, 436), (-46, 450), (-18, 458), (12, 458), (40, 450), (66, 436), (90, 418)])
    return on_body(f'<path fill="{P[5]}" d="M170 180C164 116 214 70 282 68C350 70 400 116 394 180C360 166 320 160 282 160C244 160 204 166 170 180Z"/>'
                   f'<path fill="{P[3]}" d="M168 176C206 164 244 158 282 158C320 158 358 164 396 176L394 192C356 180 318 176 282 176C246 176 208 180 170 192Z"/>'
                   + dots + pearls)


def shoebox():   # Ник Свинмерн (Zappos): коробка с кедом в руках
    return (f'<path fill="{P[4]}" d="M178 448L382 448L374 524L186 524Z"/>'
            f'<path fill="{P[5]}" d="M166 424L394 424L386 452L174 452Z"/>'
            f'<path fill="{P[3]}" d="M174 452L386 452L384 462L176 462Z"/>'
            f'<path fill="{P[7]}" d="M204 420C204 388 230 376 254 378C268 390 296 398 326 396C350 398 362 408 360 420Z"/>'
            f'<path fill="{P[2]}" d="M204 420L360 420L360 426L204 426Z"/>'
            f'<path fill="none" stroke="{P[3]}" stroke-width="5" d="M246 386L262 398M262 382L278 394"/>'
            f'<path fill="{P[6]}" d="M240 482h80v8h-80z"/>')


def perfume():   # Джо Малон: флакон духов впереди
    return (f'<rect fill="{P[0]}" stroke="{P[5]}" stroke-width="4" x="244" y="372" width="72" height="50" rx="6"/>'
            f'<rect fill="{P[7]}" x="218" y="420" width="124" height="112" rx="14"/>'
            f'<rect fill="{P[6]}" x="300" y="420" width="42" height="112" rx="10"/>'
            f'<rect fill="{P[5]}" x="240" y="452" width="80" height="54" rx="4"/>'
            f'<rect fill="{P[7]}" x="248" y="460" width="64" height="38" rx="3"/>'
            f'<path fill="{P[2]}" d="M258 472h44v5h-44zM266 484h28v4h-28z"/>')


PEOPLE = {
    "mosbows": ("curly", "dark", bow_tie),
    "mikaila": ("bun", "dark", bee_lemonade),
    "estee": ("bob", "light", hat_pearls),
    "zappos": ("short", "light", shoebox),
    "jomalone": ("bob", "light", perfume),
}

if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "drawn"), exist_ok=True)
    for pid, (hair, skin, extra) in PEOPLE.items():
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">{base(HAIR[hair], skin)}{extra()}</svg>'
        open(os.path.join(HERE, "drawn", pid + ".svg"), "w", encoding="utf-8").write(svg)
        print(pid, len(svg) // 1024, "KB")
