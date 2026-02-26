import unittest
from unittest.mock import MagicMock

from kyberReserve.endpoints import EndpointItem
from kyberReserve.reserveClient import ReserveClient


class TestRfqParamsLinear(unittest.TestCase):
    def test_get_rfq_params_linear_calls_expected_endpoint(self) -> None:
        client: ReserveClient = ReserveClient.__new__(ReserveClient)
        endpoint_key = "setting-v4_v4_rfq-params-linear"
        client.endpoints = {
            endpoint_key: EndpointItem(
                path="rfq-params-linear",
                base="setting-v4",
                sub_base="v4",
                url="",
                methods=["GET"],
                secured=True,
                options={},
                params={},
                description="test",
            )
        }

        expected = {"success": {"ok": True}}
        client.requestGET = MagicMock(return_value=expected)

        resp = client.get_rfq_params_linear()

        self.assertEqual(resp, expected)
        client.requestGET.assert_called_once_with("setting-v4/v4/rfq-params-linear")


if __name__ == "__main__":
    unittest.main()
