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


_CRYPTO_PROFILES: dict[str, dict] = {
    "bitcoin": {
        "description": "Bitcoin is a decentralized digital currency that can be transferred on the peer-to-peer bitcoin network.",
        "homepage": "https://bitcoin.org",
        "categories": ["Cryptocurrency", "Layer 1 (L1)"],
        "genesis_date": "2009-01-03",
        "hashing_algorithm": "SHA-256",
        "image_url": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
        "market_cap_rank": 1,
        "max_supply": "21000000",
    },
    "ethereum": {
        "description": "Ethereum is a decentralized, open-source blockchain with smart contract functionality.",
        "homepage": "https://ethereum.org",
        "categories": ["Smart Contract Platform", "Layer 1 (L1)"],
        "genesis_date": "2015-07-30",
        "hashing_algorithm": "Ethash",
        "image_url": "https://assets.coingecko.com/coins/images/279/large/ethereum.png",
        "market_cap_rank": 2,
    },
    "solana": {
        "description": "Solana is a high-throughput Layer 1 blockchain designed for fast, low-cost transactions.",
        "homepage": "https://solana.com",
        "categories": ["Smart Contract Platform", "Layer 1 (L1)"],
        "image_url": "https://assets.coingecko.com/coins/images/4128/large/solana.png",
        "market_cap_rank": 5,
    },
}


def crypto_profile_meta(asset_id: str) -> dict:
    """Fixture profile extras keyed by CoinGecko id."""
    return dict(_CRYPTO_PROFILES.get((asset_id or "").strip().lower()) or {})


_CRYPTO_CATEGORIES: dict[str, str] = {
    "bitcoin": "Layer 1",
    "ethereum": "Layer 1",
    "solana": "Layer 1",
    "cardano": "Layer 1",
    "avalanche-2": "Layer 1",
    "near": "Layer 1",
    "aptos": "Layer 1",
    "sui": "Layer 1",
    "toncoin": "Layer 1",
    "cosmos": "Layer 1",
    "algorand": "Layer 1",
    "hedera-hashgraph": "Layer 1",
    "internet-computer": "Layer 1",
    "blockstack": "Layer 1",
    "optimism": "Smart Contract / L2",
    "arbitrum": "Smart Contract / L2",
    "matic-network": "Smart Contract / L2",
    "polkadot": "Smart Contract / L2",
    "uniswap": "DeFi",
    "aave": "DeFi",
    "maker": "DeFi",
    "injective-protocol": "DeFi",
    "the-graph": "DeFi",
    "dogecoin": "Meme",
    "pepe": "Meme",
    "shiba-inu": "Meme",
    "ripple": "Payments / Other",
    "stellar": "Payments / Other",
    "litecoin": "Payments / Other",
    "bitcoin-cash": "Payments / Other",
    "monero": "Payments / Other",
    "vechain": "Payments / Other",
    "filecoin": "Payments / Other",
    "worldcoin-wld": "Payments / Other",
    "tron": "Payments / Other",
    "binancecoin": "Exchange",
    "okb": "Exchange",
    "render-token": "AI / Infra",
    "tether": "Stablecoin",
    "usd-coin": "Stablecoin",
    "dai": "Stablecoin",
}


def crypto_category(coin_id: str, symbol: str = "") -> str:
    """Heatmap/quote bucket for a CoinGecko id (or ticker). Unknown → Others."""
    key = (coin_id or "").strip().lower()
    if key in _CRYPTO_CATEGORIES:
        return _CRYPTO_CATEGORIES[key]
    ticker = (symbol or "").strip().upper()
    if ticker:
        for cid, t, _name, _price in _CRYPTO:
            if t.upper() == ticker:
                return _CRYPTO_CATEGORIES.get(cid, "Others")
    return "Others"


def fixture_crypto_heatmap_rows() -> list[tuple[str, str, str, str, float, float]]:
    """(coin_id, symbol, name, category, change_pct, market_cap) for fixture heatmap."""
    rows: list[tuple[str, str, str, str, float, float]] = []
    n = len(_CRYPTO)
    for rank, (coin_id, ticker, name, price) in enumerate(_CRYPTO, start=1):
        seed = sum(ord(c) * (i + 3) for i, c in enumerate(coin_id))
        change = ((seed % 1101) / 100.0) - 5.5
        px = float(Decimal(price))
        market_cap = (n - rank + 1) * 1_000_000_000.0 * max(px, 0.01)
        rows.append(
            (coin_id, ticker, name, crypto_category(coin_id), round(change, 2), market_cap)
        )
    return rows
