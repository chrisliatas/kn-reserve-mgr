from dataclasses import dataclass
from datetime import datetime


@dataclass
class Transaction:
    """
    https://github.com/ethereum/EIPs/blob/master/EIPS/eip-1559.md#specification
    """

    blockNumber: int  # block number where this transaction was in
    hash: str  # hash of the transaction.
    nonce: int  # the number of transactions made by the sender prior to this one.
    blockHash: str  # hash of the block where this transaction was in.
    transactionIndex: int  # integer of the transactions index position in the block.
    from_: str  # sender's address.
    to: str  # address of the receiver. null when it's a contract creation transaction.
    value: int  # value transferred in Wei.
    type_: int  # transaction type, 2 (EIP-1559), 0 (legacy), 1 (access list)
    chainId: int  # etherscan attribute
    gas_limit: int  # gas provided by the sender.
    gasPrice: int  # gas price provided by the sender in gwei.
    maxFeePerGas: int  # max fee per unit of gas willing to be paid for the transaction
    maxPriorityFeePerGas: int  # max price of the consumed gas to be included as a tip.

    def __repr__(self) -> str:
        return (
            f"(Number: {self.blockNumber},\nHash: {self.hash},\nNonce: {self.nonce},\n"
            f"BlockHash: {self.blockHash},\nTxn idx: {self.transactionIndex},\nSender"
            f": {self.from_},\nReceiver: {self.to},\nETH amount: {self.value},\nTxn "
            f"type: {self.type_},\nChain Id: {self.chainId},\nGas Limit (Wei): "
            f"{self.gas_limit},\nGas Price (Wei): {self.gasPrice},\nMax Fee per Gas "
            f"(Wei): {self.maxFeePerGas},\nMax Priority Fee per Gas (Wei): "
            f"{self.maxPriorityFeePerGas})"
        )


@dataclass
class Block:
    """
    Transactions are stored in the order they appear in the block. List idx 0 is the
    first transaction in the block (the one with the highest gas fee).
    """

    baseFeePerGas: int
    difficulty: int
    extraData: str
    gasLimit: int
    gasUsed: int
    hash: str
    miner: str
    mixHash: str
    nonce: str
    number: int
    timestamp: int
    totalDifficulty: int
    transactions: list[Transaction]

    @property
    def num_txs(self) -> int:
        return len(self.transactions)

    @property
    def ts_date(self) -> str:
        return datetime.utcfromtimestamp(self.timestamp).strftime("%d-%m-%Y %H:%M:%S")

    @property
    def ts_ago(self) -> str:
        ago_td = datetime.utcnow() - datetime.utcfromtimestamp(self.timestamp)
        # convert to days, hours, minutes
        days = ago_td.days
        hours, remainder = divmod(ago_td.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m ago"

    def get_txn(self, hash: str) -> Transaction | None:
        for txn in self.transactions:
            if txn.hash == hash:
                return txn
        return None
