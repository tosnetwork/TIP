---
tip: 2
title: Protocol-Native Stable Assets and Circle USDC Interoperability
author: TOS Core Contributors (@tosnetwork)
status: Draft
type: Standards Track
category: Core
created: 2026-09-15
---

# TIP-2: Protocol-Native Stable Assets and Circle USDC Interoperability

## Abstract

This TIP proposes a protocol-native stable-asset framework for TOS Network and a
three-phase path to interoperable USDC settlement without introducing a separate
stablecoin workchain or representing canonical stable assets as Jetton-style
per-owner wallet contracts.

**Phase 1** standardizes registered protocol-native assets directly in the
existing `CurrencyCollection.extra` / `ExtraCurrencyCollection` balance model.
It introduces a consensus-governed native-asset registry, restricted mint and
burn authority, supply accounting, wallet and Agent Account support, and an
optional fee-eligibility flag. Phase 1 is asset-generic; USDC is the first target
but the framework may later register other externally backed or protocol-native
assets.

**Phase 2** integrates Circle xReserve, subject to Circle onboarding TOS as an
xReserve remote blockchain. A USDC-backed stable asset, provisionally referred
to as `USDCx`, is minted as a TOS protocol-native extra currency only after a
valid Circle deposit attestation, and is burned before a withdrawal can release
USDC from xReserve. The design intentionally avoids a third-party lock-and-mint
bridge and avoids a Jetton representation on TOS.

**Phase 3** migrates to Circle-issued native USDC and CCTP if and when Circle
onboards TOS as an official CCTP domain. CCTP burn-and-mint then becomes the
canonical path between Arc and TOS, as well as other supported CCTP domains.
Migration from xReserve-backed `USDCx` to official USDC MUST preserve supply,
prevent dual issuance, and use an explicit activation and redemption plan.

This TIP defines architecture and safety requirements. It does not claim that
Circle has approved TOS for xReserve or CCTP, does not assign a Circle domain
identifier, and does not permit TOS to label an independently issued asset as
Circle-native USDC.

## Motivation

TOS is designed for autonomous Agents that discover services, enter agreements,
execute work, and settle value. A volatile network token is useful for network
security and validator economics, but commercial Agents frequently need a
stable unit of account for quotes, budgets, escrow, accounting, and machine-to-
machine settlement.

The TOS base protocol already contains most of the data model needed for a
native multi-asset system. At the baseline reviewed for this TIP,
`tosnetwork/tos` commit
`2004ce5e618c4a9d8ed5fe5ae51912d65bb524cd`, an account balance is a
`CurrencyCollection` with a native `tomis` component and an
`ExtraCurrencyCollection`. Internal messages carry a `CurrencyCollection`, the
TVM `BALANCE` primitive exposes both the native balance and extra-currency
dictionary, `RAWRESERVEX` reserves extra currencies, and transaction
`total_fees` is itself a `CurrencyCollection`. ConfigParam 7 also demonstrates
that the protocol already has consensus-level extra-currency minting concepts.

However, ordinary wallets, Agent Account flows, SDK message builders, stablecoin
escrows, and transaction fee charging remain TOS-centric. In particular, the
current compute phase buys and deducts gas from `balance.tomis`, and the compute
phase records `gas_fees:Tomis`. Existing stablecoin settlement therefore uses a
Jetton-style contract model and still needs native TOS to execute token-wallet
hops.

Creating a separate USDC workchain would duplicate execution and settlement
infrastructure while leaving Agents and applications to route between two
chains. A protocol-native stable asset is simpler: the same Wallet V5, Agent
Account, escrow, message routing, and TVM can carry both TOS and stable assets.
The intended long-term separation is:

```text
TOS   = validator staking, network security, protocol coordination, native fee asset
USDC  = commerce, pricing, escrow, settlement, and optionally a fee-eligible asset
```

The stable-asset framework also avoids binding consensus to one issuer. USDC is
the first interoperability target because Circle provides xReserve for partner
blockchains and CCTP for native USDC burn-and-mint. The framework itself MUST
remain generic enough to register future stable or externally backed assets
without redesigning account storage or message formats.

## Normative language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in RFC 2119
and RFC 8174.

Publication or merger of this Draft does not activate any new asset, mint any
value, authorize a Circle integration, or change transaction fee rules. Every
consensus-affecting phase requires a separate implementation, conformance
results, and deterministic activation under the TOS upgrade process.

## Goals

This TIP has the following goals:

1. Represent registered stable assets directly in account
   `ExtraCurrencyCollection` balances.
2. Permit native transfer, reserve, escrow, and Agent policy enforcement without
   deploying one token-wallet contract per account.
3. Define a restricted, consensus-visible mint/burn authority model suitable
   for externally backed assets.
4. Support Circle xReserve as the preferred bootstrap path for a USDC-backed TOS
   stable asset if Circle approves TOS as a remote chain.
5. Support migration to official Circle-native USDC and CCTP if Circle later
   approves TOS as a CCTP domain.
6. Preserve TOS as the staking and validator-security asset.
7. Provide a path for stable-asset fee payment without requiring a separate
   stablecoin workchain.
