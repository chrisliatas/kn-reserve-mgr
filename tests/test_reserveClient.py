"""
Sample tests for the ReserveClient class
"""

import unittest
from unittest.mock import patch

from kyberReserve.reserveClient import ReserveClient


class TestReserveClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up the ReserveClient instance for testing
        cls.client = ReserveClient(
            key_file="path/to/key_file.json",
            authContext="auth_context",
            endpoints_json="path/to/endpoints.json",
            timeout=60,
        )

    def test_sign(self):
        # Mock the PreparedRequest object
        request = unittest.mock.Mock()
        request.headers = {}

        # Call the sign method
        signed_request = self.client.sign(request)

        # Assert that the Signature header is added to the request
        self.assertIn("Signature", signed_request.headers)

    @patch("reserveClient.requests.sessions.Session.send")
    def test_request_success(self, mock_send):
        # Mock the response object
        response = unittest.mock.Mock()
        response.status_code = 200
        response.json.return_value = {"success": {"data": "example"}}

        # Configure the mock_send to return the mocked response
        mock_send.return_value = response

        # Call the request method
        result = self.client.request("GET", "example_endpoint")

        # Assert that the result is as expected
        self.assertEqual(result, {"success": {"data": "example"}})

    @patch("reserveClient.requests.sessions.Session.send")
    def test_request_failure(self, mock_send):
        # Mock the response object
        response = unittest.mock.Mock()
        response.status_code = 400
        response.text = "Bad request"

        # Configure the mock_send to return the mocked response
        mock_send.return_value = response

        # Call the request method
        result = self.client.request("GET", "example_endpoint")

        # Assert that the result is as expected
        self.assertEqual(
            result,
            {
                "failed": "bad http status 400 reply:Bad request for request to example_endpoint, params:None, data: None, json: None"
            },
        )

    def test_get_authdata(self):
        # Mock the requestGET method
        self.client.requestGET = unittest.mock.Mock(
            return_value={"success": {"data": "example"}}
        )

        # Call the get_authdata method
        result = self.client.get_authdata()

        # Assert that the result is as expected
        self.assertEqual(result, {"success": {"data": "example"}})


if __name__ == "__main__":
    unittest.main()
