import unittest
from aeternity.signing import Account
import aeternity.transactions, aeternity.oracles, aeternity.hashing, aeternity.config, aeternity.contract, \
    aeternity.epoch, aeternity.utils
import aeternity as ae
from aeternity.epoch import EpochClient
from aeternity.transactions import TxBuilder, TxSigner
from aeternity.oracles import Oracle
from aeternity.config import Config
from aeternity.contract import Contract, ContractError
from aeternity.aens import AEName
from pprint import pprint as pp, pformat as pf
from aeternity.openapi import OpenAPIClientDetailedException
import logging
import requests
from requests import Request, Response
from pprint import pprint
import IPython, json, threading
import urllib.parse
from aeternity.config import *
from threading import Thread
from typing import Tuple
from queue import Queue, LifoQueue
from enum import Enum
import time
import conf
from conf import *
from websocket import WebSocketApp, WebSocket, WebSocketTimeoutException, WebSocketPayloadException, WebSocketException

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

acc_initiator = conf.P3
acc_responder = conf.P4

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
        if not role == "starter" or role == "acknowledger":
            raise ValueError("Role must be starter or acknowledger")
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
        network_id = network_id or client._get_active_config().network_id
        nonce = nonce or client.get_next_nonce(self.me.get_address())

        tx = client.api.post_channel_close_mutual(body={
            "from_id": self.me.get_address(),
            "responder_amount_final": amt_i,
            "fee": fee,
            "initiator_amount_final": amt_r,
            "channel_id": channel_id,
            "ttl": ttl,
            "nonce" : nonce
        }).tx

        signer = TxSigner(self.me, network_id)

        return signer.cosign_encode_transaction(tx, partner_account)


def get_ws_thread(ini: Account = acc_initiator,
                  res: Account = acc_responder,
                  role: Role = Role.RESPONDER,
                  existing_channel_id: str = None,
                  last_state_tx: str = None,
                  network_id: str = CONF.network_id) -> Tuple[Queue, WebSocket, Thread, WsMsgFactory]:
    '''
    :return: (q, s, t, f) where
        q: stack of incoming messages for this websocket client
        s: websocket, decorated with .sendj method to submit json messages
        t: websocket handler thread
        f: message factory for this websocket client
    '''
    options = {
        'initiator_id': ini.get_address(),
        'responder_id': res.get_address(),
        'lock_period': 1,
        'push_amount': 0,
        'initiator_amount': 10**9,
        'responder_amount': 10**9,
        'channel_reserve': 10**6,
        'ttl': 0,
        'nonce' : 8,
        'port': 1234,
        'role': role.value,
        'timeout_accept': 3600000,
        'timeout_funding_create': 3600000,
        'timeout_funding_sign': 3600000,
        'timeout_funding_lock': 3600000,
        'timeout_idle': 3600000,
        'timeout_open': 3600000,
        'timeout_sign': 3600000,
        'minimum_depth': 2,
        'MinDepth' : 1, "min_depth" : 1
    }
    if role == Role.INITIATOR:
        options["host"] = "localhost"

    if existing_channel_id is not None and last_state_tx is not None:
        options['existing_channel_id'] = existing_channel_id
        options['offchain_tx'] = last_state_tx

    q = LifoQueue(maxsize=2000)

    options_str = urllib.parse.urlencode(options)

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

    T = Thread(target=ws.run_forever, kwargs={'ping_interval': 15})
    log.debug("About to start " + role.value)
    T.start()

    def sendj(msg):
        log.debug(f"[{role.value} sent] " + msg.__str__())
        ws.sock.send(json.dumps(msg))
    ws.sock.sendj = sendj

    F = WsMsgFactory(me=ini if role == Role.INITIATOR else res,
                     partner_address=res.get_address() if role == Role.INITIATOR else ini.get_address(),
                     role=role,
                     channel_id=existing_channel_id,
                     network_id=network_id)

    return (q, ws.sock, T, F)

EXISTING_CHANNEL = "ch_25sqma1dMKbDnKrv14r9Hokvz9RncQb4DQmA6aNVT8whXsgV5z"
LAST_STATE =  'tx_+QEhCwH4hLhAIm1kX8yP/VE0wEK2gBosm0BTEpbCikESiTjU6PVASHf9v0gCr7rlCVzk0wkWyCQu5mPwVQuWlIebl12VJxGdCrhAKNY3rU3F+LgqKPkBSxLLkFv2MbV8gB5WWXyaiUz1A9wCDWgYBNYPe0xH+H6vjMOTtM9dqckZ+HRIGU7pmxkfALiX+JU5AaEGjsTY8PZlPqQbwJkFeVuYqVnJpyuvFwfO/e/2rBpV/JcF+E24S/hJggI6AaEBhQ28rSi+fAwdzrAiB4k1FxYD2gF7EOg5DLwZ+fTnFJ2hAexHBYw0cRKr7MkjpAYyigrfnm3zk9lEoMqpTCU0cMG/AKBraNSrjWf4aT6yv9vp/1PlTsvOxVK6rqumH3Yk6WCPuWHD11o='

