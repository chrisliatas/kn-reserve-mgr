from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from kyberReserve.reserveClient import ReserveClient
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


# ----------------- Pricing analysis -----------------
class Side(Enum):
    BID = 0
    ASK = 1


@dataclass
class Level:
    level: float
    price: float

    def as_dict(self):
        return {"l": self.level, "p": self.price}


@dataclass
class PWI:
    qA: float
    qB: float
    qC: float
    min_min: float

    def calculate(self, x: float) -> float:
        return (self.qA * x * x + self.qB * x + self.qC) * self.min_min


@dataclass
class RFQParams:
    assetID: int
    # Integration            Integration
    refETHAmount: float
    ethStep: float
    maxETHSizeSell: float
    minSlippage: float
    maxSlippage: float
    # enabled                bool
    # swapEnabled            bool
    askOffset: float
    bidOffset: float
    imbAmountMultiplier: float
    ethAmountToIgnoreShift: float
    ethStepMultiplier: float
    pwi: PWI


@dataclass
class MatrixRate:
    assetID: int
    totalTarget: float
    currentBalance: float
    maxImb: float
    matrix: dict[Side, list[Level]]
    param: RFQParams
    maxSell: float


def mtxToJson(mtx: dict[Side, list[Level]], sideName: bool = True) -> dict:
    if sideName:
        return {side.name: [l.as_dict() for l in lvls] for side, lvls in mtx.items()}
    else:
        return {side.value: [l.as_dict() for l in lvls] for side, lvls in mtx.items()}


def getMultiplier(isBid: bool) -> float:
    if isBid:
        return -1.0
    return 1.0


def imbalanceCalculator(
    lvl_size: float,
    lvl_p: float,
    bal_dict: dict,
    maxImbal: float,
    minImb: float,
    multiplier: float,
    pwi: PWI,
) -> tuple[float, float]:
    """Calculate imbalance spreads."""
    min_Imb = minImb
    imbSpread = 0.0
    virtual = max(bal_dict["current"] - multiplier * (lvl_size / lvl_p), 0.0)
    imbal = abs(virtual - bal_dict["target"]) / bal_dict["target"]
    imbal = min(imbal, maxImbal)
    if imbal <= min_Imb:
        min_Imb = imbal
    else:
        # imbSpread = spreadCalculate(quad_dict, imbal)
        imbSpread = pwi.calculate(imbal)
    return min_Imb, imbSpread


def matrixSideCalculator(
    pricing_debug: dict,
    bal_dict: dict,
    maxImbal: float,
    historyOffset: float,
    side_offset: dict,
    pwi: PWI,
    side: Side,
    tokenDecimals: int,
) -> tuple[list[Level], list[Level]]:
    """Calculate BID/ASK prices for the levels pricing-matrix.
    This function will add spread to matrix rate:
    1. If a level moves `currentBalance` closer to target than previous level, spread won't be added to price.
    2. If a level moves `currentBalance` further away from target than previous level or changes side, spread will be added to price.
    """
    isBid = True if side == Side.BID else False
    amts = pricing_debug["buy_amounts"] if isBid else pricing_debug["sell_amounts"]
    rates = pricing_debug["buy_rates"] if isBid else pricing_debug["sell_rates"]
    offset = side_offset["bid"] if isBid else side_offset["ask"]
    volatility = pricing_debug["debug"]["volatility"]
    multiplier = getMultiplier(isBid)
    minImb = abs(bal_dict["current"] - bal_dict["target"]) / bal_dict["target"]
    # print("Min Imbalance: ", minImb)
    levelSpread = 0.0

    imbalance_spread = []
    matrixPrice = []
    for amt, prc in zip(amts, rates):
        pLvl = amt / 10**tokenDecimals
        pPrice = prc / 10**tokenDecimals if isBid else 10**tokenDecimals / prc
        price = pPrice + historyOffset
        minImb, imbSpread = imbalanceCalculator(
            pLvl, pPrice, bal_dict, maxImbal, minImb, multiplier, pwi
        )
        # print(f"Min Imbalance: {minImb}, lvl: {pLvl}, spread: {imbSpread}")
        # if imbSpread > 0.0:
        imbalance_spread.append(Level(pLvl, imbSpread))
        spread = multiplier * (price * (imbSpread + levelSpread) + volatility)
        sideOffset = price * offset
        mtxPrice = pPrice + sideOffset + spread
        matrixPrice.append(Level(pLvl, mtxPrice))
        levelSpread += 1e-16
    return imbalance_spread, matrixPrice


def get_tokenPricing(
    kr: ReserveClient,
    asset: str,
    totalTarget: float,
    pwi: PWI,
    maxImbal: float,
    historyOffset: float,
    side_offset: dict,
    pricing_debug: dict | None = None,
) -> tuple[dict[Side, list[Level]], dict[Side, list[Level]]]:
    assetID = kr.get_assetID(asset)
    current_bal = kr.get_currentBalance(assetID)
    bal_dict = dict(current=current_bal, target=totalTarget)
    if pricing_debug is None:
        pricing_debug = kr.get_asset_rate(assetID)
    # assetDecimal = get_decimals(asset)
    ethDecimal = kr.get_decimals(asset)
    # `mtx` contains prices, `dbg` contains imbalances
    mtx: dict[Side, list[Level]] = {}
    dbug: dict[Side, list[Level]] = {}
    for side in Side:
        dbug[side], mtx[side] = matrixSideCalculator(
            pricing_debug,
            bal_dict,
            maxImbal,
            historyOffset,
            side_offset,
            pwi,
            side,
            ethDecimal,
        )
    return mtx, dbug


