import unittest
from vehicle_context import wants_near_vehicle, vehicle_response

class VehicleTests(unittest.TestCase):
    def test_nearby(self):
        self.assertTrue(wants_near_vehicle('COPOM, consultar a placa do veículo que estou abordando'))
        self.assertTrue(wants_near_vehicle('Verifica o carro aqui na frente, COPOM'))
        self.assertFalse(wants_near_vehicle('Consultar placa ABC1D23'))
    def test_snapshot(self):
        response=vehicle_response({'found':True,'plate':'ABC 1234','model':'Sultan','distance_m':4.2})
        self.assertIn('ABC1234',response)
        self.assertIn('Sultan',response)
        self.assertIn('Sem consulta',response)
    def test_no_target(self):
        self.assertIn('Nenhum veículo',vehicle_response({'found':False}))
if __name__ == '__main__': unittest.main()
