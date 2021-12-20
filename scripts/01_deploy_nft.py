from scripts.utils import get_deployer
from tests.conftest import NftCollection


def main():
    deployer = get_deployer()
    nft_collection = deployer.deploy(
        NftCollection, "Sample NFT", "SNF", "http://example.com/nft/"
    )
    nft_collection.mint(deployer, {"from": deployer})
    nft_collection.mint(deployer, {"from": deployer})
