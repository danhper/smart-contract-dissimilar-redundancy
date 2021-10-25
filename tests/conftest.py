import pytest

INITIAL_SUPPLY = 200_000_000 * 10 ** 18


@pytest.fixture
def admin(accounts):
    return accounts[0]


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
def proxy_trivial_token_s(admin, trivial_token_s, Proxy, interface):
    data = trivial_token_s.initialize.encode_input(INITIAL_SUPPLY)
    deployed = admin.deploy(Proxy)
    deployed.addImplementation(trivial_token_s, data)
    return interface.IERC20(deployed, owner=admin)
