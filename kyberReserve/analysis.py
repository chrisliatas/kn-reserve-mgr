from kyberReserve.utils import convert_rate_to_binance


def parse_0x_request(
    requests_reply: list, tokens_decimals: dict, tokens_addr: dict
) -> list:
    weth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2".lower()

    requests_simple = []
    first_time = 0
    for r in requests_reply:
        if "takerToken" in r["log"]:
            taker_token_addr = r["log"]["takerToken"]["address"]
            maker_token_addr = r["log"]["makerToken"]["address"]
            taker_token_decimals = int(r["log"]["takerToken"]["decimals"])
            maker_token_decimals = int(r["log"]["makerToken"]["decimals"])
            taker_token_amount = r["log"]["request"]["sellAmountBaseUnits"]
            maker_token_amount = r["log"]["request"]["buyAmountBaseUnits"]

        else:
            taker_token_addr = r["log"]["request"]["sellTokenAddress"]
            maker_token_addr = r["log"]["request"]["buyTokenAddress"]
            try:
                taker_token_decimals = int(tokens_decimals[taker_token_addr])
            except KeyError:
                taker_token_decimals = 18
            try:
                maker_token_decimals = int(tokens_decimals[maker_token_addr])
            except KeyError:
                maker_token_decimals = 18
            taker_token_amount = r["log"]["request"]["sellAmountBaseUnits"]
            maker_token_amount = r["log"]["request"]["buyAmountBaseUnits"]

        if "signedOrder" in r["log"]["response"]:
            resp = r["log"]["response"]["signedOrder"]
        else:
            resp = r["log"]["response"]
        if len(maker_token_amount) > 0:
            req_amount = f"{(int(maker_token_amount)/10**maker_token_decimals):.5f}"
            resp_amount = f'{int(resp["makerAmount"])/10**maker_token_decimals:.5f}'

        else:
            req_amount = f"{(int(taker_token_amount)/10**taker_token_decimals):.5f}"
            resp_amount = f'{int(resp["takerAmount"]) / 10 ** taker_token_decimals:.5f}'
        in_amount = f'{int(resp["takerAmount"]) / 10 ** taker_token_decimals:.5f}'
        out_amount = f'{int(resp["makerAmount"]) / 10 ** maker_token_decimals:.5f}'
        try:
            req_ratio = float(req_amount) / float(resp_amount)
        except ZeroDivisionError:
            continue  # very small trade

        time = r["time"]
        if len(requests_simple) == 0:
            first_time = time
        # time_delta = time - requests_simple[-1]["time"] if len(requests_simple) > 0 else 0
        time_full_delta = time - first_time
        maker_token_name = (
            "WETH"
            if maker_token_addr.lower() == weth
            else tokens_addr[maker_token_addr]
        )
        taker_token_name = (
            "WETH"
            if taker_token_addr.lower() == weth
            else tokens_addr[taker_token_addr]
        )

        if req_ratio > 1:
            req_ratio = f"{req_ratio:.2}"
        try:
            bin_pair, bin_side, bin_rate = convert_rate_to_binance(
                float(in_amount), float(out_amount), taker_token_name, maker_token_name
            )
        except TypeError as err:
            print(
                f"TypeError converting rate to binance: in_amount:{in_amount} "
                f"out_amount:{out_amount} taker_token_name:{taker_token_name} "
                f"maker_token_name:{maker_token_name} - {err}"
            )
            continue

        r = {
            "pair": bin_pair,
            "side": bin_side,
            "price": f"{bin_rate:.6}",
            # "request_amount": req_amount,
            # "request_token": taker_token_name if req_token == "taker" else maker_token_name,
            # "out_token":maker_token_name,
            "request_ratio": req_ratio,
            "time_full_delta": time_full_delta // 1000,
            "time": time // 1000,
        }
        requests_simple.append(r)
    return requests_simple


def get_analytic_eth_rate(
    analytic_rates: dict, token: str, eth_amount: float, tokens: dict
) -> dict:
    rates = {"ask": 0, "bid": 0}
    token_buy, token_sell = 0, 0
    token_index = tokens[token]
    data = None
    for i in analytic_rates["data"]:
        if i["asset"] == token_index:
            data = i
    if not data:
        return rates
    for i, d in enumerate(data["sell_amounts"]):
        if d / 10**18 >= eth_amount:
            token_buy = 1 / (data["sell_rates"][i] / 10**18)
            rates["ask"] = token_buy
            break
    for i, d in enumerate(data["buy_amounts"]):
        if d / 10**18 >= eth_amount:
            token_sell = data["buy_rates"][i] / 10**18
            rates["bid"] = token_sell
            break

    return rates


def get_analytic_eth_rate_out_to_in(
    analytic_rates: dict, token_in: str, token_out: str, eth_amount: float, tokens: dict
):
    token = None
    buy_token = False
    if token_in not in ["ETH", "WETH"]:
        token = token_in
    elif token_out not in ["ETH", "WETH"]:
        token = token_out
        buy_token = True
    if not token:
        return 0

    rates = get_analytic_eth_rate(analytic_rates, token, eth_amount, tokens)
    try:
        if buy_token:
            return 1 / rates["ask"]
        return rates["bid"]
    except ZeroDivisionError:
        return 0


def find_if_address_in_RFQs(rfqs_result: list, addresses: list):
    if not isinstance(addresses, list):
        raise BaseException("addresses input should be list")
    addresses = [a.lower() for a in addresses]
    res = {}
    requests_raw = {}
    for i in rfqs_result:
        req = i["log"]["request"]
        try:
            # old format
            addr = req["txOrigin"].lower()
        except KeyError:
            # new formats
            if "userAddress" in req:
                addr = req["userAddress"].lower()
            else:
                addr = req["trader"].lower()
        if addr in addresses:
            t = i["time"]
            req = i["log"]["request"]
            req["time"] = t
            print(i)
            if addr in res:
                res[addr].append(t)
            else:
                res[addr] = [t]
            if addr in requests_raw:
                requests_raw[addr].append(req)
            else:
                requests_raw[addr] = [req]

    res_new = {}
    for addr in res:
        count = len(res[addr])
        ts_all = res[addr]
        ts_all.sort(reverse=True)
        wait_times = []
        for ind, ts in enumerate(ts_all):
            if ind > 0:
                wait_time = ts_all[ind - 1] - ts
                wait_times.append(wait_time)
        wait_times.sort()
        if len(wait_times) > 2:
            median = wait_times[len(wait_times) // 2]
        else:
            median = 0
        median_wait = median
        res_new[addr] = {"count": count, "median_wait": median_wait}
    return res_new, requests_raw
