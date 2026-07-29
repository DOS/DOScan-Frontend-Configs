# DOS Chain token lists

This directory contains the public Uniswap Token Lists consumed by DOScan
backend deployments through `TOKEN_LIST_URL`.

Blockscout does not ship per-chain token-list files. Each deployment owns and
hosts its list at a stable HTTP(S) URL. Token icons belong in
`configs/token-icons/` and each `logoURI` must use the canonical raw GitHub URL.

## Adding a token

1. Add a permanent SVG or PNG under `configs/token-icons/`.
2. Add the token to the matching network JSON file.
3. Use the checksummed contract address and exact chain ID.
4. Increment the list version and timestamp.
5. Confirm the contract and its on-chain metadata before merging.
