"""Pruebas del lector de brief en PDF (preparar_brief.leer_brief_pdf) con el brief real de los Videos 6 a 16.
Si el PDF no está en esta compu (_RECURSOS/referencias), se saltean."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_HERRAMIENTAS"))
import preparar_brief  # noqa: E402
import velabody  # noqa: E402

PDF = next((velabody.RAIZ / "_RECURSOS" / "referencias").glob("Brief de edición*.pdf"), None) \
    if (velabody.RAIZ / "_RECURSOS" / "referencias").exists() else None


@unittest.skipUnless(PDF, "no está el brief en PDF en _RECURSOS/referencias")
class TestBriefPdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.videos, cls.lineamientos = preparar_brief.leer_brief_pdf(PDF)
        cls.por_numero = {v["video"]: v for v in cls.videos}

    def test_los_11_videos_con_su_titulo(self):
        self.assertEqual(sorted(self.por_numero), list(range(6, 17)))
        # título partido en dos renglones en el PDF
        self.assertTrue(self.por_numero[9]["titulo"].endswith("con el sistema SMART"))

    def test_tabla_que_sigue_en_otra_pagina(self):
        # la ficha del Video 8 empieza al pie de una página y sigue en la siguiente: 3 hooks + bloques 2 a 8
        bloques = [b["bloque"] for b in self.por_numero[8]["bloques"]]
        self.assertEqual(bloques, ["Hook 1", "Hook 2", "Hook 3"] + [str(n) for n in range(2, 9)])

    def test_cada_link_en_su_celda(self):
        b2 = next(b for b in self.por_numero[8]["bloques"] if b["bloque"] == "2")
        self.assertEqual([x["texto"] for x in b2["links_clip"]], ["Clip"])
        self.assertTrue(b2["links_insert"])
        ids = {x["id"] for b in self.por_numero[8]["bloques"] for x in b["links_insert"] + b["links_clip"]}
        self.assertIn("1koIuSC-UrPs_SZ1di3g9xsV5ZbIYqPBJ", ids)          # C3831, bajado para el ADS14

    def test_extras_fuera_de_la_tabla(self):
        extras = self.por_numero[9]["extras"]
        self.assertEqual([x["texto"] for x in extras[0]["links"]], ["Insert A", "Insert B"])

    def test_lineamientos_generales(self):
        self.assertIn("primeros 5 segundos", self.lineamientos)
        self.assertIn("Duración", self.lineamientos)
        self.assertNotIn("Video 6 —", self.lineamientos)


if __name__ == "__main__":
    unittest.main()
