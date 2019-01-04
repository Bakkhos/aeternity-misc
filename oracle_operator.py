import json
import logging
import re
import time
import requests
from aeternity.config import Config
from aeternity.epoch import EpochClient
from aeternity.oracles import Oracle, OracleQuery
from aeternity.signing import Account
import aeternity, aeternity.oracles as oracles

from common import E2, CONF_EDGE, P3, CONF_PRIV
CONF = CONF_PRIV
ACC = P3
epoch = EpochClient(native=False,
                    debug=True,
                    configs=[CONF])

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class OraclefJean(Oracle):
    """
    An oracle that can provide data from JSON APIs from the web.

    Just provide an URL that returns JSON for a GET request

    And provide the a jq-style query:
        (but it's reduced to alphanumeric non-quoted key traversal for plain
        objects and lists, e.g.)

        {'this': {'is': ['some', 'awesome'], 'api': 'result'}}}

        with the parameter
            jq='.this.is[1]'
        would return
            "awesome"

    """
    def _error(self, message, data=None):
        if data is None:
            data = {}
        return {'status': 'error', 'message': message, 'data': data}

    def _success(self, data):
        return {'status': 'ok', 'message': '', 'data': data}

    def _jq_traverse(self, jq, data):
        assert jq.startswith('.')  # remove identity
        if jq == '.':
            return data
        ret_data = data
        for subpath in jq[1:].split('.'):
            obj_traverse = subpath
            list_index = None
            list_indexed_match = re.match('(\w*)\[(\d+:?\d*)\]', subpath)
            if list_indexed_match:
                obj_traverse, list_index = list_indexed_match.groups()
            if obj_traverse:
                ret_data = ret_data[obj_traverse]
            if list_index is not None:
                # slices
                if ':' in list_index:
                    start, end = list_index.split(':')
                    start, end = int(start), int(end)
                    ret_data = ret_data[start:end]
                else:
                    # indices
                    ret_data = ret_data[int(list_index)]
        return ret_data

    def get_response(self, query):
        query = json.loads(query)
        try:
            url, jq = query['url'], query['jq']
        except (KeyError, AssertionError) as exc:
            print(exc)
            return self._error('malformed query')
        try:
            json_data = requests.get(url).json()
        except Exception:
            return self._error('request/json error')
        try:
            ret_data = self._jq_traverse(jq, json_data)
        except (KeyError, AssertionError):
            return self._error('error traversing json/invalid jq')
        # make sure the result is not huge
        ret_data = json.dumps(ret_data)
        if len(ret_data) > 1024:
            return self._error('return data is too big (>1024 bytes)')
        return self._success(ret_data)

    def register(self, account, **kwargs):
        super().register(account,
                         query_format='''{'url': 'str', 'jq': 'str'}''',
                         response_format='''{'status': 'error'|'ok', 'message': 'str', 'data': {}}''',
                         **kwargs)
def create():
    ora = OraclefJean(epoch)
    ora.register(ACC)
    print(f'Oracle {ora.id} ready')
    return ora

def service(ora):
    answered = set()
    while True:
        queries = ora.client.get_oracle_queries_by_pubkey(pubkey=ora.id)
        for q in queries.oracle_queries:
            if not q['id'] in answered:
                qstr = oracles.hashing.decode(q['query'])
                queries = ora.get_response(qstr)
                ora.client.blocking_mode = True
                ora.respond(account=ACC,
                            query_id=q['id'],
                            response=json.dumps(queries))
                ora.client.blocking_mode = False
                answered.add(q['id'])
        time.sleep(2)

ora = create()
#ora = OraclefJean(client, "ok_2wCbfuyWA6oFeCtdzNfyuqeoBTbRuZjVe8SwzVfXrceptLYoDf")
log.info(f"oracle id {ora.id}")
service(ora)

