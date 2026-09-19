"""
Generate a self-signed SSL certificate for local / internal HTTPS.

Usage:
    python deploy/generate_ssl_cert.py
    python deploy/generate_ssl_cert.py --domains localhost,127.0.0.1,mysite.local
"""
from __future__ import annotations

import argparse
import datetime
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

CERT_DIR = Path(__file__).resolve().parent / 'certs'
CERT_FILE = CERT_DIR / 'cert.pem'
KEY_FILE = CERT_DIR / 'key.pem'


def generate(domains: list[str], days: int = 825) -> None:
    CERT_DIR.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'IN'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'SP-Tech Software Solution'),
        x509.NameAttribute(NameOID.COMMON_NAME, domains[0]),
    ])

    alt_names: list[x509.GeneralName] = []
    for d in domains:
        try:
            alt_names.append(x509.IPAddress(ipaddress.ip_address(d)))
        except ValueError:
            alt_names.append(x509.DNSName(d))

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    KEY_FILE.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    print(f'Certificate written to: {CERT_FILE}')
    print(f'Private key written to: {KEY_FILE}')
    print(f'Valid for domains/IPs: {", ".join(domains)} ({days} days)')
    print('Browsers will show a warning for self-signed certs - click Advanced -> Proceed.')


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate self-signed SSL certificate')
    parser.add_argument(
        '--domains',
        default='sanjivani.com,www.sanjivani.com,localhost,127.0.0.1',
        help='Comma-separated DNS names / IPs',
    )
    parser.add_argument('--days', type=int, default=825)
    args = parser.parse_args()
    domains = [d.strip() for d in args.domains.split(',') if d.strip()]
    generate(domains, args.days)


if __name__ == '__main__':
    main()
