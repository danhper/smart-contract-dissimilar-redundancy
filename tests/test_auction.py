import time

import pytest
from brownie import ZERO_ADDRESS


@pytest.fixture
def auction_proxy(
    alice,
    Proxy,
    EnglishAuctionS,
    EnglishAuctionV,
    nft_collection,
    alice_nft,
    interface,
):
    auction_s = alice.deploy(EnglishAuctionS)
    auction_v = alice.deploy(EnglishAuctionV)
    proxy = alice.deploy(Proxy)

    proxy.addImplementation(auction_s.address, b"")
    proxy.addImplementation(auction_v.address, b"")

    ends_at = int(time.time()) + 3_600
    auction = interface.IEnglishAuction(proxy)

    nft_collection.approve(auction.address, alice_nft, {"from": alice})

    auction.start(nft_collection, alice_nft, ends_at, {"from": alice})
    return auction


@pytest.mark.parametrize(
    "auction_name", ["english_auction_s", "english_auction_v", "auction_proxy"]
)
def test_bid(request, auction_name, bob):
    auction = request.getfixturevalue(auction_name)
    assert auction.highestBid() == 0
    assert auction.highestBidder() == ZERO_ADDRESS

    auction.bid({"from": bob, "value": 10 ** 18})

    assert auction.highestBid() == 10 ** 18
    assert auction.highestBidder() == bob
