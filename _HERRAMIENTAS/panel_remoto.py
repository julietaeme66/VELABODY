"""Control remoto del panel VELABODY Builder (depuración CEP en localhost:8088).

Uso:
    python panel_remoto.py js   "<javascript del panel>"     # evalúa JS en el panel
    python panel_remoto.py jsx  "<extendscript>"             # ejecuta ExtendScript en Premiere
    python panel_remoto.py log                               # muestra el log del panel
"""
import json
import sys
import urllib.request

import websocket

PUERTO = 8088


def conectar():
    paginas = json.load(urllib.request.urlopen(f"http://localhost:{PUERTO}/json", timeout=5))
    pagina = next(p for p in paginas if p["title"] == "VELABODY Builder")
    return websocket.create_connection(pagina["webSocketDebuggerUrl"], timeout=600)


def evaluar_js(ws, expr: str, asincrono=False):
    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                        "params": {"expression": expr, "awaitPromise": asincrono, "returnByValue": True}}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == 1:
            res = r.get("result", {})
            if "exceptionDetails" in res:
                return "✖ " + json.dumps(res["exceptionDetails"], ensure_ascii=False)[:800]
            return res.get("result", {}).get("value")


def evaluar_jsx(ws, codigo: str):
    expr = ("new Promise(function(ok){ window.__adobe_cep__.evalScript(" + json.dumps(codigo) +
            ", function(r){ ok(r); }); })")
    return evaluar_js(ws, expr, asincrono=True)


if __name__ == "__main__":
    modo = sys.argv[1]
    ws = conectar()
    if modo == "js":
        out = evaluar_js(ws, sys.argv[2])
    elif modo == "jsx":
        out = evaluar_jsx(ws, sys.argv[2])
    else:
        out = evaluar_js(ws, "document.getElementById('log').textContent + '\\n[ruta] ' + document.getElementById('ruta').value")
    sys.stdout.reconfigure(encoding="utf-8")
    print(out)
