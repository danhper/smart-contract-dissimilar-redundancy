// SPDX-License-Identifier: MIT

// NOTE: take from Openzeppelin Proxy contract

pragma solidity ^0.8.0;

/**
 * @dev This abstract contract provides a fallback function that delegates all calls to another contract using the EVM
 * instruction `delegatecall`. We refer to the second contract as the _implementation_ behind the proxy, and it has to
 * be specified by overriding the virtual {_implementation} function.
 *
 * Additionally, delegation to the implementation can be triggered manually through the {_fallback} function, or to a
 * different contract through the {_delegate} function.
 *
 * The success and return data of the delegated call will be returned back to the caller of the proxy.
 */
contract Proxy {
    struct CheckCall {
        address targetContract;
        bytes data;
    }

    address[] public implementations;

    error RevertDelegation(bool success, bytes revertData, bytes32 checksHash);

    function addImplementation(address implementation, bytes memory data)
        public
    {
        (bool success, ) = implementation.delegatecall(data);
        require(success, "initial data call failed");
        implementations.push(implementation);
    }

    function delegateAndCheck(
        address _implementation,
        bytes memory data,
        CheckCall[] memory checks,
        bool revertExecution
    )
        public
        returns (
            bool success,
            bytes memory returnData,
            bytes32 checksHash
        )
    {
        (success, returnData) = _implementation.delegatecall(data);
        checksHash = keccak256(abi.encodePacked(success, returnData));
        for (uint256 i = 0; i < checks.length; i++) {
            CheckCall memory checkCall = checks[i];
            (bool checkSuccess, bytes memory checkData) = checkCall
                .targetContract
                .call(checkCall.data);
            checksHash = keccak256(
                abi.encodePacked(checksHash, checkSuccess, checkData)
            );
        }
        if (revertExecution) {
            revert RevertDelegation(success, returnData, checksHash);
        } else {
            return (success, returnData, checksHash);
        }
    }

    function getErrorMessage(
        address _implementation,
        bytes memory data,
        CheckCall[] memory checks
    )
        external
        returns (
            bool,
            bytes memory,
            bytes32
        )
    {
        (bool success, bytes memory returnData) = address(this).delegatecall(
            abi.encodeWithSignature(
                "delegateAndCheck(address,bytes,(address,bytes)[],bool)",
                _implementation,
                data,
                checks,
                true
            )
        );
        require(!success, "should have failed");

        assembly {
            returnData := add(returnData, 4) // drop signature
        }

        (
            bool delegatedSuccess,
            bytes memory delegatedreturnData,
            bytes32 checksHash
        ) = abi.decode(returnData, (bool, bytes, bytes32));

        return (delegatedSuccess, delegatedreturnData, checksHash);
    }

    /**
     * @dev Delegates the current call to `implementation`.
     *
     * This function does not return to its internall call site, it will return directly to the external caller.
     */
    function _delegate(address _implementation) internal virtual {
        assembly {
            // Copy msg.data. We take full control of memory in this inline assembly
            // block because it will not return to Solidity code. We overwrite the
            // Solidity scratch pad at memory position 0.
            calldatacopy(0, 0, calldatasize())

            // Call the implementation.
            // out and outsize are 0 because we don't know the size yet.
            let result := delegatecall(
                gas(),
                _implementation,
                0,
                calldatasize(),
                0,
                0
            )

            // Copy the returned data.
            returndatacopy(0, 0, returndatasize())

            switch result
            // delegatecall returns 0 on error.
            case 0 {
                revert(0, returndatasize())
            }
            default {
                return(0, returndatasize())
            }
        }
    }

    /**
     * @dev Delegates the current call to the address returned by `_implementation()`.
     *
     * This function does not return to its internall call site, it will return directly to the external caller.
     */
    function _fallback() internal virtual {
        _delegate(implementations[0]);
    }

    /**
     * @dev Fallback function that delegates calls to `implementation`. Will run if no other
     * function in the contract matches the call data.
     */
    fallback() external payable virtual {
        _fallback();
    }

    /**
     * @dev Fallback function that delegates calls to the `implementation`. Will run if call data
     * is empty.
     */
    receive() external payable virtual {
        _fallback();
    }
}
