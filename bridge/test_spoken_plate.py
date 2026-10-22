import tempfile
import unittest
from pathlib import Path
from vehicle_context import explicit_plate, plate_spoken_response
from dispatch_records import resolve

class SpokenPlateTests(unittest.TestCase):
    def test_brazilian_patterns(self):
        self.assertEqual(explicit_plate('QAP COPOM, verifica veículo placa QBJ32O90'), 'QBJ32O90')
        self.assertEqual(explicit_plate('Consultar placa ABC1D23 QSL'), 'ABC1D23')
        self.assertEqual(explicit_plate('Pesquisa da placa ABC-1234'), 'ABC1234')
    def test_without_explicit_plate(self):
        self.assertIsNone(explicit_plate('Consultar o veículo que estou abordando'))
    def test_match_real_vehicle(self):
        with tempfile.TemporaryDirectory() as d:
            result=plate_spoken_response('QBJ32O90', {'found':True,'plate':'QBJ32O90','model':'Sultan','distance_m':3},Path(d),resolve)
            self.assertIn('Sultan', result)
            self.assertIn('confere',result)
    def test_mismatch_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as d:
            result=plate_spoken_response('QBJ32O90', {'found':True,'plate':'ABC1234','model':'Sultan'},Path(d),resolve)
            self.assertIn('não confere',result)
            self.assertIn('simulad', result.lower())
    def test_without_near_vehicle_is_simulated(self):
        with tempfile.TemporaryDirectory() as d:
            result=plate_spoken_response('QBJ32O90', {'found':False},Path(d),resolve)
            self.assertIn('simulad', result.lower())

if __name__=='__main__':
    unittest.main()
