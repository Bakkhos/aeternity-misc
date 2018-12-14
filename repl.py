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
from aeternity.openapi import OpenAPIClientDetailedException
import logging
import requests
from requests import Request, Response
from pprint import pprint

import IPython
from aeternity.config import *
from conf import *
session = requests.Session()

def compile(fname : str, **kwargs):
    fname = f"./contracts/{fname}.aes"
    with open(fname, 'r') as f:
        try:
            C = Contract(f.read(),
                            client=epoch,
                            abi="sophia",
                            **kwargs)
        except ContractError as e:
            if isinstance(e.__context__, OpenAPIClientDetailedException):
                log.info(e.__context__.http_resp.json()['reason'])
            else:
                raise e

if __name__ == '__main__':
    #print(ACC2.get_address())
    #print(ACC2.get_private_key())
    #print(MAIN.get_private_key())
    IPython.embed()
