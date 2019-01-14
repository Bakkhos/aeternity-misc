from collections import namedtuple
import aeternity as ae, aeternity.transactions, aeternity.hashing
import logging
from attr import attrs, attrib
from typing import Union, List

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

def _int(b: bytes) -> int:
    '''
    Deserialize int
    :param b: aeternity integer, as bytes
    :return:
    '''
    return int.from_bytes(b, "big")

def _id(b: bytes) -> str:
    '''
    :param b: aeternity identifier, as bytes
    :return: identifier as encoded string (th_, ch_, ak_, ...)
    '''
    PREFIX = {ae.transactions.ID_TAG_CHANNEL: ae.hashing.identifiers.CHANNEL,
              ae.transactions.ID_TAG_ACCOUNT: ae.hashing.identifiers.ACCOUNT_PUBKEY,
              ae.transactions.ID_TAG_ORACLE: ae.hashing.identifiers.ORACLE_PUBKEY,
              ae.transactions.ID_TAG_NAME: ae.hashing.identifiers.NAME,
              ae.transactions.ID_TAG_COMMITMENT: ae.hashing.identifiers.COMMITMENT,
              ae.transactions.ID_TAG_CONTRACT: ae.hashing.identifiers.CONTRACT_PUBKEY}
    tag = b[0]
    if tag in PREFIX.keys():
        return ae.hashing.encode(PREFIX.get(tag), b[1:])
    else:
        raise ValueError(f"Unrecognized Tag {tag} on identifier {b}")

#Classes for parsing objects into
# following naming scheme at https://github.com/aeternity/protocol/blob/master/serializations.md#signed-transaction
class SignedTx(namedtuple("SignedTx", ["signatures", "transaction"])):
    pass

@attrs(auto_attribs=True)
class ChannelOffchainUpdate(object):
    pass

@attrs(auto_attribs=True)
class ChannelOffchainUpdateTransfer(ChannelOffchainUpdate):
    frm : str
    to : str
    amount : int

@attrs(auto_attribs=True, frozen=True)
class ChannelOffchainTx(object):
    channel_id : str
    round : int
    updates : List[ChannelOffchainUpdate]
    state_hash : str

#class ChannelOffchainTx(namedtuple("ChannelOffchainTx", ["channel_id", "round", "updates", "state_hash"])):
#   pass

# class ChannelOffchainUpdateTransfer(namedtuple("ChannelOffchainUpdateTransfer", ["frm", "to", "amount"])):
#     pass

class MerklePatriciaTreeNode(namedtuple("MerklePatriciaTreeNode", ["mpt_hash","mpt_values"])):
    @classmethod
    def from_list(cls, l):
        [mpt_hash, mpt_values] = l
        return cls(mpt_hash = ae.hashing.encode(ae.hashing.identifiers.ACCOUNT_PUBKEY, mpt_hash),
                   mpt_values = [parse_rlp(ae.hashing.encode(ae.hashing.identifiers.ACCOUNT_PUBKEY,mpt_value)) for mpt_value in mpt_values])

class ProofOfInclusion(namedtuple("ProofOfInclusion", ["root_hash","treepath"])):
    @classmethod
    def from_list(cls, l):
        [root_hash, sortedpath] = l

        return cls(root_hash=ae.hashing.encode(ae.hashing.identifiers.ACCOUNT_PUBKEY, root_hash),
                   treepath = [MerklePatriciaTreeNode.from_list(node) for node in sortedpath])

class POI(namedtuple("POI", ["accounts","calls","channels","contracts","ns","oracles"])):
    @classmethod
    def from_list(cls, l):
        [accounts, calls, channels ,contracts, ns, oracles] = l

        return cls(accounts =   [ProofOfInclusion.from_list(akproof) for akproof in accounts],
                   calls =      [ProofOfInclusion.from_list(caproof) for caproof in calls],
                   channels =   [ProofOfInclusion.from_list(chproof) for chproof in channels],
                   contracts =  [ProofOfInclusion.from_list(coproof) for coproof in contracts],
                   ns =         [ProofOfInclusion.from_list(nmproof) for nmproof in ns],
                   oracles =    [ProofOfInclusion.from_list(okproof) for okproof in oracles]
                   )

def parse_rlp(rlp_serialized: str):
    '''
    Convert a RLP strings into a nametuple
    The field names and orders correspond to the names and orders in https://github.com/aeternity/protocol/blob/master/serializations.md
    Currently only works with states
    :param rlp_serialized: string encoded rlp serialized object
    :return: Namedtuple
    '''
    try:
        # todo: consider if this parser is really correct. it is way too ad-hoc...
        # will do as a utility for interactive use, for now
        obj = ae.hashing.decode_rlp(rlp_serialized)

        if len(obj) < 2:
            raise ValueError(f"Decoded RLP list {obj} is expected to have length >= 2")

        if not _int(obj[1]) == ae.transactions.VSN:
            raise ValueError(f"Unknown RLP version: {_int(obj[1])}")

        tag = _int(obj[0])

        if tag == ae.transactions.OBJECT_TAG_SIGNED_TRANSACTION:
            return SignedTx(signatures=[ae.hashing.encode(ae.hashing.identifiers.SIGNATURE, s) for s in obj[2]],
                            transaction=parse_rlp(ae.hashing.encode("tx", obj[3])))

        elif tag == ae.transactions.OBJECT_TAG_CHANNEL_OFF_CHAIN_TRANSACTION:
            return ChannelOffchainTx(channel_id=_id(obj[2]),
                                     round=_int(obj[3]),
                                     updates=[parse_rlp(ae.hashing.encode("tx", upd)) for upd in obj[4]],
                                     state_hash=ae.hashing.encode(ae.hashing.identifiers.STATE, obj[5]))
        elif tag == ae.transactions.OBJECT_TAG_POI:
            return POI.from_list(obj[2:])

        elif tag == ae.transactions.OBJECT_TAG_CHANNEL_OFF_CHAIN_UPDATE_TRANSFER:
            return ChannelOffchainUpdateTransfer(frm=_id(obj[2]),
                                                 to=_id(obj[3]),
                                                 amount=_int(obj[4]))

        else:
            log.warning(f"Unknown Object tag {tag}. Will not deserialize {rlp_serialized}")
            return rlp_serialized
    except Exception:
        raise ValueError(f"Exception parsing {rlp_serialized}")
