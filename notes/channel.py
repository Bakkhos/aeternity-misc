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
from common import *

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

# Channels documentation:
# https://github.com/aeternity/protocol/blob/master/channels/README.md
# http://aeternity.com/epoch-api-docs/#/channel
