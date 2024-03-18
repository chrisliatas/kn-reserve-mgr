QUOTE_CURRENCIES = ["DAI", "USDT", "BUSD", "USDC", "BTC", "WBTC", "WETH", "ETH"]


def decimals_by_token(token_name, token_list):
    for i in token_list:
        if i.name == token_name:
            return i.decimals


class TokenItem:
    def __init__(
        self,
        name,
        decimals,
        addresses: list,
        min_res,
        max_per_block,
        max_total,
        quote_rate=1,
        chain="eth_mainnet",
    ):
        self.name = name
        self.decimals = decimals
        self.addresses = addresses
        self.min_res = min_res
        self.max_per_block = max_per_block
        self.max_total = max_total
        self.quote_rate = quote_rate
        self.chain = chain


class rebalance_token(TokenItem):
    def __init__(
        self, name, decimals, addresses: list, min_res, max_per_block, max_total
    ):
        super().__init__(name, decimals, addresses, min_res, max_per_block, max_total)
        self.token_imbalances = {}  # imbalances of token amounts per token
        self.quote_imbalances = {}  # imbalances of quote amounts per token

    def add_trade(
        self, token_name: str, amount_base: float, amount_quote: float, buy: bool
    ):
        """
        buy is for token units reserve bought, it is positive in token and negative in
        self(quote)
        """
        multiplier_base, multiplier_quote = -1, 1
        if buy:
            multiplier_base, multiplier_quote = 1, -1
        if token_name in self.token_imbalances:
            self.token_imbalances[token_name] += multiplier_base * amount_base
            self.quote_imbalances[token_name] += multiplier_quote * amount_quote
        else:
            self.token_imbalances[token_name] = multiplier_base * amount_base
            self.quote_imbalances[token_name] = multiplier_quote * amount_quote

    def reset_values(self):
        self.token_imbalances = {}  # imbalances of token amounts per token
        self.quote_imbalances = {}  # imbalances of quote amounts per token


bsc_test_btc = TokenItem(
    "BTC",
    8,
    ["0xDe06c589cbdd69B96025413Fd82BfB2079fb790A".lower()],
    10,
    500000000,
    500000000,
    50_000,
    "bsc_testnet",
)

bsc_test_usdt = TokenItem(
    "USDT",
    6,
    ["0xfCdCcd4cD29bd4B53274C8E900b00a6DB3460e08".lower()],
    1000000000000000,
    50000000000000000000000,
    50000000000000000000000,
    1,
    "bsc_testnet",
)

bsc_test_link = TokenItem(
    "LINK",
    18,
    ["0xC7327B55218103194F69061c65Ad24D3d9DBFa51".lower()],
    3000000000000000,
    10000000000000000000000,
    10000000000000000000000,
    25,
    "bsc_testnet",
)

bsc_test_aave = TokenItem(
    "AAVE",
    18,
    ["0x5466cBa4D2D2f8603EEd8433D20fe64870428Bf3".lower()],
    421000000000000000,
    1000000000000000000000,
    1000000000000000000000,
    400,
    "bsc_testnet",
)


bsc_test_1inch = TokenItem(
    "1INCH",
    18,
    ["0x0AE0Ed81FA2c476f199061c51dd9e4f7860Df6FF".lower()],
    10000000000000000,
    20000000000000000000000,
    20000000000000000000000,
    4,
    "bsc_testnet",
)

bsc_test_busd = TokenItem(
    "BUSD",
    18,
    ["0x1486e4Ac531A6446cd5A5D61D16983f96a871100".lower()],
    10000000000000000,
    200000000000000000000000,
    200000000000000000000000,
    1,
    "bsc_testnet",
)

bsc_test_usdc = TokenItem(
    "USDC",
    18,
    ["0x1E33ce46Be97ee7a0E85D6F6e32d59E94BCf3E80".lower()],
    10000000000000000,
    300000000000000000000000,
    300000000000000000000000,
    1,
    "bsc_testnet",
)

bsc_test_bnb = TokenItem(
    "BNB",
    18,
    ["0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".lower()],
    10000000000000,
    2000000000000000000000,
    2000000000000000000000,
    250,
    "bsc_testnet",
)

bsc_bnb = TokenItem(
    "BNB",
    18,
    ["0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".lower()],
    10000000000000,
    2000000000000000000000,
    2000000000000000000000,
    250,
    "bsc_mainnet",
)

