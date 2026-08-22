---
tip: 1
title: TOS DNS and the `.tos` Namespace
author: TOS Core Contributors (@tosnetwork)
status: Draft
type: Standards Track
category: Interface
created: 2026-08-22
requires: TEP-62, TEP-64, TEP-81
---

## Abstract

This TIP defines the canonical `.tos` naming system. It adopts the resolver,
NFT, open-auction, renewal, and release behavior of the official TON DNS
contracts at commit `d08131031fb659d2826cccc417ddd9b98476f814`, while giving
the namespace a TOS root, a TOS launch schedule, TOS-denominated bids, and
TOS-native record meanings.

The root is selected by masterchain configuration parameter 4. It delegates
`.tos` to an immutable Collection whose permanent Domain Items are both NFTs
and resolvers. Registration is an open ascending auction. Names remain usable
only while their lifecycle is healthy. Names are aliases, never cryptographic
principals: security-sensitive applications resolve from finalized state,
validate the Domain Item, and bind durable authority to the resulting address
or Native object identifier.

This TIP freezes name encoding, category hashes, record types, operation codes,
auction and lifecycle rules, deployment governance, resolver limits, and a
versioned cross-language vector corpus. It does not introduce a consensus, TVM,
Lite Server, or DNS record-format change.

## Motivation

TOS needs human-readable names for wallets, Sites, Agents, Capabilities,
Messaging contacts, and storage objects. A naming layer is useful only if each
implementation agrees on the exact bytes and if a displayed name cannot become
an alternate source of payment or execution authority.

The existing TOS code already inherits TON-compatible `dnsresolve`, DNS record
TL-B types, and configuration parameter 4. Reusing the audited public design is
safer and more interoperable than creating a new auction or registry. The TOS
profile therefore minimizes semantic differences and moves TOS-specific
behavior into deployment parameters, category meanings, provenance, and client
safety rules.

## Normative language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in RFC 2119
and RFC 8174.

## Specification

### 1. Reference contracts and compatibility boundary

The v1 contracts SHALL be derived from `ton-blockchain/dns-contract` commit
`d08131031fb659d2826cccc417ddd9b98476f814`.

The Collection and Domain Item auction, finalization, renewal, release, record,
and transfer state machines MUST remain semantically identical to that commit.
The allowed TOS deployment differences are:

1. the Root recognizes only the `tos` suffix;
2. currency names and tooling use TOS/Tomi while retaining `10^9` base units;
3. `auction_start_time` is the TOS activation value in Section 8;
4. build, deployment, test, and content URLs are TOS-specific; and
5. ConfigParam 80 is absent under the v1 governance policy.

Every release MUST publish the upstream commit, a complete source diff,
reproducible Root/Collection/Item code hashes, StateInit hashes, and deployment
addresses. An unreported semantic difference is non-conforming.

### 2. Architecture and authority

Resolution begins at the Root address stored as 256 bits in masterchain
configuration parameter 4. The Root MUST be deployed in workchain `-1`; clients
MUST NOT infer another workchain because parameter 4 carries no workchain ID.

The canonical path is:

```text
finalized ConfigParam 4
  -> immutable .tos Root
  -> immutable .tos Collection in workchain 0
  -> permanent Domain Item in workchain 0
  -> optional owner-controlled delegated resolvers
```

The Root, Collection, and item code cell used by a Collection are immutable.
Changing any of them requires a new release. Replacing the Collection or item
code changes deterministic Domain Item addresses and therefore requires an
explicit migration and a parameter-4 governance activation.

A `.tos` string MUST NOT be used as a signature domain, authorization key,
Accepted Quote identity, payment destination without confirmation, or durable
database key for irreversible actions. Applications MUST store the resolved
raw address or re-derived Native object ID and MAY retain the name as display
metadata.

### 3. Canonical names

Public `.tos` input SHALL use lowercase ASCII. A canonical dotted name:

- contains only non-empty components;
- contains no leading or trailing dot;
- contains no control, space, slash, colon, NUL, or non-ASCII byte;
- ends in the exact component `tos`; and
- is at most 126 UTF-8 bytes in dotted form.

Lookup UI MAY offer to lowercase input only after displaying the canonicalized
result. Registration and mutation interfaces MUST reject uppercase input.

The on-chain second-level label rule is inherited unchanged: 4 through 126
bytes, lowercase `a`-`z`, `0`-`9`, and hyphen only in an interior position.
Consecutive interior hyphens and `xn--` satisfy the contract. Public UI SHOULD
warn on them and SHOULD recommend labels no longer than 63 bytes, but resolvers
MUST support every contract-valid label that fits the full-name limit.

