import time
from pathlib import Path
from typing import Callable, Iterable, Optional, TypeVar

import pytest
from brownie import config, project
from brownie.project.main import Project

INITIAL_SUPPLY = 200_000_000 * 10 ** 18

BROWNIE_PACKAGES_PATH = Path.home() / ".brownie" / "packages"

T = TypeVar("T")


class ArgumentType:
    Static = 0
    CallData = 1
    Env = 2


class EnvArg:
    Chainid = 0
    Coinbase = 1
    Difficulty = 2
    Gaslimit = 3
    Number = 4
    Timestamp = 5
    Gasleft = 6
    Sender = 7
    Sig = 8
    Value = 9
    Gasprice = 10
    Origin = 11


@pytest.fixture(autouse=True)
def isolation_setup(fn_isolation):
    pass


def find(
    predicate: Callable[[T], bool], iterable: Iterable[T], message: Optional[str] = None
) -> T:
    for item in iterable:
        if predicate(item):
            return item
    if message is None:
        message = f"not found in {iterable}"
    raise ValueError(message)


def load_dependent_project(name: str) -> Project:
    dependency_name = find(lambda dep: f"{name}@" in dep, config["dependencies"])
    return project.load(BROWNIE_PACKAGES_PATH / dependency_name)  # type: ignore


NftCollection = load_dependent_project("openzeppelin-contracts").ERC721PresetMinterPauserAutoId  # type: ignore


@pytest.fixture
def admin(accounts):
    return accounts[0]


@pytest.fixture
def alice(accounts):
    return accounts[1]


@pytest.fixture
def bob(accounts):
    return accounts[2]


@pytest.fixture
def trivial_token_s(admin, TrivialTokenS):
    return admin.deploy(TrivialTokenS)


@pytest.fixture
def trivial_token_v(admin, TrivialTokenV):
    return admin.deploy(TrivialTokenV)


@pytest.fixture
def proxy_trivial_token_v_raw(admin, trivial_token_v, Proxy):
    data = trivial_token_v.initialize.encode_input(INITIAL_SUPPLY)
    deployed = admin.deploy(Proxy)
    deployed.addImplementation(trivial_token_v.address, data)
    return deployed


@pytest.fixture
def proxy_trivial_token_v(admin, proxy_trivial_token_v_raw, interface):
    return interface.IERC20(proxy_trivial_token_v_raw, owner=admin)


@pytest.fixture
def proxy_trivial_token_s_raw(admin, trivial_token_s, Proxy):
    data = trivial_token_s.initialize.encode_input(INITIAL_SUPPLY)
    deployed = admin.deploy(Proxy)
    deployed.addImplementation(trivial_token_s.address, data)
    return deployed


@pytest.fixture
def proxy_trivial_token_s(admin, proxy_trivial_token_s_raw, interface):
    return interface.IERC20(proxy_trivial_token_s_raw, owner=admin)


@pytest.fixture
def nft_collection(admin):
    return admin.deploy(NftCollection, "Sample NFT", "SNF", "http://example.com/nft/")


@pytest.fixture
def alice_nft(nft_collection, alice):
    nft_collection.mint(alice)
    token_id = nft_collection.tokenOfOwnerByIndex(
        alice, nft_collection.balanceOf(alice) - 1
    )
    return token_id


def deploy_auction(Contract, seller, nft_collection, token_id):
    ends_at = int(time.time()) + 3_600
    auction = seller.deploy(Contract)
    nft_collection.approve(auction, token_id, {"from": seller})
    auction.start(nft_collection, token_id, ends_at, {"from": seller})
    return auction


@pytest.fixture
def english_auction_s(alice, EnglishAuctionS, nft_collection, alice_nft):
    return deploy_auction(EnglishAuctionS, alice, nft_collection, alice_nft)


@pytest.fixture
def english_auction_v(alice, EnglishAuctionV, nft_collection, alice_nft):
    return deploy_auction(EnglishAuctionV, alice, nft_collection, alice_nft)
