import time
from brownie import EnglishAuctionS, EnglishAuctionV, Proxy, interface  # type: ignore
from scripts.utils import get_deployer, with_deployed

from tests.conftest import NftCollection


@with_deployed(NftCollection)
def _deploy_auction(nft_collection, AuctionContract):
    deployer = get_deployer()
    auction = deployer.deploy(AuctionContract)

    token_id = nft_collection.tokenOfOwnerByIndex(deployer, 0)
    ends_at = int(time.time()) + 3_600

    nft_collection.approve(auction.address, token_id, {"from": deployer})

    auction.start(nft_collection, token_id, ends_at, {"from": deployer})


def solidity():
    _deploy_auction(EnglishAuctionS)


def vyper():
    _deploy_auction(EnglishAuctionV)
