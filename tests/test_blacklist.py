import unittest
from unittest.mock import MagicMock, call, patch

from kyberReserve.endpoints import EndpointItem
from kyberReserve.reserveClient import ReserveClient


class TestBlacklist(unittest.TestCase):
    def _build_client(self) -> ReserveClient:
        client: ReserveClient = ReserveClient.__new__(ReserveClient)
        client.endpoints = {
            "setting-v4_v4_blacklist-addr": EndpointItem(
                path="blacklist-addr",
                base="setting-v4",
                sub_base="v4",
                url="",
                methods=["GET"],
                secured=True,
                options={},
                params={"from_time": "int (ms)"},
                description="test",
            )
        }
        client.requestGET = MagicMock()
        return client

    def test_blacklist_get_snapshot_and_delta_params(self) -> None:
        client = self._build_client()
        client.requestGET = MagicMock(return_value={"success": {"ok": True}})

        snapshot = client.blacklist_get()
        delta = client.blacklist_get(from_time=1783495488623)

        self.assertEqual(snapshot, {"success": {"ok": True}})
        self.assertEqual(delta, {"success": {"ok": True}})
        self.assertEqual(
            client.requestGET.call_args_list,
            [
                call("setting-v4/v4/blacklist-addr", params=None),
                call(
                    "setting-v4/v4/blacklist-addr",
                    params={"from_time": 1783495488623},
                ),
            ],
        )

    def test_blacklist_sync_initializes_then_applies_delta(self) -> None:
        client = self._build_client()
        client.requestGET = MagicMock(
            side_effect=[
                {
                    "success": {
                        "success": True,
                        "data": [
                            {"a": "0xAAA", "d": "first", "e": 0},
                            {"a": "0xBBB", "d": "second", "e": 999},
                            {"a": "0xEXPIRED", "d": "old", "e": 50},
                        ],
                    }
                },
                {
                    "success": {
                        "success": True,
                        "data": [
                            {"a": "0xCCC", "d": "new", "e": 0},
                            {"a": "0xAAA", "d": "removed", "e": 150},
                        ],
                    }
                },
            ]
        )

        with patch(
            "kyberReserve.reserveClient.ts_millis",
            side_effect=[100, 100, 200, 200],
        ):
            initial = client.blacklist_sync()
            delta = client.blacklist_sync()

        self.assertEqual(
            initial["success"],
            {
                "blacklist": [
                    {"a": "0xAAA", "d": "first", "e": 0},
                    {"a": "0xBBB", "d": "second", "e": 999},
                ],
                "revoked": [{"a": "0xEXPIRED", "d": "old", "e": 50}],
                "from_time": None,
                "next_from_time": 100,
                "record_count": 3,
                "is_delta": False,
            },
        )
        self.assertEqual(
            delta["success"],
            {
                "blacklist": [
                    {"a": "0xBBB", "d": "second", "e": 999},
                    {"a": "0xCCC", "d": "new", "e": 0},
                ],
                "revoked": [{"a": "0xAAA", "d": "removed", "e": 150}],
                "from_time": 100,
                "next_from_time": 200,
                "record_count": 2,
                "is_delta": True,
            },
        )
        self.assertEqual(
            client.requestGET.call_args_list[1].kwargs,
            {"params": {"from_time": 100}},
        )

    def test_get_banned_addresses_uses_merged_snapshot(self) -> None:
        client = self._build_client()
        client.requestGET = MagicMock(
            return_value={
                "success": {
                    "success": True,
                    "data": [
                        {"a": "0xABC", "e": 0},
                        {"a": "0xDEF", "e": 200},
                    ],
                }
            }
        )

        with patch("kyberReserve.reserveClient.ts_millis", side_effect=[100, 100]):
            banned = client.get_banned_addresses()

        self.assertEqual(banned, ["0xabc", "0xdef"])

    def test_blacklist_sync_rejects_record_without_expiry(self) -> None:
        client = self._build_client()
        client.requestGET = MagicMock(
            return_value={"success": {"success": True, "data": [{"a": "0xAAA"}]}}
        )

        with patch("kyberReserve.reserveClient.ts_millis", return_value=100):
            self.assertEqual(
                client.blacklist_sync(),
                {"failed": "blacklist record missing valid expiry"},
            )

    def test_get_banned_addresses_logs_backend_failure(self) -> None:
        client = self._build_client()
        client.requestGET = MagicMock(return_value={"failed": "backend unavailable"})

        with self.assertLogs("kyberReserve.reserveClient", level="ERROR") as logs:
            banned = client.get_banned_addresses()

        self.assertEqual(banned, [])
        self.assertIn("backend unavailable", logs.output[0])

    def test_blacklist_get_rejects_invalid_from_time(self) -> None:
        for from_time in [True, -1, "100"]:
            with self.subTest(from_time=from_time):
                client = self._build_client()
                response = client.blacklist_get(from_time=from_time)  # type: ignore[arg-type]
                self.assertEqual(
                    response,
                    {
                        "failed": (
                            "from_time must be a non-negative integer (milliseconds)"
                        )
                    },
                )
                client.requestGET.assert_not_called()


if __name__ == "__main__":
    unittest.main()
