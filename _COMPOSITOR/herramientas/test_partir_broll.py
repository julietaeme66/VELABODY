"""Pruebas de velabody.partir_broll_largo (B-roll largo cortado cada 3-4 s) y de la regla del B-roll sin
movimientos bruscos (broll_visual.parte_sin_sacudidas, velabody.broll_sin_sacudidas), con clips simulados."""
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_HERRAMIENTAS"))
import broll_visual  # noqa: E402
import numpy as np  # noqa: E402
import velabody  # noqa: E402

RT = {"broll_max_s": 4.0, "broll_plano_s": 3.5, "broll_cerrado_zoom": 1.5, "broll_distinto": 0.6}


def visual_falso(otra, brusco=lambda ruta, t0, t1, cache=None: 0.0):
    """broll_visual con respuestas fijas: `otra` es el inicio de la otra parte (o None si no hay); `brusco`
    da el movimiento de cada tramo, y el arranque sin sacudidas es el quieto más cercano (cada 0,5 s)."""
    def sin_sacudidas(ruta, preferido, dur, largo, umbral, usados=(), cache=None, radio=None):
        if brusco(ruta, preferido, preferido + dur) < umbral:
            return preferido
        quietos = [s / 2 for s in range(int(largo * 2)) if s / 2 + dur <= largo and brusco(ruta, s / 2, s / 2 + dur) < umbral
                   and not any(s / 2 < u1 and s / 2 + dur > u0 for u0, u1 in usados)
                   and (radio is None or abs(s / 2 - preferido) <= radio)]
        return min(quietos, key=lambda s: abs(s - preferido)) if quietos else preferido
    def otra_parte(ruta, dur, largo, anterior, usados, umbral, cache=None, brusco_max=None, menos_brusco=False):
        if otra is None or menos_brusco or brusco_max is None or brusco(ruta, otra, otra + dur) < brusco_max:
            return otra
        return None
    return types.SimpleNamespace(otra_parte=otra_parte, foco_cercano=lambda *a, **k: (0.6, 0.4), brusco=brusco,
                                 parte_sin_sacudidas=sin_sacudidas)


class TestPartirBroll(unittest.TestCase):
    def tearDown(self):
        sys.modules["broll_visual"] = broll_visual

    def partir(self, otra, graficos=(), dur=9.6, sin_cola=False, brusco=None):
        sys.modules["broll_visual"] = visual_falso(otra, *([brusco] if brusco else []))
        broll = [{"clip": "B", "in": 10.0, "out": 10.0 + dur, "t": 5.0, "foco_x": 0.5, "foco_y": 0.5, "zoom": 1.0, "bloque": 2}]
        palabras = [{"i": 5.0 + 0.4 * k, "f": 5.3 + 0.4 * k} for k in range(30)]
        # sin_cola: el archivo termina donde termina el primer plano, no hay cómo seguir de corrido
        medio = lambda c: {"ruta": "B.mp4", "duracion": 13.5 if sin_cola else 40.0}
        notas = []
        velabody.partir_broll_largo(RT, broll, palabras, list(graficos), [], medio, 30, notas, None)
        return broll, notas

    def test_corta_en_planos_de_3_a_4_s_sin_huecos(self):
        broll, _ = self.partir(otra=30.0)
        self.assertEqual(len(broll), 3)
        fin = lambda b: b["t"] + b["out"] - b["in"]
        for x, y in zip(broll, broll[1:]):
            self.assertAlmostEqual(fin(x), y["t"], places=3)
        self.assertTrue(all(2.0 <= b["out"] - b["in"] <= 4.5 for b in broll))
        self.assertAlmostEqual(fin(broll[-1]), 5.0 + 9.6, places=3)

    def test_alterna_otra_parte_y_plano_cerrado(self):
        broll, _ = self.partir(otra=30.0)
        self.assertEqual(broll[1]["zoom"], 1.5)                       # primero, el mismo momento más cerca
        self.assertAlmostEqual(broll[1]["in"], broll[0]["out"], places=3)
        self.assertEqual(broll[2]["in"], 30.0)                        # después, otra parte en plano abierto
        self.assertEqual(broll[2]["zoom"], 1.0)

    def test_sin_plano_cerrado_posible_va_a_otra_parte(self):
        broll, _ = self.partir(otra=30.0, dur=9.6, sin_cola=True)
        self.assertEqual(broll[1]["in"], 30.0)

    def test_sin_otra_parte_va_al_plano_cerrado(self):
        broll, _ = self.partir(otra=None)
        self.assertEqual(broll[1]["zoom"], 1.5)
        self.assertAlmostEqual(broll[1]["in"], broll[0]["out"], places=3)

    def test_no_corta_a_mitad_de_un_grafico(self):
        broll, _ = self.partir(otra=30.0, graficos=[{"t": 6.0, "fin": 11.0}])
        self.assertTrue(all(not 6.0 < b["t"] < 11.0 for b in broll))

    def test_plano_cerrado_con_sacudida_arranca_donde_la_camara_esta_quieta(self):
        # lo que sigue al primer plano (desde ~13 s) tiene un barrido hasta los 15,5 s: el plano cerrado arranca ahí
        broll, _ = self.partir(otra=30.0, brusco=lambda ruta, t0, t1, cache=None: 80.0 if t0 < 15.5 and t1 > 13.5 else 0.0)
        self.assertEqual(broll[1]["zoom"], 1.5)
        self.assertEqual(broll[1]["in"], 15.5)

    def test_plano_cerrado_lejos_no_va_pasa_a_otra_parte(self):
        # quieto recién a los 17 s: más de 3 s del momento original, ya no mostraría lo mismo
        broll, _ = self.partir(otra=30.0, brusco=lambda ruta, t0, t1, cache=None: 80.0 if t0 < 17 and t1 > 13.5 else 0.0)
        self.assertEqual(broll[1]["in"], 30.0)
        self.assertEqual(broll[1]["zoom"], 1.0)

    def test_clip_que_se_mueve_entero_usa_la_otra_parte_menos_brusca(self):
        broll, notas = self.partir(otra=30.0, brusco=lambda ruta, t0, t1, cache=None: 60.0 if t0 >= 29 else 80.0)
        self.assertEqual(broll[1]["in"], 30.0)
        self.assertTrue(any("menos brusco" in n for n in notas))

    def test_sin_nada_menos_brusco_no_corta(self):
        # cortar a otro tramo igual de sacudido no mejora nada: el plano sigue de corrido
        broll, _ = self.partir(otra=30.0, brusco=lambda ruta, t0, t1, cache=None: 80.0)
        self.assertEqual(len(broll), 1)

    def test_corto_no_se_toca(self):
        broll, _ = self.partir(otra=30.0, dur=3.9)
        self.assertEqual(len(broll), 1)


