import aeternity as ae
import aeternity.hashing
import aeternity.identifiers
from aeternity.transactions import *
from aeternity.identifiers import *
from typing import Union

def readable(data : Union[str, list]):
    '''
    Heuristic
    Doesnt work well
    Decodes a rlp string into a form that is easier to understand and can be readily used to display the rlp structure
    in a tool like 'aecli inspect' or while debugging
    :param data: rlp string or decoded list
    :return:
    '''
    if isinstance(data, str):
        data = decode_rlp(data)
    else:
        try:
            encode_rlp("tx", data) #this throws an error on malformed rlp lists
        except Exception as e:
            raise ValueError(e)

    def _readable(rlp):
        '''
        Translate rlp into human readable form recursively
        :param data:
        :return:
        '''

        #Base cases
        if isinstance(rlp, bytes):
            if len(rlp) == 0:
                return b''
            if len(rlp) < 5:
                return int.from_bytes(rlp, "big")
            elif len(rlp) == 33:
                tag=rlp[0]
                id =rlp[1:]
                if tag == ID_TAG_ACCOUNT:
                    return encode(ACCOUNT_PUBKEY, id)
                elif tag == ID_TAG_CHANNEL:
                    return encode(CHANNEL, id)
                elif tag == ID_TAG_COMMITMENT:
                    return encode(COMMITMENT, id)
                elif tag == ID_TAG_NAME:
                    return encode(NAME, id)
                elif tag == ID_TAG_ORACLE:
                    return encode(ORACLE_PUBKEY, id)
                else:
                    return "??_" + encode("tx", rlp)[3:]
            else:
                return "??_" + encode("tx", rlp)[3:]
        elif isinstance(rlp, list):
            return [_readable(x) for x in rlp]
        else:
            raise ValueError

    return _readable(data)
