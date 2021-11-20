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
    # proxy.addImplementation(auction_v.address, b"")

    ends_at = int(time.time()) + 3_600
    auction = interface.IEnglishAuction(proxy)

    nft_collection.approve(auction.address, alice_nft, {"from": alice})

    auction.start(nft_collection, alice_nft, ends_at, {"from": alice})
    return auction


def test_bid_s(bob, english_auction_s):
    assert english_auction_s.highestBid() == 0
    assert english_auction_s.highestBidder() == ZERO_ADDRESS

    english_auction_s.bid({"from": bob, "value": 10 ** 18})

    assert english_auction_s.highestBid() == 10 ** 18
    assert english_auction_s.highestBidder() == bob


def test_bid_v(bob, english_auction_v):
    assert english_auction_v.highestBid() == 0
    assert english_auction_v.highestBidder() == ZERO_ADDRESS

    english_auction_v.bid({"from": bob, "value": 10 ** 18})

    assert english_auction_v.highestBid() == 10 ** 18
    assert english_auction_v.highestBidder() == bob


def test_bid_proxy(bob, auction_proxy):
    assert auction_proxy.highestBid() == 0
    assert auction_proxy.highestBidder() == ZERO_ADDRESS

    auction_proxy.bid({"from": bob, "value": 10 ** 18})

    assert auction_proxy.highestBid() == 10 ** 18
    assert auction_proxy.highestBidder() == bob
