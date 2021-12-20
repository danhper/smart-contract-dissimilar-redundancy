from brownie import accounts
from tests.conftest import NftCollection


def main():
    deployer = accounts[0]
    deployer.deploy(NftCollection, "Sample NFT", "SNF", "http://example.com/nft/")
