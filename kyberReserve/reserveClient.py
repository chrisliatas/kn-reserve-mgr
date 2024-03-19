import base64
import hashlib
import hmac
import logging
import urllib.parse
from datetime import timedelta
from functools import wraps
from time import time
from timeit import default_timer as timer
from typing import Any, Callable

import requests.models
from requests import PreparedRequest, Request, Response

from kyberReserve.endpoints import ReserveEndpoints
from kyberReserve.tokens import kn_traded_full
from kyberReserve.utils import (
    AuthContext,
    AuthenticationData,
    convert_float_to_twei,
    convert_rate_to_binance,
    dates_gen,
    dt_ts_milis,
    str_to_dtime,
    ts_millis,
)

lgr = logging.getLogger(__name__)


def response_stats(func) -> Callable:
    """Decorator to record request - response statistics."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> dict[str, Any]:
        start = timer()
        resp = func(*args, **kwargs)
        end = timer()
        stats = {"roundtrip": f"{end - start}", "local_time": time()}
        if isinstance(resp, dict) and "success" in resp and (r := resp["success"]):
            if isinstance(r, Response):
                stats.update(
                    {
                        "elapsed": f"{r.elapsed}",
                        "srv_time": r.headers.get("Date", "-"),
                    }
                )
        resp["stats"] = stats
        return resp

    return wrapper


class ReserveClient:
    """Kyber Reserve API client."""

    def __init__(
        self,
        key_file: str,
        authContext: AuthContext,
        endpoints_json: str,
        timeout: int = 60,
    ) -> None:
        """Initialize Reserve API client.
        Args:
            key_file: path to json file with authentication data.
            authContext: context for authentication data.
            timeout: timeout for requests. Default 60 seconds.
        """
        self.auth_data = AuthenticationData(key_file)
        self.auth_ctx = authContext
        self.host, self.key_id, self.secret = self.auth_data.get_ctx(self.auth_ctx)
        self.endpoints = ReserveEndpoints(endpoints_json).endpoints
        lgr.info(f"ReserveClient initialized with auth context: {self.auth_ctx}")
        self.timeout = timeout
        (
            self.tokens,
            self.exchanges,
            self.tokens_addr,
            self.tokens_decimals,
        ) = self.get_tokens_exchanges_from_asset_info()

    def sign(
        self,
        request: PreparedRequest,
        headers: list[str] = ["(request-target)", "nonce", "digest"],
    ) -> PreparedRequest:
        self._add_date(request)
        if "digest" in headers:
            self._add_digest(request)
        msg = self._get_string_to_sign(request, headers)
        raw_sig = hmac.new(self.secret, msg, hashlib.sha512).digest()
        sig = base64.b64encode(raw_sig).decode()
        sig_struct = [
            ("keyId", self.key_id),
            ("algorithm", "hmac-sha512"),
            ("headers", " ".join(headers)),
            ("signature", sig),
        ]
        request.headers["Signature"] = ",".join(f'{k}="{v}"' for k, v in sig_struct)
        return request

    @staticmethod
    def _add_digest(request: PreparedRequest) -> None:
        if request.body is not None and "Digest" not in request.headers:
            digest = hashlib.sha256(request.body).digest()  # pyre-ignore
            request.headers["Digest"] = "SHA-256=" + base64.b64encode(digest).decode()

    @staticmethod
    def _add_date(request: PreparedRequest) -> None:
        if "nonce" not in request.headers:
            request.headers["nonce"] = ts_millis()

    @staticmethod
    def _get_string_to_sign(request: PreparedRequest, headers: list[str]) -> bytes:
        sts = []
        for header in headers:
            if header == "(request-target)":
                path_url = requests.models.RequestEncodingMixin.path_url.fget(request)
                sts.append(f"(request-target): {request.method.lower()} {path_url}")
            else:
                if header.lower() == "host":
                    value = request.headers.get(
                        "host", urllib.parse.urlparse(request.url).hostname
                    )
                else:
                    value = request.headers.get(header, "")
                sts.append(f"{header.lower()}: {value}")
        return "\n".join(sts).encode()

    def _request(
        self,
        method: str,
        url: str,
        data: Any | None = None,
        params: Any | None = None,
        json: Any | None = None,
        timeout: int | None = None,
    ) -> Response:
        custom_headers = {}
        if params and isinstance(params, dict) and "integration" in params:
            if "0x/quote" in url:
                if params["integration"] == "0x":
                    custom_headers["0x-api-key"] = self.auth_data.data["0x-api-key"]
                elif params["integration"] == "paraswap":
                    custom_headers["api-key"] = "API-KEY"
            params.pop("integration")

        req = Request(method, url, data=data, params=params, json=json)
        with requests.sessions.Session() as session:
            prep = session.prepare_request(req)
            sreq = self.sign(prep)
            for key, value in custom_headers.items():
                sreq.headers[key] = value
            # Send the request.
            send_kwargs = {
                "timeout": timeout,
                "allow_redirects": True,
            }
            return session.send(sreq, **send_kwargs)

    def request(
        self,
        method: str,
        endpoint: str,
        data: Any | None = None,
        params: Any | None = None,
        json: Any | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        try:
            resp = self._request(
                method=method,
                url=f"{self.host}/{endpoint}",
                data=data,
                params=params,
                json=json,
                timeout=timeout or self.timeout,
            )
            if resp.status_code == 200:
                resp_data = resp.json()
                return {"success": resp_data}
            else:
                reason = (
                    f" bad http status {resp.status_code} reply:{resp.text} for request"
                    f" to {endpoint}, params:{params}, data: {data}, json: {json}"
                )
                return {"failed": reason}
        except requests.exceptions.RequestException as e:
            reason = f"Cannot make request to host: {endpoint} {e.__repr__()}"
            return {"failed": reason}

    def requestGET(
        self,
        endpoint: str,
        data: Any | None = None,
        params: Any | None = None,
        json: Any | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "GET",
            endpoint,
            data=data,
            params=params,
            json=json,
            timeout=timeout,
        )

    def requestPOST(
        self,
        endpoint: str,
        data: Any | None = None,
        params: Any | None = None,
        json: Any | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            endpoint,
            data=data,
            params=params,
            json=json,
            timeout=timeout,
        )

    def requestGET_url(self, url: str, params: dict, timeout: int) -> dict[str, Any]:
        """Used to request **out-of-context URL**."""
        try:
            resp: Response = self._request("GET", url, params=params, timeout=timeout)
            resp.raise_for_status()
        except Exception as ex:
            return {"failed": str(ex)}
        return {"success": resp}

    def get_authdata(self) -> dict[str, Any]:
        return self.requestGET(self.endpoints["v3_authdata"].full_path())

    def get_balances(self) -> dict[str, Any]:
        resp = self.get_authdata()
        try:
            return resp["success"]["data"]["balances"]
        except KeyError as e:
            return {"failed": f"KeyError - {e}"}

    def get_asset_info(self, incl_disabled: bool = True) -> dict[str, Any]:
        endpoint = self.endpoints["v3_asset"].full_path(dict(include_disabled=True))
        if not incl_disabled:
            endpoint = self.endpoints["v3_asset"].full_path()
        return self.requestGET(endpoint)

    def get_0x_rate(self, params: dict) -> dict[str, Any]:
        return self.requestGET(self.endpoints["0x_quote"].full_path(), params=params)

    def get_0x_rate_check_nr(self, params: dict) -> dict[str, Any]:
        for i in range(2):
            if i == 1:
                params["nr"] = True
            resp = self.requestGET(
                self.endpoints["0x_price"].full_path(), params=params
            )
        return resp

    def get_analytic_rate(self, params: dict | None = None) -> dict[str, Any]:
        return self.requestGET(
            self.endpoints["0x_current-pricing"].full_path(), params=params
        )

    def get_0x_levels(self, params: dict | None = None) -> dict[str, Any]:
        return self.requestGET(self.endpoints["0x_levels"].full_path(), params=params)

    def get_0x_mid_prices(self, params: dict) -> dict[str, Any]:
        return self.requestGET(
            self.endpoints["0x_mid-prices"].full_path(), params=params
        )

    def get_addresses(self) -> dict[str, Any]:
        return self.requestGET(self.endpoints["v3_addresses"].full_path())

    def get_current_rfq_pricing(self, params: dict | None = None) -> dict[str, Any]:
        return self.requestGET(
            self.endpoints["rfq_current-base-pricing"].full_path(), params=params
        )

    def get_tokens_exchanges_from_asset_info(
        self, incl_disabled: bool = True, incl_WETH: bool = True
    ) -> tuple[dict, dict, dict, dict]:
        resp = self.get_asset_info(incl_disabled)
        assets = resp.get("success")
        if not assets:
            raise BaseException(f"cannot get asset info {resp}")
        tokens = {}
        exchanges = {}
        tokens_addr = {}
        tokens_decimals = {}
        # print(assets)
        for i in assets["data"]:
            if i["symbol"] not in tokens:
                tokens[i["symbol"]] = i["id"]
                tokens[i["id"]] = i["symbol"]
                tokens_addr[i["symbol"]] = i["address"]
                tokens_addr[i["address"]] = i["symbol"]
                tokens_decimals[i["symbol"]] = i["decimals"]
                tokens_decimals[i["address"]] = i["decimals"]
                if "exchanges" in i:
                    for _ in i["exchanges"]:
                        if _["exchange_id"] not in exchanges:
                            exchanges[_["exchange_id"]] = {}
                        if "trading_pairs" in _:
                            for pair in _["trading_pairs"]:
                                exchanges[_["exchange_id"]][pair["id"]] = [
                                    pair["base"],
                                    pair["quote"],
                                ]
        if incl_WETH:
            weth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2".lower()
            tokens["WETH"] = weth
            tokens_decimals["WETH"] = 18
            tokens_decimals[weth] = 18
            tokens[weth] = "WETH"
            tokens_addr[weth] = "WETH"
            tokens_addr["WETH"] = weth

        for e in exchanges:
            new_pairs = {}
            for pair in exchanges[e]:
                p = f"{tokens[exchanges[e][pair][0]]}{tokens[exchanges[e][pair][1]]}"
                new_pairs[p] = exchanges[e][pair]
                # print(p)
                exchanges[e][pair].append(p)
            for np in new_pairs:
                exchanges[e][np] = new_pairs[np]
        return tokens, exchanges, tokens_addr, tokens_decimals

    def get_0x_price(
        self,
        token_in: str,
        token_out: str,
        token_amount: float,
        integration="0x",
        side="sell",
        fake_ib=True,
    ) -> dict[str, Any]:
        token_in_addr, token_out_addr = None, None
        for i in kn_traded_full:
            if i.name.upper() == token_in.upper():
                token_in_addr = i.addresses[-1]
                decimals_in = i.decimals
            if i.name.upper() == token_out.upper():
                token_out_addr = i.addresses[-1]
                decimals_out = i.decimals
            if isinstance(token_in_addr, str) and isinstance(token_out_addr, str):
                break
        if not (isinstance(token_in_addr, str) and isinstance(token_out_addr, str)):
            print(f"can't find token addresses for {token_in} and {token_out}")
            return {"failed": "can't find token addresses"}

        params_add = {}
        if integration == "paraswap":
            if side == "sell":
                params_add = {
                    "amount": str(convert_float_to_twei(token_amount, decimals_in))
                }
            elif side == "buy":
                params_add = {
                    "amount": str(convert_float_to_twei(token_amount, decimals_out))
                }
            if len(params_add) == 0:
                raise BaseException(
                    f"cannot calculate token amount {token_amount} side{side}"
                )

            params = {
                "from": token_in_addr,
                "to": token_out_addr,
                "takerAddress": "0x0000000000000000000000000000000000000000",
                "txOrigin": "0xBA6a9d57D22889630FB731f80625d7786EE36157",
                "side": side.upper(),
                "integration": integration,
            }
            for key, value in params_add.items():
                params[key] = value
        elif integration == "0x":
            params = {
                "sellTokenAddress": token_in_addr,
                "buyTokenAddress": token_out_addr,
                "sellAmountBaseUnits": str(
                    convert_float_to_twei(token_amount, decimals_in)
                ),
                "takerAddress": "0x0000000000000000000000000000000000000000",
                "txOrigin": "0xBA6a9d57D22889630FB731f80625d7786EE36157",
                "comparisonPrice": "10000000",
                "protocolVersion": "4",
                "ib": str(fake_ib),
                "integration": integration,
            }

        return self.get_0x_rate(params)

    def get_0x_rate_out_to_in(
        self,
        token_in: str,
        token_out: str,
        token_in_amount: int,
    ) -> float:
        resp = self.get_0x_price(token_in, token_out, token_in_amount)
        if not (p := resp.get("success")):
            return 0
        if not isinstance(p, dict) and "signedOrder" in p:
            return 0
        token_in_decimals = self.tokens_decimals[p["signedOrder"]["takerToken"]]
        token_out_decimals = self.tokens_decimals[p["signedOrder"]["makerToken"]]
        token_in_amount = int(p["signedOrder"]["takerAmount"]) / 10**token_in_decimals
        token_out_amount = int(p["signedOrder"]["makerAmount"]) / 10**token_out_decimals
        return token_out_amount / token_in_amount

    def get_0x_price_two_sided(self, token: str, eth_amount: float, integration="0x"):
        t_address, w_address = None, None
        for t in kn_traded_full:
            if t.name.upper() == token:
                t_address = t.addresses[-1]
                t_decimals = t.decimals
            if t.name.upper() == "WETH":
                w_address = t.addresses[-1]
                w_decimals = t.decimals
        if not isinstance(t_address, str) or not isinstance(w_address, str):
            print(f"can't get two sides rate for {token}")
            return
        # buy rate
        resp = self.get_0x_price("WETH", token, eth_amount, integration=integration)
        if not (b_r := resp.get("success")):
            print(f"missing buy rate")
            return
        # print(b_r)
        buy_amount = (
            int(b_r["makerAmount"])
            if "makerAmount" in b_r
            else int(b_r["signedOrder"]["makerAmount"])
        )
        # sell rate
        resp = self.get_0x_price(token, "WETH", buy_amount / 10**t_decimals)
        if not (s_r := resp.get("success")):
            print(f"missing sell rate")
            return
        # print(s_r)

        sell_amount = (
            int(s_r["makerAmount"])
            if "makerAmount" in s_r
            else int(s_r["signedOrder"]["makerAmount"])
        )
        print(f"buy_amount:{buy_amount} sell_amount:{sell_amount}")
        side1_rate = convert_rate_to_binance(
            eth_amount, buy_amount / 10**t_decimals, "ETH", token
        )[2]
        side2_rate = convert_rate_to_binance(
            buy_amount / 10**t_decimals, sell_amount / 10**w_decimals, token, "ETH"
        )[2]
        side1_side = convert_rate_to_binance(
            eth_amount, buy_amount / 10**t_decimals, "ETH", token
        )[1]
        side2_side = convert_rate_to_binance(
            buy_amount / 10**t_decimals, sell_amount / 10**w_decimals, token, "ETH"
        )[1]
        if side1_side.lower() == "ask" and side2_side.lower() == "bid":
            ask, bid = side1_rate, side2_rate
        elif side2_side.lower() == "ask" and side1_side.lower() == "bid":
            ask, bid = side2_rate, side1_rate
        else:
            ask, bid = 0, 0
            print("cannot convert")
            return
        print(
            f"{self.auth_ctx}:{integration}\nask:{ask}\nbid:{bid}\nspread percent is "
            f"{round(100*(ask-bid)/((ask+bid)/2),3)}"
        )

    def get_rate_trigger(
        self, from_time=ts_millis() - 3600 * 1000, to_time=ts_millis()
    ):
        endpoint = self.endpoints["v3_token-rate-trigger"].full_path()
        past_triggers = {}
        while from_time < to_time:
            params = {
                "fromTime": from_time,
                "toTime": min(from_time + 86399999, to_time),
            }
            print(f"getting triggers from:{from_time} to:{to_time}")
            from_time += 86400000
            x = 0
            while x < 3:
                x += 1
                try:
                    resp = self.requestGET(endpoint, params=params)
                    if not (r := resp.get("success")):
                        print(f"missing triggers")
                        return
                    if (
                        isinstance(r, dict)
                        and "data" in r.keys()
                        and r["data"]
                        and r["success"]
                    ):
                        for id in r["data"]:
                            if id not in past_triggers:
                                past_triggers[id] = r["data"][id]
                            else:
                                past_triggers[id] += r["data"][id]

                    break
                except Exception as e:
                    print(f"exception {e.__repr__(), e} in {endpoint}")
                    if x == 3:
                        return
        return past_triggers

    def get_trade_history_new(
        self, from_time=ts_millis() - 86400 * 1000, to_time=ts_millis()
    ) -> list[dict[str, Any]]:
        endpoint = self.endpoints["v3_tradehistory"].full_path()
        past_trades = []
        while from_time < to_time:
            params = {
                "fromTime": from_time,
                "toTime": min(from_time + 86399999, to_time),
            }
            from_time += 86400000
            x = 0
            while x < 3:
                x += 1
                try:
                    resp = self.requestGET(endpoint, params=params)
                    if not (r := resp.get("success")):
                        print(f"missing trades")
                        return past_trades
                    if (
                        isinstance(r, dict)
                        and "data" in r.keys()
                        and r["data"]
                        and ("data" in r["data"])
                        and r["data"]["data"]
                    ):
                        for e in r["data"]["data"]:
                            if bool(r["data"]["data"][e]):
                                for pair_id in r["data"]["data"][e]:
                                    for trade in r["data"]["data"][e][pair_id]:
                                        trade["pair_id"] = int(pair_id)
                                        # print(int(e),int(pair_id))
                                        trade["pair"] = self.exchanges[int(e)][
                                            int(pair_id)
                                        ][2]
                                        trade["pair"] = trade["pair"].replace(
                                            f"-{int(e)}", ""
                                        )
                                        trade["exchange_id"] = int(e)
                                        past_trades.append(trade)
                    break
                except Exception as e:
                    print(trade, pair_id, e)
                    print(f"exception {e.__repr__(), e} in trade_history_3")
                    if x == 3:
                        return past_trades
        return past_trades

    def get_open_orders(self) -> dict[str, Any]:
        endpoint = self.endpoints["v3_open-orders"].full_path()
        params = None
        x = 0
        while x < 3:
            x += 1
            try:
                resp = self.requestGET(endpoint, params=params)
                if not (r := resp.get("success")):
                    print(f"missing open orders")
                    return {"failed": "missing open orders"}
                # print(r)
                if isinstance(r, dict) and "success" in r and r["success"]:
                    return r
                break
            except Exception as e:
                print(f"exception {e.__repr__(), e} in open_orders")
                if x == 3:
                    return {"failed": e.__repr__()}
        return {"failed": "unknown error"}

    def get_price_from_0x_levels(
        self, zerox_levels: dict, token_in: str, token_out: str, amount_in: float
    ) -> float:
        token_in_addr = self.tokens_addr[token_in].lower()
        token_in_decimals = self.tokens_decimals[token_in]
        token_out_addr = self.tokens_addr[token_out].lower()
        price = zerox_levels[f"{token_in_addr}_{token_out_addr}"]
        total_in_amount = 0
        total_out_amount = 0
        for level in price:
            in_amount = level[0] / 10**token_in_decimals
            total_out_amount += (in_amount - total_in_amount) * level[1] / 10**18
            total_in_amount = in_amount
            if total_in_amount > amount_in:
                excess_in_amount = total_in_amount - amount_in
                excess_out_amount = excess_in_amount * level[1] / 10**18
                total_out_amount -= excess_out_amount
                break
        if total_in_amount < amount_in:
            return 0
        return total_out_amount / amount_in if amount_in > 0 else 0

    def _requestGET_retry(
        self, endpoint: str, params: dict, results: list, retries: int = 3
    ):
        """Retry requestGET in case of exception"""
        x = 0
        while x < retries:
            x += 1
            try:
                resp = self.requestGET(endpoint, params=params)
                if not (r := resp.get("success")):
                    print(f"Cannot get: {endpoint}")
                    return
                if isinstance(r, dict) and "data" in r.keys() and r["data"]:
                    results += r["data"]
                break
            except Exception as e:
                print(f"exception {e.__repr__(), e} in {endpoint}")
                if x == retries:
                    return

    def get_activities(
        self,
        from_time=ts_millis() - 86400 * 1000,
        to_time=ts_millis(),
        action="set_rates",
    ):
        """Get activities from the reserve."""
        endpoint = self.endpoints["v3_activities"].full_path()
        list_activities = []
        while from_time < to_time:
            params = {
                "actions": action,
                "fromTime": from_time,
                "toTime": min(from_time + 86399999, to_time),
            }
            from_time += 86400000
            self._requestGET_retry(endpoint, params, list_activities)
        return list_activities

    def get_0x_quote_logs(
        self,
        from_time=ts_millis() - 86400 * 1000,
        to_time=ts_millis(),
        action="quote",
    ) -> list[dict[str, Any]]:
        print(from_time, to_time, type(from_time), type(to_time))
        time_unit_to_split_requests_ms = 3600_000
        endpoint = self.endpoints["0x_activity_logs"].full_path()
        quote_logs = []
        while from_time < to_time:
            params = {
                "type": action,
                "fromTime": from_time,
                "toTime": min(from_time + time_unit_to_split_requests_ms - 1, to_time),
                # "cut":2
            }
            from_time += time_unit_to_split_requests_ms
            self._requestGET_retry(endpoint, params, quote_logs)
        return quote_logs

    def get_quotes(
        self, from_time: int, to_time: int, cut: int = 2, verbose: bool = False
    ) -> list[dict[str, Any]]:
        """Get RFQs for 0x, Paraswap, Hashflow. See also `get_all_quotes` for a more
        convenient way to get quotes."""
        params = {
            "type": "quote",
            "fromTime": from_time,
            "toTime": to_time,
            "cut": cut,
        }
        resp_with_stats = response_stats(self.requestGET)
        resp = resp_with_stats(
            self.endpoints["0x_activity_logs"].full_path(), params=params, timeout=120
        )
        rfqs = []
        stats = (
            {"fromTime": params["fromTime"], "toTime": params["toTime"]}
            if verbose
            else {}
        )
        if "success" in resp.keys():
            reply = resp["success"]
            if verbose:
                stats["success"] = True
                print(resp["stats"] | stats)
            rfqs = sorted(reply["data"], key=lambda d: d["id"])
        else:
            # stats["success"] = False
            msg = f"Request failed for [{from_time}, {to_time}], with: {resp['failed']}"
            raise ValueError(msg)
        return rfqs

    def get_all_quotes(
        self, start_dt: str, end_dt: str, step: timedelta, verbose: bool = False
    ) -> list[dict[str, Any]]:
        """Get quote logs for 0x, paraswap, hashflow RFQs, using the given time range
        and step.
        Args:
            start_dt: start date-time in format: "DD-MM-DD HH:MM:SS"
            end_dt: end date-time in format: "YYYY-MM-DD HH:MM:SS"
            tep: time step in hours or minutes or else
            verbose: print progress
        Example:
            start_dt = "15/2/24 13:00:00.0+00:00"
            end_dt = "15/2/24 15:25:59.999+00:00"
            q_logs =  get_all_quotes(start_dt, end_dt, timedelta(hours=3))
        Returns:
            list of quote logs
        """
        from_time = str_to_dtime(start_dt)
        to_time = str_to_dtime(end_dt)
        almost_step = step - timedelta(seconds=0.001)
        rfqs = []
        _timer_start_run = timer()
        for date in dates_gen(step, from_time, to_time):
            _rfqs = self.get_quotes(dt_ts_milis(date), dt_ts_milis(date + almost_step))
            rfqs += _rfqs
            if verbose:
                print(f"{date}, rfqs number: {len(_rfqs)}")
        if verbose:
            _timer_end_run = timer()
            # _dt_finished = datetime.now()
            print(
                f"Download took: {timedelta(seconds=_timer_end_run - _timer_start_run)}"
            )
            # print(f"Finished at: {_dt_finished}")
        return rfqs

    def blacklist_0x_get(self) -> dict[str, Any]:
        return self.requestGET(self.endpoints["0x_blacklist"].full_path())

    def get_banned_addresses(self) -> list[str]:
        """Get only banned addresses from the 0x blacklist data."""
        try:
            banned = self.blacklist_0x_get()["success"]["data"]
        except KeyError as e:
            lgr.error(f"Cannot get banned addresses - KeyError: {e}")
            return []
        banned_addr = [a["address"] for a in banned]
        return [i.lower() for i in banned_addr]

    def blacklist_0x_set(
        self, list_of_addresses_and_desc: list, list_type="add"
    ) -> dict[str, Any]:
        """
        :param list_of_addresses_and_desc: [[address1, desc1],...,[addressN, descN]]
        :param list_type: "add" adds, "remove" removes
        :return:
        """
        if list_type not in ["add", "remove"]:
            return {"failed": "list_type must be 'add' or 'remove'"}
        endpoint = self.endpoints["0x_blacklist"].full_path()
        params: dict[str, list] = {}
        params[list_type] = []
        if list_type == "add":
            for add, desc in list_of_addresses_and_desc:
                bl = {"address": add, "description": desc}
                params[list_type].append(bl)
        else:
            params[list_type] = list_of_addresses_and_desc
        return self.requestPOST(endpoint, json=params)

    def whitelist_0x_get(self) -> dict[str, Any]:
        return self.requestGET(self.endpoints["0x_whitelist"].full_path())

    def whitelist_0x_set(
        self, list_of_addresses_and_desc: list, list_type="add"
    ) -> dict[str, Any]:
        """
        :param list_of_addresses_and_desc: [[address1, desc1],...,[addressN, descN]]
        :param list_type: "add" adds, "remove" removes
        :return:
        """
        endpoint = self.endpoints["0x_whitelist"].full_path()
        params: dict[str, list] = {}
        params[list_type] = []
        for add, desc in list_of_addresses_and_desc:
            bl = {"address": add, "description": desc}
            params[list_type].append(bl)
        return self.requestPOST(endpoint, json=params)

    def get_feed_configuration(self) -> dict[str, Any]:
        return self.requestGET(self.endpoints["v3_feed-configurations"].full_path())

    def get_rates(
        self, from_time=ts_millis() - 86400 * 1000, to_time=ts_millis()
    ) -> dict[str, Any]:
        activities = self.get_activities(from_time, to_time, "set_rates")
        # print(activities)
        result: dict[str, Any] = {}
        for actitvity in activities:
            # print(actitvity)
            params = actitvity["params"]
            if actitvity["action"] == "set_rates":
                is_mining_ok = (
                    1 if actitvity["mining_status"].lower() != "failed" else 0
                )
                rates = zip(
                    params["assets"],
                    params["buys"],
                    params["sells"],
                    params["afpMid"],
                    params["triggers"],
                )
                timestamp = int(actitvity["timestamp"])
                for token, buy, sell, afpMid, trigger in rates:
                    if token not in result:
                        result[token] = []
                    result[token].append(
                        {
                            "buy": 1 / (buy / 10**18) if buy != 0 else 0,
                            "sell": sell / 10**18,
                            "afpmid": afpMid / 10**18,
                            "timestamp": timestamp,
                            "trigger": 1 if trigger else 0,
                            "mining_ok": 1 if is_mining_ok else 0,
                        }
                    )
        return result

    def get_vol_prices(
        self, symbol: str, from_ts: int, to_ts: int, interval: int
    ) -> dict[str, Any]:
        """Get volatility and prices for a symbol."""
        params = {"symbol": symbol, "from": from_ts, "to": to_ts, "interval": interval}
        return self.requestGET(
            self.endpoints["price-volatility_prices"].full_path(), params=params
        )

    def get_volatility(self, pairs: str) -> dict[str, Any]:
        params = {"pairs": pairs}
        return self.requestGET(
            self.endpoints["price-volatility_price-volatility"].full_path(),
            params=params,
        )

    def m_t_m(self, base: str, quote: str, timestamp_sec: int | None = None) -> float:
        if base == "WETH":
            base = "ETH"
        if quote == "WETH":
            quote = "ETH"
        params: dict[str, Any] = dict(base=base, quote=quote)
        if timestamp_sec is None:
            url = self.endpoints["mark-to-market_rate"].full_url()
        else:
            params["time"] = timestamp_sec
            url = self.endpoints["mark-to-market_historical/rate"].full_url()
        resp_with_stats = response_stats(self.requestGET_url)
        resp = resp_with_stats(url, params, timeout=120)
        reply = Response()
        mtm = 0.0
        if "success" in resp.keys():
            reply = resp["success"]
            stats = {"base": params["base"], "quote": params["quote"], "success": True}
            print(resp["stats"] | stats)
            try:
                mtm = reply.json()["data"]["rate"]
            except KeyError:
                print(f"No rate for [{base}, {quote}], data: {reply.json()}")
        else:
            print(
                f"Request failed for [{base}, {quote}], with: {resp['failed']}, "
                f"stats: {resp['stats']}"
            )
        return mtm
