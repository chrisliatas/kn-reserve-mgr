from enum import Enum


class AssetGroupType(str, Enum):
    V3_LEGACY = "v3_legacy"
    PRICING_CEX_GROUP = "pricing_cex_group"
    ALL = "all"


class AssetGroupSettingType(str, Enum):
    ONCHAIN_CEX_PAIR_REBALANCE = "onchain_cex_pair_rebalance"
    ONCHAIN_CEX_PAIR_PRICING = "onchain_cex_pair_pricing"
    CEX_GROUP_SETTING = "cex_group_setting"
    ALL = "all"


class AssetLinkType(str, Enum):
    ERC20_TRANSFER = "erc20_transfer"
    ALL = "all"


class AssetType(str, Enum):
    DEFAULT = "default"
    UNLISTED = "unlisted"
    ALL = "all"


class AssetClass(str, Enum):
    ONCHAIN = "onchain"
    CEX = "cex"
    ALL = "all"


class AssetGroupLinkType(str, Enum):
    ASSET_GROUP_LINK = "asset_group_link"
    ALL = "all"


class ChangeList(str, Enum):
    CREATE_ASSET_V4 = "create_asset_v4"
    UPDATE_ASSET_V4 = "update_asset_v4"
    CREATE_ASSET_LINK_V4 = "create_asset_link_v4"
    UPDATE_ASSET_LINK_V4 = "update_asset_link_v4"
    CREATE_ASSET_GROUP_V4 = "create_asset_group_v4"
    UPDATE_ASSET_GROUP_V4 = "update_asset_group_v4"
    CREATE_ASSET_GROUP_SETTING_V4 = "create_asset_group_setting_v4"
    UPDATE_ASSET_GROUP_SETTING_V4 = "update_asset_group_setting_v4"
    CREATE_TRADING_PAIR_V4 = "create_trading_pair_v4"
    UPDATE_TRADING_PAIR_V4 = "update_trading_pair_v4"
    DELETE_TRADING_PAIR_V4 = "delete_trading_pair_v4"
    CREATE_PAIR_RQF_PARAMS = "create_pair_rfq_params"
    UPDATE_PAIR_RQF_PARAMS = "update_pair_rfq_params"
    DELETE_PAIR_RQF_PARAMS = "delete_pair_rfq_params"
    CREATE_ASSET_GROUP_LINK = "create_asset_group_link"
    CREATE_RQF_PARAMES_V4 = "create_rfq_params_v4"
    UPDATE_RQF_PARAMS_V4 = "update_rfq_params_v4"