The resolver encoding SHALL split on `.`, reverse components, append one NUL
byte to each component, and concatenate them:

```text
alice.tos           -> tos\0alice\0
translate.alice.tos -> tos\0alice\0translate\0
```

Encoded input MUST be byte-aligned and at most 127 bytes. A leading NUL is an
explicit self/relative-resolver query and MUST NOT be exposed as an ordinary
trailing-dot spelling.

The Domain Item index is the TVM representation hash `slice_hash(label_cell)`
of a cell containing the exact label bytes. It is not `SHA256(label)`.

### 4. Resolver algorithm

A resolver MUST:

1. read parameter 4 and fail closed if absent;
2. anchor all hops to one verified block/checkpoint;
3. call `dnsresolve(encoded_name, category)` at the Root;
4. validate that consumed bits are positive, byte-aligned, within the remaining
   slice, and end on a component boundary;
5. accept `dns_next_resolver` only for a partial answer;
6. reject a partial answer whose record has another type;
7. contact at most eight resolver contracts, including the Root;
8. reject a repeated resolver address before contacting it again;
9. reject unknown TL-B tags, category/type mismatches, and trailing data; and
10. return the block, resolver path, lifecycle result, and provenance class
    with the answer.

Hop exhaustion and cycle detection are errors distinct from “not found”. A
gateway cache MUST be bounded. Positive answers MUST NOT outlive the lesser of
the implementation TTL and the Domain Item renewal deadline. A reorg or a
finalized record, delegation, auction, or lifecycle change MUST invalidate the
affected name or subtree before the original TTL expires.

### 5. DNS record wire format

This TIP reuses the existing TOS TL-B constructors:

```text
dns_text#1eda _:Text = DNSRecord;
dns_next_resolver#ba93 resolver:MsgAddressInt = DNSRecord;
dns_adnl_address#ad01 adnl_addr:bits256 flags:(## 8)
  { flags <= 1 } proto_list:flags . 0?ProtoList = DNSRecord;
dns_smc_address#9fd3 smc_addr:MsgAddressInt flags:(## 8)
  { flags <= 1 } cap_list:flags . 0?SmcCapList = DNSRecord;
dns_storage_address#7473 bag_id:bits256 = DNSRecord;
_ (HashmapE 256 ^DNSRecord) = DNS_RecordSet;
```

Category zero requests the complete record dictionary and is not itself a
category. Other categories are `SHA256(UTF-8 category_name)`:

| Name | Hash | Required record | Meaning |
|---|---|---|---|
| `dns_next_resolver` | `19f02441ee588fdb26ee24b2568dd035c3c9206e11ab979be62e55558a1d17ff` | `dns_next_resolver` | delegated resolver |
| `site` | `fbae041b02c41ed0fd8a4efb039bc780dd6af4a1f0c420f42561ae705dda43fe` | `dns_adnl_address` | TOS Site ADNL identity |
| `wallet` | `e8d44050873dba865aa7c170ab4cce64d90839a34dcfd6cf71d14e0205443b1b` | `dns_smc_address` | payment account |
| `agent` | `d4f0bc5a29de06b510f9aa428f1eedba926012b591fef7a518e776a7c9bd1824` | `dns_smc_address` | finalized Agent account |
| `capability` | `38a5be91af79d7e5ba9809bf383c699b6864ee50446239fe56a45e32b84638fe` | `dns_smc_address` | finalized Capability account |
| `messenger` | `050f993ea2322d4b6940f8560a253a11709fdc5ab08fd994bceb096846ea1645` | `dns_smc_address` | Agent used as a Messaging contact |
| `storage` | `49a25f9feefaffecad0fcd30c50dc9331cff8b55ece53def6285c09e17e6f5d7` | `dns_storage_address` | storage Bag ID |
| `text` | `982d9e3eb996f559e633f4d194def3761d909f5a3b647d1a851fead67c32c9d1` | `dns_text` | untrusted presentation text |

An implementation MUST fail closed when a known category contains the wrong
record type. Unknown categories obtained through category zero MAY be ignored.
Text is never authoritative and MUST be escaped before display.

For `agent`, `capability`, and `messenger`, the address is only the first step.
The consumer MUST load finalized Native state, confirm the reviewed registry
code/version, re-derive the account address from network, object kind, and
object ID, compare it byte-for-byte, and then apply revocation, controller,
owner, version, and policy checks. `messenger` resolves to an Agent, not
directly to a transport endpoint.

### 6. Contract operations and getters

The inherited operation codes are frozen:

| Operation | Code |
|---|---:|
| NFT transfer | `0x5fcc3d14` |
| edit full content | `0x1a0b9d51` |
| change DNS record | `0x4eb1f0f9` |
| get static data / finish auction | `0x2fcb26a2` |
| report static data | `0x8b771735` |
| fill Collection balance | `0x370fec51` |
| outbid notification | `0x557cea20` |
| process governance decision | `0x44beae41` |
| release balance and re-auction | `0x4ed14b65` |

Clients SHALL use the inherited message bodies and getters, including
`dnsresolve`, `get_nft_data`, `get_domain`, `get_auction_info`, and
`get_last_fill_up_time`. “Finish auction” SHALL send `get_static_data` with a
query ID; an empty transfer or unknown opcode is not a valid finalizer.

### 7. Auction and lifecycle parameters

The following values are adopted without semantic divergence:

| Parameter | Value |
|---|---:|
| base unit | `1 TOS = 1,000,000,000 Tomi` |
| initial first-auction duration | 604,800 seconds (7 days) |
| final first-auction duration | 3,600 seconds (1 hour) |
| duration ramp | 12 periods of 2,592,000 seconds |
| anti-sniping extension | at least 3,600 seconds remaining |
| minimum next bid | `floor(previous_bid * 105 / 100)` |
| renewal/release interval | 31,622,400 seconds (366 days) |
| release comparison | strictly greater than the interval |
| item storage reserve | 1,000,000,000 Tomi |
| minimum-price decay | multiply by `90/100`, flooring each period, for 21 periods; use final floor after period 21 |

Minimum opening prices are denominated in whole TOS before decay:

| Label bytes | Initial | Final floor |
|---:|---:|---:|
| 4 | 1000 | 100 |
| 5 | 500 | 50 |
| 6 | 400 | 40 |
| 7 | 300 | 30 |
| 8 | 200 | 20 |
| 9 | 100 | 10 |
| 10 | 50 | 5 |
| 11–126 | 10 | 1 |

Every accepted bid updates `last_fill_up_time`. Finalization preserves it.
Owner top-up, transfer, content/record mutation, and release update it. Release
is allowed only when no auction exists and
`now - last_fill_up_time > 31,622,400`. It retains the same item address and
record dictionary while clearing ownership and starting a new seven-day
auction. Therefore a new owner MUST review and replace inherited records.

Raw getters may retain records during an auction or after expiry. A
security-sensitive consumer MUST reject records when `auction_end_time != 0`,
when no valid renewal clock exists, or when `now` is later than the renewal
deadline. Ended but unfinalized auctions remain auctions.

### 8. TOS v1 economic and launch decisions

The candidate mainnet `auction_start_time` is:

```text
1798761600  # 2027-01-01 00:00:00 UTC
```

This restarts the inherited seven-day-to-one-hour duration ramp and 21-period
price decay at `.tos` launch. Reusing TON’s 2022 timestamp is forbidden because
it would launch immediately at the shortest duration and lowest floor.

Activation MUST NOT occur unless all mainnet gates in Section 11 have passed
before this timestamp. If they have not, governance MUST select a later UTC
midnight, rebuild all three deployment artifacts, regenerate this TIP’s vector
corpus, publish the new hashes, and repeat review. Deploying after a missed
timestamp with a partially elapsed ramp is forbidden.

Winning proceeds are permanently retained by the immutable Collection, which
has no withdrawal path. TOS v1 explicitly treats this as economic burning. No
treasury, deployer, registrar, or frontend receives auction proceeds.

TOS v1 has no reserved-name or seizure list. ConfigParam 80 SHALL remain absent.
The inherited governance operation is therefore inert. Enabling it, using a
negative substitute, or adding a proceeds destination requires a separate TIP
and contract-security review.

### 9. Governance and upgrades

Parameter 4 controls the entire namespace and MUST be protected as a critical
configuration parameter before public activation. The change that protects it
and the later change that sets the Root MAY be separate proposals, but the Root
MUST NOT be activated first.

The release manifest MUST contain:

- source repository and commit;
- pinned TON upstream commit and complete diff;
- compiler/Fift versions and reproducible build instructions;
- Root, Collection, and Item code hashes and StateInit hashes;
- Root and Collection addresses;
- activation timestamp and block;
- shared-vector version; and
- incident contact and upstream-monitoring owner.

There is no in-place contract upgrade. An upgrade deploys a new immutable Root
and Collection, publishes new item-address vectors and a migration plan, gives
at least 30 days public notice, and changes parameter 4 through critical
governance. Clients MUST display the release identity and fail closed on an
unknown production release.

### 10. Provenance classes