bsc_usdt = TokenItem(
    "USDT",
    18,
    ["0x55d398326f99059ff775485246999027b3197955".lower()],
    1000000000000000,
    200000000000000000000000,
    200000000000000000000000,
    1,
    "bsc_mainnet",
)

bsc_busd = TokenItem(
    "BUSD",
    18,
    ["0xe9e7cea3dedca5984780bafc599bd69add087d56".lower()],
    1000000000000000,
    200000000000000000000000,
    200000000000000000000000,
    1,
    "bsc_mainnet",
)

bsc_ltc = TokenItem(
    "LTC",
    18,
    ["0x4338665CBB7B2485A8855A139b75D5e34AB0DB94".lower()],
    10000000000000,
    1000000000000000000000,
    1000000000000000000000,
    180,
    "bsc_mainnet",
)

bsc_xrp = TokenItem(
    "XRP",
    18,
    ["0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE".lower()],
    10000000000000000,
    300000000000000000000000,
    300000000000000000000000,
    0.5,
    "bsc_mainnet",
)


bsc_btc = TokenItem(
    "BTC",
    18,
    ["0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c".lower()],
    100000000000,
    1000000000000000000,
    1000000000000000000,
    60_000,
    "bsc_mainnet",
)

bsc_eth = TokenItem(
    "ETH",
    18,
    ["0x2170ed0880ac9a755fd29b2688956bd959f933f8".lower()],
    1000000000000,
    100000000000000000000,
    100000000000000000000,
    2_000,
    "bsc_mainnet",
)


