import json
import os
from enum import Enum
from time import time

from kyberReserve.tokens import QUOTE_CURRENCIES


class AuthContext(Enum):
    STAGING = 1
    PROD = 2
    PROD_RW = 3


def ts_millis():
    return int(time() * 1000)


def wei_to_eth(wei: int) -> float:
    return wei / 1e18


def load_json_file(key_file: str):
    with open(key_file) as fh:
        auth_data = json.load(fh)
    return auth_data


class AuthenticationData:
    """ "Manage authentication data for Reserve API."""

    def __init__(self, key_file: str) -> None:
        self.data = load_json_file(key_file)

    def get_ctx(self, authContext: AuthContext) -> tuple[str, str, bytes]:
        """Get HOST, KEY_ID, SECRET based on context usage, production or test server.
        :param authContext: AuthContext.STAGING, AuthContext.PROD, AuthContext.PROD_RW
        """
        is_testnet = True if authContext == AuthContext.STAGING else False
        prod_rw = True if authContext == AuthContext.PROD_RW else False
        host = self.data["test"]["HOST"] if is_testnet else self.data["prod"]["HOST"]
        if is_testnet:
            key_id = self.data["test"]["creds"]["KEY_ID"]
            secret = self.data["test"]["creds"]["SECRET"]
        else:
            key_id = (
                self.data["prod"]["creds_rw"]["KEY_ID"]
                if prod_rw
                else self.data["prod"]["creds"]["KEY_ID"]
            )
            secret = (
                self.data["prod"]["creds_rw"]["SECRET"]
                if prod_rw
                else self.data["prod"]["creds"]["SECRET"]
            )
        return host, key_id, secret.encode()


def convert_float_to_twei(input_num: float, token_decimals: int):
    str_num = f"{input_num:.18f}"
    try:
        ind = str_num.index(".") + 1
    except ValueError:
        ind = len(str_num)

    for _ in range(token_decimals):
        str_num += "0"
    if len(str_num[ind:]) > token_decimals:
        str_num = str_num[:ind] + str_num[ind : ind + token_decimals]
    str_num = str_num.replace(".", "")
    return int(str_num)


def convert_rate_to_binance(
    in_amount: float,
    out_amount: float,
    in_currency: str,
    out_currency: str,
    quote_currencies=QUOTE_CURRENCIES,
) -> tuple | None:
    importance_in, importance_out = 100, 100
    convert_currencies = {"WETH": "ETH", "WBTC": "BTC"}
    if in_currency in convert_currencies:
        in_currency = convert_currencies[in_currency]
    if out_currency in convert_currencies:
        out_currency = convert_currencies[out_currency]
    if in_currency in quote_currencies:
        importance_in = quote_currencies.index(in_currency)
    if out_currency in quote_currencies:
        importance_out = quote_currencies.index(out_currency)
    if importance_in == importance_out or in_amount <= 0 or out_amount <= 0:
        print(
            f"weird rate output for in:{in_amount} out:{out_amount}"
            f" in_token:{in_currency} out_token:{out_currency}"
        )
        return None
    if (
        importance_in < importance_out
    ):  # in_currency is the quote we buy with in to get out
        # print(f"{out_currency}{in_currency} ASK {in_amount/out_amount}")
        return (
            f"{out_currency}{in_currency}",
            "ASK",
            in_amount / out_amount,
            out_currency,
            in_currency,
        )
    else:  # out currency is the quote se sell base for quote
        # print(f"{in_currency}{out_currency} BID {out_amount / in_amount}")
        return (
            f"{in_currency}{out_currency}",
            "BID",
            out_amount / in_amount,
            in_currency,
            out_currency,
        )


def saveEveryNth(results: list, filename: str, nRes: int) -> bool:
    saved = False
    if (n_res := len(results)) >= nRes:
        if os.path.exists(filename):
            try:
                with open(filename, "r") as infile:
                    res = json.load(infile)
                    res += results
            except json.decoder.JSONDecodeError as der:
                print(f"Decoder error {der}")
                res = results
            with open(filename, "w") as outfile:
                json.dump(res, outfile)
            print(f"Saved {len(res)} results")
            saved = True
        else:
            with open(filename, "w") as outfile:
                json.dump(results, outfile)
            print(f"Saved {n_res} results")
            saved = True
    return saved
