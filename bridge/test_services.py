import unittest
from service_intent import parse_service,service_reply
class Tests(unittest.TestCase):
 def test_ambulancia(self): self.assertEqual(parse_service("COPOM, solicito ambulância na minha localização")["service"], "ambulance")
 def test_conducao(self): self.assertEqual(parse_service("Central, solicito uma viatura para condução do indivíduo")["service"], "prisoner_transport")
 def test_guincho(self): self.assertEqual(parse_service("Preciso de guincho para remoção do veículo")["service"], "tow")
 def test_iml(self): self.assertEqual(parse_service("COPOM, acione o IML no local")["service"], "coroner")
 def test_nao_acione(self): self.assertIsNone(parse_service("O que é um guincho?"))
 def test_confirma(self): self.assertIn("encaminhada",service_reply("ambulance", True))
if __name__=='__main__': unittest.main()
