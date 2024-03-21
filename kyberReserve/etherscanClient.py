import random
from collections import deque
from enum import Enum
from time import sleep
from typing import Any

import requests

from kyberReserve.storage import Block, Transaction
from kyberReserve.utils import saveEveryNth


def parseTx(tx: dict) -> Transaction:
    return Transaction(
        blockNumber=int(tx["blockNumber"], 16),
        hash=tx["hash"],
        nonce=int(tx["nonce"], 16),
        blockHash=tx["blockHash"],
        transactionIndex=int(tx["transactionIndex"], 16),
        from_=tx["from"],
        to=tx["to"],
        value=int(tx["value"], 16),
        type_=int(tx["type"], 16),
        chainId=int(tx.get("chainId", "0"), 16),
        gas_limit=int(tx["gas"], 16),
        gasPrice=int(tx["gasPrice"], 16),
        maxFeePerGas=int(tx.get("maxFeePerGas", "0"), 16),
        maxPriorityFeePerGas=int(tx.get("maxPriorityFeePerGas", "0"), 16),
    )


def parseBlock(block: dict) -> Block:
    return Block(
        baseFeePerGas=int(block["baseFeePerGas"], 16),
        difficulty=int(block["difficulty"], 16),
        extraData=block["extraData"],
        gasLimit=int(block["gasLimit"], 16),
        gasUsed=int(block["gasUsed"], 16),
        hash=block["hash"],
        miner=block["miner"],
        mixHash=block["mixHash"],
        nonce=block["nonce"],
        number=int(block["number"], 16),
        timestamp=int(block["timestamp"], 16),
        totalDifficulty=int(block["totalDifficulty"], 16),
        transactions=[parseTx(tx) for tx in block["transactions"]],
    )


class RelationDirection(Enum):
    INCOMING = 1
    OUTGOING = 2
    BOTH = 3


