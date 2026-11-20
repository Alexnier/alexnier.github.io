"""Actualiza directos.json con los directos más recientes del canal (20 nov 2026).

Lee el feed de YouTube de la lista automática de directos del canal (UULV + id del canal; YouTube la llena sola con cada
directo terminado) y escribe directos.json: [{"id", "titulo", "juego", "gancho", "fecha", "vistas"}], el más nuevo
primero (máximo MAX). Solo usa la biblioteca de Python. Lo corre GitHub cada hora (.github/workflows/directos.yml) y solo
guarda si la lista cambió. La página (index.html, sección «Directos anteriores») lo lee y enseña del 2.º al 9.º: el 1.º
ya está en el reproductor de arriba.
Se edita aquí: LISTA (la lista de YouTube), MAX."""
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

LISTA = "UULVCdCqcU1KpL0PyVr63vOMlw"
MAX = 15
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}
SALIDA = Path(__file__).resolve().parent / "directos.json"


def leer():
    req = urllib.request.Request(f"https://www.youtube.com/feeds/videos.xml?playlist_id={LISTA}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raiz = ET.fromstring(r.read())
    out = []
    for e in raiz.findall("a:entry", NS)[:MAX]:
        titulo = e.findtext("a:title", "", NS).strip()
        juego, _, gancho = titulo.partition("|")
        est = e.find("m:group/m:community/m:statistics", NS)
        out.append({"id": e.findtext("yt:videoId", "", NS), "titulo": titulo, "juego": juego.strip() if gancho else "",
                    "gancho": gancho.strip() or titulo, "fecha": e.findtext("a:published", "", NS)[:10],
                    "vistas": int(est.get("views", 0)) if est is not None else 0})
    return out


if __name__ == "__main__":
    nuevos = leer()
    if not nuevos:
        raise SystemExit("el feed vino vacío: no cambio nada")
    try:
        viejos = json.loads(SALIDA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        viejos = None
    # solo cuenta como cambio un directo nuevo o un título distinto (las vistas cambian a cada rato y no merecen otra versión)
    clave = lambda xs: [(x["id"], x["titulo"]) for x in (xs or [])]
    if clave(nuevos) == clave(viejos):
        print("sin cambios")
    else:
        SALIDA.write_text(json.dumps(nuevos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"directos.json: {len(nuevos)} directos, el más nuevo: {nuevos[0]['titulo']}")
