// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.9;

import "OpenZeppelin/openzeppelin-contracts@4.3.3/contracts/token/ERC721/IERC721.sol";

import "../../../interfaces/IEnglishAuction.sol";

contract EnglishAuctionS is IEnglishAuction {
    address public override collection;
    uint256 public override tokenId;
    bool public override started;
    uint256 public override endsAt;
    address public override seller;
    uint256 public override highestBid;
    address public override highestBidder;
    bool public override finalized;

    function start(
        address _collection,
        uint256 _tokenId,
        uint256 _endsAt
    ) external override {
        require(!started, "auction already started");

        IERC721(_collection).transferFrom(msg.sender, address(this), _tokenId);

        seller = msg.sender;
        collection = _collection;
        started = true;
        endsAt = _endsAt;
    }

    function bid() external payable override {
        require(started, "auction not started");
        require(endsAt > block.timestamp, "auction has ended");
        require(msg.value > 0, "bid must more than 0");
        require(msg.value > highestBid, "bid is too low");

        if (highestBid > 0) {
            // reimburse previous highest bidder
            payable(highestBidder).transfer(highestBid);
        }

        highestBid = msg.value;
        highestBidder = msg.sender;
    }

    function finalize() external override {
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
