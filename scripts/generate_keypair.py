# scripts/generate_keypair.py
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from pathlib import Path

KEYS_DIR = Path("keys")
KEYS_DIR.mkdir(exist_ok=True)

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

(KEYS_DIR / "private_key.pem").write_bytes(private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
))
(KEYS_DIR / "public_key.pem").write_bytes(private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
))
print("Keypair written to keys/. Never commit keys/private_key.pem.")