import json
import unittest
import aeternity
from aeternity.openapi import OpenAPIClientException
from aeternity.signing import Account
import aeternity.transactions, aeternity.oracles, aeternity.config, aeternity.contract, aeternity.epoch, aeternity.utils, aeternity.hashing as encoding
from aeternity.epoch import EpochClient
import aeternity.config as config
from aeternity.transactions import TxBuilder, TxSigner
from aeternity.oracles import Oracle
from aeternity.config import Config
from aeternity.contract import Contract, ContractError

from aeternity.aens import AEName
from pprint import pprint as pp, pformat as pf
import logging
import IPython
from aeternity.config import *
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
from conf import *

with open("contracts/AddConstant.aes", "r") as source_file:
    id = Contract(source_file.read(), epoch, abi="sophia") #sophia causes http error 500 when calling, js-sdk doc says only sophia-address is supported...

    #print(id)
    #print(id.call('main', json.dumps((2,))))
    #epoch.set_native(False)
    txc = id.tx_create(ACC2)
    #epoch.set_native(True)
    #id.tx_call(ACC2, 'main', json.dumps({'x' : 2}))




#signer = aeternity.transactions.TxSigner(ACC,'ae_devnet')
#tx, sig, txhash = signer.sign_encode_transaction(cctx)
#epoch.broadcast_transaction(tx, txhash)


# Channels documentation:
# https://github.com/aeternity/protocol/blob/master/channels/README.md
# http://aeternity.com/epoch-api-docs/#/channel