weth = TokenItem("WETH", 18, ["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"], 1, 0, 0)
knc = TokenItem(
    "KNC",
    18,
    [
        "0xdd974d5c2e2928dea5f71b9825b8b646686bd200",
        "0xdefa4e8a7bcba345f687a2f1456f5edd9ce97202",
    ],
    1500000000000000,
    50000000000000000000000,
    50000000000000000000000,
)
omg = TokenItem(
    "OMG",
    18,
    ["0xd26114cd6ee289accf82350c8d8487fedb8a0c07"],
    500000000000000,
    10000000000000000000000,
    10000000000000000000000,
)
eos = TokenItem(
    "EOS", 18, ["0x86fa049857e0209aa7d9e616f7eb3b3b78ecfdb0"], 1000000000000000, 0, 0
)
snt = TokenItem(
    "SNT",
    18,
    ["0x744d70fdbe2ba4cf95131626614a1763df805b9e"],
    30000000000000000,
    700000000000000000000000,
    700000000000000000000000,
)
gto = TokenItem("GTO", 5, ["0xc5bbae50781be1669306b9e001eff57a2957b09d"], 10, 0, 0)
req = TokenItem(
    "REQ", 18, ["0x8f8221afbb33998d8584a2b05749ba73c37a938a"], 1000000000000000, 0, 0
)
bat = TokenItem(
    "BAT",
    18,
    ["0x0d8775f648430679a709e98d2b0cb6250d2887ef"],
    3333333333333333,
    150000000000000000000000,
    150000000000000000000000,
)
mana = TokenItem(
    "MANA",
    18,
    ["0x0f5d2fb29fb7d3cfee444a200298f468908cc942"],
    3333333333333333,
    200000000000000000000000,
    200000000000000000000000,
)
powr = TokenItem(
    "POWR",
    6,
    ["0x595832f8fc6bf59c85c527fec3740a1b7a361269"],
    50000,
    100000000000,
    100000000000,
)
elf = TokenItem(
    "ELF",
    18,
    ["0xbf2179859fc6d5bee9bf9158632dc51678a4100e"],
    50000000000000000,
    120000000000000000000000,
    120000000000000000000000,
)
eth = rebalance_token(
    "ETH", 18, ["0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"], 1, 0, 0
)
appc = TokenItem(
    "APPC", 18, ["0x1a7a8bd9106f2b8d977e08582dc7d24c723ab0db"], 1000000000000000, 0, 0
)
eng = TokenItem("ENG", 8, ["0xf0ee6b27b759c9893ce4f094b49ad28fd15a23e4"], 10000, 0, 0)
rdn = TokenItem(
    "RDN", 18, ["0x255aa6df07540cb5d3d297f0d0d4d84cb52bc8e6"], 1000000000000000, 0, 0
)
salt = TokenItem("SALT", 8, ["0x4156d3342d5c385a87d264f90653733592000581"], 10000, 0, 0)
bqx = TokenItem("BQX", 8, ["0x5af2be193a6abca9c8817001f45744777db30756"], 10000, 0, 0)
ast = TokenItem("AST", 4, ["0x27054b13b1b798b345b591a4d22e6562d47ea75a"], 10, 0, 0)
link = TokenItem(
    "LINK",
    18,
    ["0x514910771af9ca656af840dff83e8264ecf986ca"],
    150000000000000,
    10000000000000000000000,
    10000000000000000000000,
)
zil = TokenItem(
    "ZIL", 12, ["0x05f4a42e251f2d52b8ed15e9fedaacfcef1fad27"], 10000000000, 0, 0
)
dgx = TokenItem(
    "DGX",
    9,
    ["0x4f3afec4e5a3f2a6a1a411def7d7dfe50ee057bf"],
    100000,
    2000000000000,
    2000000000000,
)
abt = TokenItem(
    "ABT", 18, ["0xb98d4c97425d9908e66e53a6fdf673acca0be986"], 100000000000000, 0, 0
)
enj = TokenItem(
    "ENJ",
    18,
    ["0xf629cbd94d3791c9250152bd8dfbdf380e2a3b9c"],
    2000000000000000,
    160000000000000000000000,
    160000000000000000000000,
)
ae = TokenItem(
    "AE", 18, ["0x5ca9a71b1d01849c0a95490cc00559717fcf0d1d"], 1000000000000000, 0, 0
)
aion = TokenItem(
    "AION", 8, ["0x4ceda7906a5ed2179785cd3a40a69ee8bc99c466"], 100000, 0, 0
)
blz = TokenItem(
    "BLZ",
    18,
    ["0x5732046a883704404f284ce41ffadd5b007fd668"],
    10000000000000000,
    300000000000000000000000,
    300000000000000000000000,
)
poly = TokenItem(
    "POLY",
    18,
    ["0x9992ec3cf6a55b00978cddf2b27bc6882d88d1ec"],
    100000000000000000,
    50000000000000000000000,
    50000000000000000000000,
)
edu = TokenItem(
    "EDU", 18, ["0xf263292e14d9d8ecd55b58dad1f1df825a874b7c"], 100000000000000000, 0, 0
)
lba = TokenItem(
    "LBA", 18, ["0xfe5f141bf94fe84bc28ded0ab966c16b17490657"], 1000000000000000, 0, 0
)
cvc = TokenItem(
    "CVC",
    8,
    ["0x41e5560054824ea6b0732e656e3ad64e20e94e45"],
    1000000,
    9000000000000,
    9000000000000,
)
tusd = TokenItem(
    "TUSD", 18, ["0x8dd5fbce2f6a956c3022ba3663759011dd51e73e"], 10000000000000000, 0, 0
)
pnt = TokenItem(
    "PNT",
    18,
    ["0x89ab32156e46f46d02ade3fecbe5fc4243b9aaed"],
    10000000000000000,
    15000000000000000000000,
    15000000000000000000000,
)
pay = TokenItem(
    "PAY",
    18,
    ["0xb97048628db6b661d4c2aa833e95dbe1a905b280"],
    100000000000000000,
    40000000000000000000000,
    40000000000000000000000,
)
bnt = TokenItem(
    "BNT",
    18,
    ["0x1f573d6fb3f13d689ff844b4ce37794d79a7ff1c"],
    1000000000000000,
    30000000000000000000000,
    30000000000000000000000,
)
dta = TokenItem(
    "DTA", 18, ["0x69b148395ce0015c13e36bffbad63f49ef874e03"], 100000000000000000, 0, 0
)
chat = TokenItem(
    "CHAT", 18, ["0x442bc47357919446eabc18c7211e57a13d983469"], 10000000000000000, 0, 0
)
poe = TokenItem("POE", 8, ["0x0e0989b1f9b8a38983c2ba8053269ca62ec9b195"], 1000000, 0, 0)
sub = TokenItem("SUB", 2, ["0x12480e24eb5bec1a9d4369cab6a80cad3c0a377a"], 1, 0, 0)
wax = TokenItem("WAX", 8, ["0x39bb259f66e1c59d5abef88375979b4d20d98022"], 1000000, 0, 0)
rep = TokenItem(
    "REP",
    18,
    [
        "0x1985365e9f78359a9b6ad760e32412f4a445e862",
        "0x221657776846890989a759ba2973e427dff5c9bb",
    ],
    100000000000000,
    3000000000000000000000,
    3000000000000000000000,
)
bnb = TokenItem(
    "BNB", 18, ["0xb8c77482e45f1f44de1745f52c74426c631bdd52"], 100000000000000, 0, 0
)
zrx = TokenItem(
    "ZRX",
    18,
    ["0xe41d2489571d322189246dafa5ebde1f4699f498"],
    5000000000000000,
    100000000000000000000000,
    100000000000000000000000,
)
ren = TokenItem(
    "REN", 18, ["0x408e41876cccdc0f92210600ef50372656052a38"], 100000000000000000, 0, 0
)
qkc = TokenItem(
    "QKC",
    18,
    ["0xea26c4ac16d4a5a106820bc8aee85fd0b7b2b664"],
    100000000000000000,
    60000000000000000000000,
    60000000000000000000000,
)
dat = TokenItem(
    "DAT", 18, ["0x81c9151de0c8bafcd325a57e3db5a5df1cebf79c"], 1000000000000000000, 0, 0
)
ost = TokenItem(
    "OST",
    18,
    ["0x2c4e8f2d746113d0696ce89b35f0d8bf88e0aeca"],
    500000000000000000,
    600000000000000000000000,
    600000000000000000000000,
)
eko = TokenItem(
    "EKO", 18, ["0xa6a840e50bcaa50da017b91a0d86b8b2d41156ee"], 1000000000000000000, 0, 0
)
wbtc = TokenItem(
    "WBTC",
    8,
    ["0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"],
    10,
    2500000000,
    2500000000,
)
bix = TokenItem(
    "BIX", 18, ["0xb3104b4b9da82025e8b9f8fb28b3553ce2f67069"], 100000000000000000, 0, 0
)
cdt = TokenItem(
    "CDT", 18, ["0x177d39ac676ed1c67a2b268ad7f1e58826e5b0af"], 1000000000000000000, 0, 0
)
mco = TokenItem(
    "MCO",
    8,
    ["0xb63b606ac810a52cca15e44bb630fd42d8d1d83d"],
    100000,
    800000000000000000000,
    800000000000000000000,
)
rlc = TokenItem(
    "RLC",
    9,
    ["0x607f4c5bb672230e8672085532f7e901544a7375"],
    2000000,
    60000000000000,
    60000000000000,
)
lrc = TokenItem(
    "LRC",
    18,
    ["0xbbbbca6a901c926f240b89eacb641d8aec7aeafd"],
    10000000000000000,
    200000000000000000000000,
    200000000000000000000000,
)
npxs = TokenItem(
    "NPXS",
    18,
    ["0xa15c7ebe1f07caf6bff097d8a589fb8ac49ae5b3"],
    10000000000000000000,
    0,
    0,
)
cnd = TokenItem(
    "CND", 18, ["0xd4c435f5b09f855c3317c8524cb1f586e42795fa"], 1000000000000000000, 0, 0
)
usdc = rebalance_token(
    "USDC",
    6,
    ["0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"],
    1000,
    1500000000000,
    1500000000000,
)
sai = TokenItem(
    "SAI", 18, ["0x89d24a6b4ccb1b6faa2625fe562bdd9a23260359"], 1000000000000000, 0, 0
)
usdt = rebalance_token(
    "USDT",
    6,
    ["0xdac17f958d2ee523a2206206994597c13d831ec7"],
    1000,
    1500000000000,
    1500000000000,
)
pax = rebalance_token(
    "PAX",
    18,
    ["0x8e870d67f660d95d5be530380d0ec0bd388289e1"],
    1000000000000000,
    1500000000000000000000000,
    1500000000000000000000000,
)
edo = TokenItem(
    "EDO", 18, ["0xced4e93198734ddaff8492d525bd258d49eb388e"], 10000000000000000, 0, 0
)
wabi = TokenItem(
    "WABI", 18, ["0x286bda1413a2df81731d4930ce2f862a35a609fe"], 50000000000000000, 0, 0
)
lend = TokenItem(
    "LEND",
    18,
    ["0x80fb784b7ed66730e8b1dbd9820afd29931aab03"],
    500000000000000000,
    120000000000000000000000,
    120000000000000000000000,
)
dai = rebalance_token(
    "DAI",
    18,
    ["0x6b175474e89094c44da98b954eedeac495271d0f"],
    1000000000000000,
    1500000000000000000000000,
    1500000000000000000000000,
)
usds = TokenItem(
    "USDS",
    6,
    ["0xa4bdb11dc0a2bec88d24a3aa1e6bb17201112ebe"],
    10000,
    30000000000,
    30000000000,
)
loom = TokenItem(
    "LOOM",
    18,
    ["0xa4e8c3ec456107ea67d3075bf9e3df3a75823db0"],
    300000000000000000,
    300000000000000000000000,
    300000000000000000000000,
)
storm = TokenItem(
    "STORM",
    18,
    ["0xd0a4b8946cb52f0661273bfbc6fd0e0c75fc6433"],
    2000000000000000000,
    5000000000000000000000000,
    5000000000000000000000000,
)
stmx = TokenItem(
    "STMX",
    18,
    ["0xbe9375c6a420d2eeb258962efb95551a5b722803"],
    2000000000000000000,
    20000000000000000000000000,
    20000000000000000000000000,
)
busd = rebalance_token(
    "BUSD",
    18,
    ["0x4fabb145d64652a948d72533023f6e7a623c7c53"],
    10000000000000000,
    1500000000000000000000000,
    1500000000000000000000000,
)