8. Keep Wallet V5 and Agent Account authorization semantics independent from
   the choice of fee or settlement asset.

## Non-goals

This TIP does not:

- create a new workchain solely for USDC;
- add EVM execution;
- define a third-party multisig lock-and-mint bridge as the canonical USDC path;
- make a Jetton the canonical representation of a registered native asset;
- assign an xReserve or CCTP domain identifier without Circle;
- claim that `USDCx` is Circle-issued native USDC;
- change validator staking from TOS to USDC;
- define an on-chain TOS/USD oracle as a requirement for Phase 1 or Phase 2;
- make every extra currency fee-eligible;
- permit arbitrary contracts or governance keys to mint registered stable assets;
- require protocol-native USDC fee payment before stable-asset transfer and
  settlement are production ready.

## Specification

### 1. Existing TOS balance model

The existing balance model is retained:

```text
CurrencyCollection
    tomis: Tomis
    other: ExtraCurrencyCollection

ExtraCurrencyCollection
    asset_id:uint32 -> amount:VarUInteger32
```

A **protocol-native asset** under this TIP is an `asset_id` whose semantics are
registered by consensus and whose balances are held directly in the `other`
map. It is not a smart-contract token whose authoritative balances live in
separate token-wallet contracts.

An account may therefore hold, conceptually:

```text
Account balance
    TOS                  83.451000000
    Extra[USDC asset]  1532.470000
    Extra[EURC asset]   850.000000
```

Asset decimal precision is metadata governing canonical human-readable and
cross-chain conversion. The stored amount remains an unsigned integer. An asset
profile MUST define the exact decimal precision and MUST reject lossy or
ambiguous conversion at interoperability boundaries.

### 2. Native Asset Registry

Phase 1 MUST introduce a masterchain-governed Native Asset Registry. The exact
configuration parameter number is intentionally not allocated by this Draft;
the implementation profile MUST assign an unused positive ConfigParam index,
add its TL-B schema to `block.tlb`, and freeze the index before activation.

The logical registry entry is:

```text
NativeAssetDescriptor
    version:uint16
    asset_id:uint32
    decimals:uint8
    asset_class:uint8
    flags:uint32
    controller:MsgAddressInt
    controller_code_hash:bits256
    issuer_profile_hash:bits256
    migration_epoch:uint32
```

The first version MUST define at least these asset classes:

```text
0 = protocol-defined
1 = externally-backed
2 = reserved
```

The first version MUST define at least these flags:

```text
TRANSFERABLE
MINTABLE
BURNABLE
FEE_ELIGIBLE
MINT_PAUSED
BURN_PAUSED
MIGRATION_ONLY
```

Unknown descriptor versions, unknown consensus-critical flags, duplicate
`asset_id` entries, invalid controller addresses, or zero controller code hashes
MUST make the registry invalid.

`controller` is the only account authorized to request consensus-native mint or
burn operations for the asset. `controller_code_hash` pins the authorized code
identity. A mutable owner key alone MUST NOT be sufficient to replace the
controller implementation or bypass registry policy.

`issuer_profile_hash` commits to an asset-specific external issuance profile.
For xReserve this profile commits to the accepted Circle source/remote domains,
attesters, token identifier, message version, decimal precision, and replay
rules. For official CCTP USDC it commits to the CCTP integration profile. The
profile itself may be stored in a separate immutable cell or published release
artifact; all validators MUST agree on its hash.

### 3. Asset identifiers

`asset_id` is a TOS consensus identifier and MUST NOT be assumed to equal an
EVM chain ID, Circle domain ID, ERC-20 address, or application token ID.

The implementation profile MUST allocate identifiers deterministically and MUST
reserve separate identifiers for assets with different redemption or trust
models. In particular, xReserve-backed `USDCx` and Circle-native CCTP USDC MUST
NOT silently reuse one identifier while both supplies can exist.

If migration chooses to preserve one user-facing symbol, clients MUST still be
able to distinguish the pre-migration and post-migration asset identifiers until
all old supply is provably retired.

### 4. Native mint and burn actions

Phase 1 MUST add a consensus-defined mechanism by which the registered
controller can mint or burn a registered native asset. This TIP specifies the
semantics, not the final TVM opcode encoding.

A conforming implementation MUST provide operations equivalent to:

```text
MINT_NATIVE_ASSET(asset_id, recipient, amount, evidence_hash, replay_id)
BURN_NATIVE_ASSET(asset_id, holder, amount, destination, evidence_hash, replay_id)
```

The implementation MAY expose these as new output actions, a privileged
precompiled controller interface, or another deterministic protocol primitive,
provided all clients enforce identical semantics.

For `MINT_NATIVE_ASSET`:

1. the asset MUST exist and have `MINTABLE` set;
2. `MINT_PAUSED` MUST be clear;
3. the requesting account MUST equal `controller` and its active code hash MUST
   equal `controller_code_hash`;
4. `amount` MUST be non-zero and fit the registered asset bounds;
5. `replay_id` MUST not have been consumed for that asset/controller profile;
6. asset-specific evidence MUST validate before supply changes;
7. the recipient balance MUST increase by exactly `amount`;
8. total circulating supply MUST increase by exactly `amount`; and
9. the consumed replay identity MUST become durable in the same committed state
   transition as the mint.

