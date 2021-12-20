import time
from brownie import EnglishAuctionS, EnglishAuctionV, Proxy, interface  # type: ignore
from scripts.utils import get_deployer, with_deployed

from tests.conftest import ArgumentType, NftCollection, encode_args


@with_deployed(NftCollection)
def main(nft_collection):
    deployer = get_deployer()
    auction_s = deployer.deploy(EnglishAuctionS)
    auction_v = deployer.deploy(EnglishAuctionV)
    proxy = deployer.deploy(Proxy)

    proxy.addImplementation(auction_s.address, b"")
    proxy.addImplementation(auction_v.address, b"")

    token_id = nft_collection.tokenOfOwnerByIndex(deployer, 0)

    proxy.registerCheck(
        EnglishAuctionS.signatures["finalize"],
        nft_collection.address,
        encode_args(
            NftCollection, "ownerOf", [(ArgumentType.Static, ("uint256", token_id))]
        ),
        {"from": deployer},
    )

    ends_at = int(time.time()) + 3_600
    auction = interface.IEnglishAuction(proxy)

    nft_collection.approve(auction.address, token_id, {"from": deployer})

    auction.start(
        nft_collection, token_id, ends_at, {"from": deployer, "gas_price": 30 * 10 ** 9}
    )
