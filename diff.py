import unittest
import aeternity
from aeternity.signing import Account
import aeternity.transactions, aeternity.oracles, aeternity.config, aeternity.contract, aeternity.epoch, aeternity.utils
from aeternity.epoch import EpochClient
from aeternity.transactions import TxBuilder, TxSigner
from aeternity.oracles import Oracle
from aeternity.config import Config
from aeternity.contract import Contract, ContractError
from aeternity.aens import AEName
from pprint import pprint as pp, pformat as pf
import logging
import IPython
from conf import CONF_MAIN

log = logging.getLogger(__name__)

Config.set_defaults(CONF_MAIN)
epoch = EpochClient()

if __name__ == '__main__':
    #get top block
    top = epoch.get_top_block()
    target=top.target
    BASE = 256
    exponent = target >> 24
    mantissa = target & 0x00FFFFFF
    difficulty = 2**256 // (mantissa << (8 * (exponent - 3)))
    print(f"Target: {hex(target)}\n Exponent: {exponent}\n Mantissa: {mantissa}\n Difficulty: {difficulty}")

    CARD_TRY_RATE = 1/0.225
    CARD_SOL_RATE = CARD_TRY_RATE/42
    SOLS_PER_DAY = 3600 * 24 * CARD_SOL_RATE

    blocks_per_day = SOLS_PER_DAY / difficulty

    EUR_PER_AE = 0.377
    AE_PER_BLK = 471

    DAILY_PWRCOST = 0.3 * 24 * 0.25

    income = EUR_PER_AE * AE_PER_BLK * blocks_per_day
    profit = income - DAILY_PWRCOST

    print(f"Expected Blocks: {blocks_per_day:.3} /d\n Income: {income:.3} /d\n Profit net of power cost: {profit:.3} /d {profit*30.5:.1f} /m")

    print(f"Assumes: Attempt rate {CARD_TRY_RATE:.3} (/s) Solution rate {CARD_SOL_RATE:.3f} (/s)")
