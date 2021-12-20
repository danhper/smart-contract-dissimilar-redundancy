import time

import hypothesis.strategies as st
import pytest
from brownie import ZERO_ADDRESS
from brownie.exceptions import VirtualMachineError
from brownie.test import given, strategy
from brownie.test.strategies import _address_strategy as addresses

from tests.conftest import ArgumentType, NftCollection, encode_args


# NOTE: workaround to avoid modifying blockchain state when calling `request.getfixturevalue`
@pytest.fixture(autouse=True, scope="module")
def create_fixtures(nft_collection, alice_nft):
    pass


@pytest.fixture(scope="module")
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

    proxy.registerCheck(
        EnglishAuctionS.signatures["finalize"],
        nft_collection.address,
        encode_args(
            NftCollection, "ownerOf", [(ArgumentType.Static, ("uint256", alice_nft))]
        ),
        {"from": alice},
    )

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


class EnsureConsistent:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, _exc_tb):
        return not (
            exc_type == VirtualMachineError
            and exc_val.revert_msg.startswith("all implementations must")
        )


def ensure_consistent():
    return EnsureConsistent()


@given(bids=st.lists(st.tuples(st.integers(min_value=0), addresses())))
def test_bid_consistency(auction_proxy, bids):
    with ensure_consistent():
        for value, account in bids:
            auction_proxy.bid({"from": account, "value": value})


@given(bids=st.lists(st.tuples(st.integers(min_value=0), addresses())))
def test_finalize_consistency(chain, auction_proxy, bids, alice):
    with ensure_consistent():
        for value, account in bids:
            auction_proxy.bid({"from": account, "value": value})
        chain.sleep(3600)
        auction_proxy.finalize({"from": alice})