For `BURN_NATIVE_ASSET`:

1. the asset MUST exist and have `BURNABLE` set;
2. `BURN_PAUSED` MUST be clear;
3. the holder MUST have at least `amount` available after required reservations;
4. `amount` MUST be non-zero;
5. the balance and total circulating supply MUST decrease by exactly `amount`;
6. the burn event/receipt MUST commit to the destination domain, recipient,
   amount, asset profile, network identity, and replay identity; and
7. no external withdrawal or attestation may be treated as valid unless the burn
   is finalized under the required finality policy.

A failed evidence check MUST NOT partially mint or burn.

### 5. Supply accounting

Every registered mintable asset MUST have consensus-verifiable circulating
supply accounting. Implementations MUST be able to prove:

```text
sum(account balances for asset_id) = circulating_supply(asset_id)
```

subject only to explicitly specified system balances or in-flight accounting
that are themselves represented in consensus state.

For an externally backed stable asset, the bridge/controller accounting MUST
also enforce the external invariant appropriate to that profile. For xReserve:

```text
TOS USDCx circulating supply <= USDC reserve attributable to TOS in xReserve
```

A relayer, RPC server, or off-chain indexer MUST NOT be the source of truth for
TOS supply.

ConfigParam 7 MUST NOT be used as the ordinary per-transfer bridge mint API.
It is configuration-level extra-currency issuance and does not provide the
per-deposit evidence, replay, recipient, and controller semantics required by
this TIP.

### 6. Native transfers

Internal messages already carry a `CurrencyCollection`. Wallets, Agent Accounts,
contracts, SDKs, JSON-RPC, explorers, and indexing code MUST be extended to
preserve and display registered extra currencies rather than assuming the
`other` dictionary is empty.

A native stable-asset transfer is an ordinary internal message whose value has:

```text
tomis = optional TOS amount
other[asset_id] = stable asset amount
```

No token-master or per-owner token-wallet hop is required.

Message validation MUST reject malformed extra-currency dictionaries, duplicate
keys, non-canonical integer encodings, zero-valued entries where forbidden by
the canonical codec, and arithmetic overflow.

### 7. Wallet V5

Wallet V5 MUST remain an authorization and action container, not a stablecoin
ledger contract.

Its action list may send an internal message containing any registered native
asset allowed by the base protocol. Wallet V5 contract authorization semantics,
`global_id`, wallet ID, sequence number, expiration, signature mode, extension
rules, and optional authentication root are unchanged by the asset choice.

SDK message builders MUST stop hard-coding an empty extra-currency dictionary.
A conforming high-level API SHOULD expose a structure equivalent to:

```text
OutMessage
    to
    tos_value
    extra_currencies: map<uint32, uint256>
    body
    state_init
    send_mode
```

Applications SHOULD use registry metadata to render decimals and symbols but
MUST sign and hash canonical integer amounts and `asset_id` values, not localized
strings.

### 8. Agent Account

Agent Account MUST gain asset-aware economic actions without reinterpreting
existing TOS-only opcodes.

The existing `native_send`, `task_send`, deploy, and checked-call wire formats
that encode a single `value:coins` remain TOS-denominated for backwards
compatibility. A new versioned asset-transfer action MUST carry at least:

```text
network_global_id
controller_epoch
seqno
valid_until
target
asset_id
amount
optional_tos_value
body_or_action_payload
```

The signed request MUST bind every field above.

Agent policy MUST be extended so a controller cannot convert a TOS spending
limit into permission to spend USDC. A conforming policy model MUST support
per-asset limits, including at minimum:

```text
asset_id
max_per_tx
daily_limit
spent_today
spend_day
```

A policy MAY also restrict destination, service profile, agreement identity,
contract action, or fee asset. Policy accounting MUST use atomic integer units
of the registered asset.

Authorization source and fee source are independent. A controller or
post-quantum authentication module may authorize a USDC payment while a separate
mechanism pays TOS fees, or a later fee-eligible USDC profile may pay fees
directly.

### 9. Stablecoin escrow

A native-asset escrow SHOULD hold the settlement amount directly in its account
`CurrencyCollection` rather than derive and control a Jetton wallet.

For registered native USDC-like assets, an escrow release or refund becomes one
native `CurrencyCollection` transfer. Implementations SHOULD therefore remove
Jetton-specific assumptions such as per-owner wallet derivation,
`transfer_notification`, `excesses`, and a second token-wallet execution hop
from the native-asset escrow profile.

Existing Jetton escrow contracts remain valid for Jetton assets and are not
silently reinterpreted.

### 10. Fee eligibility

Phase 1 introduces registry semantics for `FEE_ELIGIBLE`, but enabling an asset
for fees is a separate protocol activation.

Current TOS compute charging is TOS-specific: gas is bought from
`balance.tomis`, compute fees are represented as `Tomis`, and accepted compute
fees are deducted from the TOS balance. Therefore registering USDC as a native
extra currency does not by itself make USDC a gas currency.

Before any native asset other than TOS can pay protocol fees, a separate
implementation profile MUST specify all fee components that may be paid in that
asset, including:

