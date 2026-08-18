# Offlinea - Writeup

## Overview

This challenge is a two-stage web exploit:

1. Abuse the PHP front-end to make Selenium visit the internal Flask service.
2. Exploit a Python `str.format()` injection in the Flask logs page to leak the Flask secret key.
3. Forge a JWT and read the `secrets` table, which already contains the flag.

The important files are:

- [challenge/service/bartender.php](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/service/bartender.php)
- [challenge/internal/app.py](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/internal/app.py)
- [challenge/internal/init_db.py](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/internal/init_db.py)

## Recon

The application is split into two services:

- PHP front-end on port `8000`
- Flask back-end on port `5000`

The PHP front-end exposes `/bartender.php`, which forwards user-controlled input to the Flask `/generate` endpoint.

The Flask app does three important things:

- stores every visited URL in SQLite history
- renders `/logs` using `render_template("bartender.html", log_data=log)`
- protects `/bartender` with a JWT signed by a runtime-generated `SECRET_KEY`

## Vulnerability 1: DNS rebinding / internal SSRF

The PHP layer attempts to block private targets, but the actual Selenium visit happens in Flask, not in PHP.

Relevant code:

- [challenge/service/bartender.php](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/service/bartender.php#L28)
- [challenge/internal/app.py](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/internal/app.py#L62)

Why this matters:

- PHP checks the user-supplied URL once.
- The URL must return `200 OK` directly. Redirects fail the PHP gate.
- Flask later loads the same URL with Chrome.
- If the hostname resolves to a public IP during the PHP check, then later flips to `127.0.0.1`, Selenium can be forced to visit the internal Flask service.

This is the intended entry point.

## Vulnerability 2: Python format-string injection

The `/logs` route calls:

```python
log = logify(rec)
```

and `logify()` does:

```python
history_1 = row_separator.join(history)
log = history_1.format(logify=logify)
```

This is unsafe because the database contents are inserted into a format string without escaping braces.

Relevant code:

- [challenge/internal/app.py](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/internal/app.py#L55)
- [challenge/internal/app.py](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/internal/app.py#L165)

That means if we can store a payload like:

```text
{logify.__globals__[app].config[SECRET_KEY]}
```

inside the `history.url` field, then rendering `/logs` will resolve it and leak the Flask secret key.

## Vulnerability 3: JWT forgery

The `/bartender` route is protected by:

```python
jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
```

If `is_admin` is true, access is granted.

Relevant code:

- [challenge/internal/app.py](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/internal/app.py#L116)

Once the secret key is leaked, we can forge a valid HS256 token and bypass the gate.

## Exploitation Steps

### 1. Prepare a rebinding domain

Use a domain you control and configure it so that:

- the first lookup resolves to a public IP
- a later lookup resolves to `127.0.0.1`

The first request must pass the PHP filter.
The second request should make Selenium reach the internal Flask app.
The hosted page must answer `200 OK` without redirecting.

### 2. Plant the format-string payload

Send a request to the PHP front-end with a URL like:

```text
http://rebind.example/%7Blogify.__globals__[app].config[SECRET_KEY]%7D
```

The `%7B` and `%7D` encoding bypasses the PHP brace regex while still decoding into braces on the Flask side.

This causes the payload to be stored in `history.url`.

### 3. Trigger the internal `/logs` page

After the DNS record flips to `127.0.0.1`, request:

```text
http://rebind.example/logs
```

The Selenium browser now reaches the Flask app internally and renders the stored history.

The malicious URL is interpreted by `str.format()`, which leaks `app.config['SECRET_KEY']` into the rendered page and the generated PDF.

If you need the exact format-string target, it is:

```text
{logify.__globals__[app].config[SECRET_KEY]}
```

### 4. Forge the JWT

Use the leaked secret to sign a token:

```python
import jwt

secret = "LEAKED_SECRET"
token = jwt.encode(
    {"username": "guest", "is_admin": True},
    secret,
    algorithm="HS256",
)

print(token)
```

### 5. Read the flag

Call the protected endpoint with the forged token:

```text
http://rebind.example/bartender?token=PASTE_TOKEN_HERE
```

The response returns the full `secrets` table.

The flag is inserted during initialization in:

- [challenge/internal/init_db.py](C:/Users/User/Downloads/offlnea/web_offlinea/challenge/internal/init_db.py#L34)

## Why the challenge is “easy”

The solve path is short once the pieces are connected:

- trust boundary confusion between PHP and Flask
- weak SSRF defense built around DNS timing
- unsafe rendering of database content with `str.format()`
- JWT secret stored in process memory and used directly for auth

The hard part is usually recognizing that `/logs` is the leak primitive and not the end goal.

## Summary

Final chain:

1. Rebind DNS to reach internal Flask.
2. Store a format-string payload in history through a direct `200 OK` page.
3. Visit `/logs` to leak `SECRET_KEY`.
4. Forge `HS256` JWT with `is_admin=true`.
5. Request `/bartender` with the forged token and retrieve the flag.
