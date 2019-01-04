import json
import logging
import time
from pprint import pprint as pp
import aeternity
from aeternity.config import Config
from aeternity.epoch import EpochClient
from aeternity.oracles import OracleQuery
from aeternity.signing import Account
import common
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

from common import E1, CONF_EDGE, P4, CONF_PRIV
CONF = CONF_PRIV
ACC = P4
epoch = EpochClient(native=False,
                    debug=True,
                    configs=[CONF],
                    blocking_mode=True)

class AeternityInUSDOracleQuery(OracleQuery):
    pass

query = AeternityInUSDOracleQuery(epoch, oracle_id='ok_21bgH1gJT53UQ459gZyfvFSyY9KDu2dWx3EaJhLv3468fc8QUp')
query.execute(sender=ACC,
              query=json.dumps({
                  'url': 'https://api.coinmarketcap.com/v1/ticker/aeternity/?convert=USD',
                  'jq': '.[0].price_usd',
              }))

print(f"Query id {query.id}")

response = None
while response is None or response == 'or_Xfbg4g==':
    response = query.get_response_object().response
    time.sleep(1)

response = json.loads(aeternity.oracles.hashing.decode(response))
log.info(response)