- compute gas;
- storage fees;
- import fees;
- forward fees;
- action-phase fees;
- block/value-flow fee accounting; and
- validator/fee-collector settlement.

The profile MUST define deterministic fee prices. It MUST NOT require an
unbounded or manipulable spot-price oracle during transaction validation.
Possible profiles include fixed stable-denominated fee schedules, periodically
activated governance prices, or a separately specified deterministic conversion
mechanism.

When an extra currency is charged as a fee, transaction `total_fees` SHOULD use
the existing `CurrencyCollection` capability to record the charged asset.
Compute-phase serialization that currently fixes `gas_fees:Tomis` requires a
versioned consensus change before non-TOS compute fees can be represented
natively.

Until that upgrade activates, gas sponsorship MAY provide a USDC-only user
experience while validators continue to collect TOS. Such sponsorship is a UX
layer and MUST NOT be described as protocol-native USDC gas.

## Phase 1 — Protocol-Native Stable Asset Framework

### 11. Phase 1 scope

Phase 1 is complete only when the following capabilities are implemented and
validated on a TOS test network:

1. Native Asset Registry with deterministic activation.
2. Restricted mint and burn primitive.
3. Consensus supply accounting and replay protection.
4. Native extra-currency transfer support in Wallet V5 SDKs and node APIs.
5. Asset-aware Agent Account action and policy support.
6. Native stable-asset escrow profile.
7. Explorer/RPC/indexer representation of balances, transfers, fees, and supply.
8. Test fixtures for multiple registered native assets.
9. Emergency pause that can stop external mint/burn without freezing ordinary
   user-to-user transfers unless the asset profile explicitly requires it.
10. Upgrade and rollback rules that cannot restore already-consumed mint replay
    identities or recreate burned supply.

Phase 1 SHOULD first run with test-only assets whose issuer profiles make no
claim on real-world reserves.

### 12. Phase 1 activation

Phase 1 activation MUST use an explicit TOS global-version/capability boundary
or equivalent deterministic consensus activation. Validator software support
MUST precede configuration activation.

The activation package MUST publish:

- exact TL-B schemas;
- allocated ConfigParam index for the registry;
- asset/action constructor identifiers;
- code hashes for privileged controllers;
- supply and replay state formats;
- Wallet V5 and Agent Account test vectors;
- C++ and Rust codec parity evidence where both implementations consume the
  changed structures;
- multi-node replay and block-validation tests; and
- a migration statement for pre-activation accounts and messages.

## Phase 2 — Circle xReserve-backed USDCx

### 13. External dependency

Phase 2 MUST NOT activate unless Circle accepts TOS as an xReserve partner/remote
blockchain and assigns the required Circle-issued domain and integration
parameters.

Circle xReserve is designed for partner blockchains that issue USDC-backed
stablecoins. USDC is deposited into a Circle-deployed xReserve contract on a
source chain, Circle's xReserve attester signs a deposit attestation, and the
remote blockchain mints an equivalent USDC-backed stablecoin. Withdrawal burns
the remote stablecoin, the remote-chain attester signs the burn intent, xReserve
independently validates the burn, and reserve USDC is released or forwarded to
a supported destination.

TOS MUST treat Circle documentation and the jointly approved integration
profile as the authority for current xReserve message formats, domains,
attesters, and operational requirements.

### 14. USDCx representation on TOS

The Phase 2 asset is a TOS protocol-native extra currency, not a Jetton.
Provisionally:

```text
asset class       = externally-backed
symbol            = USDCx (UI metadata)
decimals          = 6
backing            = 1:1 USDC held through Circle xReserve
mint authority     = registered TOS xReserve controller
burn authority     = registered TOS xReserve controller
fee eligibility    = disabled initially unless separately activated
```

The final symbol and marketing name MUST follow Circle's partner requirements.
TOS MUST NOT present USDCx as Circle-native USDC.

### 15. Deposit: source chain to TOS

The normative logical flow is:

```text
User
  -> deposit USDC into Circle xReserve on an approved source chain
  -> xReserve DepositIntent
  -> Circle xReserve attestation
  -> submit intent + attestation to TOS controller
  -> verify profile, attester, amount, remote domain/token/recipient and replay
  -> MINT_NATIVE_ASSET(USDCx, recipient, amount, ...)
```

The TOS controller MUST verify at least:

1. deposit message version and magic/domain separation;
2. source and TOS remote domain identifiers from the approved Circle profile;
3. remote token identifier assigned to the TOS native USDCx asset;
4. exact six-decimal amount semantics;
5. approved Circle xReserve attester signature;
6. recipient commitment;
7. fee amount if the xReserve profile permits relayer fees;
8. unique deposit/replay identity; and
9. any finality condition required by Circle for the source deposit.

The mint MUST be impossible before all checks succeed.

### 16. Withdrawal: TOS to USDC

The logical flow is:

```text
User/Agent
  -> burn native USDCx on TOS
  -> finalized TOS BurnIntent / BurnReceipt
  -> TOS remote attester signs the Circle-defined burn intent
  -> xReserve independently validates the burn
  -> Circle/xReserve withdrawal attestation
  -> release/forward USDC to the requested destination
```

