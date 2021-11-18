# @version ^0.3.0

from vyper.interfaces import ERC721


collection: public(address)
tokenId: public(uint256)
started: public(bool)
endsAt: public(uint256)
seller: public(address)
highestBid: public(uint256)
highestBidder: public(address)
finalized: public(bool)

@external
def __init__(_collection: address, _token_id: uint256, _ends_at: uint256):
    self.collection = _collection
    self.endsAt = _ends_at
    self.tokenId = _token_id
    self.seller = msg.sender

@external
def start():
    assert msg.sender == self.seller, "only seller can start auction"
    ERC721(self.collection).transferFrom(msg.sender, self, self.tokenId)
    self.started = True

@external
@payable
def bid(): 
    assert self.started, "auction not started"
    assert self.endsAt > block.timestamp, "auction has ended"
    assert msg.value > self.highestBid, "bid is too low"

    if self.highestBid > 0:
        # reimburse previous highest bidder
        send(self.highestBidder, self.highestBid)

    self.highestBid = msg.value
    self.highestBidder = msg.sender

@external
def finalize():
    assert block.timestamp > self.endsAt, "auction has not ended"
    assert not self.finalized, "auction has already been finalized"

    if self.highestBidder != ZERO_ADDRESS:
        # transfer ownership to highest bidder
        ERC721(self.collection).transferFrom(self, self.highestBidder, self.tokenId)

        # pay seller
        send(self.seller, self.highestBid)
    else:
        # transfer ownership back to seller
        ERC721(self.collection).transferFrom(self, self.seller, self.tokenId)

    self.finalized = True