yfi = TokenItem(
    "YFI",
    18,
    ["0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e"],
    150000000000,
    11000000000000000000,
    11000000000000000000,
)
aave = TokenItem(
    "AAVE",
    18,
    ["0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"],
    12500000000000,
    1500000000000000000000,
    1500000000000000000000,
)

snx = TokenItem(
    "SNX",
    18,
    ["0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f"],
    300000000000000,
    10000000000000000000000,
    10000000000000000000000,
)
oneinch = TokenItem(
    "1INCH",
    18,
    ["0x111111111117dc0aa78b770fa6a738034120c302"],
    1000000000000000,
    100000000000000000000000,
    100000000000000000000000,
)

matic = TokenItem(
    "MATIC",
    18,
    ["0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0"],
    2000000000000000,
    200000000000000000000000,
    200000000000000000000000,
)

ata = TokenItem(
    "ATA",
    18,
    ["0x0000000000000000000000000000000000000000"],
    1000000000000000,
    200000000000000000000000,
    200000000000000000000000,
)

ogn = TokenItem(
    "OGN",
    18,
    ["0x8207c1ffc5b6804f6024322ccf34f29c3541ae26"],
    2000000000000000,
    200000000000000000000000,
    200000000000000000000000,
)
c98 = TokenItem(
    "C98",
    18,
    ["0xAE12C5930881c53715B369ceC7606B70d8EB229f"],
    5000000000000000,
    100000000000000000000000,
    100000000000000000000000,
)
btc = rebalance_token(
    "BTC",
    18,
    ["0x0000000000000000000000000000000000000000"],
    166666666666666,
    100000000000000000000,
    100000000000000000000,
)

