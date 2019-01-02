import json
import unittest
import aeternity
from aeternity.openapi import OpenAPIClientException, OpenAPIClientDetailedException
from aeternity.signing import Account
import aeternity.transactions, aeternity.oracles, aeternity.config, aeternity.contract, aeternity.epoch
import aeternity.utils, aeternity.hashing as encoding
from aeternity.epoch import EpochClient
import aeternity.config as config
from aeternity.transactions import TxBuilder, TxSigner
from aeternity.oracles import Oracle
from aeternity.config import Config
from aeternity.contract import Contract, ContractError
from pprint import pprint, pformat
from aeternity.aens import AEName
import logging
import IPython
from aeternity.config import *
from typing import Tuple

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

from common import CONF_EDGE, E2, E3
epoch=EpochClient(configs=[CONF_EDGE],
                  native=False,
                  debug=True)

def create1():
    with open("contracts/AddConstant.aes", "r") as source_file:
        C = Contract(source_file.read(),
                     epoch,
                     abi="sophia")

        txc = C.tx_create(E2,
                          init_state='(44)',
                          fee=10 * DEFAULT_FEE)

def txcall1():
    with open("contracts/AddConstant.aes", "r") as source_file:
        C = Contract(source_file.read(),
                     epoch,
                     abi="sophia",
                     address='ct_mXU7sLxNERev3AfFYdcc7QKZ5VM4LZnULJLuRLCwhWSH5DSVM')  # sophia causes http error 500 when calling, js-sdk doc says only sophia-address is supported...

    resp = C.tx_call(E2, 'add', '(100)', fee=100 * DEFAULT_FEE)
    # Response:
    # ('tx_+NUrAaEBonPSUOclKSfuV6ZHMGVRxu/Slv2bKx/9CFzoA4xNLos5oQVlGaM4O7QRVYBzIshCf9KcjtWz4n67bTHUn+gHwomnEgGDHoSAAAGDApgQAbiAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAeh/CJh4t/79euG1vRIfp6l6338BeQAECveFJ9t1/QBgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGSgjQYN',
    # 'tx_+QEfCwH4QrhAP5MbynC34Xt8mau1WeJfHEp1KNZf87+sgkZMtCc/lxsw5ITLOnleo78poJbvhDvnNgPqiVZ+fnP4OqVM2us9BrjX+NUrAaEBonPSUOclKSfuV6ZHMGVRxu/Slv2bKx/9CFzoA4xNLos5oQVlGaM4O7QRVYBzIshCf9KcjtWz4n67bTHUn+gHwomnEgGDHoSAAAGDApgQAbiAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAeh/CJh4t/79euG1vRIfp6l6338BeQAECveFJ9t1/QBgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGQXnHzA',
    # 'sg_9KQeMKYo3gzLcvME1NC5xXuw9CG9MbAL2mHosWLQjbCxjnnTjocfQBKHTouVuRbsqeurqSFUztBVNmxuRNLUQoTddL1zB',
    # 'th_2MDtBbkhdqbRHWtbgCEKMHfmwopg6cemoBrMtQvdvZnJMymTZ',
    # ContractCallObject(caller_id='ak_2EYdVkgMvZUSHzSNLPXd5aau9ehNiAaJv5H5yjc1EwcsjZVR7x',
    #   caller_nonce=57,
    #   contract_id='ct_mXU7sLxNERev3AfFYdcc7QKZ5VM4LZnULJLuRLCwhWSH5DSVM',
    #   gas_price=1,
    #   gas_used=161,
    #   height=322913,
    #   log=[],
    #   return_type='ok',
    #   return_value='cb_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJBm8dG0'))

    ret = C.decode_data('cb_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJBm8dG0', '(int)')
    # {"type":"word","value":144} (ok)


def callstatic():
    with open("contracts/StaticFunctions.aes", "r") as source_file:
        D = Contract(source_file.read(), epoch, abi="sophia")

    pprint(D.call('inc', '(2)'))
    # http error 500


def createfaucet():
    with open("contracts/Faucet.aes", "r") as source_file:
        C = Contract(source_file.read(),
                     epoch,
                     abi="sophia")

    txc = C.tx_create(E2,
                      fee=100 * DEFAULT_FEE,
                      init_state='(1000)',
                      deposit=10 ** 6)  # created at ct_gb9MvkKZuirbdRHtnYwKjGHKSJa4d3qAgUvvS9iG9TNyCcMMF with tx th_M6MxiedbHzBRrHMyBGajfQejCDhTsbxcq5peFRWrvFNQ26BzV
    pprint(txc)


def callfaucet():
    epoch.blocking_mode=True
    with open("contracts/Faucet.aes", "r") as source_file:
        C = Contract(source_file.read(),
                     epoch,
                     abi="sophia",
                     address="ct_gb9MvkKZuirbdRHtnYwKjGHKSJa4d3qAgUvvS9iG9TNyCcMMF")

    _, _, _, th, call = C.tx_call(E3,
                                  function='take',
                                  arg='()',  #other examples: (50) - unsure how to encode complex types, addresses for rest api
                                  gas=10**5,
                                  gas_price=1,
                                  fee=10**6,  #actual payment is fee+gas_spent*gas_price. presume tx size in bytes sets lower bound on fee
                                  tx_ttl=4,
                                  amount=0)

    RTYPE = 'int'
    log.info(call)
    #ContractCallObject(caller_id='ak_Z6PGcvFTqGUv2LWmwtF96zFui6AvZXJQ7GKocWrtGN4TxNL4W', caller_nonce=46,
    #                   contract_id='ct_gb9MvkKZuirbdRHtnYwKjGHKSJa4d3qAgUvvS9iG9TNyCcMMF', gas_price=1, gas_used=22456,
    #                   height=333051, log=[], return_type='ok',
    #                   return_value='cb_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAArMtts')                 #rvalue: 0

    #earlier...
    #ContractCallObject(caller_id='ak_Z6PGcvFTqGUv2LWmwtF96zFui6AvZXJQ7GKocWrtGN4TxNL4W', caller_nonce=1,
    #                   contract_id='ct_gb9MvkKZuirbdRHtnYwKjGHKSJa4d3qAgUvvS9iG9TNyCcMMF', gas_price=1, gas_used=170000,
    #                   height=330766, log=[], return_type='error', return_value='cb_b3V0X29mX2dhc0caXYY')) #rvalue: b'out_of_gas'

    try:
        if call.return_type == 'error':
            rv = aeternity.utils.hashing.decode(call.return_value) #'out_of_gas'
        else:
            rv = C.decode_data(call.return_value, RTYPE)  #(0, 'word') #only really works for RTYPE=string, else it gives dt=='word' and a 256-bit number
            try:
                x, dt = rv
                if dt == 'word' and RTYPE == 'address':
                    rv = aeternity.utils.hashing.encode('ak', x.to_bytes(32, 'big'))
            except Exception:
                pass

        log.info(f"rvalue decoded as {rv}")

    except Exception:
        pass

    return
    #Notes:
    # - see comments in Faucet.aes
    # - Calling /encode-calldata rest endpoint with private function or wrong function name returns 403, reason: unknown_function
    # - Did not test self-built tx


if __name__ == '__main__':
    try:
        callfaucet()
    except ContractError as e:
        pprint(e.__context__.http_resp.request.body)

