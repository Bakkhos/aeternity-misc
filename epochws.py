import sys, IPython
import aeternity.transactions, aeternity.oracles, aeternity.hashing, aeternity.config, aeternity.contract
import aeternity as ae, logging
import json, time, urllib.parse, IPython
from threading import Thread
from typing import Tuple
from queue import Queue, LifoQueue
from typing import Callable
from aeternity.contract import Contract
from aeternity.epoch import EpochClient
from aeternity.signing import Account
from aeternity.transactions import TxSigner
from websocket import WebSocketApp, WebSocket, WebSocketTimeoutException, WebSocketPayloadException, WebSocketException
from enum import Enum
from typing import Union
from deserialize import parse_rlp
import attr
from attr import attrs, attrib  # attrs

from common import CONF_PRIV, P3, P4

CONF = CONF_PRIV
ACC_INITIATOR = P3
ACC_RESPONDER = P4
EPOCH = EpochClient(debug=True,
                    native=True,
                    configs=[CONF])

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class Role(Enum):
    INITIATOR = "initiator"
    RESPONDER = "responder"

class WsMsgFactory(object):
    '''
    Colletion of factory functions for legacy epoch ws api messages
    as described at https://github.com/aeternity/protocol/blob/master/epoch/api/channel_ws_api.md
    cf. https://github.com/aeternity/protocol/blob/master/epoch/api/channels_api_usage.md
    '''

    def __init__(self,
                 me: Account,
                 partner_address: str,
                 network_id: str,
                 role: Role = Role.INITIATOR,
                 channel_id: str = None):
        self.me = me
        self.partner = partner_address
        self.txsigner = TxSigner(me, network_id)
        self.channel_id = channel_id
        self.role = role

    def message(self, action, tag, payload):
        return {'action': action,
                'tag': tag,
                'payload': payload}

    def channel_open(self, opening_tx: str):
        txs, sig, txh = self.txsigner.sign_encode_transaction(opening_tx)
        return {
            "action": f"{self.role.value}_sign",
            "payload": {"tx": txs}
        }

    def sign_update(self, update, role="starter"):
        '''
        Sign a proposed channel update
        :param update: Transaction to sign, or message with such tx in ['payload']['tx']
        :param role: stater or responder
        :return: ws message that provides the signed transaction
        '''
        if not (role == "starter" or role == "acknowledger"):
            raise ValueError(f"Role was {role}. It must be starter or acknowledger")
        if not isinstance(update, str):
            update = update['payload']['tx']

        txs, _, _ = self.txsigner.sign_encode_transaction(update)
        return {
            'action': f"update{'_ack' if role == 'acknowledger' else ''}",
            'payload': {'tx': txs}
        }

    def info_balances(self, *args):
        if len(args) == 0:
            args = [self.me.get_address(), self.partner]
        return {
            'action': 'get',
            'tag': 'balances',
            'payload': {'accounts': args}
        }

    def contract_create(self, bytecode, calldata, deposit, vm_version=1):
        return {
            'action': 'update',
            'tag': 'new_contract',
            'payload': {
                'code': bytecode,
                'call_data': calldata,
                'deposit': deposit,
                'vm_version': vm_version
            }
        }

    def contract_call(self, ct_addr, calldata, amt=0):
        return {'action': 'update',
                'tag': 'call_contract',
                'payload': {
                    'contract': ct_addr,
                    'vm_version': 1,
                    'amount': amt,
                    'call_data': calldata
                }}

    def transfer(self, payer, payee, amount):
        return {
            'action': 'update',
            'tag': 'new',
            'payload': {
                'from': payer,
                'to': payee,
                'amount': amount
            }
        }

    def getPoi(self, accounts, contracts):
        return {'action': 'get',
                'tag': 'poi',
                'payload': {'accounts': accounts, 'contracts': contracts}}