listed_tokens = [
    oneinch,
    aave,
    bat,
    blz,
    bnt,
    busd,
    cvc,
    dai,
    dgx,
    enj,
    knc,
    link,
    lrc,
    mana,
    omg,
    pax,
    rlc,
    snt,
    snx,
    usdc,
    usdt,
    wbtc,
    yfi,
    zrx,
    matic,
    ogn,
    c98,
]
new_listed_tokens = [
    oneinch,
    aave,
    bat,
    blz,
    cvc,
    dai,
    dgx,
    enj,
    knc,
    link,
    lrc,
    mana,
    omg,
    rlc,
    snt,
    snx,
    usdc,
    usdt,
    wbtc,
    yfi,
    zrx,
    matic,
    ogn,
    c98,
]
tokens = [busd, dai, pax, usdc, usdt]
kn_traded_full = [
    knc,
    omg,
    eos,
    snt,
    gto,
    req,
    bat,
    mana,
    powr,
    elf,
    eth,
    appc,
    eng,
    rdn,
    salt,
    bqx,
    ast,
    link,
    zil,
    dgx,
    abt,
    enj,
    ae,
    aion,
    blz,
    poly,
    edu,
    lba,
    cvc,
    tusd,
    pay,
    bnt,
    dta,
    chat,
    poe,
    sub,
    wax,
    rep,
    bnb,
    zrx,
    ren,
    qkc,
    dat,
    ost,
    eko,
    wbtc,
    bix,
    cdt,
    mco,
    rlc,
    lrc,
    npxs,
    cnd,
    usdc,
    sai,
    usdt,
    pax,
    edo,
    wabi,
    lend,
    dai,
    usds,
    loom,
    storm,
    busd,
    stmx,
    aave,
    btc,
    yfi,
    oneinch,
    snx,
    pnt,
    matic,
    ogn,
    ata,
    c98,
    weth,
]

rebalance_tokens = [eth, usdt, btc, pax, usdc, busd, dai]
