import sys
from functools import lru_cache, wraps
from typing import cast

from brownie import accounts, network
from brownie.network.account import LocalAccount

DEV_CHAIN_IDS = {1337}


def is_live():
    return network.chain.id not in DEV_CHAIN_IDS


@lru_cache()
def get_deployer():
    if not is_live():
        return accounts[0]
    if network.chain.id == 137:
        return cast(LocalAccount, accounts.load("polygon-master"))
    raise ValueError(f"chain id {network.chain.id} not yet supported")


def abort(reason, code=1):
    print(f"error: {reason}", file=sys.stderr)
    sys.exit(code)


def with_deployed(Contract):
    def wrapped(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if len(Contract) == 0:
                abort(f"{Contract.deploy._name} not deployed")

            contract = Contract[0]
            result = f(contract, *args, **kwargs)
            return result

        return wrapper

    return wrapped
