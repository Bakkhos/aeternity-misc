import unittest
import aeternity
from aeternity.signing import Account
import aeternity.transactions, aeternity.oracles, aeternity.config, aeternity.contract, aeternity.epoch, aeternity.utils
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
from queue import Queue
from enum import Enum
from conf import *
from websocket import WebSocketApp, WebSocket, WebSocketTimeoutException, WebSocketPayloadException, WebSocketException
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class ProtocolState(Enum):
    CLOSED = 0
    INITIALIZED = 1
    ACCEPTED = 2
    HALF_SIGNED = 3
    SIGNED = 4
    OPEN = 5
    DISCONNECTED = 6
    CLOSING = 7

class OnchainChannelState(Enum):
    DOES_NOT_EXIST = 0
    OPEN = 1
    LOCKED = 2
    CLOSING = 3

class EpochWebsocketChannel:
    def __init__(self,
                 me : Account,
                 partner : str,
                 role : str = "initiator",
                 id: str = None,
                 state: ProtocolState = ProtocolState.CLOSED,
                 network_id : str = CONF.network_id,
                 ws : WebSocket = None
                 ):

        self.me = me
        self.partner = partner
        self.txsigner = TxSigner(me, network_id)
        self.id = id
        self.role = role
        self.state = state
        self.ws = ws

    def _channel_open(self, signing_request: str):
        opening_tx = json.loads(signing_request)["payload"]["tx"]
        #todo: parse opening_tx, extract initial state, persist it...

        txs, sig, txh = self.txsigner.sign_encode_transaction(opening_tx)
        msg = json.dumps(
            {
                "action": f"{self.role}_sign",
                "payload": {"tx": txs}
            })
        self.ws.send(msg)

    '''
    Perform arbitrary transaction within open channel
    '''
    def transact(self, tx):
        pass


    '''Propose mutual closure'''
    def close_mutual(self):
        pass

    '''
    
    '''