@attrs(auto_attribs=True, init=False)
class EpochWSChannelConnection(object):
    '''
    Websocket client to interact with the epoch ws api
    '''
    q: LifoQueue  # stack of incoming messages
    s: Callable[[dict], None]  # callable to submit a json message on the websocket
    f: WsMsgFactory  # message factory for this connection

    def __init__(self,
                 role: Role,
                 acc: Account,
                 partner_addr: str,
                 existing_channel_id: str = None,
                 last_state_tx: str = None,
                 network_id: str = CONF.network_id,
                 epoch: EpochClient = EPOCH,
                 port: int = 1234,
                 responder_host: str = "localhost",
                 initial_amount: int = 10 ** 9,
                 partner_initial_amount: int = 10 ** 9,
                 lock_period: int = 1,
                 push_amount: int = 0,
                 channel_reserve: int = 0,
                 ping_interval: int = 15,
                 creation_tx_ttl: int = 0,
                 creation_tx_nonce: int = None,
                 timeout_accept: int = 3_600_000,
                 timeout_funding_create: int = 3_600_000,
                 timeout_funding_sign: int = 3_600_000,
                 timeout_funding_lock: int = 3_600_000,
                 timeout_idle: int = 3_600_000,
                 timeout_open: int = 3_600_000,
                 timeout_sign: int = 3_600_000,
                 minimum_depth: int = 4):

        if not isinstance(acc, Account):
            raise ValueError(f"Account must be an Account, not an address. Got: {acc}")
        if not (role == Role.RESPONDER or role == role.INITIATOR):
            raise ValueError(f"Role must be {Role.INITIATOR} or {Role.RESPONDER}.")

        # create queue for incoming messages
        q = LifoQueue(maxsize=2000)
        self.q = q

        # calculate URL for websocket connect
        ini_addr = acc.get_address() if role == role.INITIATOR else partner_addr  # type:str
        res_addr = acc.get_address() if role == role.RESPONDER else partner_addr  # type:str
        ini_amt = initial_amount if role == role.INITIATOR else partner_initial_amount
        res_amt = initial_amount if role == role.RESPONDER else partner_initial_amount
        del partner_addr, initial_amount, partner_initial_amount

        options = {
            'initiator_id': ini_addr,
            'responder_id': res_addr,
            'lock_period': lock_period,
            'push_amount': push_amount,
            'initiator_amount': ini_amt,
            'responder_amount': res_amt,
            'channel_reserve': channel_reserve,
            'ttl': creation_tx_ttl,
            'nonce': creation_tx_nonce or epoch.get_next_nonce(ini_addr),
            'port': port,
            'role': role.value,
            'timeout_accept': timeout_accept,
            'timeout_funding_create': timeout_funding_create,
            'timeout_funding_sign': timeout_funding_sign,
            'timeout_funding_lock': timeout_funding_lock,
            'timeout_idle': timeout_idle,
            'timeout_open': timeout_open,
            'timeout_sign': timeout_sign,
            'minimum_depth': minimum_depth
        }

        if role == Role.INITIATOR:
            options["host"] = responder_host

        if existing_channel_id is not None and last_state_tx is not None:
            options['existing_channel_id'] = existing_channel_id
            options['offchain_tx'] = last_state_tx

        options_str = urllib.parse.urlencode(options)

        # create WebSocketApp thread to receive messages from the websocket
        def on_message(ws, message):
            message = json.loads(message)
            log.info(f"[{role.value}] " + message.__str__())
            try:
                action = message['action']
                if action == 'info':
                    pass
                else:
                    q.put(message)
            except Exception:
                log.warning(f"[{role.value}] Message without action tag: {message.__str__()}")

        def on_error(ws, message):
            log.warning(message)

        def on_close(ws):
            log.info(f"[{role.value}] ws closed")

        def on_open(ws: WebSocket):
            log.info(f"[{role.value}] ws open")

        def on_ping(ws, message):
            log.info(f"[{role.value}] ping received:" + str(message))

        def on_pong(ws, message):
            log.log(logging.NOTSET, f"[{role.value}] pong received:" + str(message))


        url = epoch._get_active_config().channels_url + "?" + options_str
        log.debug(f"About to connect to: {url}")
        ws = WebSocketApp(url,
                          on_open=on_open,
                          on_message=on_message,
                          on_error=on_error,
                          on_close=on_close,
                          on_ping=on_ping,
                          on_pong=on_pong)

        self._thread = Thread(target=ws.run_forever,
                              kwargs={'ping_interval': ping_interval})  # pings keep connection open
        log.debug("About to start " + role.value)
        self._thread.start()

        # Create function to submit messages
        def sendj(msg):
            log.debug(f"[{role.value} sent] " + msg.__str__())
            ws.sock.send(json.dumps(msg))

        self.s = sendj

        # Create message factory
        self.f = WsMsgFactory(me=acc,
                              partner_address=res_addr if role == Role.INITIATOR else ini_addr,
                              role=role,
                              channel_id=existing_channel_id,
                              network_id=network_id)

    def as_tuple(self) -> Tuple[LifoQueue, Callable[[dict], None], WsMsgFactory]:
        '''
        :return: (q, s, f) where
-        q: stack of incoming messages
-        s: function to submit a json message on the websocket
-        f: message factory for this connection
        '''
        return (self.q, self.s, self.f)

