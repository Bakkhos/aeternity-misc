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

from common import E1, CONF_EDGE
epoch = EpochClient(native=False,
                    debug=True,
                    configs=[CONF_EDGE])

class AeternityInUSDOracleQuery(OracleQuery):
    pass

query = AeternityInUSDOracleQuery(epoch, oracle_id='ok_2wCbfuyWA6oFeCtdzNfyuqeoBTbRuZjVe8SwzVfXrceptLYoDf')
query.execute(sender=E1,
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