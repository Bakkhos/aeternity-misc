import sys
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

from common import CONF_PRIV, P3, P4

CONF = CONF_PRIV
ACC_INITIATOR = P3
ACC_RESPONDER = P4
epoch = EpochClient(debug=True,
                    native=True,
                    configs=[CONF])

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Role(Enum):
    INITIATOR = "initiator"
    RESPONDER = "responder"


class WsMsgFactory:
    def __init__(self,
                 me: Account,
                 partner_address: str,
                 role: Role = Role.INITIATOR,
                 channel_id: str = None,
                 network_id: str = CONF.network_id
                 ):
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

    def tx_mutual_close(self, channel_id,
                        amt_i,
                        amt_r,
                        partner_account: Account,
                        nonce=None,
                        fee=40000,
                        client: EpochClient = epoch,
                        network_id=None,
                        ttl=0):

        tx = client.tx_builder.tx_channel_close_mutual(self.me.get_address(),
                                                       channel_id,
                                                       amt_i,
                                                       amt_r,
                                                       ttl,
                                                       fee,
                                                       nonce=nonce or client.get_next_nonce(self.me.get_address()))
        signer = TxSigner(self.me,
                          network_id=network_id or client._get_active_config().network_id)

        return signer.cosign_encode_transaction(tx, partner_account)


def get_ws_thread(ini: Account = ACC_INITIATOR,
                  res: Account = ACC_RESPONDER,
                  role: Role = Role.RESPONDER,
                  existing_channel_id: str = None,
                  last_state_tx: str = None,
                  network_id: str = CONF.network_id,
                  lifoQueue: bool = True,
                  **kwargs) -> Tuple[Queue, Callable[[dict], None], Thread, WsMsgFactory]:
    '''
    Create a websocket client to interact with the epoch ws api
    :return: (q, s, t, f) where
        q: stack of incoming messages
        s: function to submit a json message on the websocket
        t: websocket handler thread
        f: message factory for this connection
    '''

    # calculate URL for websocket connect
    options = {
        'initiator_id': ini.get_address(),
        'responder_id': res.get_address(),
        'lock_period': 1,
        'push_amount': 0,
        'initiator_amount': 10 ** 9,
        'responder_amount': 10 ** 9,
        'channel_reserve': 10 ** 6,
        'ttl': 0,
        'nonce': 8,
        'port': 1234,
        'role': role.value,
        'timeout_accept': 3600000,
        'timeout_funding_create': 3600000,
        'timeout_funding_sign': 3600000,
        'timeout_funding_lock': 3600000,
        'timeout_idle': 3600000,
        'timeout_open': 3600000,
        'timeout_sign': 3600000,
        'minimum_depth': 2
    }
    options.update(kwargs)

    if role == Role.INITIATOR:
        options["host"] = "localhost"

    if existing_channel_id is not None and last_state_tx is not None:
        options['existing_channel_id'] = existing_channel_id
        options['offchain_tx'] = last_state_tx

    options_str = urllib.parse.urlencode(options)

    # create queue for incoming messages
    q = LifoQueue(maxsize=2000) if lifoQueue else Queue(maxsize=2000)

    # create WebSocketApp thread to handle communication with the websocket
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

    ws = WebSocketApp("ws://localhost:3014/channel" + "?" + options_str,
                      on_open=on_open,
                      on_message=on_message,
                      on_error=on_error,
                      on_close=on_close,
                      on_ping=on_ping,
                      on_pong=on_pong)

    T = Thread(target=ws.run_forever, kwargs={'ping_interval': 15}) #pings keep connection open
    log.debug("About to start " + role.value)
    T.start()

    # Create function to submit messages
    def sendj(msg):
        log.debug(f"[{role.value} sent] " + msg.__str__())
        ws.sock.send(json.dumps(msg))

    # Create message factory
    F = WsMsgFactory(me=ini if role == Role.INITIATOR else res,
                     partner_address=res.get_address() if role == Role.INITIATOR else ini.get_address(),
                     role=role,
                     channel_id=existing_channel_id,
                     network_id=network_id)

    return (q, sendj, T, F)

