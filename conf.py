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
ACC3 = Account.from_keystore(HOME + "3", "")
A1 = Account.from_keystore(HOME + "mainminor1", "")
A2=Account.from_keystore(HOME + "mainminor2", "")
UAT = Account.from_keystore(HOME + "uat1", "")
UAT2 = Account.from_keystore(HOME + "uat2", "")
P1=Account.from_keystore(HOME+"p1","")
P2=Account.from_keystore(HOME+"p2","")
P3=Account.from_keystore(HOME+"p3","")
P4=Account.from_keystore(HOME+"p4","")

CONF_MAIN = Config(external_url="http://localhost:3013",
                   internal_url="http://localhost:3113",
                   channels_url="localhost:3014/channel",
                   network_id='ae_mainnet')

CONF_EDGE = Config(external_url="https://sdk-edgenet.aepps.com",
                   internal_url="https://sdk-edgenet.aepps.com",
                   network_id='ae_devnet')

CONF_UAT = Config(external_url="http://localhost:3013",
                   internal_url="http://localhost:3113",
                   channels_url="localhost:3014/channel",
                   network_id='ae_uat')

CONF_PRIV = Config(external_url="http://localhost:3013",
                   internal_url="http://localhost:3113",
                   channels_url="localhost:3014/channel",
                   network_id='tirnanog')

CONF = CONF_PRIV

Config.set_defaults(CONF)

epoch = EpochClient(debug=True,
                    native=False,
                    force_compatibility=False)
