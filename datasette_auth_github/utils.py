import base64
import hashlib
import hmac
from http.cookies import SimpleCookie

SALT = "datasette-auth-github"


class BadSignature(Exception):
    pass


class Signer:
    def __init__(self, secret):
        self.secret = secret

    def signature(self, value):
        return (
            base64.urlsafe_b64encode(salted_hmac(SALT, value, self.secret).digest())
            .strip(b"=")
            .decode()
        )

    def sign(self, value):
        return "{}:{}".format(value, self.signature(value))

    def unsign(self, signed_value):
        if ":" not in signed_value:
            raise BadSignature("No : found")
        value, signature = signed_value.rsplit(":", 1)
        if hmac.compare_digest(signature, self.signature(value)):
            return value
        raise BadSignature("Signature does not match")


async def send_html(send, html, status=200, headers=None):
    headers = headers or []
    if "content-type" not in [h.lower() for h, v in headers]:
        headers.append(["content-type", "text/html"])
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                [key.encode("utf8"), value.encode("utf8")] for key, value in headers
            ],
        }
    )
    await send({"type": "http.response.body", "body": html.encode("utf8")})


def ensure_bytes(s):
    if not isinstance(s, bytes):
        return s.encode("utf-8")
    else:
        return s


def force_list(value):
    if isinstance(value, str):
        return [value]
    return value


def salted_hmac(salt, value, secret):
    salt = ensure_bytes(salt)
    secret = ensure_bytes(secret)
    key = hashlib.sha1(salt + secret).digest()
    return hmac.new(key, msg=ensure_bytes(value), digestmod=hashlib.sha1)


def cookies_from_scope(scope):
    cookie = dict(scope.get("headers") or {}).get(b"cookie")
    if not cookie:
        return {}
    simple_cookie = SimpleCookie()
    simple_cookie.load(cookie.decode("utf8"))
    return {key: morsel.value for key, morsel in simple_cookie.items()}