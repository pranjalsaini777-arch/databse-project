import unittest
from unittest.mock import patch
import app as module
class AppChecks(unittest.TestCase):
    def setUp(self):
        self.c=module.app.test_client(); self.h={'X-App-Token':module.TOKEN}
    def test_home_and_assets(self):
        self.assertEqual(self.c.get('/').status_code,200)
        for p in ['/static/style.css','/static/app.js']:
            with self.c.get(p) as response:
                self.assertEqual(response.status_code,200)
    def test_disconnected_does_not_fabricate_data(self):
        self.assertFalse(self.c.get('/api/health').json['connected'])
        for p in ['dashboard','shipments','inventory','tasks','transport','movements','reports/0']:
            self.assertEqual(self.c.get('/api/'+p).status_code,400)
    def test_mutations_require_token(self):
        self.assertEqual(self.c.post('/api/connect',json={}).status_code,403)
    def test_credentials_required(self):
        self.assertEqual(self.c.post('/api/connect',json={},headers=self.h).status_code,400)
    def test_local_host_only(self):
        self.assertEqual(self.c.get('/',headers={'Host':'attacker.example'}).status_code,403)
    def test_codespace_host(self):
        with patch.dict(module.os.environ, {'CODESPACES':'true','CODESPACE_NAME':'test-space','GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN':'app.github.dev'}):
            self.assertEqual(self.c.get('/',headers={'Host':'test-space-5000.app.github.dev'}).status_code,200)
            self.assertEqual(self.c.get('/',headers={'Host':'other-space-5000.app.github.dev'}).status_code,403)
            self.assertEqual(self.c.post('/api/disconnect',json={},headers={'Host':'test-space-5000.app.github.dev'}).status_code,403)
    def test_reports_match_original(self):
        reports=self.c.get('/api/reports').json
        self.assertEqual(len(reports),10)
        self.assertEqual(self.c.get('/api/reports/99').status_code,400)
    def test_invalid_quantity_rejected_before_database(self):
        for q in [0,'NaN','Infinity','0.0001','invalid']:
            r=self.c.post('/api/movements',json={'task_id':7,'bin_id':1,'product_id':1,'lot_code':'LOT_A','quantity_change':q},headers=self.h)
            self.assertEqual(r.status_code,400,q)
    def test_terminal_status_cannot_reopen(self):
        r=self.c.post('/api/shipments/1/status',json={'expected':'DELIVERED','status':'IN_TRANSIT'},headers=self.h)
        self.assertEqual(r.status_code,400)
if __name__=='__main__': unittest.main()
