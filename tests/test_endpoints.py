import json
import os
import shutil
import tempfile
import unittest

from kyberReserve.endpoints import EndpointItem, ReserveEndpoints, load_endpoints


class TestEndpoints(unittest.TestCase):
    def setUp(self):
        # create temporary directory and test JSON file
        self.tempdir = tempfile.mkdtemp()
        self.json_file = self._write_test_json()

    def tearDown(self):
        # remove temporary directory
        shutil.rmtree(self.tempdir)

    def _write_test_json(self):
        data = [
            {
                "base": "base",
                "url": "http://example.com",
                "endpoints": [
                    {
                        "path": "endpoint1",
                        "methods": ["GET", "POST"],
                        "secured": True,
                        "options": {"opt1": "val1"},
                        "params": {"param1": "val2"},
                        "description": "Test endpoint1",  # trailing comma for Black
                    },
                    {
                        "path": "endpoint2",
                        "sub_base": "sub",
                        "methods": ["DELETE"],
                        "secured": False,
                        "options": {},
                        "params": {},
                        "description": "Test endpoint2",  # trailing comma for Black
                    },
                ],
            },
        ]
        path = os.path.join(self.tempdir, "test_endpoints.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_load_endpoints_creates_items(self):
        endpoints = load_endpoints(self.json_file)
        self.assertIn("base_endpoint1", endpoints)
        self.assertIn("base_sub_endpoint2", endpoints)

        item1 = endpoints["base_endpoint1"]
        self.assertIsInstance(item1, EndpointItem)
        self.assertEqual(item1.path, "endpoint1")
        self.assertEqual(item1.base, "base")
        self.assertEqual(item1.sub_base, "")
        self.assertEqual(item1.url, "http://example.com")
        self.assertEqual(item1.methods, ["GET", "POST"])
        self.assertTrue(item1.secured)
        self.assertEqual(item1.options, {"opt1": "val1"})
        self.assertEqual(item1.params, {"param1": "val2"})
        self.assertEqual(item1.description, "Test endpoint1")

        item2 = endpoints["base_sub_endpoint2"]
        self.assertEqual(item2.sub_base, "sub")
        self.assertEqual(item2.methods, ["DELETE"])
        self.assertFalse(item2.secured)

    def test_full_path_and_full_url_and_host_base(self):
        endpoints = load_endpoints(self.json_file)
        item1 = endpoints["base_endpoint1"]
        # full_path without options
        self.assertEqual(item1.full_path(), "base/endpoint1")
        # full_path with options
        opts = {"a": "1", "b": "2"}
        path_with_opts = item1.full_path(opts)
        self.assertIn(
            path_with_opts,
            ("base/endpoint1?a=1&b=2", "base/endpoint1?b=2&a=1"),
        )
        # full_url
        self.assertEqual(item1.full_url(), "http://example.com/base/endpoint1")
        prefix = "http://example.com/base/endpoint1?"
        self.assertTrue(item1.full_url(opts).startswith(prefix))
        # host_base
        self.assertEqual(item1.host_base, "http://example.com/base")

        item2 = endpoints["base_sub_endpoint2"]
        # full_path uses sub_base
        self.assertEqual(item2.full_path(), "base/sub/endpoint2")
        # full_url with sub_base
        self.assertEqual(item2.full_url(), "http://example.com/base/sub/endpoint2")
        # host_base includes sub_base
        self.assertEqual(item2.host_base, "http://example.com/base/sub")

    def test_to_dict_and_repr(self):
        endpoints = load_endpoints(self.json_file)
        item1 = endpoints["base_endpoint1"]
        expected_dict = {
            "path": "endpoint1",
            "base": "base",
            "sub_base": "",
            "url": "http://example.com",
            "methods": ["GET", "POST"],
            "secured": True,
            "options": {"opt1": "val1"},
            "params": {"param1": "val2"},
            "description": "Test endpoint1",
        }
        self.assertEqual(item1.to_dict(), expected_dict)
        expected_repr = (
            "EndpointItem(base/endpoint1, http://example.com, ['GET', 'POST'], "
            "{'opt1': 'val1'}, {'param1': 'val2'}, Test endpoint1)"
        )
        self.assertEqual(repr(item1), expected_repr)

    def test_reserve_endpoints_uses_load(self):
        reserve = ReserveEndpoints(self.json_file)
        loaded = load_endpoints(self.json_file)
        self.assertEqual(set(reserve.endpoints.keys()), set(loaded.keys()))
        for key, item in reserve.endpoints.items():
            self.assertIsInstance(item, EndpointItem)
            self.assertEqual(item.path, loaded[key].path)


if __name__ == "__main__":
    unittest.main()
