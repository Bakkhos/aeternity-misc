import json
import unittest
import aeternity
from aeternity.openapi import OpenAPIClientException
from aeternity.signing import Account
import aeternity.transactions, aeternity.oracles, aeternity.config, aeternity.contract, aeternity.epoch, aeternity.utils, aeternity.hashing as encoding
from aeternity.epoch import EpochClient
from aeternity.transactions import TxBuilder, TxSigner
from aeternity.oracles import Oracle
from aeternity.config import Config
from aeternity.contract import Contract, ContractError
from aeternity.aens import AEName
from pprint import pprint as pp, pformat as pf
import logging
import IPython
from aeternity.config import *
from conf import *


# channel endpoints
# Api(name='post_channel_create', doc='Get a channel_create transaction object', params=[
#     Param(name='body', raw='body', pos='body',
#           field=FieldDef(required=True, type='#/definitions/ChannelCreateTx', values=[], minimum=None, maximum=None,
#                          default=None))], responses={200: Resp(schema='UnsignedTx', desc='Successful operation'),
#                                                      400: Resp(schema='Error', desc='Invalid transaction'),
#                                                      404: Resp(schema='Error', desc='Initiator not found')},
#     endpoint='https://sdk-edgenet.aepps.com/v2/debug/channels/create', http_method='post'),
# Api(name='post_channel_deposit', doc='Get a channel_deposit transaction object', params=[
#     Param(name='body', raw='body', pos='body',
#           field=FieldDef(required=True, type='#/definitions/ChannelDepositTx', values=[], minimum=None, maximum=None,
#                          default=None))], responses={200: Resp(schema='UnsignedTx', desc='Successful operation'),
#                                                      400: Resp(schema='Error', desc='Invalid transaction')},
#     endpoint='https://sdk-edgenet.aepps.com/v2/debug/channels/deposit', http_method='post'),
# Api(name='post_channel_withdraw', doc='Get a channel_withdrawal transaction object', params=[
#     Param(name='body', raw='body', pos='body',
#           field=FieldDef(required=True, type='#/definitions/ChannelWithdrawTx', values=[], minimum=None, maximum=None,
#                          default=None))], responses={200: Resp(schema='UnsignedTx', desc='Successful operation'),
#                                                      400: Resp(schema='Error', desc='Invalid transaction')},
#     endpoint='https://sdk-edgenet.aepps.com/v2/debug/channels/withdraw', http_method='post'),
# Api(name='post_channel_snapshot_solo', doc='Get a channel_snapshot_solo transaction object', params=[
#     Param(name='body', raw='body', pos='body',
#           field=FieldDef(required=True, type='#/definitions/ChannelSnapshotSoloTx', values=[], minimum=None,
#                          maximum=None, default=None))],
#     responses={200: Resp(schema='UnsignedTx', desc='Successful operation'),
#                400: Resp(schema='Error', desc='Invalid transaction')},
#     endpoint='https://sdk-edgenet.aepps.com/v2/debug/channels/snapshot/solo', http_method='post'),
# Api(name='post_channel_close_mutual', doc='Get a channel_close_mutual transaction object', params=[
#     Param(name='body', raw='body', pos='body',
#           field=FieldDef(required=True, type='#/definitions/ChannelCloseMutualTx', values=[], minimum=None,
#                          maximum=None, default=None))],
#     responses={200: Resp(schema='UnsignedTx', desc='Successful operation'),
#                400: Resp(schema='Error', desc='Invalid transaction')},
#     endpoint='https://sdk-edgenet.aepps.com/v2/debug/channels/close/mutual', http_method='post'),
# Api(name='post_channel_close_solo', doc='Get a channel_close_solo transaction object', params=[
#     Param(name='body', raw='body', pos='body',
#           field=FieldDef(required=True, type='#/definitions/ChannelCloseSoloTx', values=[], minimum=None, maximum=None,
#                          default=None))], responses={200: Resp(schema='UnsignedTx', desc='Successful operation'),
#                                                      400: Resp(schema='Error', desc='Invalid transaction')},
#     endpoint='https://sdk-edgenet.aepps.com/v2/debug/channels/close/solo', http_method='post'),
# Api(name='post_channel_slash', doc='Get a channel_slash transaction object', params=[
#     Param(name='body', raw='body', pos='body',
#           field=FieldDef(required=True, type='#/definitions/ChannelSlashTx', values=[], minimum=None, maximum=None,
#                          default=None))], responses={200: Resp(schema='UnsignedTx', desc='Successful operation'),
#                                                      400: Resp(schema='Error', desc='Invalid transaction')},
#     endpoint='https://sdk-edgenet.aepps.com/v2/debug/channels/slash', http_method='post'),
# Api(name='post_channel_settle', doc='Get a channel_settle transaction object', params=[
#     Param(name='body', raw='body', pos='body',
#           field=FieldDef(required=True, type='#/definitions/ChannelSettleTx', values=[], minimum=None, maximum=None,
#                          default=None))], responses={200: Resp(schema='UnsignedTx', desc='Successful operation'),
#                                                      400: Resp(schema='Error', desc='Invalid transaction')},
#     endpoint='https://sdk-edgenet.aepps.com/v2/debug/channels/settle', http_method='post'),

# create channel based on top of chain
global_state_hash = epoch.get_top_block().state_hash
#
try:
    cctx = epoch.api.post_channel_create(body={
        "responder_amount": 10**9,
        "initiator_amount": 10**9,
        "initiator_id": ACC.get_address(),
        "responder_id": ACC2.get_address(),
        "state_hash": encoding.hash_encode(encoding.identifiers.STATE,"()"),  #hash of the channel's state... how to compute state and hash? any tools?
        "fee": DEFAULT_FEE,
        "push_amount": 0, #?
        "ttl": DEFAULT_TX_TTL,
        "nonce": epoch.get_next_nonce(ACC.get_address()),
        "lock_period": 10, #10 blocks?
        "channel_reserve": 10**8
    }).tx
except OpenAPIClientException as e:
    print(e)


signer = aeternity.transactions.TxSigner(ACC,'ae_devnet')
tx, sig, txhash = signer.sign_encode_transaction(cctx)

epoch.broadcast_transaction(tx, txhash)


# Channels documentation:
# https://github.com/aeternity/protocol/blob/master/channels/README.md
# http://aeternity.com/epoch-api-docs/#/channel