TOS MUST finalize the burn before the remote attester signs it. The attester
MUST NOT sign a locally observed mempool request, unfinalized transaction, or
RPC response that is not bound to finalized chain state.

The remote attester key is an interoperability security boundary. It MUST be
separate from ordinary wallet/controller keys, stored in an operationally
hardened signer, support audited rotation, and use monotonic replay/finality
state. Loss or compromise of this key MUST have a documented pause and recovery
procedure.

### 17. Dual-attestation model

xReserve uses independent Circle and remote-blockchain attesters. TOS MUST keep
those roles separate:

- Circle's xReserve attester authorizes recognition of a reserve deposit for a
  remote-chain mint.
- The TOS remote attester attests that a finalized native USDCx burn occurred
  before reserve release.

A TOS validator quorum is not automatically the xReserve remote attester unless
Circle and TOS explicitly adopt and audit such a design. Conversely, the remote
attester MUST NOT gain general validator, governance, or arbitrary mint powers.

### 18. xReserve source and destination chains

At the time this TIP was drafted, Circle documentation listed Ethereum as a
mainnet xReserve source and Arc Testnet and Ethereum Sepolia as testnet sources.
Circle documentation also allows withdrawals to supported Gateway or CCTP
chains and to other xReserve remote chains.

Therefore Phase 2 MUST NOT hard-code an assumption that Arc mainnet is an
xReserve source until Circle publishes and assigns that production route for the
TOS integration. If Arc is available only as a destination through CCTP at a
given time, xReserve may release/forward USDC to Arc through Circle-supported
infrastructure without TOS inventing an independent Arc bridge.

### 19. TOS recipient encoding

Circle interoperability messages use fixed-width destination identifiers while
a TOS address includes a workchain and a 256-bit account identifier. The final
integration profile MUST define a collision-resistant, versioned recipient
encoding.

The RECOMMENDED logical structure is:

```text
TosRecipientV1
    workchain:int32
    account_id:bits256
```

If an external message field permits only 32 bytes, the profile SHOULD place a
commitment in that field and carry the full TOS recipient in authenticated hook
or auxiliary data:

```text
recipient_commitment =
    SHA256("TOS-STABLE-RECIPIENT-V1" || workchain || account_id)
```

TOS MUST recompute the commitment before minting. The domain string and integer
endianness MUST be frozen in test vectors before production use.

### 20. Phase 2 security gate

Before production USDCx activation, the implementation MUST demonstrate:

- valid Circle deposit attestation -> exactly one mint;
- replayed deposit -> no second mint;
- modified amount/recipient/domain/token -> rejection;
- stale or removed Circle attester -> rejection after the defined transition;
- burn -> exact supply decrement before any remote attestation;
- failed/duplicate withdrawal handling without restoring spendable supply twice;
- crash/restart of the TOS attester without double-signing conflicting burn
  identities;
- pause behavior;
- source and destination finality handling;
- total TOS USDCx supply reconciled against the attributable xReserve reserve;
- key rotation with overlap that cannot authorize both conflicting histories;
- malformed and oversized message rejection; and
- testnet end-to-end deposit and withdrawal through Circle's supported test
  environment.

## Phase 3 — Circle-native USDC and CCTP

### 21. External dependency

Phase 3 begins only if Circle officially supports TOS as a CCTP blockchain/domain
and native USDC is issued for TOS under Circle's production requirements.

TOS MUST NOT self-assign a CCTP domain. Circle domain identifiers are issued by
Circle and are distinct from public chain IDs and from TOS native `asset_id`
values.

### 22. Canonical CCTP flow

With official support, canonical Arc <-> TOS USDC transfer SHOULD use CCTP's
burn-and-mint model:

```text
Arc native USDC
    -> burn through Arc CCTP
    -> Circle attestation
    -> TOS CCTP receiver/controller
    -> mint TOS native USDC
```

and:

```text
TOS native USDC
    -> burn on TOS
    -> CCTP message / TOS domain event
    -> Circle attestation
    -> Arc MessageTransmitter / token messenger flow
    -> mint Arc native USDC
```

At draft time, Arc Testnet is CCTP domain `26`. This value MUST NOT be generalized
to Arc mainnet or copied as a future TOS domain. Implementations MUST use
Circle's then-current production domain registry.

### 23. TOS CCTP controller

The TOS CCTP controller MUST be a registered native-asset controller with:

- code hash pinned in the Native Asset Registry;
- approved Circle MessageTransmitter/TokenMessenger profile identifiers;
- approved Circle attester set and rotation procedure;
- strict replay protection;
- explicit source/destination domain checks;
- exact six-decimal USDC amounts;
- recipient binding;
- pause controls; and
- no owner path that can mint without a valid Circle authorization.

If Circle's production TOS integration requires a module, precompile, or other
non-contract execution model, that implementation MAY replace the controller
shape above only if it preserves the same consensus invariants.

### 24. Migration from USDCx to native USDC

Phase 3 MUST publish a migration profile before native USDC activation.

Two supplies MUST NOT be simultaneously presented as one canonical asset without
an explicit conversion rule. The migration MUST choose one of these models or a
separately reviewed equivalent:

