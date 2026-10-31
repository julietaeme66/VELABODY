"""Pruebas de velabody.numeros_en_cifras: en los gráficos los números van en cifras (regla del 30/10)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_HERRAMIENTAS"))
import velabody  # noqa: E402


class TestNumerosEnCifras(unittest.TestCase):
    def test_numero_con_letras_pasa_a_cifra(self):
        self.assertEqual(velabody.numeros_en_cifras("CINCO COSAS"), "5 COSAS")
        self.assertEqual(velabody.numeros_en_cifras("DIECISÉIS SESIONES"), "16 SESIONES")
        self.assertEqual(velabody.numeros_en_cifras("VEINTITRÉS"), "23")

    def test_decena_y_unidad(self):
        self.assertEqual(velabody.numeros_en_cifras("TREINTA Y CINCO MINUTOS"), "35 MINUTOS")
        self.assertEqual(velabody.numeros_en_cifras("CUARENTA Y UNO"), "41")
        self.assertEqual(velabody.numeros_en_cifras("TREINTA"), "30")

    def test_articulos_y_texto_sin_numeros_no_cambian(self):
        for t in ("UNA RECOMENDACIÓN", "QUE NO SABÍAS", "CORTE 3D", "REPORTE POR QR"):
            self.assertEqual(velabody.numeros_en_cifras(t), t)


if __name__ == "__main__":
    unittest.main()
