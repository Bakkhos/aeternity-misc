from aeternity.aens import AEName
from aeternity.config import Config
from aeternity.epoch import EpochClient
from aeternity.signing import Account
from conf import *

def claim(client, account, name : str):
    name = AEName(name, client)
    if name.is_available():
        name.preclaim(account)
        name.claim(account)
        name.update(account, target=account.address)

if __name__ == '__main__':
    claim(epoch, ACC, "schallundrauch.test")