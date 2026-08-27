"""Test per /api/hierarchy. Integrazione: usa il client Flask di test contro
il vero endpoint SPARQL configurato in .env (nessun mock, come il resto
dell'app). Esegui con: python3 -m unittest tests/test_hierarchy.py
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module


class HierarchyEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def _get_formal_constraint_scheme(self):
        resp = self.client.get('/api/hierarchy')
        self.assertEqual(resp.status_code, 200)
        return json.loads(resp.data)

    def test_json_serializable(self):
        data = self._get_formal_constraint_scheme()
        # Se e' stato deserializzato da resp.data senza eccezioni, e'
        # gia' valido JSON; verifichiamo anche il round-trip di ri-encoding.
        json.dumps(data)

    def test_node_count(self):
        data = self._get_formal_constraint_scheme()

        def count(node):
            return 1 + sum(count(c) for c in node['children'])

        total = sum(count(c) for c in data['children'])
        self.assertEqual(total, 155)

    def test_max_depth(self):
        data = self._get_formal_constraint_scheme()

        def max_depth(node):
            if not node['children']:
                return 1
            return 1 + max(max_depth(c) for c in node['children'])

        depth = max((max_depth(c) for c in data['children']), default=0)
        self.assertEqual(depth, 3)

    def test_no_cycles(self):
        data = self._get_formal_constraint_scheme()

        def walk(node, ancestors):
            self.assertNotIn(node['uri'], ancestors,
                              f"ciclo rilevato: {node['uri']} e' un proprio antenato")
            for child in node['children']:
                walk(child, ancestors | {node['uri']})

        for root in data['children']:
            walk(root, frozenset())


if __name__ == '__main__':
    unittest.main()