**Redeem-and-mint migration**

1. stop new xReserve USDCx deposits into TOS;
2. keep USDCx transfers/redemptions enabled;
3. users burn USDCx and redeem reserve USDC through xReserve;
4. users transfer native USDC back to TOS through CCTP; and
5. retire USDCx when circulating supply reaches zero.

**Atomic protocol migration**

A direct in-protocol conversion MAY be used only if Circle and TOS jointly
define how corresponding xReserve reserves are converted/released and how an
equal native-USDC authorization is established. TOS MUST NOT locally convert
USDCx balances into native USDC without matching external reserve/issuer state.

During migration, explorers and wallets MUST distinguish `USDCx` and `USDC` by
`asset_id`, issuer profile, and redemption path even if UI migration tools offer
a one-click flow.

### 25. Native USDC fee eligibility

Phase 3 does not automatically make native USDC a gas asset. Fee eligibility is
activated only after the fee-accounting profile in Section 10 is implemented and
validated.

If enabled, a transaction MAY select native USDC as its fee asset while TOS
continues to be the validator staking/security asset. The fee model MUST define
where collected USDC goes: validator distribution, fee collector, burn, treasury,
or deterministic conversion. The choice MUST be explicit and MUST NOT silently
change TOS staking weight or consensus security.

A user-facing goal MAY be:

```text
Agent Account
    TOS   = 0
    USDC  = 100.000000

Pay 10.000000 USDC
Fee  0.002317 USDC
```

but this UX is conforming as **protocol-native USDC gas** only after validators
natively account for and collect USDC-denominated fees. Before then, equivalent
UX is sponsorship.

## Rationale

### 26. Why not a separate stablecoin workchain

A separate workchain would create a second execution and account domain for a
problem that the existing base protocol can express through
`CurrencyCollection`. It would complicate Agent identity, account policy,
escrow, routing, and cross-workchain failure handling without being necessary
for stable settlement.

A future specialized workchain remains possible for an execution model that
actually requires different consensus or VM semantics. Stablecoin denomination
alone is not such a requirement.

### 27. Why not use a Jetton as canonical USDC

Jettons are appropriate application-level tokens, but canonical settlement and
fee assets benefit from protocol-level balances:

- one authoritative account balance instead of a derived per-owner token wallet;
- one-hop native transfers;
- simpler escrow;
- no token-wallet notification/excess path;
- less native TOS required merely to move the token;
- direct Agent Account policy accounting; and
- a feasible future path to protocol-native fee charging.

This proposal does not remove Jettons or require existing Jetton assets to
migrate.

### 28. Why xReserve before CCTP

CCTP is the preferred end state for native USDC because it uses Circle's
canonical burn-and-mint interoperability between supported native-USDC domains.
TOS cannot unilaterally join CCTP.

xReserve exists specifically to let partner blockchains issue USDC-backed
stablecoins before they have Circle-native USDC. It provides Circle-deployed
reserve infrastructure and attestations while allowing the remote blockchain to
adapt its stablecoin implementation to its own execution environment. That
makes it a better bootstrap model than a TOS-operated third-party bridge.

### 29. Why the framework is asset-generic

Hard-coding USDC semantics into every account, wallet, or TVM instruction would
make later assets costly and create issuer-specific consensus code. The registry
keeps generic transfer and accounting logic separate from an issuer profile.

The same framework may later support EURC or another approved asset, but each
asset requires its own registry entry, controller, issuer profile, supply
invariants, and security review.

## Backwards Compatibility

Phase 1 is additive to the account balance representation because
`ExtraCurrencyCollection` already exists. Existing accounts with no registered
extra-asset balances remain valid.

Existing messages with an empty extra-currency dictionary remain valid.
Existing Wallet V5 signatures remain valid under their existing action encoding.
SDKs that assume `other` is empty must be upgraded to send or display native
stable assets but do not need to reinterpret old transactions.

Existing Agent Account TOS-only opcodes retain their current semantics. New
asset-aware actions use new versioned opcodes and policy fields. Implementations
MUST NOT reinterpret a historical `value:coins` as a stable-asset amount.

Existing Jetton contracts and stablecoin escrows continue to function. Native
stable assets use a separate contract/application profile.

Native non-TOS fee charging is consensus-incompatible with old clients and MUST
therefore use an explicit global-version/capability activation after all
validators support it.

## Test Cases

The implementation MUST include at least the following conformance classes.
Exact byte vectors belong under `assets/tip-2/` when wire encodings are
frozen.

### 30. Registry

```text
valid registered asset                         -> accept
unknown descriptor version                     -> reject
unknown critical flag                          -> reject
duplicate asset_id                             -> reject
controller/code-hash mismatch                  -> reject
paused mint                                    -> reject
paused burn                                    -> reject
```

### 31. Mint and replay

```text
valid evidence, amount A, replay R              -> recipient +A, supply +A
same evidence and replay R again                -> reject, no state change
same replay R with different recipient          -> reject
same replay R with different amount             -> reject
invalid attestation                             -> reject, no supply change
zero amount                                     -> reject
```

