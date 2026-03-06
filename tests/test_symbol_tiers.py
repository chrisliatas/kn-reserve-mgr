import unittest
from unittest.mock import MagicMock

from kyberReserve.endpoints import EndpointItem
from kyberReserve.reserveClient import ReserveClient


class TestSymbolTiers(unittest.TestCase):
    def test_get_symbol_tiers_calls_expected_endpoint(self) -> None:
        client: ReserveClient = ReserveClient.__new__(ReserveClient)
        endpoint_key = "price-volatility-v4_v4_symbol-tiers"
        client.endpoints = {
            endpoint_key: EndpointItem(
                path="symbol-tiers",
                base="price-volatility-v4",
                sub_base="v4",
                url="",
                methods=["GET"],
                secured=True,
                options={},
                params={},
                description="test",
            )
        }

        expected = {"success": {"tiers": {"ETH-USDT": "A"}}}
        client.requestGET = MagicMock(return_value=expected)

        resp = client.get_symbol_tiers()

        self.assertEqual(resp, expected)
        client.requestGET.assert_called_once_with("price-volatility-v4/v4/symbol-tiers")


if __name__ == "__main__":
    unittest.main()
