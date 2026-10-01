import hashlib
import hmac
import ipaddress
import time

def sign_session(secret, now=None):
    expires=str(int(time.time() if now is None else now)+30*86400)
    signature=hmac.new(secret.encode(),expires.encode(),hashlib.sha256).hexdigest()
    return expires+'.'+signature

def valid_session(secret, token, now=None):
    try:
        expires,signature=token.split('.')
        if int(expires)<(time.time() if now is None else now):return False
        expected=hmac.new(secret.encode(),expires.encode(),hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature,expected)
    except (ValueError,AttributeError):return False

def local_client(remote):
    try:return ipaddress.ip_address(remote).is_loopback
    except ValueError:return False

def allowed_client(remote, networks):
    try:return any(ipaddress.ip_address(remote) in ipaddress.ip_network(n) for n in networks)
    except ValueError:return False
