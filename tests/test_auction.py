from brownie import ZERO_ADDRESS


def test_bid_s(alice, english_auction_s):
    assert english_auction_s.highestBid() == 0
    assert english_auction_s.highestBidder() == ZERO_ADDRESS

    english_auction_s.bid({"from": alice, "value": 10 ** 18})

    assert english_auction_s.highestBid() == 10 ** 18
    assert english_auction_s.highestBidder() == alice


def test_bid_v(alice, english_auction_v):
    assert english_auction_v.highestBid() == 0
    assert english_auction_v.highestBidder() == ZERO_ADDRESS

    english_auction_v.bid({"from": alice, "value": 10 ** 18})

    assert english_auction_v.highestBid() == 10 ** 18
    assert english_auction_v.highestBidder() == alice
