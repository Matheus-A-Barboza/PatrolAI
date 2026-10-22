import unittest
from backup_intent import parse_backup_request, backup_reply

class BackupTests(unittest.TestCase):
    def test_local_code2(self):
        self.assertEqual(parse_backup_request('QAP COPOM, solicito apoio na minha localização')['code'], 2)
    def test_local_code3(self):
        self.assertEqual(parse_backup_request('COPOM preciso de reforço urgente em código 3')['code'], 3)
    def test_negated(self):
        self.assertIsNone(parse_backup_request('COPOM não preciso de apoio'))
    def test_general_question(self):
        self.assertIsNone(parse_backup_request('Qual é a política de apoio?'))
    def test_acks(self):
        self.assertIn('encaminhada', backup_reply(True,2))
        self.assertIn('Não foi possível',backup_reply(False,3))
if __name__=='__main__': unittest.main()