qr, sr, Tr, Fr = get_ws_thread(ini=acc_initiator,
                               res=acc_responder,
                               role=Role.RESPONDER,
                               existing_channel_id=EXISTING_CHANNEL,
                               last_state_tx=LAST_STATE,
                               network_id=epoch._get_active_config().network_id)

qi, si, Ti, Fi = get_ws_thread(ini=acc_initiator,
                               res=acc_responder,
                               role=Role.INITIATOR,
                               existing_channel_id=EXISTING_CHANNEL,
                               last_state_tx=LAST_STATE,
                               network_id=epoch._get_active_config().network_id) #todo check: on action:leave, do both get get the same state?

def clearq():
    '''
    Clear qi and qr
    '''
    while not qi.empty():
        qi.get_nowait()
    while not qr.empty():
        qr.get_nowait()


if not EXISTING_CHANNEL:
    signing_request = qi.get()
    ch_open_tx = signing_request["payload"]["tx"]
    si.sendj(Fi.channel_open(ch_open_tx))
    sr.sendj(Fr.channel_open(ch_open_tx))
    time.sleep(3*60)
else:
    time.sleep(1)

m = qr.get_nowait()
ch_id = m['channel_id']

def both_acknowledge(initiator_is_starter=True):
    ((ss, Fs, qs), (sa, Fa, qa)) = ((si, Fi, qi), (sr, Fr, qr)) if initiator_is_starter else ((sr, Fr, qr), (si, Fi, qi))

    time.sleep(1)
    ss.sendj(Fs.sign_update(qs.get_nowait(), role="starter"))
    time.sleep(1)
    sa.sendj(Fa.sign_update(qa.get_nowait(), role="acknowledger"))

if not EXISTING_CHANNEL:
    #create contract
    C = Contract(open("contracts/AddConstant.aes", "r").read(), epoch)

    si.sendj(Fi.contract_create(C.bytecode, C.encode_calldata("init", "(42)"), 0))
    both_acknowledge()

    ca = aeternity.hashing.contract_id(acc_initiator.get_address(), 2)
    ca_ak = "ak_" + ca[3:]

    #put money into contract
    si.sendj(Fi.contract_call(ca, C.encode_calldata("add", "(1)"), 10**6))
    both_acknowledge()
    si.sendj(Fr.contract_call(ca, C.encode_calldata("add", "(1)"), 10**6))
    both_acknowledge()

    #transfers
    # si.sendj(Fi.transfer(Acci.get_address(), Accr.get_address(), 10**7))
    # both_acknowledge()
    #
    # si.sendj(Fi.transfer(Accr.get_address(), Acci.get_address(), 2* 10**7))
    # both_acknowledge()

    # call, get money out
    #si.sendj(Fr.contract_call(ca, C.encode_calldata("take", "()")))
    #both_acknowledge()

    #sr.sendj(Fr.transfer(Acci.get_address(), Accr.get_address(), 10000))
    #both_acknowledge(False)

# get balances and state
si.sendj(Fi.info_balances(acc_initiator.get_address(), acc_responder.get_address(), "ak_" + ca[3:]))

#trivial update
si.sendj(Fi.transfer(acc_initiator.get_address(), acc_responder.get_address(), 0))
both_acknowledge()

m = qi.get_nowait()
state_round = m['payload']['state']

# get poi
si.sendj(Fi.getPoi([acc_initiator.get_address(), acc_responder.get_address()],
                   [ca]))
time.sleep(1)
m = qi.get_nowait()
poi = m["payload"]["poi"]

#leave
si.sendj({"action" : "leave"})
time.sleep(1)
m = qi.get_nowait()
state_round_last = m["payload"]["state"]

print(state_round_last == state_round)


sctx = epoch.tx_builder.tx_channel_close_solo(acc_initiator.get_address(),
                                              state_round,
                                              poi,
                                              ch_id,
                                              ttl=0,
                                              fee=100000,
                                              nonce=epoch.get_next_nonce(acc_initiator.get_address()))

signer = TxSigner(acc_initiator, epoch._get_active_config().network_id)
txs, _, txh = signer.sign_encode_transaction(sctx)
epoch.broadcast_transaction(txs, txh)

time.sleep(5*60)

#settle tx
sctx = epoch.tx_builder.tx_channel_settle(acc_initiator.get_address(),
                                          state_round,
                                          poi,
                                          ch_id,
                                          ttl=0,
                                          fee=100000,
                                          nonce=epoch.get_next_nonce(acc_initiator.get_address())).tx

signer = TxSigner(acc_initiator, epoch._get_active_config().network_id)
txs, _, txh = signer.sign_encode_transaction(sctx)
epoch.broadcast_transaction(txs, txh)

pass
