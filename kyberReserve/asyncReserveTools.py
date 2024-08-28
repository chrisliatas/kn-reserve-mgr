import asyncio
import base64
import hashlib
import hmac
import json
import logging
from typing import Any

import aiohttp
from yarl import URL

from kyberReserve.endpoints import ReserveEndpoints
from kyberReserve.utils import AuthContext, AuthenticationData, ts_millis

lgr = logging.getLogger(__name__)


class RequestItem:
    _url: URL
    _headers: dict[str, str]
    _standard_headers = {
        "User-Agent": "python-requests/2.31.0",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }
    _signed = False

    def __init__(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        signed_fields: list[str] | None = None,
        body: str | None = None,
        params: dict[str, Any] | None = None,
        key_id: str | None = None,
        secret: bytes | None = None,
    ) -> None:
        self.method = method.upper()
        self.params = params
        self.url = url  # type: ignore
        self.custom_headers = headers
        self.headers = self.custom_headers or self._standard_headers
        self.signedList = signed_fields or ["(request-target)", "nonce", "digest"]
        self.body = body
        self.key_id = key_id
        self.secret = secret

    @property
    def url(self) -> URL:
        """Get the str representation of url provided."""
        return self._url

    @url.setter
    def url(self, value: str) -> None:
        self._url = URL(value)
        if self.params:
            self._url = self._url.with_query(self.params)

    @property
    def headers(self) -> dict[str, str]:
        return self._headers

    @headers.setter
    def headers(self, value: dict[str, str]) -> None:
        self._headers = value.copy()

    @property
    def path_url(self) -> str:
        return self._url.path_qs

    @property
    def host(self) -> str | None:
        return self._url.host

    @property
    def hasSecret(self) -> bool:
        return True if self.secret else False

    def _add_digest(self) -> None:
        if self.body is not None and "Digest" not in self.headers:
            digest = hashlib.sha256(self.body.encode()).digest()
            self._headers["Digest"] = "SHA-256=" + base64.b64encode(digest).decode()

    def _add_sign_specific_headers(self) -> None:
        if "nonce" not in self._headers:
            self._headers["nonce"] = str(ts_millis())
        self._add_digest()

    def _get_string_to_sign(self) -> bytes:
        """
        Create the string to be signed from a selection of specific header fields.
        Returns: Example of return bytes
            b'(request-target): get /0x/current-pricing\nnonce: 1698960526459\ndigest: '
        """
        sts = []
        for field in self.signedList:
            if field == "(request-target)":
                sts.append(f"(request-target): {self.method.lower()} {self.path_url}")
            else:
                if (sfield := field.lower()) == "host":
                    value = self.headers.get("host", self.host)
                else:
                    value = self.headers.get(field, "")
                sts.append(f"{sfield}: {value}")
        return "\n".join(sts).encode()

    def sign(self) -> None:
        if self._signed:
            print(f"Already signed at {self.headers['nonce']}")
            return
        if not self.secret or not self.key_id:
            raise Exception("Cannot sign request without a SECRET or KEY-ID.")
        self._add_sign_specific_headers()
        msg = self._get_string_to_sign()
        raw_sig = hmac.new(self.secret, msg, hashlib.sha512).digest()
        sig = base64.b64encode(raw_sig).decode()
        sig_struct = [
            ("keyId", self.key_id),
            ("algorithm", "hmac-sha512"),
            ("headers", " ".join(self.signedList)),
            ("signature", sig),
        ]
        self._headers["Signature"] = ",".join(f'{k}="{v}"' for k, v in sig_struct)
        self._signed = True

    def reset(self) -> None:
        self.headers = self.custom_headers or self._standard_headers
        self._signed = False


async def fetch_url(request: RequestItem, timeout: int = 60) -> dict:
    """Asynchronously fetches a request.

    Args:
        request: The `RequestItem` to fetch.

    Returns:
        A response json object.
    """
    url = request.url
    if request.hasSecret:
        request.sign()
    lgr.debug(f"fetch_url - Fetching: {url}")
    try:
        session_timeout = aiohttp.ClientTimeout(
            total=None, sock_connect=timeout, sock_read=timeout
        )
        async with aiohttp.ClientSession(
            headers=request.headers, timeout=session_timeout
        ) as session:
            async with session.get(url, allow_redirects=True, timeout=timeout) as resp:
                resp.raise_for_status()
                return {"success": await resp.json()}
    except (asyncio.exceptions.TimeoutError, aiohttp.ClientResponseError) as err:
        lgr.error(f"Error fetching {url}: {err}")
        return {"failed": str(err)}


async def fetch_all_urls(reqs: list[RequestItem]) -> list[dict]:
    """Asynchronously fetches all requests in a list.

    Args:
        reqs: A list of URLs to fetch.

    Returns:
        A list of response objects.
    """

    tasks = []
    for req in reqs:
        tasks.append(asyncio.create_task(fetch_url(req)))

    responses = await asyncio.gather(*tasks)
    return responses


