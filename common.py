from aeternity.signing import Account
from aeternity.epoch import EpochClient
from aeternity.config import Config
import logging, IPython

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

HOME = "/home/ck/Sync/Aeternity/keys/"
E1 = Account.from_keystore(HOME + "1", "")
E2 = Account.from_keystore(HOME + "2", "")
E3 = Account.from_keystore(HOME + "3", "")
M1 = Account.from_keystore(HOME + "mainminor1", "")
M2 = Account.from_keystore(HOME + "mainminor2", "")
UAT1 = Account.from_keystore(HOME + "uat1", "")
UAT2 = Account.from_keystore(HOME + "uat2", "")
P1=Account.from_keystore(HOME+"p1","")
P2=Account.from_keystore(HOME+"p2","")
P3=Account.from_keystore(HOME+"p3","")
P4=Account.from_keystore(HOME+"p4","")

CONF_MAIN = Config(external_url="http://localhost:3013",
                   internal_url="http://localhost:3113",
                   channels_url="ws://localhost:3014/channel",
                   network_id='ae_mainnet')

CONF_EDGE = Config(external_url="https://sdk-edgenet.aepps.com",
                   internal_url="https://sdk-edgenet.aepps.com",
                   network_id='ae_devnet')

CONF_UAT = Config(external_url="http://localhost:3013",
                   internal_url="http://localhost:3113",
                   channels_url="ws://localhost:3014/channel",
                   network_id='ae_uat')

CONF_PRIV = Config(external_url="http://localhost:3013",
                   internal_url="http://localhost:3113",
                   channels_url="ws://localhost:3014/channel",
                   network_id='tirnanog')

CONF_DEFAULT = CONF_PRIV
Config.set_defaults(CONF_DEFAULT)