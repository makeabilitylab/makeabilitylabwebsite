# Security Policy

This is the source for the [Makeability Lab website](https://makeabilitylab.cs.washington.edu),
a Django site hosted by the University of Washington's Allen School.

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Report it privately through GitHub: on this repository's **Security** tab, choose
**Report a vulnerability**
([direct link](https://github.com/makeabilitylab/makeabilitylabwebsite/security/advisories/new)).
Only the maintainers can see the report.

Useful things to include: the URL or file involved, steps to reproduce, and what
an attacker could do with it. We are a small research lab, not a security team,
so we can't promise a response time, but we read every report and will reply.

## Scope

- The code in this repository, and the two sites it deploys:
  `makeabilitylab.cs.washington.edu` and `makeabilitylab-test.cs.washington.edu`.
- The servers themselves are run by UW CSE IT. For a problem with the hosting
  infrastructure rather than this code, contact `support@cs.washington.edu`.

## Supported versions

Only the latest release (the newest tag) is deployed and maintained.

## For maintainers

- Dependency alerts: the repository's Security tab (Dependabot), tracked in #1460.
- Secret scanning and push protection are enabled. Never commit `config.ini`,
  API keys, or database dumps; never write secrets under `media/`, `static/`
  or any other web-served path.
- A fix for something exploitable goes out before it is described in a public
  issue or pull request.