if __name__ == "__main__":
    '''
    Manual test of channel
    '''
    EXISTING_CHANNEL = None
    LAST_STATE = None

    R = EpochWSChannelConnection(role=Role.RESPONDER,
                                 acc=ACC_RESPONDER,
                                 partner_addr=ACC_INITIATOR.get_address(),
                                 existing_channel_id=EXISTING_CHANNEL,
                                 last_state_tx=LAST_STATE,
                                 network_id=EPOCH._get_active_config().network_id,
                                 epoch=EPOCH,
                                 initial_amount=10 ** 6,
                                 partner_initial_amount=10 ** 6)
    qr, sr, Fr = R.q, R.s, R.f

    I = EpochWSChannelConnection(role=Role.INITIATOR,
                                 acc=ACC_INITIATOR,
                                 partner_addr=ACC_RESPONDER.get_address(),
                                 existing_channel_id=EXISTING_CHANNEL,
                                 last_state_tx=LAST_STATE,
                                 network_id=EPOCH._get_active_config().network_id,
                                 epoch=EPOCH,
                                 initial_amount=10 ** 6,
                                 partner_initial_amount=10 ** 6
                                 )
    qi, si, Fi = I.q, I.s, I.f


    def both_acknowledge(initiator_is_starter=True):
        (S, A) = (I, R) if initiator_is_starter else (R, I)
        (ss, qs, Fs) = (S.s, S.q, S.f)
        (sa, qa, Fa) = (A.s, A.q, A.f)

        time.sleep(1)  # should use blocking/synchronous jsonrpc instead of this
        ss(Fs.sign_update(qs.get_nowait(), role="starter"))
        time.sleep(1)
        sa(Fa.sign_update(qa.get_nowait(), role="acknowledger"))


    if not EXISTING_CHANNEL:
        signing_request = qi.get()
        ch_open_tx = signing_request["payload"]["tx"]
        si(Fi.channel_open(ch_open_tx))
        sr(Fr.channel_open(ch_open_tx))
        time.sleep(30)
    else:
        time.sleep(1)

    m = qr.get_nowait()
    ch_id = m['channel_id']

    # transfers
    # si(Fi.transfer(ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address(), 10 ** 7))
    # both_acknowledge()

    # si(Fi.transfer(ACC_RESPONDER.get_address(), ACC_INITIATOR.get_address(), 2 * 10 ** 7))
    # both_acknowledge()

    # create contract
    C = Contract(open("contracts/AddConstant.aes", "r").read(), EPOCH)
    # C = Contract(open("contracts/FaucetMin.aes", "r").read(), EPOCH)

    si(Fi.contract_create(C.bytecode, C.encode_calldata("init", "(1000000)"), 0))
    both_acknowledge()

    state_parsed = parse_rlp(qi.get_nowait()["payload"]["state"])
    round = state_parsed.transaction.round

    ca = aeternity.hashing.contract_id(ACC_INITIATOR.get_address(), round)
    ca_ak = "ak_" + ca[3:]

    # put money into contract
    si(Fi.contract_call(ca, C.encode_calldata("add", "(0)"), 10 ** 6))
    both_acknowledge()
    sr(Fr.contract_call(ca, C.encode_calldata("add", "(0)"), 10 ** 6))
    both_acknowledge(initiator_is_starter=False)


    # withdraw
    # si(Fr.contract_call(ca, C.encode_calldata("take", "()")))
    # both_acknowledge()

    # get balances
    def get_balances(*addresses):
        si(Fi.info_balances(*addresses))
        time.sleep(1)
        m = qi.get_nowait()
        balances = dict()
        for x in m["payload"]:
            balances[x["account"]] = x["balance"]
        return balances


    balances = get_balances(ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address(), ca_ak)

    # get poi
    si(Fi.getPoi([ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address()],
                 [ca]))

    time.sleep(1)
    m = qi.get_nowait()
    old_poi = m["payload"]["poi"]

    # update
    si(Fi.transfer(ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address(),
                   0))  # it does not work if i set 1... but it also does not work if I get the POI after this transaction
    both_acknowledge()

    # get latest state - note that the root hash is the hash of the old poi, before the transfer
    m = qi.get_nowait()
    state = m['payload']['state']
    stateh = parse_rlp(state)

    # solo close
    sctx = EPOCH.tx_builder.tx_channel_close_solo(ACC_INITIATOR.get_address(),
                                                  state,
                                                  old_poi,
                                                  ch_id,
                                                  ttl=0,
                                                  fee=10 ** 6,  # todo: fee calculation function
                                                  nonce=EPOCH.get_next_nonce(ACC_INITIATOR.get_address()))

    signer = TxSigner(ACC_INITIATOR, CONF.network_id)
    txs, _, txh = signer.sign_encode_transaction(sctx)
    EPOCH.broadcast_transaction(txs, txh)

    time.sleep(30)

    # settle tx
    sctx = EPOCH.tx_builder.tx_channel_settle(ch_id,
                                              ACC_INITIATOR.get_address(),
                                              balances[ACC_INITIATOR.get_address()],
                                              balances[ACC_RESPONDER.get_address()],  # balance of contract is LOST!
                                              ttl=0,
                                              fee=10 ** 5,
                                              nonce=EPOCH.get_next_nonce(ACC_INITIATOR.get_address()))

    signer = TxSigner(ACC_INITIATOR, CONF.network_id)
    txs, _, txh = signer.sign_encode_transaction(sctx)
    EPOCH.broadcast_transaction(txs, txh)

    # initiator received initiator_amount_final - settleTx fee
    # responder received responder_amount_final
    pass
    sys.exit(0)
