import time
from pathlib import Path
from typing import Callable, Iterable, Optional, TypeVar

import pytest
from brownie import config, project
from brownie.project.main import Project
from eth_abi.abi import encode_single

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


@pytest.fixture(scope="session")
def admin(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def alice(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def bob(accounts):
    return accounts[2]


@pytest.fixture(scope="session")
def charlie(accounts):
    return accounts[3]


@pytest.fixture(scope="module")
def trivial_token_s(admin, TrivialTokenS):
    return admin.deploy(TrivialTokenS)


@pytest.fixture(scope="module")
def trivial_token_v(admin, TrivialTokenV):
    return admin.deploy(TrivialTokenV)


@pytest.fixture(scope="module")
def proxy_trivial_token_v_raw(admin, trivial_token_v, Proxy):
    data = trivial_token_v.initialize.encode_input(INITIAL_SUPPLY)
    deployed = admin.deploy(Proxy)
    deployed.addImplementation(trivial_token_v.address, data)
    return deployed


@pytest.fixture(scope="module")
def proxy_trivial_token_v(admin, proxy_trivial_token_v_raw, interface):
    return interface.IERC20(proxy_trivial_token_v_raw, owner=admin)


@pytest.fixture(scope="module")
def proxy_trivial_token_s_raw(admin, trivial_token_s, Proxy):
    data = trivial_token_s.initialize.encode_input(INITIAL_SUPPLY)
    deployed = admin.deploy(Proxy)
    deployed.addImplementation(trivial_token_s.address, data)
    return deployed


@pytest.fixture(scope="module")
def proxy_trivial_token_s(admin, proxy_trivial_token_s_raw, interface):
    return interface.IERC20(proxy_trivial_token_s_raw, owner=admin)


@pytest.fixture(scope="module")
def nft_collection(admin):
    return admin.deploy(NftCollection, "Sample NFT", "SNF", "http://example.com/nft/")


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def english_auction_s(alice, EnglishAuctionS, nft_collection, alice_nft):
    return deploy_auction(EnglishAuctionS, alice, nft_collection, alice_nft)


@pytest.fixture(scope="module")
def english_auction_v(alice, EnglishAuctionV, nft_collection, alice_nft):
    return deploy_auction(EnglishAuctionV, alice, nft_collection, alice_nft)


def encode_args(contract, func_name, arguments):
    data = bytes.fromhex(contract.signatures[func_name][2:])
    data += len(arguments).to_bytes(1, byteorder="big")
    for arg_type, arg_data in arguments:
        data += arg_type.to_bytes(1, byteorder="big")
        if arg_type == ArgumentType.Static:
            arg_data = encode_single(arg_data[0], arg_data[1])
            data += len(arg_data).to_bytes(2, byteorder="big")
            data += arg_data
        elif arg_type == ArgumentType.CallData:
            data += arg_data[0].to_bytes(2, byteorder="big")
            data += arg_data[1].to_bytes(2, byteorder="big")
        elif arg_type == ArgumentType.Env:
            data += arg_data.to_bytes(1, byteorder="big")
    return data
