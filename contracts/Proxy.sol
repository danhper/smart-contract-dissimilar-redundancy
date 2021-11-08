// SPDX-License-Identifier: MIT

// NOTE: taken from Openzeppelin Proxy contract

pragma solidity 0.8.9;

import "./vendor/BytesLib.sol";

contract Proxy {
    uint8 constant STATIC_ARG = 0;
    uint8 constant CALL_DATA_ARG = 1;
    uint8 constant ENV_ARG = 2;

    uint8 constant ENV_CHAINID = 0;
    uint8 constant ENV_COINBASE = 1;
    uint8 constant ENV_DIFFICULTY = 2;
    uint8 constant ENV_GASLIMIT = 3;
    uint8 constant ENV_NUMBER = 4;
    uint8 constant ENV_TIMESTAMP = 5;
    uint8 constant ENV_GASLEFT = 6;
    uint8 constant ENV_SENDER = 7;
    uint8 constant ENV_SIG = 8;
    uint8 constant ENV_VALUE = 9;
    uint8 constant ENV_GASPRICE = 10;
    uint8 constant ENV_ORIGIN = 11;

    /// @dev data should be encoded as follow
    ///
    /// |  0 - 4    |       5     |      6 --
    /// | signature |  args count |    args
    ///
    /// each arg should be encoded as follow
    ///
    /// |    0    |   1 -
    /// | argType |  argData
    ///
    /// and argData should be encoded as follow
    /// argType == 0 (Static) -> number of bytes and raw data for argument
    /// argType == 1 (CallData) -> offset and length of data in callData as uint16 (e.g. 0x000400a0 will be the first address in the call data)
    /// argType == 2 (Env) -> single byte corresponding to the following
    /// * 1  -> block.coinbase (address): current block miner’s address
    /// * 2  -> block.difficulty (uint): current block difficulty
    /// * 3  -> block.gaslimit (uint): current block gaslimit
    /// * 4  -> block.number (uint): current block number
    /// * 5  -> block.timestamp (uint): current block timestamp as seconds since unix epoch
    /// * 6  -> gasleft() returns (uint256): remaining gas
    /// * 7  -> msg.gas (uint): remaining gas - deprecated in version 0.4.21 and to be replaced by gasleft()
    /// * 8  -> msg.sender (address): sender of the message (current call)
    /// * 9  -> msg.sig (bytes4): first four bytes of the calldata (i.e. function identifier)
    /// * 10 -> msg.value (uint): number of wei sent with the message
    /// * 11 -> now (uint): current block timestamp (alias for block.timestamp)
    /// * 12 -> tx.gasprice (uint): gas price of the transaction
    /// * 13 -> tx.origin (address): sender of the transaction (full call chain)
    struct CheckCall {
        address targetContract;
        bytes data;
    }

    uint256[100] __gap;

    address[] public implementations;

    /// @notice maps a function signature to a set of checks
    mapping(bytes4 => CheckCall[]) public functionsChecks;

    error RevertDelegation(bool success, bytes revertData, bytes32 checksHash);

    function addImplementation(address implementation, bytes memory data) public {
        if (data.length > 0) {
            (bool success, ) = implementation.delegatecall(data);
            require(success, "initial data call failed");
        }
        implementations.push(implementation);
    }

    function allImplementations() external view returns (address[] memory) {
        return implementations;
    }

    function registerCheck(
        bytes4 functionSignature,
        address targetContract,
        // bytes4 targetSignature,
        bytes calldata data
    ) external {
        CheckCall[] storage calls = functionsChecks[functionSignature];
        CheckCall storage checkCall = calls.push();
        checkCall.targetContract = targetContract;
        // checkCall.signature = targetSignature;
        checkCall.data = data;
        // for (uint256 i = 0; i < args.length; i++) {
        //     checkCall.arguments.push(args[i]);
        // }
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
            bytes memory callData = _encodeCalldata(checkCall, data);
            (bool checkSuccess, bytes memory checkData) = checkCall.targetContract.call(callData);
            require(checkSuccess, "check failed");
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
        bool success;
        bytes memory returnData;
        bytes32 checksHash;

        // FIXME: might be a simpler way with abi.decode or so
        bytes4 sig;
        for (uint256 i = 0; i < 4; i++)
            sig |= bytes4(uint32(uint8(msg.data[i])) << uint8(24 - i * 8));
        require(sig > 0, "signature parse failed");

        CheckCall[] memory checks = functionsChecks[sig];

        uint256 len = implementations.length;
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

    function _encodeCalldata(CheckCall memory check, bytes calldata msgData)
        internal
        view
        returns (bytes memory result)
    {
        result = BytesLib.slice(check.data, 0, 4);
        uint8 argsCount = uint8(check.data[4]);
        uint256 currentOffset = 5;
        for (uint256 i = 0; i < argsCount; i++) {
            uint8 argType = uint8(check.data[currentOffset++]);

            bytes memory arg;
            if (argType == STATIC_ARG) {
                uint16 argLength = parseUint16(check.data, currentOffset);
                arg = BytesLib.slice(check.data, currentOffset + 2, argLength);
                currentOffset += argLength + 2;
            } else if (argType == CALL_DATA_ARG) {
                uint16 offset = parseUint16(check.data, currentOffset);
                uint16 length = parseUint16(check.data, currentOffset + 2);
                arg = msgData[offset:offset + length];
                currentOffset += 4;
            } else if (argType == ENV_ARG) {
                uint8 varType = uint8(check.data[currentOffset++]);
                if (varType == ENV_CHAINID) arg = abi.encode(block.chainid);
                else if (varType == ENV_COINBASE) arg = abi.encode(block.coinbase);
                else if (varType == ENV_DIFFICULTY) arg = abi.encode(block.difficulty);
                else if (varType == ENV_GASLIMIT) arg = abi.encode(block.gaslimit);
                else if (varType == ENV_NUMBER) arg = abi.encode(block.number);
                else if (varType == ENV_TIMESTAMP) arg = abi.encode(block.timestamp);
                else if (varType == ENV_GASLEFT) arg = abi.encode(gasleft());
                else if (varType == ENV_SENDER) arg = abi.encode(msg.sender);
                else if (varType == ENV_SIG) arg = abi.encode(msg.sig);
                else if (varType == ENV_VALUE) arg = abi.encode(msg.value);
                else if (varType == ENV_GASPRICE) arg = abi.encode(tx.gasprice);
                else if (varType == ENV_ORIGIN) arg = abi.encode(tx.origin);
                else revert("unknown environment variable");
            } else {
                revert("unknown argument type");
            }
            result = BytesLib.concat(result, arg);
        }
    }

    function parseUint16(bytes memory data, uint256 offset) internal pure returns (uint16) {
        return uint16(uint8(data[offset]) << 8) | uint16(uint8(data[offset + 1]));
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
