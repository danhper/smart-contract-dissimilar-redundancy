# @version ^0.3.0

event Transfer:
    _from: indexed(address)
    _to: indexed(address)
    _value: uint256

event Approval:
    _owner: indexed(address)
    _spender: indexed(address)
    _value: uint256

balances: HashMap[address, uint256]
approvals: HashMap[address, HashMap[address, uint256]]
totalSupply: public(uint256)
initialized: bool

@external
def initialize(supply: uint256):
    assert not self.initialized, "already initialized"
    self.balances[msg.sender] = supply
    self.totalSupply = supply
    self.initialized = True

@external
@view
def balanceOf(account: address) -> uint256:
    return self.balances[account]

@internal
def transfer_internal(from_: address, to: address, amount: uint256):
    assert self.balances[from_] >= amount, "balance too low"
    self.balances[from_] -= amount
    self.balances[to] += amount
    log Transfer(from_, to, amount)

@external
def transfer(to: address, amount: uint256) -> bool:
    self.transfer_internal(msg.sender, to, amount)
    return True

@external
def transferFrom(from_: address, to: address, amount: uint256) -> bool:
    assert self.approvals[from_][to] >= amount, "not enough approved"
    self.approvals[from_][to] -= amount
    self.transfer_internal(from_, to, amount)
    return True

@external
def allowance(account: address, spender: address) -> uint256:
    return self.approvals[account][spender]

@external
def approve(account: address, spender: address, amount: uint256) -> bool:
    self.approvals[account][spender] = amount
    log Approval(account, spender, amount)
    return True
