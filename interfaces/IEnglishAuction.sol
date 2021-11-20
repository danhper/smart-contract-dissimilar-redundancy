// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.9;

interface IEnglishAuction {
    function collection() external view returns (address);

    function tokenId() external view returns (uint256);

    function started() external view returns (bool);

    function endsAt() external view returns (uint256);

    function seller() external view returns (address);

    function highestBid() external view returns (uint256);

    function highestBidder() external view returns (address);

    function finalized() external view returns (bool);

    function start(
        address _collection,
        uint256 _tokenId,
        uint256 _endsAt
    ) external;

    function bid() external payable;

    function finalize() external;
}
