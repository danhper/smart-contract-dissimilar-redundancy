import brownie
import pytest
from brownie.exceptions import VirtualMachineError
from eth_abi.abi import decode_single, encode_single

from conftest import INITIAL_SUPPLY

TRANSFERED_AMOUNT = 2 * 10 ** 18


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


def test_proxy(proxy_trivial_token_v):
    assert proxy_trivial_token_v.totalSupply() == INITIAL_SUPPLY


def make_args(accounts, raw_proxy, token_proxy, last_value=None):
    args = [
        raw_proxy.implementations(0),
        token_proxy.transfer.encode_input(accounts[2], TRANSFERED_AMOUNT),
        [
            (
                token_proxy,
                _encode_args(
                    token_proxy,
                    "balanceOf",
                    [(ArgumentType.Static, ("address", accounts[0].address))],
                ),
            ),
            (
                token_proxy,
                _encode_args(
                    token_proxy,
                    "balanceOf",
                    [(ArgumentType.Static, ("address", accounts[2].address))],
                ),
            ),
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


def test_register_checks(accounts, TrivialTokenV, proxy_trivial_token_v_raw):
    signature = TrivialTokenV.signatures["transfer"]
    assert len(proxy_trivial_token_v_raw.getChecks(signature)) == 0
    proxy_trivial_token_v_raw.registerCheck(
        signature,
        proxy_trivial_token_v_raw.address,
        _encode_args(TrivialTokenV, "totalSupply", []),
        {"from": accounts[0]},
    )
    assert len(proxy_trivial_token_v_raw.getChecks(signature)) == 1
    proxy_trivial_token_v_raw.registerCheck(
        signature,
        proxy_trivial_token_v_raw.address,
        _encode_args(
            TrivialTokenV,
            "balanceOf",
            [(ArgumentType.Static, ("address", accounts[0].address))],
        ),
        {"from": accounts[0]},
    )
    assert len(proxy_trivial_token_v_raw.getChecks(signature)) == 2


def test_same_implementation(
    accounts, proxy_trivial_token_s_raw, proxy_trivial_token_s, TrivialTokenS
):
    other_trivial_token_s = accounts[0].deploy(TrivialTokenS)
    proxy_trivial_token_s_raw.addImplementation(other_trivial_token_s, b"")
    proxy_trivial_token_s_raw.registerCheck(
        other_trivial_token_s.signatures["transfer"],
        proxy_trivial_token_s_raw,
        _encode_args(TrivialTokenS, "totalSupply", []),
    )
    proxy_trivial_token_s_raw.registerCheck(
        other_trivial_token_s.signatures["transfer"],
        proxy_trivial_token_s_raw,
        _encode_args(
            TrivialTokenS,
            "balanceOf",
            [(ArgumentType.Static, ("address", accounts[0].address))],
        ),
    )
    assert proxy_trivial_token_s.totalSupply() == INITIAL_SUPPLY
    proxy_trivial_token_s.transfer(accounts[1], 10_000_000)
    assert proxy_trivial_token_s.balanceOf(accounts[1]) == 10_000_000


def test_buggy_implementation(
    accounts, proxy_trivial_token_s_raw, proxy_trivial_token_s, TrivialTokenBuggy
):
    buggy_token = accounts[0].deploy(TrivialTokenBuggy)
    proxy_trivial_token_s_raw.addImplementation(buggy_token, b"")

    proxy_trivial_token_s_raw.registerCheck(
        buggy_token.signatures["transferFrom"],
        proxy_trivial_token_s_raw,
        _encode_args(
            TrivialTokenBuggy,
            "allowance",
            [
                # (ArgumentType.Static, ("address", accounts[0].address)),
                (ArgumentType.CallData, (4, 32)),
                (ArgumentType.Env, EnvArg.Sender),
                # (ArgumentType.Static, ("address", accounts[2].address)),
            ],
        ),
    )

    assert proxy_trivial_token_s.totalSupply() == INITIAL_SUPPLY
    proxy_trivial_token_s.approve(accounts[2], 10_000_000, {"from": accounts[0]})
    with brownie.reverts("all implementations must return the same checks"):  # type: ignore
        proxy_trivial_token_s.transferFrom(
            accounts[0], accounts[1], 10_000_000, {"from": accounts[2]}
        )
    assert proxy_trivial_token_s.balanceOf(accounts[1]) == 0


def _encode_args(contract, func_name, arguments):
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