class TestSinSacudidas(unittest.TestCase):
    """Velocidad de cámara armada a mano: quieto, con un barrido entre 4 y 6 s, y quieto otra vez."""
    RUTA = "falso.mp4"

    def setUp(self):
        t = np.arange(1, 300) * broll_visual.PASO_MOV                  # 0,1 a 29,9 s
        v = np.where((t > 4) & (t < 6), 120.0, 5.0)
        broll_visual._mov[self.RUTA] = (t, v)

    def tearDown(self):
        broll_visual._mov.pop(self.RUTA, None)

    def test_tramo_quieto_queda_donde_lo_puso_el_plan(self):
        self.assertEqual(broll_visual.parte_sin_sacudidas(self.RUTA, 10.0, 3.0, 30.0, 35), 10.0)

    def test_tramo_con_barrido_se_corre_al_mas_cercano_sin_sacudidas(self):
        s = broll_visual.parte_sin_sacudidas(self.RUTA, 4.5, 3.0, 30.0, 35)
        self.assertLess(broll_visual.brusco(self.RUTA, s, s + 3.0), 35)
        self.assertAlmostEqual(s, 6.0, delta=0.15)                       # justo después del barrido

    def test_no_pisa_lo_que_ya_usa_otro_broll(self):
        s = broll_visual.parte_sin_sacudidas(self.RUTA, 4.5, 3.0, 30.0, 35, usados=[(5.5, 10.0)])
        self.assertTrue(s + 3.0 <= 5.5 or s >= 10.0)
        self.assertLess(broll_visual.brusco(self.RUTA, s, s + 3.0), 35)

    def test_builder_mueve_el_broll_y_avisa(self):
        broll = [{"clip": "B", "in": 4.5, "out": 7.5, "t": 2.0, "zoom": 1.0}]
        notas = []
        velabody.broll_sin_sacudidas(broll, lambda c: {"ruta": self.RUTA, "duracion": 30.0}, notas, None)
        self.assertAlmostEqual(broll[0]["in"], 6.0, delta=0.15)
        self.assertAlmostEqual(broll[0]["out"] - broll[0]["in"], 3.0, places=3)
        self.assertIn("movimiento brusco", notas[0])


if __name__ == "__main__":
    unittest.main()