### 32. Burn

```text
holder balance >= A, valid destination          -> balance -A, supply -A
holder balance < A                              -> reject
replayed burn identity                          -> reject
burn under paused profile                       -> reject
malformed destination                           -> reject
```

### 33. Wallet V5

```text
TOS-only out message                            -> unchanged behavior
USDC-only native out message                    -> exact extra-currency transfer
TOS + USDC out message                          -> exact CurrencyCollection transfer
malformed extra-currency map                    -> reject
signature mutation of asset_id or amount        -> reject
```

### 34. Agent Account

```text
USDC amount <= per-tx and daily policy           -> accept
USDC amount > per-tx policy                      -> reject
USDC cumulative amount > daily policy            -> reject
TOS policy large but USDC policy small           -> USDC limit still enforced
asset_id mutation after signature                -> reject
replay seqno                                     -> reject
```

### 35. xReserve

```text
valid Circle deposit attestation                 -> one USDCx mint
same deposit attestation twice                   -> one total mint
wrong remote domain                              -> reject
wrong remote token                               -> reject
wrong recipient commitment                       -> reject
wrong amount                                     -> reject
removed/expired attester                         -> reject per rotation rules
finalized burn + valid remote attester            -> eligible withdrawal
unfinalized burn                                 -> attester must not sign
```

### 36. CCTP

When Phase 3 is specified by Circle/TOS integration artifacts:

```text
valid supported-domain burn/attestation          -> one native USDC mint
wrong source domain                              -> reject
wrong TOS destination domain                     -> reject
replayed CCTP message                            -> reject
modified recipient                               -> reject
modified amount                                  -> reject
```

### 37. Fee-eligible asset

Before activation:

```text
registered USDC balance, no TOS, external TVM tx -> existing no-gas behavior
```

After fee profile activation:

```text
selected fee asset registered + FEE_ELIGIBLE     -> deduct exact asset fee
selected asset not FEE_ELIGIBLE                   -> reject
insufficient selected fee balance                 -> reject
fee record asset/amount differs from deduction    -> block invalid
```

## Reference Implementation

The initial implementation is expected in `tosnetwork/tos` and SHOULD reuse the
existing protocol structures rather than introduce a parallel token ledger.
Relevant baseline areas include:

```text
crypto/block/block.tlb
crypto/block/block.h
crypto/block/block.cpp
crypto/block/transaction.cpp
crypto/vm/tosops.cpp
crypto/smartcont/wallet-v5-code.fc
crypto/smartcont/wallet-v5.tol
crypto/smartcont/agent-account-code.fc
crypto/smartcont/tos-service-stablecoin-escrow-v2.fc
sdk/js/packages/wallets/
tosctl/src/block/
tosctl/src/executor/
validator/impl/
```

The implementation SHOULD be split into reviewable PRs matching the phases:

1. native-asset registry and mint/burn core;
2. wallet/SDK/native-transfer support;
3. Agent Account multi-asset policy and actions;
4. native stable-asset escrow;
5. xReserve testnet controller and attester tooling;
6. xReserve production activation after Circle onboarding;
7. CCTP integration after Circle domain support;
8. optional native stable-asset fee accounting as a separately activated core
   change.

No implementation PR should claim production Circle interoperability using only
local fixtures.

## Security Considerations

### 38. Mint authority is a consensus-critical boundary

A bug or bypass in a registered mint controller can create unbacked stable
assets. Controller identity MUST therefore be pinned by both address and code
identity, and the host MUST reject mint requests from any other account.

No owner, upgrade key, relayer, RPC service, or Agent controller may have an
undocumented path to arbitrary minting.

### 39. External issuer trust

xReserve-backed USDCx inherits trust in Circle's reserve and attestation system
plus the TOS remote-chain integration and attester. Native CCTP USDC inherits
Circle issuer and attestation assumptions. These assets are not trustless merely
because their TOS balances are protocol-native.

Clients MUST expose the issuer/redemption profile to users and MUST NOT equate
protocol-native storage with decentralized issuance.

### 40. Replay protection

Every external deposit, withdrawal, mint, and burn authorization MUST have a
unique canonical replay identity. Replay state MUST survive process crashes,
validator restarts, pruning boundaries required by the profile, controller
rotation, and ordinary contract state transitions.

Attestation signatures alone are insufficient if the same valid attestation can
be submitted twice.

### 41. Attester rotation

Circle and TOS remote attesters require bounded, explicit key rotation.
Overlapping old/new validity MAY be supported for continuity, but the profile
MUST prevent two keys from authorizing conflicting interpretations of one replay
identity.

Emergency removal MUST be possible without rewriting historical validity.

### 42. Finality

The TOS remote attester MUST derive burn authorization from finalized chain state
under a frozen finality profile. RPC observations from one node are not adequate
proof of finality.

The Circle-side source finality requirements are external integration parameters
and MUST be updated only through the reviewed issuer profile.

### 43. Address confusion

EVM addresses, Circle 32-byte recipient identifiers, TOS account IDs, and full
TOS `(workchain, account_id)` addresses are different namespaces. Encodings MUST
use explicit domains and MUST NOT truncate a full TOS address to fit an external
field.