class ContextSignedRequest:
    """Create a request with a specific context for signing."""

    def __init__(
        self,
        key_file: str,
        authContext: AuthContext,
        endpoints_json: str,
    ) -> None:
        """Initialize Request based on AuthContext given.
        Args:
            key_file: path to json file with authentication data.
            authContext: context for authentication data.
        """
        self.auth_data = AuthenticationData(key_file)
        self.auth_ctx = authContext
        self.host, self.key_id, self.secret = self.auth_data.get_ctx(self.auth_ctx)
        self.endpoints = ReserveEndpoints(endpoints_json).endpoints
        lgr.info(f"ReserveClient initialized with auth context: {self.auth_ctx}")

    def get(
        self,
        endpoint: str,
        params: Any | None = None,
    ) -> RequestItem:
        """Convenience function to create a `RequestItem` for GET requests."""
        return RequestItem(
            method="GET",
            url=f"{self.host}/{endpoint}",
            headers=None,
            signed_fields=None,
            body=None,
            params=params,
            key_id=self.key_id,
            secret=self.secret,
        )

    def post(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        signed_fields: list[str] | None = None,
        data: Any | None = None,
        params: Any | None = None,
    ) -> RequestItem:
        """Convenience function to create a `RequestItem` for GET requests."""
        return RequestItem(
            method="POST",
            url=f"{self.host}/{endpoint}",
            headers=headers,
            signed_fields=signed_fields,
            body=json.dumps(data) if data else None,
            params=params,
            key_id=self.key_id,
            secret=self.secret,
        )

    async def async_mtm(
        self,
        base: list[str],
        quote: list[str],
        ts_sec: int | list[int] | None = None,
        ts_unique: bool = True,
    ) -> list[dict[str, Any]]:
        """Get mark-to-market rates asynchronously.
        Use `ts_unique=True` to match each base-quote pair with a unique timestamp,
        otherwise, all timestamps will be used for each pair."""
        # replace all occurrences of deviating tokens base and quote
        if "WETH" in base:
            base = ["ETH" if b == "WETH" else b for b in base]
        if "WETH" in quote:
            quote = ["ETH" if q == "WETH" else q for q in quote]
        if "BEAM" in base:
            base = ["BEAMX" if b == "BEAM" else b for b in base]
        if "BEAM" in quote:
            quote = ["BEAMX" if q == "BEAM" else q for q in quote]
        # make array of params combining base and quote lists
        pairs = [(i, j) for i in base for j in quote if i != j]
        params: list[dict[str, Any]] = [dict(base=b, quote=q) for b, q in pairs]
        temp_host = self.host
        self.host = self.endpoints["mark-to-market_rate"].host_base
        endpoint = (
            self.endpoints["mark-to-market_rate"].path
            if ts_sec is None
            else self.endpoints["mark-to-market_historical/rate"].path
        )
        reqs = []
        mtm = []
        for idx, p in enumerate(params):
            if ts_sec is None:
                reqs.append(self.get(endpoint, p))
                mtm.append(p | {"time": None})
            else:
                if isinstance(ts_sec, int):
                    p["time"] = ts_sec
                    reqs.append(self.get(endpoint, p))
                    mtm.append(p)
                else:
                    if ts_unique:
                        p["time"] = ts_sec[idx]
                        reqs.append(self.get(endpoint, p))
                        mtm.append(p.copy())
                    else:
                        for ts in ts_sec:
                            p["time"] = ts
                            reqs.append(self.get(endpoint, p))
                            mtm.append(p.copy())
        # if len(reqs) > 10, then send in batches of 10
        if (n_reqs := len(reqs)) > 10:
            print(f"Fetching {n_reqs} requests in batches of 10")
            responses = []
            for i in range(0, n_reqs, 10):
                print(f"Fetching {i} to {i+10} of {n_reqs}")
                responses += await fetch_all_urls(reqs[i : i + 10])
        else:
            responses = await fetch_all_urls(reqs)
        self.host = temp_host
        for i, resp in enumerate(responses):
            if "success" in resp.keys() and "success" in resp["success"].keys():
                try:
                    mtm[i]["rate"] = resp["success"]["data"]["rate"]
                except KeyError:
                    print(
                        f"No rate for [{mtm[i]['base']}, {mtm[i]['quote']}, "
                        f"{mtm[i]['time']}], data: {resp}"
                    )
                    mtm[i]["rate"] = 0.0
            else:
                print(
                    f"Request failed for [{mtm[i]['base']}, {mtm[i]['quote']}, "
                    f"{mtm[i]['time']}], with: {resp['failed']}"
                )
                mtm[i]["rate"] = 0.0
        return mtm
