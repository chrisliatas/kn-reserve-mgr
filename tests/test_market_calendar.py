import unittest
from unittest.mock import MagicMock, patch

from kyberReserve.endpoints import EndpointItem
from kyberReserve.reserveClient import ReserveClient


class TestMarketCalendar(unittest.TestCase):
    def _build_client(self) -> ReserveClient:
        client: ReserveClient = ReserveClient.__new__(ReserveClient)
        client.timeout = 60
        client.endpoints = {
            "events": EndpointItem(
                path="events",
                base="",
                sub_base="",
                url="https://market-calendar.kyberengineering.io",
                methods=["GET"],
                secured=False,
                options={},
                params={"period": "str", "min_severity": "str"},
                description="Get market calendar events",
            )
        }
        return client

    def test_get_market_calendar_events_passes_filters_and_json(self) -> None:
        client = self._build_client()
        response = MagicMock()
        response.json.return_value = {"events": [{"severity": "medium"}]}

        with patch.object(
            client, "requestGET_url", return_value={"success": response}
        ) as request_mock:
            result = client.get_market_calendar_events(
                period="week", min_severity="medium"
            )

        self.assertEqual(result, {"success": {"events": [{"severity": "medium"}]}})
        request_mock.assert_called_once_with(
            "https://market-calendar.kyberengineering.io/events",
            params={"period": "week", "min_severity": "medium"},
            timeout=60,
            secured=False,
        )

    def test_get_market_calendar_events_propagates_request_failure(self) -> None:
        client = self._build_client()
        with patch.object(
            client,
            "requestGET_url",
            return_value={"failed": "VPN connection unavailable"},
        ):
            result = client.get_market_calendar_events()

        self.assertEqual(result, {"failed": "VPN connection unavailable"})

    def test_get_market_calendar_events_uses_date_without_period(self) -> None:
        client = self._build_client()
        response = MagicMock()
        response.json.return_value = {"events": []}
        with patch.object(
            client, "requestGET_url", return_value={"success": response}
        ) as request_mock:
            result = client.get_market_calendar_events(date="2026-11-17")

        self.assertEqual(result, {"success": {"events": []}})
        self.assertEqual(
            request_mock.call_args.kwargs["params"],
            {
                "min_severity": "high",
                "date": "2026-11-17",
            },
        )
