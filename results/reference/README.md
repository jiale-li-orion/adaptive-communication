# Frozen Reference Results

This directory is the immutable comparison plane used by reproduction audits.

- communication-substrate/claims/: frozen comparators for current C1-C11 result evidence.
- agentic/: frozen compact comparators for A1-A6 deterministic/infrastructure claims.
- legacy-communication/: comparators retained only to audit superseded C5/C9/C10 experiments.

Live evidence belongs under results/communication-substrate/claims/ or results/agentic/. Reference files are comparison anchors and do not become claims by location alone.

For current communication claims, artifact/reproduce_all.sh uses explicit live-result to frozen-reference pairs. Legacy references are consumed only by historical/semantic audits.
