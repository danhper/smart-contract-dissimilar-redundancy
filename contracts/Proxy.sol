// SPDX-License-Identifier: MIT

// NOTE: taken from Openzeppelin Proxy contract

pragma solidity ^0.8.0;

contract Proxy {
    struct CheckCall {
        address targetContract;
        bytes data;
    }

    address[] public implementations;

    /// @notice maps a function signature to a set of checks
    mapping(bytes4 => CheckCall[]) public functionsChecks;

    error RevertDelegation(bool success, bytes revertData, bytes32 checksHash);

    function addImplementation(address implementation, bytes memory data) public {
        (bool success, ) = implementation.delegatecall(data);
        require(success, "initial data call failed");
        implementations.push(implementation);
    }

    function registerCheck(
        bytes4 functionSignature,
        address targetContract,
        bytes memory data
    ) external {
        functionsChecks[functionSignature].push(CheckCall(targetContract, data));
    }

    function delegateAndCheck(
        address _implementation,
        bytes calldata data,
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
            (bool checkSuccess, bytes memory checkData) = checkCall.targetContract.call(
                checkCall.data
            );
            checksHash = keccak256(abi.encodePacked(checksHash, checkSuccess, checkData));
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
        return _parseDelegatedCall(success, returnData);
    }

    function getChecks(bytes4 signature) external view returns (CheckCall[] memory) {
        return functionsChecks[signature];
    }

    /**
     * @dev Delegates the current call to all registered implementations
     * and persists state only on the last call
     * If any of the implementation is inconsistent, this reverts
     *
     * This function does not return to its internall call site, it will return directly to the external caller.
     */
    function _fallback() internal virtual {
        uint256 len = implementations.length;
        bool success;
        bytes memory returnData;
        bytes32 checksHash;

        // FIXME: might be a simpler way with abi.decode or so
        bytes4 sig;
        for (uint256 i = 0; i < 4; i++)
            sig |= bytes4(uint32(uint8(msg.data[i])) << uint8(24 - i * 8));
        require(sig > 0, "signature parse failed");

        CheckCall[] memory checks = functionsChecks[sig];

        for (uint256 i = 0; i < len; i++) {
            address implementation = implementations[i];
            bool shouldRevert = i != len - 1;
            (bool delegateSuccess, bytes memory delegateData) = address(this).delegatecall(
                abi.encodeWithSignature(
                    "delegateAndCheck(address,bytes,(address,bytes)[],bool)",
                    implementation,
                    msg.data,
                    checks,
                    shouldRevert
                )
            );
            require(delegateSuccess != shouldRevert, "inconsistent return from delegate");

            (bool callSuccess, bytes memory callData, bytes32 callChecksHash) = _parseDelegatedCall(
                delegateSuccess,
                delegateData
            );

            if (i == 0) {
                success = callSuccess;
                returnData = callData;
                checksHash = callChecksHash;
                continue;
            }

            require(success == callSuccess, "all implementations must return the same success");
            require(
                _bytesEq(returnData, callData),
                "all implementations must return the same return data"
            );
            require(
                checksHash == callChecksHash,
                "all implementations must return the same checks"
            );
        }

        uint256 returnDataSize = returnData.length;

        assembly {
            // Copy the return data to the Solidity scratch pad.
            if iszero(call(gas(), 0x04, 0, add(returnData, 0x20), returnDataSize, 0, 0)) {
                invalid()
            }
            returndatacopy(0, 0, returnDataSize)

            switch success
            case 0 {
                revert(0, returnDataSize)
            }
            default {
                return(0, returnDataSize)
            }
        }
    }

    function _bytesEq(bytes memory a, bytes memory b) internal pure returns (bool) {
        uint256 len = a.length;
        if (len != b.length) {
            return false;
        }
        for (uint256 i = 0; i < len; i++) {
            if (a[i] != b[i]) {
                return false;
            }
        }
        return true;
    }

    function _parseDelegatedCall(bool success, bytes memory returnData)
        internal
        pure
        returns (
            bool,
            bytes memory,
            bytes32
        )
    {
        if (!success) {
            assembly {
                returnData := add(returnData, 4) // drop signature
            }
        }

        (bool delegatedSuccess, bytes memory delegatedreturnData, bytes32 checksHash) = abi.decode(
            returnData,
            (bool, bytes, bytes32)
        );

        return (delegatedSuccess, delegatedreturnData, checksHash);
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
