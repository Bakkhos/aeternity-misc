import aeternity
from aeternity.openapi import OpenAPIClientException
from aeternity.signing import Account
import aeternity.transactions, aeternity.oracles, aeternity.config, aeternity.contract, aeternity.epoch, \
    aeternity.utils, aeternity.hashing as encoding
from aeternity.epoch import EpochClient
import aeternity.config as config
from aeternity.transactions import TxBuilder, TxSigner
from aeternity.oracles import Oracle
from aeternity.config import Config
from aeternity.contract import Contract, ContractError
from aeternity.aens import AEName
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

HOME = "/home/ck/Sync/Aeternity/keys/"
ACC = Account.from_keystore(HOME + "1", "")
ACC2 = Account.from_keystore(HOME + "2", "")
MAIN = Account.from_keystore(HOME + "mainminor1", "")
UAT = Account.from_keystore(HOME + "uat1", "")

CONF_MAIN = Config(external_url="https://roma-net.aepps.com",
                   internal_url="https://roma-net.aepps.com",
                   network_id='ae_mainnet',
                   force_compatibility=True)

CONF_EDGE = Config(external_url="https://sdk-edgenet.aepps.com",
                   internal_url="https://sdk-edgenet.aepps.com",
                   network_id='ae_devnet',
                   force_compatibility=True)

Config.set_defaults(CONF_MAIN)

epoch = EpochClient(debug=True,
                    native=False)
