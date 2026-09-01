# Security policy

## Reporting

Please report vulnerabilities privately through GitHub Security Advisories for `TIKAZI/TIKAZ-Codex-Context-OnPremise`. Do not include real credentials, private documents, or sensitive media in a public issue.

## Scope and threat model

The project treats source files, converted text, webpages, archive members, model output, and embedded instructions as untrusted input. Important controls include bounded archive handling, process timeouts, loopback-only local vision, offline model helpers, protected-literal gates, explicit network opt-in, and source-preserving fallback.

No security workflow can guarantee safety. Users remain responsible for reviewing external binaries, model licenses, local permissions, and source authorization before processing sensitive material.
