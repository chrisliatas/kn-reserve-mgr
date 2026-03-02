import unittest
from unittest.mock import MagicMock

from kyberReserve.endpoints import EndpointItem
from kyberReserve.reserveClient import ReserveClient


class TestEwmaVolatility(unittest.TestCase):
    def _build_client(self) -> ReserveClient:
        client: ReserveClient = ReserveClient.__new__(ReserveClient)
        endpoint_key = "price-volatility-v4_v4_ewma-volatility"
        client.endpoints = {
            endpoint_key: EndpointItem(
                path="ewma-volatility",
                base="price-volatility-v4",
                sub_base="v4",
                url="",
                methods=["GET"],
                secured=True,
                options={},
                params={"pairs": "str", "volatility_period_second": "int"},
                description="test",
            )
        }
        client.requestGET = MagicMock(return_value={"success": {"ok": True}})
        return client

    def test_get_ewma_volatility_success_single_pair(self) -> None:
        client = self._build_client()
        resp = client.get_ewma_volatility(["eth-usdt"], 100)

        self.assertEqual(resp, {"success": {"ok": True}})
        client.requestGET.assert_called_once_with(
            "price-volatility-v4/v4/ewma-volatility",
            params={"pairs": "eth-usdt", "volatility_period_second": 100},
        )

    def test_get_ewma_volatility_success_multi_pair(self) -> None:
        client = self._build_client()
        resp = client.get_ewma_volatility(["eth-usdt", "btc-usdt"], 100)

        self.assertEqual(resp, {"success": {"ok": True}})
        client.requestGET.assert_called_once_with(
            "price-volatility-v4/v4/ewma-volatility",
            params={"pairs": "eth-usdt,btc-usdt", "volatility_period_second": 100},
        )

    def test_get_ewma_volatility_invalid_period(self) -> None:
        for invalid_period in [0, -1, True, "100"]:
            with self.subTest(invalid_period=invalid_period):
                client = self._build_client()
                resp = client.get_ewma_volatility(["eth-usdt"], invalid_period)
                self.assertEqual(
                    resp,
                    {"failed": "volatility_period_second must be a positive integer"},
                )
                client.requestGET.assert_not_called()

    def test_get_ewma_volatility_invalid_pairs(self) -> None:
        invalid_pairs = [[], "eth-usdt", [123], [""], ["  "]]
        for pairs in invalid_pairs:
            with self.subTest(pairs=pairs):
                client = self._build_client()
                resp = client.get_ewma_volatility(pairs, 100)  # type: ignore[arg-type]
                if pairs == [] or pairs == "eth-usdt":
                    self.assertEqual(
                        resp, {"failed": "pairs must be a non-empty list[str]"}
                    )
                else:
                    self.assertEqual(
                        resp, {"failed": "pairs must contain non-empty strings"}
                    )
                client.requestGET.assert_not_called()


if __name__ == "__main__":
    unittest.main()
