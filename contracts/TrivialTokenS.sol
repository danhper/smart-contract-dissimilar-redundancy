// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.9;

import "../interfaces/IERC20.sol";

contract TrivialTokenS is IERC20 {
    mapping(address => uint256) balances;
    mapping(address => mapping(address => uint256)) allowances;

    uint256 public override totalSupply;

    bool initialized;

    function initialize(uint256 supply) external {
        require(!initialized, "already initialized");
        totalSupply = supply;
        balances[msg.sender] = supply;
        initialized = true;
    }

    function balanceOf(address account)
        external
        view
        override
        returns (uint256)
    {
        return balances[account];
    }

    function transfer(address to, uint256 value)
        external
        override
        returns (bool)
    {
        transferInternal(msg.sender, to, value);
        return true;
    }

    function transferFrom(
        address from,
        address to,
        uint256 value
    ) external override returns (bool) {
        require(allowances[from][to] >= value, "not allowed to spend");
        allowances[from][to] -= value;
        transferInternal(from, to, value);
        return true;
    }

    function transferInternal(
        address from,
        address to,
        uint256 value
    ) internal {
        require(balances[from] >= value, "balance too low");
        balances[from] -= value;
        balances[to] += value;
        emit Transfer(from, to, value);
    }

    function approve(address spender, uint256 value)
        external
        override
        returns (bool)
    {
        allowances[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function allowance(address owner, address spender)
        external
        view
        override
        returns (uint256)
    {
        return allowances[owner][spender];
    }
}
