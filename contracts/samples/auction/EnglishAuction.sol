// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.9;

import "OpenZeppelin/openzeppelin-contracts@4.3.3/contracts/token/ERC721/IERC721.sol";

contract EnglishAuctionS {
    address public collection;
    uint256 public tokenId;
    bool public started;
    uint256 public endsAt;
    address public seller;
    uint256 public highestBid;
    address public highestBidder;
    bool public finalized;

    constructor(
        address _collection,
        uint256 _tokenId,
        uint64 _endsAt
    ) {
        collection = _collection;
        tokenId = _tokenId;
        seller = msg.sender;
        endsAt = _endsAt;
    }

    function start() external {
        require(msg.sender == seller, "only seller can start auction");
        IERC721(collection).transferFrom(msg.sender, address(this), tokenId);
        started = true;
    }

    function bid() external payable {
        require(started, "auction not started");
        require(endsAt > block.timestamp, "auction has ended");
        require(msg.value > highestBid, "bid is too low");

        if (highestBid > 0) {
            // reimburse previous highest bidder
            payable(highestBidder).transfer(highestBid);
        }

        highestBid = msg.value;
        highestBidder = msg.sender;
    }

    function finalize() external {
        require(block.timestamp > endsAt, "auction has not ended");
        require(!finalized, "auction has already been finalized");

        if (highestBidder != address(0)) {
            // transfer ownership to highest bidder
            IERC721(collection).transferFrom(address(this), highestBidder, tokenId);

            // pay seller
            payable(seller).transfer(highestBid);
        } else {
            // transfer ownership back to seller
            IERC721(collection).transferFrom(address(this), seller, tokenId);
        }

        finalized = true;
    }
}