class EtherScanClient:
    _resp: requests.Response

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.etherscan.io/api"

    def _make_url(self, module: str, action: str, **params) -> str:
        q_params = {"module": module, "action": action, "apikey": self.api_key} | params
        return f"{self.base_url}?{requests.compat.urlencode(q_params)}"

    def get_acc_balance(self, address: str) -> dict:
        """The result is returned in wei. To convert to ETH, divide by 1e18"""
        url = self._make_url("account", "balance", address=address, tag="latest")
        response = requests.get(url)
        return response.json()

    def latest_block_num(self) -> str | None:
        """Returns the number of most recent block"""
        url = self._make_url("proxy", "eth_blockNumber")
        self._resp = requests.get(url)
        return self._parse_resp()

    def _block_resp_asObj(self) -> Block | None:
        if data := self._parse_resp():
            return parseBlock(data)
        return None

    def get_block(
        self, block_num: str | int = "latest", info: bool = True, as_object: bool = True
    ) -> dict | Block | None:
        """Returns the most recent block, by default. If `block_num` is specified, it
        will return the block with that number. If `info` is False, it will return only
        the block number with tx numbers."""
        if isinstance(block_num, int):
            block_num = hex(block_num)
        url = self._make_url(
            "proxy", "eth_getBlockByNumber", tag=block_num, boolean=info
        )
        self._resp = requests.get(url)
        if as_object:
            return self._block_resp_asObj()
        return self._parse_resp()

    def get_block_by_ts(
        self,
        ts: int | None = None,
        closest: str = "before",
        info: bool = True,
        as_object: bool = True,
    ) -> dict | Block | None:
        """Returns the closest available block to the provided timestamp, either before
        or after. Timestamp is in seconds. If ts is None, it
        will return the most recent block. If `info` is False, it will return only the
        block number with tx numbers."""
        if not ts:
            return self.get_block(info=info, as_object=as_object)
        url = self._make_url("block", "getblocknobytime", timestamp=ts, closest=closest)
        self._resp = requests.get(url)
        res = self._parse_resp()
        if res:
            return self.get_block(int(res), info, as_object=as_object)
        return None

    def _transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        internal: bool = False,
    ) -> list:
        """ "This API endpoint returns a maximum of 10000 records only, so we need to
        paginate if we expect more than 10000 records."""
        action = "txlist"
        paginate = False
        if start_block == 0 and end_block == 99999999:
            # Use pagination to get all transactions
            paginate = True
        if internal:
            action = "txlistinternal"
        params = {
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": 1,
            "offset": 10_000,
            "sort": "asc",
        }
        return self._paginate_or_not("account", action, params, paginate)

    def get_transactions(
        self, address: str, start_block: int = 0, end_block: int = 99999999
    ) -> list:
        return self._transactions(address, start_block, end_block, False)

    def get_internal_transactions(
        self, address: str, start_block: int = 0, end_block: int = 99999999
    ) -> list:
        return self._transactions(address, start_block, end_block, True)

    def _token_transfers(
        self,
        address: str,
        token_contract: str | None = None,
        start_block: int = 0,
        end_block: int = 99999999,
        erc721: bool = False,
    ) -> list:
        """This API endpoint returns a maximum of 10000 records only, so we need to
        paginate if we expect more than 10000 records."""
        action = "tokentx"
        paginate = False
        if start_block == 0 and end_block == 99999999:
            # Use pagination to get all transactions
            paginate = True
        if erc721:
            action = "tokennfttx"
        params = {
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": 1,
            "offset": 10_000,
            "sort": "asc",
        }
        if token_contract:
            params["contractaddress"] = token_contract
        return self._paginate_or_not("account", action, params, paginate)

    def get_token_transfers(
        self,
        address: str,
        token_contract: str | None = None,
        start_block: int = 0,
        end_block: int = 99999999,
    ) -> list:
        """Get ERC20 token transfers"""
        return self._token_transfers(
            address, token_contract, start_block, end_block, False
        )

    def get_erc721_transfers(
        self,
        address: str,
        token_contract: str | None = None,
        start_block: int = 0,
        end_block: int = 99999999,
    ) -> list:
        """Get ERC721 token transfers"""
        return self._token_transfers(
            address, token_contract, start_block, end_block, True
        )

    def get_txn_receipt(self, txn_hash: str) -> dict | None:
        """Get the transaction receipt. Usefull to get the status of the transaction
        and gas used."""
        url = self._make_url("proxy", "eth_getTransactionReceipt", txhash=txn_hash)
        self._resp = requests.get(url)
        return self._parse_resp()

    def get_logs(
        self,
        address: str,
        topics: dict[str, str] | None = None,
        topicOperator: dict[str, str] | None = None,
        start_block: int = 0,
        end_block: int = 99999999,
    ) -> list:
        """
        For a single topic, specify the topic number such as topic0-3, (topic1, topic2)
        For multiple topics, specify the `topic` numbers and topic operator either and
        or such as below.

        topics should be a dict with the topic number as the key and the topic as the
        value.

        For `topicOperator`, specify the operator to use to combine the topic filters.
        topic0_1_opr (and|or between topic0 & topic1),
        topic1_2_opr (and|or between topic1 & topic2),
        topic2_3_opr (and|or between topic2 & topic3),
        topic0_2_opr (and|or between topic0 & topic2),
        topic0_3_opr (and|or between topic0 & topic3),
        topic1_3_opr (and|or between topic1 & topic3)
        topicOperator should be a dict with the topic number combination as the key and
        the operator as the value.

        Offset is limited to 1000 records per query, use `page` for subsequent records.
        """
        params = {
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": 1,
            "offset": 1000,
        }
        if topics:
            for i, topic in topics.items():
                params[f"topic{i}"] = topic
            if len(topics) > 1:
                if topicOperator:
                    for t_nums, op in topicOperator.items():
                        params[t_nums] = op
                else:
                    print("Need to specify topicOperator for multiple topics")
        return self._paginate_or_not("logs", "getLogs", params, True)

    def _paginate_or_not(
        self, module: str, action: str, params: dict, paginate: bool = False
    ) -> list:
        if paginate:
            all_txs = []
            while True:
                url = self._make_url(module, action, **params)
                self._resp = requests.get(url)
                if data := self._parse_resp():
                    all_txs.extend(data)
                    if len(data) < params["offset"]:
                        # Break the loop if the num of results is less than the offset
                        break
                    params["page"] += 1
                    sleep(random.randint(1, 3))
                else:
                    # Break the loop if no results are returned
                    break
            return all_txs
        else:
            url = self._make_url(module, action, **params)
            self._resp = requests.get(url)
            if data := self._parse_resp():
                return data
        return []

    def _parse_resp(self) -> Any:
        if self._resp.status_code == 200:
            data = self._resp.json()
            if "result" in data and data["result"]:
                return data["result"]
        else:
            print(f"Error fetching data: {self._resp.status_code} msg: ")
            return None

    def get_related_addresses(
        self,
        address: str,
        direction: RelationDirection,
        min_ETH: float = 0.01,
        to_lower: bool = True,
    ) -> set:
        transactions = self.get_transactions(address)
        related_addresses = set()
        for tx in transactions:
            if int(tx["value"]) / 10**18 < min_ETH:
                continue
            if tx["from"] == address.lower():
                if direction in [RelationDirection.OUTGOING, RelationDirection.BOTH]:
                    related_addresses.add(tx["to"])
            else:
                if direction in [RelationDirection.INCOMING, RelationDirection.BOTH]:
                    related_addresses.add(tx["from"])
        if to_lower and related_addresses:
            return {i.lower() for i in related_addresses}
        return related_addresses

    def get_all_related_addresses(
        self,
        starting_addresses: list[str],
        direction: RelationDirection,
        max_step_addresses: int,
        max_lookup_addresses: int,
        levels: int,
        compare_to: list[str],
        results_file: str,
        save_every_n: int,
    ) -> tuple[set[str], set[str]]:
        """Get all related addresses from the starting addresses.
        Args:
            starting_addresses (list[str]): List of addresses to start from
            direction (RelationDirection): Direction of the relation
            max_step_addresses (int): Max number of addresses to fetch from each address
            max_lookup_addresses (int): Max number of addresses to fetch
            levels (int): Number of levels to search
            compare_to_banned (list[str]): List of banned addresses to compare against
            results_file (str): File to save the results. Example:
                f_suffix = datetime.utcnow().strftime("%H%M%ST%d%m%y")
                results_file = f"./data/anal_bin_compare_{f_suffix}.json"
            save_every_n (int): Save every n results
        Returns:
            tuple[set[str], set[str]]: Tuple of related addresses and potential banned
        """
        visited_addresses = set(i.lower() for i in starting_addresses)
        queue = deque(starting_addresses, max_lookup_addresses)
        # add a separator in the queue to separate the levels
        queue.append("separator")
        results = list(visited_addresses)

        if compare_to:
            print(f"Found currently {len(compare_to)} banned addresses.")
        while queue and levels > 0:
            current_address = queue.popleft()
            if current_address == "separator":
                levels -= 1
                if levels == 0:
                    break
                queue.append("separator")
                continue
            related = self.get_related_addresses(current_address, direction)
            if (n_rel := len(related)) > max_step_addresses:
                print(
                    f"found {n_rel} related for {current_address}, current search "
                    f"queue length is {len(queue)}, reducing to {max_step_addresses}"
                    f" addresses."
                )
                related = set(random.sample(list(related), max_step_addresses))
            dif_addrs = related - visited_addresses
            visited_addresses.update(dif_addrs)
            queue.extend(dif_addrs)
            if compare_to:
                found_banned = visited_addresses.intersection(compare_to)
                if found_banned:
                    print(
                        f"Found {len(found_banned)} related banned "
                        f"address(es): {found_banned}"
                    )
            results += list(dif_addrs)
            if saveEveryNth(results, results_file, save_every_n):
                results = []
            print(f"Currently found linked addresses are {len(visited_addresses)}")

        if compare_to:
            potential_bans = set(visited_addresses).difference(compare_to)
            return visited_addresses, potential_bans
        return visited_addresses, set()
