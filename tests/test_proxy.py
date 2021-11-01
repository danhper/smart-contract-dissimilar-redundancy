from conftest import INITIAL_SUPPLY
from eth_abi.abi import decode_single
from brownie.exceptions import VirtualMachineError

TRANSFERED_AMOUNT = 2 * 10 ** 18


def test_proxy(proxy_trivial_token_v):
    assert proxy_trivial_token_v.totalSupply() == INITIAL_SUPPLY


def make_args(accounts, raw_proxy, token_proxy, last_value=None):
    args = [
        raw_proxy.implementations(0),
        token_proxy.transfer.encode_input(accounts[2], TRANSFERED_AMOUNT),
        [
            (token_proxy, token_proxy.balanceOf(accounts[0])),
            (token_proxy, token_proxy.balanceOf(accounts[2])),
        ],
    ]
    if last_value is not None:
        args.append(last_value)
    return args


def test_get_error_message(accounts, proxy_trivial_token_v_raw, proxy_trivial_token_v):
    args = make_args(accounts, proxy_trivial_token_v_raw, proxy_trivial_token_v)
    tx = proxy_trivial_token_v_raw.getErrorMessage(*args)
    delegate_call_tx = proxy_trivial_token_v_raw.delegateAndCheck(*[*args, False])
    assert tx.return_value == delegate_call_tx.return_value


def test_delegate_and_check(
    accounts,
    proxy_trivial_token_v_raw,
    proxy_trivial_token_v,
    proxy_trivial_token_s_raw,
    proxy_trivial_token_s,
):
    args = make_args(accounts, proxy_trivial_token_v_raw, proxy_trivial_token_v, True)
    try:
        tx = proxy_trivial_token_v_raw.delegateAndCheck(*args)
        assert False, "tx should fail"
    except VirtualMachineError as ex:
        assert ex.revert_msg
        skip_bytes = len("typed error: 0xfb04fa8e")
        success_v, return_data_v, checks_hash_v = decode_single(
            "(bool,bytes,bytes32)", bytes.fromhex(ex.revert_msg[skip_bytes:])
        )
    assert success_v
    assert decode_single("bool", return_data_v)
    assert proxy_trivial_token_v.balanceOf(accounts[2]) == 0
    assert proxy_trivial_token_v.balanceOf(accounts[0]) == INITIAL_SUPPLY

    args = make_args(accounts, proxy_trivial_token_s_raw, proxy_trivial_token_s, False)
    tx = proxy_trivial_token_s_raw.delegateAndCheck(*args)
    success_s, return_data_s, checks_hash_s = tx.return_value
    assert success_s
    assert decode_single("bool", return_data_s)
    assert checks_hash_s.hex() == checks_hash_v.hex()
    assert proxy_trivial_token_s.balanceOf(accounts[2]) == TRANSFERED_AMOUNT
    assert (
        proxy_trivial_token_s.balanceOf(accounts[0])
        == INITIAL_SUPPLY - TRANSFERED_AMOUNT
    )


def test_register_checks(
    accounts, TrivialTokenV, proxy_trivial_token_v, proxy_trivial_token_v_raw
):
    signature = TrivialTokenV.signatures["transfer"]
    assert len(proxy_trivial_token_v_raw.getChecks(signature)) == 0
    proxy_trivial_token_v_raw.registerCheck(
        signature,
        proxy_trivial_token_v_raw.address,
        proxy_trivial_token_v.totalSupply.encode_input(),
        {"from": accounts[0]},
    )
    assert len(proxy_trivial_token_v_raw.getChecks(signature)) == 1
