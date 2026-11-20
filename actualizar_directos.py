"""Mantiene al día los datos de la página (20 nov 2026). Lo corre GitHub cada 10 min (.github/workflows/directos.yml);
cada archivo se guarda solo si cambió, así no hay versiones de más.

· directos.json — los directos más recientes: feed de YouTube de la lista automática de directos del canal (LISTA = UULV +
  id del canal; YouTube la llena sola con cada directo terminado). [{"id", "titulo", "juego", "gancho", "fecha", "vistas"}],
  el más nuevo primero (máximo MAX). La página enseña del 2.º al 9.º en «Directos anteriores» (el 1.º va en el reproductor).
· vivo.json — si ALEXNIER está en vivo ahora: {"vivo": true|false, "id", "titulo"}. Se lee la página /live del canal como el
  bot de Lumi (isLiveNow / isLive, y un directo solo programado NO cuenta). La página pone arriba «EN VIVO AHORA».
· tienda.json — los productos publicados de la tienda en Niño Gamer (TIENDA), los más nuevos primero (máximo TIENDA_MAX):
  [{"id", "nombre", "precio", "moneda", "imagen", "url"}]. Mismo método que integrations/tienda_monitor.py del bot.
Solo usa la biblioteca de Python. Se edita aquí: CANAL, LISTA, MAX, TIENDA, TIENDA_MAX."""
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CANAL = "UCCdCqcU1KpL0PyVr63vOMlw"
LISTA = "UULV" + CANAL[2:]
MAX = 15
TIENDA = "https://ninogamer.com/creadores/gameeffectmx"
TIENDA_MAX = 8
AQUI = Path(__file__).resolve().parent
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Accept-Language": "es-MX,es;q=0.9"}


def _bajar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def directos():
    raiz = ET.fromstring(_bajar(f"https://www.youtube.com/feeds/videos.xml?playlist_id={LISTA}"))
    out = []
    for e in raiz.findall("a:entry", NS)[:MAX]:
        titulo = e.findtext("a:title", "", NS).strip()
        juego, _, gancho = titulo.partition("|")
        est = e.find("m:group/m:community/m:statistics", NS)
        out.append({"id": e.findtext("yt:videoId", "", NS), "titulo": titulo, "juego": juego.strip() if gancho else "",
                    "gancho": gancho.strip() or titulo, "fecha": e.findtext("a:published", "", NS)[:10],
                    "vistas": int(est.get("views", 0)) if est is not None else 0})
    return out


def vivo():
    html = _bajar(f"https://www.youtube.com/channel/{CANAL}/live").decode("utf-8", "ignore")
    en_vivo = ('"isLiveNow":true' in html or '"isLive":true' in html) and '"isUpcoming":true' not in html
    if not en_vivo:
        return {"vivo": False}
    m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([\w-]{11})"', html)
    t = re.search(r'<meta property="og:title" content="([^"]*)"', html)
    if not m:
        return {"vivo": False}
    import html as H
    return {"vivo": True, "id": m.group(1), "titulo": H.unescape(t.group(1)) if t else ""}


def tienda():
    html = _bajar(TIENDA).decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("la página de la tienda ya no trae __NEXT_DATA__")
    datos = json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("products") or []
    base = re.match(r"https?://[^/]+", TIENDA).group(0)
    out = []
    for p in datos:
        if str(p.get("status", "published")) != "published" or str(p.get("archived", "False")) == "True" \
                or str(p.get("isPublic", "True")) == "False" or not p.get("_id"):
            continue
        out.append({"id": p["_id"], "nombre": (p.get("name") or "Producto").strip(), "precio": p.get("price", ""),
                    "moneda": p.get("currency", "MXN"), "imagen": p.get("thumbImage", ""), "url": f"{base}/productos/{p['_id']}",
                    "_creado": float(p.get("createdAt") or 0)})
    out.sort(key=lambda p: -p["_creado"])
    for p in out: p.pop("_creado")
    return out[:TIENDA_MAX]


def _guardar(nombre, nuevo, clave=lambda x: x):
    f = AQUI / nombre
    try: viejo = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError): viejo = None
    if viejo is not None and clave(viejo) == clave(nuevo):
        print(f"{nombre}: sin cambios"); return
    f.write_text(json.dumps(nuevo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{nombre}: actualizado")


if __name__ == "__main__":
    for nombre, fn, clave in (("directos.json", directos, lambda xs: [(x["id"], x["titulo"]) for x in xs]),   # las vistas no cuentan
                              ("vivo.json", vivo, lambda x: x), ("tienda.json", tienda, lambda x: x)):
        try:
            datos = fn()
            if nombre != "vivo.json" and not datos:
                print(f"{nombre}: vino vacío, no lo cambio"); continue
            _guardar(nombre, datos, clave)
        except Exception as e:   # si una falla, las otras siguen
            print(f"{nombre}: no se pudo ({e})")
