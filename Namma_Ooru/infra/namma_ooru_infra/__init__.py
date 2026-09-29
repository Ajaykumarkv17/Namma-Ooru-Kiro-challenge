"""AWS CDK v2 (Python) infrastructure for Namma Ooru.

Stacks are split by concern (data, ai, backend, frontend, monitoring) so the
backend can be deployed independently and a local frontend can be tested against
the deployed backend before the frontend is deployed to Amplify.
"""
