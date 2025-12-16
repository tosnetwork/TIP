---
tip: <TIP number>
title: <TIP title>
author: <author name> (@github-handle), <author email>
status: Draft
type: Standards Track
category: Core
created: 2025-01-01
requires: <TIP number(s)> (optional)
---

## Abstract

A short (~200 word) description of the technical issue being addressed. This should be a very terse and human-readable version of the specification section. Someone should be able to read only the abstract to get the gist of what this specification does.

## Motivation

The motivation section should describe the "why" of this TIP. What problem does it solve? Why should someone want to implement this standard? What benefit does it provide to the TOS ecosystem? What use cases does this TIP address?

## Specification

The technical specification should describe the syntax and semantics of any new feature. The specification should be detailed enough to allow competing, interoperable implementations.

### Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `PARAM_A` | 100   | Description of parameter A |
| `PARAM_B` | 200   | Description of parameter B |

### Data Structures

```
struct ExampleStruct {
    field1: uint256
    field2: address
    field3: bytes32
}
```

### Interface

```solidity
interface IExample {
    function exampleMethod(uint256 param) external returns (bool);
    event ExampleEvent(address indexed sender, uint256 value);
}
```

## Rationale

The rationale fleshes out the specification by describing what motivated the design and why particular design decisions were made. It should describe alternate designs that were considered and related work.

The rationale should provide evidence of consensus within the community and discuss important objections or concerns raised during discussion.

## Backwards Compatibility

All TIPs that introduce backwards incompatibilities must include a section describing these incompatibilities and their severity. The TIP must explain how the author proposes to deal with these incompatibilities.

This section may be omitted if the proposal does not introduce any backwards incompatibilities.

## Test Cases

Test cases for an implementation are mandatory for TIPs that are affecting consensus changes. Tests should either be inlined in the TIP as data (such as input/expected output pairs) or included in `../assets/tip-X/`.

```
Input: 0x...
Expected Output: 0x...
```

## Reference Implementation

An optional section that contains a reference/example implementation that people can use to assist in understanding or implementing this specification.

```solidity
// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.0;

contract Example {
    // Implementation details
}
```

## Security Considerations

All TIPs must contain a section that discusses the security implications/considerations relevant to the proposed change. Include information that might be important for security discussions, surfaces risks, and can be used throughout the life-cycle of the proposal.

- What are the potential attack vectors?
- What are the mitigation strategies?
- Are there any trust assumptions?

## Copyright

Copyright and related rights waived via [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
