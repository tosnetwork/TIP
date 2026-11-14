# TOS Improvement Proposals (TIPs)

TOS Improvement Proposals (TIPs) describe standards for the TOS network, including core protocol specifications, client APIs, and contract standards.

## Contributing

1. Review [TIP Sample](TIPS/tip-sample.md) to understand the TIP format.
2. Fork the repository.
3. Add your TIP to the `TIPS/` folder following the sample format.
4. Submit a Pull Request.
5. Renumber the TIP to match its Pull Request number. A TIP number equals the
   number of the Pull Request that introduces it, so the number is assigned
   once the PR exists: update the `tip:` metadata, the heading, the file name
   `TIPS/tip-<n>.md`, and any `assets/tip-<n>/` path.

## Proposals

| TIP | Title | Status | Type |
|---|---|---|---|
| [1](TIPS/tip-1.md) | TOS DNS and the `.tos` Namespace | Draft | Standards Track / Interface |
| [2](TIPS/tip-2.md) | Protocol-Native Stable Assets and Circle USDC Interoperability | Draft | Standards Track / Core |

## TIP Status Terms

- **Draft** - A TIP that is open for consideration.
- **Review** - A TIP that is undergoing peer review.
- **Last Call** - A TIP that is in the final review window before moving to Final.
- **Final** - A TIP that has been accepted and implemented.
- **Stagnant** - A TIP that has had no activity for 6 months or more.
- **Withdrawn** - A TIP that has been withdrawn by the author(s).
- **Living** - A TIP that is designed to be continually updated.

## TIP Types

- **Standards Track** - Changes affecting most or all TOS implementations.
  - **Core** - Improvements to the core protocol.
  - **Networking** - Improvements to the networking layer.
  - **Interface** - Improvements around client API specifications.
  - **TRC** - Application-level standards and conventions (TOS Request for Comments).
- **Meta** - Describes a process or proposes a change to the TIP process.
- **Informational** - Describes a TOS design issue or provides general guidelines.

## TIP Format

Each TIP should have the following parts:

- **Preamble** - RFC 822 style headers containing metadata about the TIP.
- **Abstract** - A short (~200 word) description of the issue being addressed.
- **Motivation** - The motivation is critical for TIPs that want to change the TOS protocol.
- **Specification** - The technical specification should describe the syntax and semantics of any new feature.
- **Rationale** - The rationale fleshes out the specification by describing what motivated the design.
- **Backwards Compatibility** - All TIPs that introduce backwards incompatibilities must include a section describing these incompatibilities.
- **Test Cases** - Test cases for an implementation are mandatory for TIPs that are affecting consensus changes.
- **Reference Implementation** - An optional section that contains a reference/example implementation.
- **Security Considerations** - All TIPs must contain a section that discusses the security implications.
- **Copyright** - All TIPs must be in the public domain or under a compatible license.

## License

This repository is licensed under [CC0-1.0](LICENSE).
