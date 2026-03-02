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


class TestRfqParamsLinearChangelogs(unittest.TestCase):
    def _build_client(self) -> ReserveClient:
        client: ReserveClient = ReserveClient.__new__(ReserveClient)
        endpoint_key = "setting-v4_v4_rfq-params-linear-changelogs"
        client.endpoints = {
            endpoint_key: EndpointItem(
                path="rfq-params-linear-changelogs",
                base="setting-v4",
                sub_base="v4",
                url="",
                methods=["GET"],
                secured=True,
                options={},
                params={"from": "int (s)", "to": "int (s)"},
                description="test",
            )
        }
        client.requestGET = MagicMock(return_value={"success": {"ok": True}})
        return client

    def test_get_rfq_params_linear_changelogs_success(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = 1772418548

        resp = client.get_rfq_params_linear_changelogs(from_time, to_time)

        self.assertEqual(resp, {"success": {"ok": True}})
        client.requestGET.assert_called_once_with(
            "setting-v4/v4/rfq-params-linear-changelogs",
            params={"from": from_time, "to": to_time},
        )

    def test_get_rfq_params_linear_changelogs_success_at_168h_boundary(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = from_time + 168 * 3600

        resp = client.get_rfq_params_linear_changelogs(from_time, to_time)

        self.assertEqual(resp, {"success": {"ok": True}})
        client.requestGET.assert_called_once_with(
            "setting-v4/v4/rfq-params-linear-changelogs",
            params={"from": from_time, "to": to_time},
        )

    def test_get_rfq_params_linear_changelogs_invalid_range(self) -> None:
        for from_time, to_time in [(1772414948, 1772414948), (1772418548, 1772414948)]:
            with self.subTest(from_time=from_time, to_time=to_time):
                client = self._build_client()
                resp = client.get_rfq_params_linear_changelogs(from_time, to_time)
                self.assertEqual(
                    resp, {"failed": "from_time must be < to_time (seconds)"}
                )
                client.requestGET.assert_not_called()

    def test_get_rfq_params_linear_changelogs_invalid_types(self) -> None:
        invalid_cases = [
            ("1772414948", 1772418548),
            (None, 1772418548),
            (True, 1772418548),
            (1772414948, "1772418548"),
            (1772414948, None),
            (1772414948, True),
        ]
        for from_time, to_time in invalid_cases:
            with self.subTest(from_time=from_time, to_time=to_time):
                client = self._build_client()
                resp = client.get_rfq_params_linear_changelogs(from_time, to_time)
                self.assertEqual(
                    resp,
                    {"failed": "from_time and to_time must be integers (seconds)"},
                )
                client.requestGET.assert_not_called()

    def test_get_rfq_params_linear_changelogs_exceeds_168h(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = from_time + 168 * 3600 + 1

        resp = client.get_rfq_params_linear_changelogs(from_time, to_time)

        self.assertEqual(
            resp,
            {
                "failed": (
                    "invalid time range: duration exceeds max allowed range "
                    "of 168h0m0s"
                )
            },
        )
        client.requestGET.assert_not_called()


if __name__ == "__main__":
    unittest.main()
