from aeternity.aens import AEName
from aeternity.epoch import EpochClient
from common import CONF_PRIV, CONF_EDGE, P3, E1
ACC, CONF = P3, CONF_PRIV

epoch = EpochClient(native=False,
                    configs=[CONF],
                    debug=True,
                    blocking_mode=True)

def claim(client, account, name : str):
    name = AEName(name, client)
    if name.is_available():
        name.preclaim(account)
        name.claim(account)
        name.update(account, target=account.address)
    else:
        print(f"name {name} is taken")

if __name__ == '__main__':
    claim(epoch, ACC, "schallundrauch.test")