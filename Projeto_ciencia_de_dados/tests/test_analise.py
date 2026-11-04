"""Verifica invariantes do domínio e limites temporais da avaliação."""
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analise


class TestAnalise(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        analise.gerar_dados(cls.root)
        cls.base, cls.acoes, cls.itens, cls.doacoes, cls.audit = analise.preparar_dados(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_balancos_fisicos(self):
        b = self.base
        np.testing.assert_allclose(b.estoque_inicial+b.doado-b.consumido, b.estoque_final, atol=.011)
        np.testing.assert_allclose(b.demanda-b.consumido, b.demanda_nao_atendida, atol=.011)
        self.assertTrue((b.estoque_final >= 0).all())
        for _, grupo in b.groupby("item_id"):
            np.testing.assert_allclose(grupo.estoque_inicial.iloc[1:], grupo.estoque_final.iloc[:-1], atol=.011)

    def test_qualidade_remove_exatamente_cinco_erros_conhecidos(self):
        self.assertEqual(self.audit.removidas.tolist(), [1, 1, 1, 1, 1])
        self.assertEqual(len(self.doacoes), 432)
        self.assertTrue(self.doacoes.doacao_id.is_unique)
        self.assertTrue(self.doacoes.item_id.isin(self.itens.item_id).all())

    def test_alvo_futuro_nao_inventa_ultimo_mes(self):
        for _, grupo in self.base.groupby("item_id"):
            np.testing.assert_array_equal(grupo.alvo_falta_proximo_mes.iloc[:-1], grupo.houve_falta.iloc[1:])
            self.assertTrue(pd.isna(grupo.alvo_falta_proximo_mes.iloc[-1]))
            np.testing.assert_allclose(grupo.demanda_media_3m.iloc[2:], grupo.demanda.rolling(3).mean().iloc[2:])

    def test_cortes_pelo_mes_do_alvo(self):
        treino, val, teste = analise.separar_temporal(self.base)
        self.assertEqual((len(treino), len(val), len(teste)), (252, 72, 72))
        self.assertLess(treino.mes_alvo.max(), val.mes_alvo.min())
        self.assertLess(val.mes_alvo.max(), teste.mes_alvo.min())
        self.assertTrue((teste.mes < teste.mes_alvo).all())
        self.assertEqual(teste.mes_alvo.min(), "2025-07")
        self.assertEqual(teste.mes_alvo.max(), "2025-12")
        self.assertNotIn("alvo_falta_proximo_mes", analise.FEATURES)
        self.assertNotIn("demanda_nao_atendida", analise.FEATURES)

    def test_simulacao_reproduzivel(self):
        antes = (self.root / "dados/brutos/doacoes.csv").read_bytes()
        analise.gerar_dados(self.root)
        self.assertEqual(antes, (self.root / "dados/brutos/doacoes.csv").read_bytes())


if __name__ == "__main__":
    unittest.main()
