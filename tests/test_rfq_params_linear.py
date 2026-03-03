import unittest
import csv
import os
import tempfile
from unittest.mock import MagicMock, call, patch

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
    max_window_sec = 168 * 3600

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

    def test_get_rfq_params_linear_changelogs_success_summary_only(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = 1772418548
        client.requestGET = MagicMock(
            return_value={"success": {"data": [{"id": 1, "pair": "eth-usdt"}]}}
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "rfq_changes.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_rfq_params_linear_changelogs(
                    from_time, to_time, output_path=output_path
                )

            self.assertIn("success", resp)
            self.assertNotIn("data", resp["success"])
            self.assertEqual(resp["success"]["output_path"], output_path)
            self.assertEqual(resp["success"]["total_rows"], 1)
            self.assertEqual(resp["success"]["completed_chunks"], 1)
            client.requestGET.assert_called_once_with(
                "setting-v4/v4/rfq-params-linear-changelogs",
                params={"from": from_time, "to": to_time},
            )
            mocked_sleep.assert_not_called()
            self.assertTrue(os.path.exists(output_path))

    def test_get_rfq_params_linear_changelogs_include_data(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = from_time + 10
        client.requestGET = MagicMock(
            return_value={"success": {"data": [{"id": 1}, {"id": 2}]}}
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "rfq_changes.csv")
            with patch("kyberReserve.reserveClient.sleep"):
                resp = client.get_rfq_params_linear_changelogs(
                    from_time, to_time, output_path=output_path, include_data=True
                )

            self.assertIn("success", resp)
            self.assertIn("data", resp["success"])
            self.assertEqual(len(resp["success"]["data"]), 2)

    def test_get_rfq_params_linear_changelogs_split_windows(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = from_time + self.max_window_sec + 120
        client.requestGET = MagicMock(
            side_effect=[
                {"success": {"data": [{"id": 1}]}},
                {"success": {"data": [{"id": 2}]}},
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "rfq_changes.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_rfq_params_linear_changelogs(
                    from_time, to_time, output_path=output_path
                )

            self.assertIn("success", resp)
            self.assertEqual(client.requestGET.call_count, 2)
            self.assertEqual(
                client.requestGET.call_args_list,
                [
                    call(
                        "setting-v4/v4/rfq-params-linear-changelogs",
                        params={
                            "from": from_time,
                            "to": from_time + self.max_window_sec,
                        },
                    ),
                    call(
                        "setting-v4/v4/rfq-params-linear-changelogs",
                        params={
                            "from": from_time + self.max_window_sec,
                            "to": to_time,
                        },
                    ),
                ],
            )
            self.assertEqual(mocked_sleep.call_args_list, [call(0.5)])

    def test_get_rfq_params_linear_changelogs_retry_backoff(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = from_time + 10
        client.requestGET = MagicMock(
            side_effect=[
                {"failed": "temporary error 1"},
                {"failed": "temporary error 2"},
                {"success": {"data": [{"id": 1}]}},
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "rfq_changes.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_rfq_params_linear_changelogs(
                    from_time, to_time, output_path=output_path
                )

            self.assertIn("success", resp)
            self.assertEqual(resp["success"]["retries_used"], 2)
            self.assertEqual(mocked_sleep.call_args_list, [call(1), call(2)])

    def test_get_rfq_params_linear_changelogs_fail_fast_with_partial_save(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = from_time + self.max_window_sec + 120
        client.requestGET = MagicMock(
            side_effect=[
                {"success": {"data": [{"id": 1, "pair": "eth-usdt"}]}},
                {"failed": "boom"},
                {"failed": "boom"},
                {"failed": "boom"},
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "rfq_changes.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_rfq_params_linear_changelogs(
                    from_time, to_time, output_path=output_path
                )

            self.assertIn("failed", resp)
            self.assertEqual(resp["failed"], "boom")
            self.assertEqual(resp["meta"]["completed_chunks"], 1)
            self.assertEqual(resp["meta"]["total_rows_saved"], 1)
            self.assertEqual(client.requestGET.call_count, 4)
            self.assertEqual(mocked_sleep.call_args_list, [call(0.5), call(1), call(2)])
            with open(output_path, "r", newline="") as infile:
                rows = list(csv.DictReader(infile))
            self.assertEqual(len(rows), 1)

    def test_get_rfq_params_linear_changelogs_csv_schema_drift(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = from_time + self.max_window_sec + 120
        client.requestGET = MagicMock(
            side_effect=[
                {"success": {"data": [{"id": 1, "a": 10}]}},
                {"success": {"data": [{"id": 2, "a": 20, "extra": {"x": 1}}]}},
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "rfq_changes.csv")
            with patch("kyberReserve.reserveClient.sleep"):
                resp = client.get_rfq_params_linear_changelogs(
                    from_time, to_time, output_path=output_path
                )

            self.assertIn("success", resp)
            with open(output_path, "r", newline="") as infile:
                reader = csv.DictReader(infile)
                self.assertIn("extra.x", reader.fieldnames)
                rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].get("extra.x", ""), "")
            self.assertEqual(rows[1]["extra.x"], "1")

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

    def test_get_rfq_params_linear_changelogs_existing_output_file(self) -> None:
        client = self._build_client()
        from_time = 1772414948
        to_time = from_time + 10
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "rfq_changes.csv")
            with open(output_path, "w"):
                pass
            resp = client.get_rfq_params_linear_changelogs(
                from_time, to_time, output_path=output_path
            )

        self.assertIn("failed", resp)
        self.assertIn("output file already exists", resp["failed"])
        client.requestGET.assert_not_called()


if __name__ == "__main__":
    unittest.main()
