from aeternity.aens import AEName
from aeternity.epoch import EpochClient
from common import CONF_EDGE, E1
epoch = EpochClient(native=False,
                    configs=[CONF_EDGE],
                    debug=True)

def claim(client, account, name : str):
    name = AEName(name, client)
    if name.is_available():
        name.preclaim(account)
        name.claim(account)
        name.update(account, target=account.address)

if __name__ == '__main__':
    claim(epoch, E1, "schallundrauch.test")