`chain_anchored` means every hop and lifecycle read was verified against one
chain checkpoint. `evaluated` means a trusted local node evaluated the same
rules and returned the checkpoint and path. `quorum_agreed` means independent
providers agreed on the same result; it MUST NOT be labelled a cryptographic
proof. A response with no checkpoint or resolver path is not sufficient for a
security-sensitive operation.

Gateways, indexers, and caches never gain mutation or authorization authority.
Consumers MUST re-read finalized Native state immediately before payments,
session establishment, capability execution, or other irreversible actions.

### 11. Activation gates

Public mainnet activation requires evidence bound to exact commits:

1. parity with the latest reviewed official TON DNS release;
2. identical artifacts from two independent builders;
3. this TIP and its vector corpus in Last Call or Final status;
4. approved launch timestamp, prices, burn policy, and storage reserve;
5. two independent contract/security reviews and an independent resolver;
6. public-testnet evidence for registration, outbids/refunds, extension,
   finalization, transfer, record update, renewal, release, and re-auction;
7. fail-closed lifecycle behavior in every security-sensitive client;
8. reorg-safe resolver/indexer invalidation;
9. critical protection for parameter 4 plus published runbooks; and
10. an assigned owner and response SLA for upstream TON DNS security changes.

## Rationale

The token-denominated price table is retained because an auction discovers
market value and because changing the table without a stable TOS/fiat oracle
would merely replace a reviewed arbitrary schedule with an unreviewed one. The
launch decay limits early squatting while progressively lowering access costs.

Burning proceeds avoids granting a registrar or treasury privileged economic
control and preserves upstream semantics. Absence of ConfigParam 80 removes a
validator-wide schema change and a seizure mechanism from v1. Critical
protection for parameter 4 is necessary because replacing the Root can redirect
every name and is at least as consequential as changing other protected system
addresses.

Names deliberately remain aliases. This prevents transfer, expiry, re-auction,
cache staleness, or visually deceptive labels from silently transferring Agent,
Capability, payment, or Messaging authority.

## Backwards Compatibility

The proposal uses the existing TOS configuration parameter 4, `dnsresolve`
method, DNSRecord TL-B constructors, NFT interfaces, and client primitives. It
requires no consensus or TVM change. Existing generic DNS resolvers remain wire
compatible but are not production-conforming until they implement the limits,
lifecycle checks, and provenance rules above.

Adding parameter 4 to the critical-parameter set changes only the governance
threshold for future parameter-4 proposals. ConfigParam 80 remains absent.

## Test Cases

The normative machine-readable corpus is
[`../assets/tip-1/dns-v1.json`](../assets/tip-1/dns-v1.json). Implementations
MUST consume the file directly rather than copying values into private fixtures.
The corpus covers canonical encoding, category hashes, slice hashing,
deterministic addresses, price decay, bid rounding, auction timing, lifecycle
boundaries, operation codes, and invalid input.

Required integration tests additionally cover:

- exactly eight contacts succeeding and a ninth contact never occurring;
- repeated resolver rejection before another network request;
- partial answers with the wrong record type;
- one-checkpoint consistency across all hops and lifecycle getters;
- ended-but-unfinalized, overdue, and clockless items failing closed;
- record/delegation mutation and reorg invalidating live cache entries;
- release retaining records and address while changing owner generation;
- Agent/Capability address-to-object-ID re-derivation failure; and
- names never becoming authorization or signature-domain inputs.

## Reference Implementation

The reference implementation is maintained in:

- `tosnetwork/tos/crypto/smartcont/dns` — contracts and release tooling;
- `tosnetwork/tos` — C++, Rust, and TypeScript clients;
- `tosnetwork/tos-service-protocol` — Go finalized resolver/verifier; and
- `tosnetwork/tos/domains` — non-custodial registrar application.

The detailed architecture and delivery evidence are maintained in
`tosnetwork/doc/tos-blockchain/DNS.md`.

## Security Considerations

Implementations MUST address name confusion, malicious resolvers, cycles,
excessive depth, malformed consumed counts, record-type substitution, stale
checkpoints, reorgs, active or unfinalized auctions, overdue items, inherited
records after re-auction, governance root substitution, unknown contract code,
cache amplification, display injection, and payment substitution.

Resolvers MUST bound names, hops, in-flight work, waiters, caches, and decoded
data. Loaded contract state MUST be released on every asynchronous exit. Cache
entries MUST retain their checkpoint and authority path. Text and reverse
lookup are untrusted projections. Wallets MUST show the canonical name, raw
address, network, checkpoint age, auction state, and renewal deadline before
signing.

## Copyright

Copyright and related rights waived via
[CC0](https://creativecommons.org/publicdomain/zero/1.0/).
