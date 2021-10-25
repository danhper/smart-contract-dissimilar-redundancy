from conftest import INITIAL_SUPPLY
from eth_abi.abi import decode_single
from brownie.exceptions import VirtualMachineError


def test_proxy(proxy_trivial_token_v):
    assert proxy_trivial_token_v.totalSupply() == INITIAL_SUPPLY


def test_get_error_message(accounts, proxy_trivial_token_v_raw, proxy_trivial_token_v):
    transfered_amount = 2 * 10 ** 18

    try:
        tx = proxy_trivial_token_v_raw.getErrorMessage(
            proxy_trivial_token_v_raw.implementations(0),
            proxy_trivial_token_v.transfer.encode_input(accounts[2], transfered_amount),
            [
                (proxy_trivial_token_v, proxy_trivial_token_v.balanceOf(accounts[0])),
                (proxy_trivial_token_v, proxy_trivial_token_v.balanceOf(accounts[2])),
            ],
        )
        print("return value", tx.return_value)
    except VirtualMachineError as ex:
        print("revert msg", ex.revert_msg)


def test_delegate_and_check(accounts, proxy_trivial_token_v_raw, proxy_trivial_token_v):
    transfered_amount = 2 * 10 ** 18

    tx = proxy_trivial_token_v_raw.delegateAndCheck(
        proxy_trivial_token_v_raw.implementations(0),
        proxy_trivial_token_v.transfer.encode_input(accounts[2], transfered_amount),
        [
            (proxy_trivial_token_v, proxy_trivial_token_v.balanceOf(accounts[0])),
            (proxy_trivial_token_v, proxy_trivial_token_v.balanceOf(accounts[2])),
        ],
        False,
    )
    success, return_data, _checks_hash = tx.return_value
    assert success
    assert decode_single("bool", return_data)
    assert proxy_trivial_token_v.balanceOf(accounts[2]) == transfered_amount
    assert (
        proxy_trivial_token_v.balanceOf(accounts[0])
        == INITIAL_SUPPLY - transfered_amount
    )

    try:
        proxy_trivial_token_v_raw.delegateAndCheck(
            proxy_trivial_token_v_raw.implementations(0),
            proxy_trivial_token_v.transfer.encode_input(accounts[2], transfered_amount),
            [
                (proxy_trivial_token_v, proxy_trivial_token_v.balanceOf(accounts[0])),
                (proxy_trivial_token_v, proxy_trivial_token_v.balanceOf(accounts[2])),
            ],
            True,
        )
    except VirtualMachineError as ex:
        print(ex.revert_msg)