# ----------------- Rebalance analysis -----------------


@dataclass
class AssetTarget:
    """Target settings for an asset."""

    total: float
    reserve: float
    rebalanceThreshold: float
    transferThreshold: float
    minWithdrawThreshold: float
    triggerRebalanceTS: int


@dataclass
class RebalanceQuadratic:
    """
    Params of quadratic equation for size and price calculation.
    """

    sizeA: float
    sizeB: float
    sizeC: float
    priceA: float
    priceB: float
    priceC: float
    priceOffset: float

    def sizeCalculation(self, x: float) -> float:
        """Calculate quadratic base on size"""
        return self.sizeA * x * x + self.sizeB * x + self.sizeC

    def priceCalculation(self, x: float) -> float:
        """Calculate quadratic base on price"""
        return (self.priceA * x * x + self.priceB * x + self.priceC) * self.priceOffset


@dataclass
class Asset:
    id: int
    symbol: str
    decimals: int
    rebalanceQuadratic: RebalanceQuadratic
    target: AssetTarget
    maxImbalanceRatio: float


@dataclass
class AssetBalance:
    """Balance - contains balance information for an asset."""

    assetID: int
    symbol: str
    reserve: float
    virtual: float
    exchanges: list[dict]

    def total(self) -> float:
        """Total - returns total balance."""
        tot = self.reserve + self.virtual
        for ex in self.exchanges:
            tot += (
                ex["available"]
                + ex["locked"]
                + ex["margin_balance"]["free"]
                - ex["margin_balance"]["borrowed"]
            )
        return tot


@dataclass
class Coin:
    """Coin - contains coin's information for rebalancing."""

    asset: Asset
    balance: AssetBalance
    binanceBalance: float

    def imbalance(self) -> float:
        """Imbalance - coin's imbalance"""
        return self.balance.total() - self.asset.target.total

    def imbalanceRatio(self) -> float:
        """ImbalanceRatio - coin's imbalance ratio"""
        return self.imbalance() / self.asset.target.total

    def rebalanceSizeOffset(self) -> float:
        """RebalanceOffset - coin's rebalance offset"""
        x = abs(self.imbalanceRatio())
        return self.asset.rebalanceQuadratic.sizeCalculation(x)

    def rebalancePriceOffset(
        self, maxRebalanceOffset: float = 0.004, minRebalanceOffset: float = -0.005
    ) -> float:
        """RebalancePriceOffset - coin's rebalance price offset"""
        x = abs(abs(self.imbalanceRatio()) - self.asset.target.rebalanceThreshold)
        offset = self.asset.rebalanceQuadratic.priceCalculation(x)
        offset = min(offset, maxRebalanceOffset)
        offset = max(offset, minRebalanceOffset)
        return offset


def get_assetBalance(assetID, balances: list[dict]) -> dict[str, Any]:
    b_i = {}
    for i in balances:
        if i["asset_id"] == assetID:
            b_i = i
            break
    return b_i


def assetBalance(kr: ReserveClient, assetID: int, balances: list[dict]) -> AssetBalance:
    b_i = get_assetBalance(assetID, balances)
    return AssetBalance(
        assetID=assetID,
        symbol=b_i["symbol"],
        reserve=b_i["reserve"],
        virtual=0.0,
        exchanges=b_i["exchanges"],
    )


def randReservBalanceOffset(
    seed: int | None, amtFrom: float, amtTo: float, size: int
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pricesX = rng.uniform(amtFrom, amtTo, size)
    pricesX.sort()
    return pricesX


def testReserveRebalanceQuad(
    reserveAmntSeed: float,
    resOffsetLow: float,
    resOffsetHigh: float,
    nOffsets: int,
    randSeed: int | None,
    exchanges: list[dict],
    asset: Asset,
) -> tuple[list, list]:
    resvBalOffsets = randReservBalanceOffset(
        randSeed, resOffsetLow, resOffsetHigh, nOffsets
    )
    usdtCoinVars = []
    for i in resvBalOffsets:
        bal = AssetBalance(
            assetID=asset.id,
            symbol=asset.symbol,
            reserve=reserveAmntSeed + i,
            virtual=0.0,
            exchanges=exchanges,
        )
        usdtCoinVars.append(
            Coin(asset=asset, balance=bal, binanceBalance=bal.exchanges[0]["available"])
        )

    imbalRatios = [i.imbalanceRatio() for i in usdtCoinVars]
    res = [i.rebalancePriceOffset() for i in usdtCoinVars]
    # totBals = [i.balance.total() for i in usdtCoinVars]
    return imbalRatios, res
