"""Offline crypto catalog used by fixture client and HTTP fallback."""

from __future__ import annotations

from decimal import Decimal

from app.ports.market import AssetSearchResult

# CoinGecko id, ticker, name, USD fixture price.
_CRYPTO: tuple[tuple[str, str, str, str], ...] = (
    ("bitcoin", "BTC", "Bitcoin", "65000"),
    ("ethereum", "ETH", "Ethereum", "3500"),
    ("solana", "SOL", "Solana", "150"),
    ("binancecoin", "BNB", "BNB", "580"),
    ("ripple", "XRP", "XRP", "0.55"),
    ("cardano", "ADA", "Cardano", "0.45"),
    ("dogecoin", "DOGE", "Dogecoin", "0.12"),
    ("tron", "TRX", "TRON", "0.12"),
    ("toncoin", "TON", "Toncoin", "5.40"),
    ("avalanche-2", "AVAX", "Avalanche", "28"),
    ("chainlink", "LINK", "Chainlink", "14"),
    ("polkadot", "DOT", "Polkadot", "6.20"),
    ("matic-network", "MATIC", "Polygon", "0.55"),
    ("litecoin", "LTC", "Litecoin", "72"),
    ("bitcoin-cash", "BCH", "Bitcoin Cash", "380"),
    ("near", "NEAR", "NEAR Protocol", "4.80"),
    ("uniswap", "UNI", "Uniswap", "8.50"),
    ("internet-computer", "ICP", "Internet Computer", "9.20"),
    ("aptos", "APT", "Aptos", "8.10"),
    ("stellar", "XLM", "Stellar", "0.11"),
    ("cosmos", "ATOM", "Cosmos", "7.40"),
    ("filecoin", "FIL", "Filecoin", "4.20"),
    ("sui", "SUI", "Sui", "1.85"),
    ("pepe", "PEPE", "Pepe", "0.000009"),
    ("shiba-inu", "SHIB", "Shiba Inu", "0.000018"),
    ("aave", "AAVE", "Aave", "95"),
    ("maker", "MKR", "Maker", "1450"),
    ("optimism", "OP", "Optimism", "1.75"),
    ("arbitrum", "ARB", "Arbitrum", "0.78"),
    ("the-graph", "GRT", "The Graph", "0.18"),
    ("vechain", "VET", "VeChain", "0.028"),
    ("algorand", "ALGO", "Algorand", "0.16"),
    ("hedera-hashgraph", "HBAR", "Hedera", "0.07"),
    ("monero", "XMR", "Monero", "165"),
    ("ethereum-classic", "ETC", "Ethereum Classic", "22"),
    ("render-token", "RENDER", "Render", "6.40"),
    ("injective-protocol", "INJ", "Injective", "22"),
    ("blockstack", "STX", "Stacks", "1.65"),
    ("worldcoin-wld", "WLD", "Worldcoin", "2.10"),
    ("okb", "OKB", "OKB", "48"),
)


def crypto_catalog() -> list[AssetSearchResult]:
    return [
        AssetSearchResult(
            symbol=ticker,
            name=name,
            asset_id=coin_id,
            asset_type="crypto",
            currency="USD",
        )
        for coin_id, ticker, name, _price in _CRYPTO
    ]


def crypto_prices() -> dict[str, tuple[Decimal, str]]:
    return {
        coin_id: (Decimal(price), "USD") for coin_id, _ticker, _name, price in _CRYPTO
    }
