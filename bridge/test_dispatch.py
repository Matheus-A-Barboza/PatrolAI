import tempfile
import unittest
from pathlib import Path
from dispatch_records import extract_query, resolve

class TestRecords(unittest.TestCase):
    def test_plate(self):
        self.assertEqual(extract_query('COPOM, consultar placa ABC1D23, QSL?'),('plate','ABC1D23'))
        self.assertEqual(extract_query('verificar placa ABC-1234'),('plate','ABC1234'))
    def test_person(self):
        self.assertEqual(extract_query('Consultar nome de João da Silva, por favor'),('person','João da Silva'))
    def test_person_variations(self):
        examples = [
            'COPOM, verifica o João da Silva, por favor',
            'Solicito pesquisar o cidadão João da Silva. QSL',
            'COPOM, consulta de antecedentes do indivíduo João da Silva',
            'Consultar nome de João da Silva, por gentileza',
        ]
        for sentence in examples:
            with self.subTest(sentence=sentence):
                self.assertEqual(extract_query(sentence), ('person','João da Silva'))
    def test_incomplete_person(self):
        self.assertIsNone(extract_query('COPOM consultar indivíduo'))
    def test_conversation(self):
        self.assertIsNone(extract_query('Iniciando patrulhamento em Davis'))
    def test_repeatable(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            a=resolve(base,'plate','ABC1D23'); b=resolve(base,'plate','ABC1D23')
            self.assertEqual(a,b)
            self.assertIn('simulad',a.lower())
            self.assertIn('Não há acesso',resolve(base,'person','João da Silva'))
if __name__=='__main__': unittest.main()