### 44. Decimal confusion

USDC uses six decimals. TOS native TOS uses nine decimal base units, and other
assets may differ. Cross-chain amount conversion MUST use integers and exact
registered decimals. Floating-point conversion is forbidden in signing,
consensus, bridge, and custody logic.

### 45. Supply reconciliation

For externally backed assets, automated monitoring SHOULD continuously compare
TOS circulating supply with the external reserve/issuer state. A mismatch MUST
trigger an operational incident and SHOULD be able to pause new minting.

Monitoring does not replace consensus validation and must not silently mutate
balances.

### 46. Pause semantics

A pause mechanism SHOULD be narrowly scoped. A compromised bridge/attester
should normally stop new mint/burn interoperability while ordinary transfers of
already issued balances remain possible. Freezing user balances requires a
separate explicit asset policy and is not implied by this TIP.

### 47. Fee-market risk

If stable assets become fee-eligible, fee pricing creates economic and denial-of-
service risks. An attacker must not obtain unbounded validator computation from
a stale or manipulated conversion rate. The fee profile therefore requires
bounded deterministic pricing and separate load/gas calibration before
activation.

### 48. Upgrade safety

Changing a controller code hash, issuer profile, attester set, asset identifier,
or fee-eligibility rule is consensus/economic policy, not an ordinary
application upgrade. Changes MUST be explicitly versioned, reviewed, activated,
and auditable.

### 49. Migration safety

During USDCx -> native USDC migration, wallets and applications MUST distinguish
both assets until the old supply is retired. UI aliasing MUST NOT make a payment
signed for one `asset_id` settle in the other without an explicit conversion
transaction authorized by the user/Agent policy.

## Operational Rollout

### 50. Phase 1 readiness

- all validators run a release implementing the native-asset framework;
- multi-node deterministic execution and codec parity pass;
- test-only native assets exercise transfer, escrow, replay, pause, and supply;
- Wallet V5 and Agent Account SDKs support exact integer asset amounts;
- explorers and accounting tools display issuer profiles and asset IDs;
- no real-world asset is enabled until its controller profile is independently
  reviewed.

### 51. Phase 2 readiness

- Circle has approved TOS as an xReserve remote blockchain;
- Circle-issued remote domain and attester parameters are frozen;
- testnet deposit/withdrawal succeeds end-to-end;
- remote attester operations, rotation, backups, and incident response are
  documented and rehearsed;
- independent security review covers the TOS controller and protocol mint/burn
  boundary;
- reserve/supply reconciliation is operational;
- production activation starts with explicit limits and pause capability.

### 52. Phase 3 readiness

- Circle lists TOS as a supported CCTP/native-USDC domain;
- official contract/module/address and attester parameters are published;
- Arc <-> TOS test transfers pass in both directions using official Circle
  infrastructure;
- USDCx migration/redemption plan is active;
- wallets and explorers distinguish both asset forms during migration;
- native USDC fee eligibility, if desired, is activated separately only after
  fee-accounting conformance passes.

## Alternatives Considered

### 53. Dedicated USDC workchain

Rejected for this use case. It adds routing and execution complexity while the
base protocol already supports multi-asset account values.

### 54. Jetton-only USDC

Retained as an application option but rejected as the target canonical
representation because it adds token-wallet hops and native-TOS requirements to
stable settlement.

### 55. TOS-operated multisig bridge

Not selected as the canonical USDC route. It would add an independent bridge
trust domain and could create a wrapped asset incompatible with Circle-native
USDC liquidity. It MAY be used for isolated testing under a non-USDC name but
must not be presented as Phase 2 or Phase 3 compliance.

### 56. Gas sponsor only

Gas sponsorship remains useful and can provide a USDC-only UX before native
stable-asset fee accounting. It does not solve canonical stablecoin storage,
bridge issuance, one-hop settlement, or protocol supply accounting, so it is a
complement rather than the end state.

## References

1. TOS `CurrencyCollection`, `ExtraCurrencyCollection`, transaction and TVM
   sources at baseline commit
   `2004ce5e618c4a9d8ed5fe5ae51912d65bb524cd`:
   https://github.com/tosnetwork/tos
2. Circle CCTP supported chains and Circle-issued domains:
   https://developers.circle.com/cctp/concepts/supported-chains-and-domains
3. Circle xReserve overview:
   https://developers.circle.com/xreserve
4. Circle xReserve technical guide and dual-attestation model:
   https://developers.circle.com/xreserve/concepts/technical-guide
5. Circle USDC-backed Stablecoin Reference Specification:
   https://developers.circle.com/xreserve/concepts/usdc-backed-stablecoin-specification
6. Circle xReserve supported source/remote domains:
   https://developers.circle.com/xreserve/references/supported-blockchains-and-domains
7. Arc CCTP bridging documentation:
   https://docs.arc.io/integrate/exchanges/cctp-bridging
8. RFC 2119: https://www.rfc-editor.org/rfc/rfc2119
9. RFC 8174: https://www.rfc-editor.org/rfc/rfc8174

## Copyright

Copyright and related rights waived via
[CC0](https://creativecommons.org/publicdomain/zero/1.0/).
