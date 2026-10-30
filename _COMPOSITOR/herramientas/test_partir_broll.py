"""Pruebas de velabody.partir_broll_largo (B-roll largo cortado cada 3-4 s) con un clip simulado."""
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_HERRAMIENTAS"))
import velabody  # noqa: E402

RT = {"broll_max_s": 4.0, "broll_plano_s": 3.5, "broll_cerrado_zoom": 1.5, "broll_distinto": 0.6}


def visual_falso(otra):
    """broll_visual con respuestas fijas: `otra` es el inicio de la otra parte (o None si no hay)."""
    return types.SimpleNamespace(otra_parte=lambda *a, **k: otra, foco_cercano=lambda *a, **k: (0.6, 0.4))


class TestPartirBroll(unittest.TestCase):
    def partir(self, otra, graficos=(), dur=9.6, sin_cola=False):
        sys.modules["broll_visual"] = visual_falso(otra)
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

    def test_corto_no_se_toca(self):
        broll, _ = self.partir(otra=30.0, dur=3.9)
        self.assertEqual(len(broll), 1)


if __name__ == "__main__":
    unittest.main()
