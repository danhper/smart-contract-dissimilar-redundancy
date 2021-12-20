from brownie import accounts, network


def get_deployer():
    if network.chain.id == 137:
        return accounts.load("polygon-master")
    return accounts[0]
