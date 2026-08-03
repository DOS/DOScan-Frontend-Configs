# DOS Chain token lists

This directory contains the public Uniswap Token Lists consumed by DOScan
backend deployments through `TOKEN_LIST_URL`.

Blockscout does not ship per-chain token-list files. Each deployment owns and
hosts its list at a stable HTTP(S) URL. Token icons belong in
`configs/token-icons/` and each `logoURI` must use the canonical raw GitHub URL.

## Adding a token

1. Copy `token-entry.template.json` and replace every placeholder.
2. Confirm the contract exists on the target network and has non-empty bytecode.
3. Read `name()`, `symbol()`, and `decimals()` from the contract. Do not infer
   these values from a website or deployment script. Replace the template's
   `decimals` value with the returned integer.
4. Add a permanent SVG or PNG under `configs/token-icons/`. Use the token symbol
   as the file name unless that would collide with another token.
5. Add the completed entry to the matching network list. Use the EIP-55
   checksummed contract address and the exact chain ID.
6. Update the list timestamp and semantic version:
   - increment `patch` when correcting metadata or an icon;
   - increment `minor` when adding or removing tokens;
   - increment `major` only for an incompatible list-policy change.
7. Open the PR with `.github/PULL_REQUEST_TEMPLATE/token-list.md` and attach the
   explorer URL plus the RPC or command output used for verification.

## Icon rules

- Use SVG when available; PNG is accepted when no vector source exists.
- Keep the asset self-contained and permanent.
- SVG files must parse as XML and must not contain scripts, event handlers, or
  references outside the same SVG.
- `logoURI` must use this canonical prefix:
  `https://raw.githubusercontent.com/DOS/DOScan-Frontend-Configs/main/configs/token-icons/`.
- Do not use a mutable third-party CDN, project website, IPFS gateway, or data
  URI as `logoURI`.

## Review checklist

- The address is not the zero address and is not duplicated in the list.
- The chain ID, name, symbol, and decimals match the deployed contract.
- The icon file exists, is non-empty, and passes the SVG safety checks.
- The list timestamp represents the change and its semantic version increased.
- The official Token Lists schema and all repository checks pass.
