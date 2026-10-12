# stampede

A non-custodial trading terminal for Solana. Connect your own wallet, swap tokens through Jupiter, and follow live prices for sixteen major coins.

- **Non-custodial.** Your wallet signs every transaction. The page never holds funds or keys.
- **Live prices** from CoinGecko (BTC, ETH, SOL, LTC, XRP, BNB, DOGE, ADA, TRX, AVAX, LINK, TON, SUI, XLM, BCH, DOT) with a one-coin chart, a compare-all chart and a sortable table.
- **Real swaps** on Solana mainnet via the Jupiter swap API, with Wallet Standard wallets (Phantom, Solflare, Backpack, ...).
- A read-only terminal (`price`, `coins`, `balance`, `wallet`, `theme`, `goto`).

It is a single static file: `public/index.html`. No build step, no dependencies, no backend.

## Run it

Open `public/index.html` in a browser, or host it anywhere that serves static files. Wallet extensions and outside network requests (CoinGecko, Jupiter, a Solana RPC) need a normal browser tab. Some embedded viewers block them.

### Vercel

Import the repo. `vercel.json` already tells Vercel this is a plain static site (no framework, no build step) and to serve the `public` folder. If you set it up by hand instead, choose **Framework Preset: Other** and leave the build command, install command and output directory empty (or `public`).

### GitHub Pages

1. Push this repo to GitHub.
2. In **Settings > Pages**, set **Source** to **GitHub Actions**.
3. Every push to `main` deploys through `.github/workflows/pages.yml`.

## Configuration

Open the **network settings** panel in the trade section:

| Setting | Default | Notes |
| --- | --- | --- |
| Solana RPC | `https://api.mainnet-beta.solana.com` | The free public endpoint rate-limits browsers. Use your own provider (Helius, QuickNode, Triton, ...). |
| Jupiter swap API | `https://lite-api.jup.ag/swap/v1` | Jupiter has deprecated its V1 API in favour of V2 and its paid host needs an API key. Check their docs and update if needed. |

Both must be `https://` URLs. Settings are stored in the browser (`localStorage`).

To change the built-in defaults, search `public/index.html` for `LCFG=` (network defaults) and `LT=` (the token list).

## Before you launch

- **Verify every token mint** in the `LT` list against Solscan or Jupiter. They were written by hand.
- Use **your own RPC** endpoint.
- Confirm the **Jupiter API version** still matches the request and response shape used in `lvGetQuote` and `lvExecute`.
- Test with **tiny amounts** and a wallet holding little SOL.
- Take **legal advice** for your jurisdiction. Operating a trading front end can have licensing implications.
- There is **no platform fee**. Jupiter supports one (`platformFeeBps` and `feeAccount`) if you want to add it.

## What the page checks before a swap reaches your wallet

- The quote must match the requested pair and amount, and have a route, an output and a valid minimum.
- The transaction from the API must be a Jupiter swap that needs only the user's signature and pays fees from the user's account.
- 0.01 SOL is kept back for network fees.
- Price impact of 1% or more, slippage of 3% or more, trades over half a balance and custom tokens each require an explicit tick. Price impact of 30% or more is blocked.
- Listed tokens are checked against the network's reported decimals.

None of this replaces reading what your wallet shows before you approve.

## Tests

The tests drive a real browser with a simulated wallet, Jupiter and Solana RPC. They do not touch the network or any real funds.

```
pip install -r tests/requirements-test.txt
playwright install chromium
python tests/test_trading.py   # swap logic, safety checks, signing, confirmation
python tests/test_site.py      # page, markets, terminal, themes, accessibility, phone
```

## Notes

Trading crypto is risky and you can lose money. Nothing here is financial advice. No license has been chosen yet: add a `LICENSE` file before publishing if you want others to reuse the code.