if __name__ == "__main__":
    '''
    Manual test of channel
    '''
    EXISTING_CHANNEL = None
    LAST_STATE = None

    qr, sr, Tr, Fr = get_ws_thread(ini=ACC_INITIATOR,
                                   res=ACC_RESPONDER,
                                   role=Role.RESPONDER,
                                   existing_channel_id=EXISTING_CHANNEL,
                                   last_state_tx=LAST_STATE,
                                   network_id=epoch._get_active_config().network_id)

    qi, si, Ti, Fi = get_ws_thread(ini=ACC_INITIATOR,
                                   res=ACC_RESPONDER,
                                   role=Role.INITIATOR,
                                   existing_channel_id=EXISTING_CHANNEL,
                                   last_state_tx=LAST_STATE,
                                   network_id=epoch._get_active_config().network_id)  # todo check: on action:leave, do both get get the same state?


    def both_acknowledge(initiator_is_starter=True):
        ((ss, Fs, qs), (sa, Fa, qa)) = ((si, Fi, qi), (sr, Fr, qr)) if initiator_is_starter else (
            (sr, Fr, qr), (si, Fi, qi))

        time.sleep(1)  #should use blocking/synchronous jsonrpc instead of this
        ss(Fs.sign_update(qs.get_nowait(), role="starter"))
        time.sleep(1)
        sa(Fa.sign_update(qa.get_nowait(), role="acknowledger"))


    if not EXISTING_CHANNEL:
        signing_request = qi.get()
        ch_open_tx = signing_request["payload"]["tx"]
        si(Fi.channel_open(ch_open_tx))
        sr(Fr.channel_open(ch_open_tx))
        time.sleep(60)
    else:
        time.sleep(1)

    m = qr.get_nowait()
    ch_id = m['channel_id']

    # transfers
    si(Fi.transfer(ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address(), 10**7))
    both_acknowledge()

    si(Fi.transfer(ACC_RESPONDER.get_address(), ACC_INITIATOR.get_address(), 2* 10**7))
    both_acknowledge()

    def nocontract():
        #get poi
        si(Fi.getPoi([ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address()],[]))
        time.sleep(1)
        m = qi.get_nowait()
        poi = m["payload"]["poi"]

        #get state
        state = qi.get_nowait()["payload"]["state"]

        # solo close
        sctx = epoch.tx_builder.tx_channel_close_solo(ACC_INITIATOR.get_address(),
                                                      state,
                                                      poi,
                                                      ch_id,
                                                      ttl=0,
                                                      fee=5 * 10 ** 6,
                                                      nonce=epoch.get_next_nonce(ACC_INITIATOR.get_address()))

        #settle
        sctx = epoch.tx_builder.tx_channel_settle(ACC_INITIATOR.get_address(),
                                                  state_round,
                                                  poi,
                                                  ch_id,
                                                  ttl=0,
                                                  fee=5 * 10 ** 6,
                                                  nonce=epoch.get_next_nonce(ACC_INITIATOR.get_address())).tx

        signer = TxSigner(ACC_INITIATOR, CONF.network_id)
        txs, _, txh = signer.sign_encode_transaction(sctx)
        epoch.broadcast_transaction(txs, txh)
        pass
        sys.exit(0)

    nocontract()

    def contract():
        # create contract
        C = Contract(open("contracts/FaucetMin.aes", "r").read(), epoch)

        si(Fi.contract_create(C.bytecode, C.encode_calldata("init", "(1000000)"), 0))
        both_acknowledge()

        ca = aeternity.hashing.contract_id(ACC_INITIATOR.get_address(), 2)
        ca_ak = "ak_" + ca[3:]

        # put money into contract
        si(Fi.contract_call(ca, C.encode_calldata("give", "()"), 10 ** 6))
        both_acknowledge()
        si(Fr.contract_call(ca, C.encode_calldata("give", "()"), 10 ** 6))
        both_acknowledge()

        # call, get money out
        si(Fr.contract_call(ca, C.encode_calldata("take", "()")))
        both_acknowledge()

        # get balances and state
        si(Fi.info_balances(ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address(), "ak_" + ca[3:]))

        # trivial update
        si(Fi.transfer(ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address(), 0))
        both_acknowledge()

        m = qi.get_nowait()
        state_round = m['payload']['state']

        # get poi
        si(Fi.getPoi([ACC_INITIATOR.get_address(), ACC_RESPONDER.get_address()],
                     [ca]))
        time.sleep(1)
        m = qi.get_nowait()
        poi = m["payload"]["poi"]

        # solo close
        sctx = epoch.tx_builder.tx_channel_close_solo(ACC_INITIATOR.get_address(),
                                                      state_round,
                                                      poi,
                                                      ch_id,
                                                      ttl=0,
                                                      fee=5 * 10 ** 6,
                                                      nonce=epoch.get_next_nonce(ACC_INITIATOR.get_address()))

        signer = TxSigner(ACC_INITIATOR, CONF.network_id)
        txs, _, txh = signer.sign_encode_transaction(sctx)
        epoch.broadcast_transaction(txs, txh)

        time.sleep(30)

        # settle tx
        sctx = epoch.tx_builder.tx_channel_settle(ACC_INITIATOR.get_address(),
                                                  state_round,
                                                  poi,
                                                  ch_id,
                                                  ttl=0,
                                                  fee=5 * 10 ** 6,
                                                  nonce=epoch.get_next_nonce(ACC_INITIATOR.get_address())).tx

        signer = TxSigner(ACC_INITIATOR, CONF.network_id)
        txs, _, txh = signer.sign_encode_transaction(sctx)
        epoch.broadcast_transaction(txs, txh)
        pass
        sys.exit(0)




















































































if not __name__ == '__main__':
    class WsHandler():
        def __init__(self,
                     ini: Account,
                     res: Account,
                     network_id: str,
                     role: Role = Role.RESPONDER,
                     existing_channel_id: str = None,
                     last_state_tx: str = None,
                     lifoQueue: bool = True,
                     **kwargs):
            q, s, T, F = get_ws_thread(ini=ini,
                                       res=res,
                                       role=role,
                                       existing_channel_id=existing_channel_id,
                                       last_state_tx=last_state_tx,
                                       network_id=network_id,
                                       lifoQueue=lifoQueue,
                                       **kwargs)
            self.q = q
            self.send = s
            self._T = T
            self.F = F

        def acknowledge(self, update = None, role="starter"):
            if not (role == "starter" or role == "acknowledger"):
                raise ValueError(f"Role {role} must be starter or acknowledger")
            if update is None:
                update = self.q.get_nowait()
            self.send(self.F.sign_update(update, role=role))
