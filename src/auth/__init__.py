"""Mock role login (v3 phase 4).

Three roles and a signed session token — no passwords, no user accounts. The
token carries only the role, HMAC-signed so it cannot be tampered with. Role is
enforced on the server by the guard; the UI is never the security boundary.
"""
