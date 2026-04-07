import csv
import os
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch

from kyberReserve.endpoints import EndpointItem
from kyberReserve.reserveClient import ReserveClient


class TestTradeLogs(unittest.TestCase):
    day_ms = 24 * 60 * 60 * 1000
    max_window_ms = 7 * day_ms
    general_max_window_ms = day_ms

    def _build_client(self) -> ReserveClient:
        client: ReserveClient = ReserveClient.__new__(ReserveClient)
        client.endpoints = {
            "tradelogs-v2-tradelogs_tradelogs": EndpointItem(
                path="tradelogs",
                base="tradelogs-v2-tradelogs",
                sub_base="",
                url="https://trading-gateway.kyberengineering.io",
                methods=["GET"],
                secured=True,
                options={},
                params={"from_time": "int (ms)", "to_time": "int (ms)"},
                description="test",
            ),
            "xmonitor_v2/data_onchaintrades": EndpointItem(
                path="onchaintrades",
                base="xmonitor",
                sub_base="v2/data",
                url="https://kipseli-gateway.kyberengineering.io",
                methods=["GET"],
                secured=True,
                options={},
                params={"from": "int (ms)", "to": "int (ms)", "limit": "int"},
                description="test",
            ),
        }
        client.requestGET_url = MagicMock()
        return client

    @staticmethod
    def _response(payload: dict) -> dict[str, MagicMock]:
        response = MagicMock()
        response.json.return_value = payload
        return {"success": response}

    def test_get_general_tradelogs_small_window_returns_in_memory(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + 3600 * 1000
        client.requestGET_url = MagicMock(
            return_value=self._response({"data": [{"id": 1}, {"id": 2}]})
        )

        with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
            resp = client.get_general_tradelogs(from_time, to_time)

        self.assertEqual(resp, {"success": [{"id": 1}, {"id": 2}]})
        client.requestGET_url.assert_called_once_with(
            "https://trading-gateway.kyberengineering.io/tradelogs-v2-tradelogs/tradelogs",
            params={"from_time": from_time, "to_time": to_time},
            timeout=120,
            secured=True,
        )
        mocked_sleep.assert_not_called()

    def test_get_general_tradelogs_large_window_defaults_to_csv_summary(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + self.day_ms + 1
        output_path: str
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "raw_trades.csv")
            client.requestGET_url = MagicMock(
                side_effect=[
                    self._response({"data": [{"id": 1, "pair": "ETH-USDT"}]}),
                    self._response({"data": [{"id": 2, "pair": "ETH-USDT"}]}),
                ]
            )
            with (
                patch(
                    "kyberReserve.reserveClient.os.path.abspath",
                    return_value=output_path,
                ),
                patch("kyberReserve.reserveClient.sleep"),
            ):
                resp = client.get_general_tradelogs(from_time, to_time)

            self.assertIn("success", resp)
            self.assertEqual(resp["success"]["output_path"], output_path)
            self.assertEqual(resp["success"]["completed_chunks"], 2)
            self.assertEqual(resp["success"]["total_rows"], 2)
            self.assertNotIn("data", resp["success"])
            self.assertTrue(os.path.exists(output_path))
            self.assertEqual(client.requestGET_url.call_count, 2)

    def test_get_general_tradelogs_split_windows(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + self.general_max_window_ms + 123
        client.requestGET_url = MagicMock(
            side_effect=[
                self._response({"data": [{"id": 1}]}),
                self._response({"data": [{"id": 2}]}),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "raw_trades.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_general_tradelogs(
                    from_time, to_time, output_path=output_path
                )

        self.assertIn("success", resp)
        self.assertEqual(
            client.requestGET_url.call_args_list,
            [
                call(
                    "https://trading-gateway.kyberengineering.io/tradelogs-v2-tradelogs/tradelogs",
                    params={
                        "from_time": from_time,
                        "to_time": from_time + self.general_max_window_ms,
                    },
                    timeout=120,
                    secured=True,
                ),
                call(
                    "https://trading-gateway.kyberengineering.io/tradelogs-v2-tradelogs/tradelogs",
                    params={
                        "from_time": from_time + self.general_max_window_ms,
                        "to_time": to_time,
                    },
                    timeout=120,
                    secured=True,
                ),
            ],
        )
        self.assertEqual(mocked_sleep.call_args_list, [call(0.5)])

    def test_get_general_tradelogs_retry_backoff(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + self.day_ms + 1
        client.requestGET_url = MagicMock(
            side_effect=[
                {"failed": "temporary error 1"},
                {"failed": "temporary error 2"},
                self._response({"data": [{"id": 1}]}),
                self._response({"data": [{"id": 2}]}),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "raw_trades.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_general_tradelogs(
                    from_time, to_time, output_path=output_path
                )

        self.assertIn("success", resp)
        self.assertEqual(resp["success"]["retries_used"], 2)
        self.assertEqual(mocked_sleep.call_args_list, [call(1), call(2), call(0.5)])

    def test_get_general_tradelogs_fail_fast_with_partial_save(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + self.general_max_window_ms + 123
        client.requestGET_url = MagicMock(
            side_effect=[
                self._response({"data": [{"id": 1, "pair": "ETH-USDT"}]}),
                {"failed": "boom"},
                {"failed": "boom"},
                {"failed": "boom"},
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "raw_trades.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_general_tradelogs(
                    from_time, to_time, output_path=output_path
                )

            self.assertIn("failed", resp)
            self.assertEqual(resp["failed"], "boom")
            self.assertEqual(resp["meta"]["completed_chunks"], 1)
            self.assertEqual(resp["meta"]["total_rows_saved"], 1)
            self.assertEqual(mocked_sleep.call_args_list, [call(0.5), call(1), call(2)])
            with open(output_path, newline="") as infile:
                rows = list(csv.DictReader(infile))
            self.assertEqual(len(rows), 1)

    def test_get_general_tradelogs_incremental_csv_save(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + self.general_max_window_ms + 123
        client.requestGET_url = MagicMock(
            side_effect=[
                self._response({"data": [{"id": 1, "pair": "ETH-USDT"}]}),
                self._response({"data": [{"id": 2, "extra": {"venue": "rfq"}}]}),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "raw_trades.csv")
            with patch("kyberReserve.reserveClient.sleep"):
                resp = client.get_general_tradelogs(
                    from_time, to_time, output_path=output_path
                )

            self.assertIn("success", resp)
            with open(output_path, newline="") as infile:
                reader = csv.DictReader(infile)
                self.assertIn("chunk_from", reader.fieldnames)
                self.assertIn("chunk_to", reader.fieldnames)
                self.assertIn("fetch_ts", reader.fieldnames)
                self.assertIn("extra.venue", reader.fieldnames)
                rows = list(reader)
            self.assertEqual(len(rows), 2)

    def test_get_general_tradelogs_include_data_in_file_mode(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + self.day_ms + 1
        client.requestGET_url = MagicMock(
            side_effect=[
                self._response({"data": [{"id": 1}, {"id": 2}]}),
                self._response({"data": [{"id": 3}, {"id": 4}]}),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "raw_trades.csv")
            with patch("kyberReserve.reserveClient.sleep"):
                resp = client.get_general_tradelogs(
                    from_time,
                    to_time,
                    output_path=output_path,
                    include_data=True,
                )

        self.assertIn("success", resp)
        self.assertEqual(len(resp["success"]["data"]), 4)

    def test_get_general_tradelogs_invalid_range(self) -> None:
        for from_time, to_time in [
            (1732246550000, 1732246550000),
            (1732247104000, 1732246550000),
        ]:
            with self.subTest(from_time=from_time, to_time=to_time):
                client = self._build_client()
                resp = client.get_general_tradelogs(from_time, to_time)
                self.assertEqual(
                    resp, {"failed": "from_time must be < to_time (milliseconds)"}
                )
                client.requestGET_url.assert_not_called()

    def test_get_general_tradelogs_invalid_types(self) -> None:
        invalid_cases = [
            ("1732246550000", 1732247104000, False),
            (None, 1732247104000, False),
            (True, 1732247104000, False),
            (1732246550000, "1732247104000", False),
            (1732246550000, None, False),
            (1732246550000, True, False),
            (1732246550000, 1732247104000, "yes"),
        ]
        for from_time, to_time, include_data in invalid_cases:
            with self.subTest(
                from_time=from_time, to_time=to_time, include_data=include_data
            ):
                client = self._build_client()
                resp = client.get_general_tradelogs(
                    from_time, to_time, include_data=include_data  # type: ignore[arg-type]
                )
                self.assertIn("failed", resp)
                client.requestGET_url.assert_not_called()

    def test_get_general_tradelogs_rejects_second_based_timestamps(self) -> None:
        client = self._build_client()

        resp = client.get_general_tradelogs(1772323200, 1775001600)

        self.assertEqual(
            resp,
            {
                "failed": (
                    "from_time and to_time appear to be Unix timestamps in seconds; "
                    "get_general_tradelogs expects milliseconds"
                )
            },
        )
        client.requestGET_url.assert_not_called()

    def test_get_general_tradelogs_exact_seven_days_splits_safely(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + self.max_window_ms
        client.requestGET_url = MagicMock(
            side_effect=[self._response({"data": [{"id": idx}]}) for idx in range(7)]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "raw_trades.csv")
            with patch("kyberReserve.reserveClient.sleep"):
                resp = client.get_general_tradelogs(
                    from_time, to_time, output_path=output_path
                )

        self.assertIn("success", resp)
        self.assertEqual(client.requestGET_url.call_count, 7)
        self.assertEqual(
            client.requestGET_url.call_args_list[0],
            call(
                "https://trading-gateway.kyberengineering.io/tradelogs-v2-tradelogs/tradelogs",
                params={
                    "from_time": from_time,
                    "to_time": from_time + self.general_max_window_ms,
                },
                timeout=120,
                secured=True,
            ),
        )
        self.assertEqual(
            client.requestGET_url.call_args_list[-1],
            call(
                "https://trading-gateway.kyberengineering.io/tradelogs-v2-tradelogs/tradelogs",
                params={
                    "from_time": from_time + (6 * self.general_max_window_ms),
                    "to_time": to_time,
                },
                timeout=120,
                secured=True,
            ),
        )

    def test_get_general_tradelogs_existing_output_file(self) -> None:
        client = self._build_client()
        from_time = 1732246550000
        to_time = from_time + self.day_ms + 1
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "raw_trades.csv")
            with open(output_path, "w", encoding="utf-8"):
                pass
            resp = client.get_general_tradelogs(
                from_time, to_time, output_path=output_path
            )

        self.assertIn("failed", resp)
        self.assertIn("output file already exists", resp["failed"])
        client.requestGET_url.assert_not_called()

    def test_get_kipseli_tradelogs_small_window_returns_in_memory(self) -> None:
        client = self._build_client()
        from_time = 1775180715000
        to_time = from_time + 3600 * 1000
        client.requestGET_url = MagicMock(
            return_value=self._response({"data": [{"id": 1}, {"id": 2}]})
        )

        with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
            resp = client.get_kipseli_tradelogs(from_time, to_time)

        self.assertEqual(resp, {"success": [{"id": 1}, {"id": 2}]})
        client.requestGET_url.assert_called_once_with(
            "https://kipseli-gateway.kyberengineering.io/xmonitor/v2/data/onchaintrades",
            params={"from": from_time, "to": to_time, "limit": 10000},
            timeout=120,
            secured=True,
        )
        mocked_sleep.assert_not_called()

    def test_get_kipseli_tradelogs_limit_passthrough(self) -> None:
        client = self._build_client()
        from_time = 1775180715000
        to_time = from_time + 3600 * 1000
        client.requestGET_url = MagicMock(
            return_value=self._response({"data": [{"id": 1}]})
        )

        with patch("kyberReserve.reserveClient.sleep"):
            resp = client.get_kipseli_tradelogs(from_time, to_time, limit=100)

        self.assertEqual(resp, {"success": [{"id": 1}]})
        client.requestGET_url.assert_called_once_with(
            "https://kipseli-gateway.kyberengineering.io/xmonitor/v2/data/onchaintrades",
            params={"from": from_time, "to": to_time, "limit": 100},
            timeout=120,
            secured=True,
        )

    def test_get_kipseli_tradelogs_split_windows_preserve_limit(self) -> None:
        client = self._build_client()
        from_time = 1775180715000
        to_time = from_time + self.max_window_ms + 123
        client.requestGET_url = MagicMock(
            side_effect=[
                self._response({"data": [{"id": 1}]}),
                self._response({"data": [{"id": 2}]}),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "onchain_trades.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_kipseli_tradelogs(
                    from_time, to_time, limit=100, output_path=output_path
                )

        self.assertIn("success", resp)
        self.assertEqual(
            client.requestGET_url.call_args_list,
            [
                call(
                    "https://kipseli-gateway.kyberengineering.io/xmonitor/v2/data/onchaintrades",
                    params={
                        "from": from_time,
                        "to": from_time + self.max_window_ms,
                        "limit": 100,
                    },
                    timeout=120,
                    secured=True,
                ),
                call(
                    "https://kipseli-gateway.kyberengineering.io/xmonitor/v2/data/onchaintrades",
                    params={
                        "from": from_time + self.max_window_ms,
                        "to": to_time,
                        "limit": 100,
                    },
                    timeout=120,
                    secured=True,
                ),
            ],
        )
        self.assertEqual(mocked_sleep.call_args_list, [call(0.5)])

    def test_get_kipseli_tradelogs_large_window_defaults_to_csv_summary(self) -> None:
        client = self._build_client()
        from_time = 1775180715000
        to_time = from_time + self.day_ms + 1
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "onchain_trades.csv")
            client.requestGET_url = MagicMock(
                return_value=self._response({"data": [{"id": 1, "pair": "ETH-USDT"}]})
            )
            with (
                patch(
                    "kyberReserve.reserveClient.os.path.abspath",
                    return_value=output_path,
                ),
                patch("kyberReserve.reserveClient.sleep"),
            ):
                resp = client.get_kipseli_tradelogs(from_time, to_time)

            self.assertIn("success", resp)
            self.assertEqual(resp["success"]["output_path"], output_path)
            self.assertEqual(resp["success"]["completed_chunks"], 1)
            self.assertEqual(resp["success"]["total_rows"], 1)
            self.assertNotIn("data", resp["success"])
            self.assertTrue(os.path.exists(output_path))
            client.requestGET_url.assert_called_once_with(
                "https://kipseli-gateway.kyberengineering.io/xmonitor/v2/data/onchaintrades",
                params={"from": from_time, "to": to_time, "limit": 10000},
                timeout=120,
                secured=True,
            )

    def test_get_kipseli_tradelogs_retry_backoff(self) -> None:
        client = self._build_client()
        from_time = 1775180715000
        to_time = from_time + self.day_ms + 1
        client.requestGET_url = MagicMock(
            side_effect=[
                {"failed": "temporary error 1"},
                {"failed": "temporary error 2"},
                self._response({"data": [{"id": 1}]}),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "onchain_trades.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_kipseli_tradelogs(
                    from_time, to_time, limit=50, output_path=output_path
                )

        self.assertIn("success", resp)
        self.assertEqual(resp["success"]["retries_used"], 2)
        self.assertEqual(mocked_sleep.call_args_list, [call(1), call(2)])

    def test_get_kipseli_tradelogs_fail_fast_with_partial_save(self) -> None:
        client = self._build_client()
        from_time = 1775180715000
        to_time = from_time + self.max_window_ms + 123
        client.requestGET_url = MagicMock(
            side_effect=[
                self._response({"data": [{"id": 1, "pair": "ETH-USDT"}]}),
                {"failed": "boom"},
                {"failed": "boom"},
                {"failed": "boom"},
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "onchain_trades.csv")
            with patch("kyberReserve.reserveClient.sleep") as mocked_sleep:
                resp = client.get_kipseli_tradelogs(
                    from_time, to_time, limit=100, output_path=output_path
                )

            self.assertIn("failed", resp)
            self.assertEqual(resp["failed"], "boom")
            self.assertEqual(resp["meta"]["completed_chunks"], 1)
            self.assertEqual(resp["meta"]["total_rows_saved"], 1)
            self.assertEqual(mocked_sleep.call_args_list, [call(0.5), call(1), call(2)])
            with open(output_path, newline="") as infile:
                rows = list(csv.DictReader(infile))
            self.assertEqual(len(rows), 1)

    def test_get_kipseli_tradelogs_include_data_in_file_mode(self) -> None:
        client = self._build_client()
        from_time = 1775180715000
        to_time = from_time + self.day_ms + 1
        client.requestGET_url = MagicMock(
            return_value=self._response({"data": [{"id": 1}, {"id": 2}]})
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "onchain_trades.csv")
            with patch("kyberReserve.reserveClient.sleep"):
                resp = client.get_kipseli_tradelogs(
                    from_time,
                    to_time,
                    output_path=output_path,
                    include_data=True,
                )

        self.assertIn("success", resp)
        self.assertEqual(len(resp["success"]["data"]), 2)

    def test_get_kipseli_tradelogs_invalid_limit(self) -> None:
        invalid_limits = [0, -1, True, "100"]
        for limit in invalid_limits:
            with self.subTest(limit=limit):
                client = self._build_client()
                resp = client.get_kipseli_tradelogs(
                    1775180715000, 1775182715000, limit=limit  # type: ignore[arg-type]
                )
                self.assertEqual(
                    resp, {"failed": "limit must be a positive integer or None"}
                )
                client.requestGET_url.assert_not_called()

    def test_get_kipseli_tradelogs_invalid_range(self) -> None:
        client = self._build_client()

        resp = client.get_kipseli_tradelogs(1775182715000, 1775180715000)

        self.assertEqual(resp, {"failed": "from_time must be < to_time (milliseconds)"})
        client.requestGET_url.assert_not_called()

    def test_get_kipseli_tradelogs_rejects_second_based_timestamps(self) -> None:
        client = self._build_client()

        resp = client.get_kipseli_tradelogs(1775180715, 1775182715)

        self.assertEqual(
            resp,
            {
                "failed": (
                    "from_time and to_time appear to be Unix timestamps in seconds; "
                    "get_kipseli_tradelogs expects milliseconds"
                )
            },
        )
        client.requestGET_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()
