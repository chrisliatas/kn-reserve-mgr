import unittest
from unittest.mock import MagicMock, call

from kyberReserve.endpoints import EndpointItem
from kyberReserve.reserveClient import ReserveClient


class TestBlacklist(unittest.TestCase):
    def _build_client(self) -> ReserveClient:
        client: ReserveClient = ReserveClient.__new__(ReserveClient)
        client.endpoints = {
            "rfq_blacklist": EndpointItem(
                path="blacklist",
                base="rfq",
                sub_base="",
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
                call("rfq/blacklist", params=None),
                call("rfq/blacklist", params={"from_time": 1783495488623}),
            ],
        )

    def test_blacklist_sync_initializes_then_applies_delta(self) -> None:
        client = self._build_client()
        client.requestGET = MagicMock(
            side_effect=[
                {
                    "success": {
                        "code": "0",
                        "msg": "",
                        "blacklist": [
                            {"address": "0xAAA", "description": "first"},
                            {"a": "0xBBB", "description": "second"},
                        ],
                        "revoked": [],
                        "updatedTime": 100,
                    }
                },
                {
                    "success": {
                        "code": "0",
                        "msg": "",
                        "blacklist": [{"address": "0xCCC"}],
                        "revoked": ["0xAAA"],
                        "updatedTime": 200,
                    }
                },
            ]
        )

        initial = client.blacklist_sync()
        delta = client.blacklist_sync()

        self.assertEqual(
            initial["success"],
            {
                "blacklist": [
                    {"address": "0xAAA", "description": "first"},
                    {"a": "0xBBB", "description": "second"},
                ],
                "revoked": [],
                "updatedTime": 100,
                "from_time": None,
                "is_delta": False,
            },
        )
        self.assertEqual(
            delta["success"],
            {
                "blacklist": [
                    {"a": "0xBBB", "description": "second"},
                    {"address": "0xCCC"},
                ],
                "revoked": ["0xAAA"],
                "updatedTime": 200,
                "from_time": 100,
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
                    "blacklist": ["0xABC", {"address": "0xDEF"}],
                    "revoked": [],
                    "updatedTime": 100,
                }
            }
        )

        banned = client.get_banned_addresses()

        self.assertEqual(banned, ["0xabc", "0xdef"])

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
