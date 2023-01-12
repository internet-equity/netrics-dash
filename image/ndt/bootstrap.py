#!/usr/bin/env python3
"""NDT server launcher ensuring SSL certificate generation."""
import argparse
import pathlib
import subprocess
import sys


def make_parser():
    parser = argparse.ArgumentParser(
        description="ndt-server entrypoint",
        usage="%(prog)s [-h] [-cert PATH] [-key PATH] "
              "[ ... add'l ndt-server options ... ]",
    )

    parser.add_argument(
        '-cert',
        metavar='PATH',
        type=pathlib.Path,
        help="path to certificate file",
    )
    parser.add_argument(
        '-key',
        metavar='PATH',
        type=pathlib.Path,
        help="path to key file",
    )

    return parser


def parse_args(parser, args=None):
    (boot_args, _ndt_args) = parser.parse_known_args(args)
    return boot_args


def generate_certificate(cert, key):
    if not cert or not key:
        return None

    if cert.exists():
        if not key.exists():
            print('specified cert exists but key does not: '
                  'will not consider generation', file=sys.stderr)

        return None

    if not key.exists():
        try:
            subprocess.run(['openssl', 'genrsa', '-out', key], check=True)
        except subprocess.CalledProcessError as exc:
            print(f'error: openssl genrsa: exit {exc.returncode}', file=sys.stderr)
            return exc.returncode

    openssl_proc = subprocess.run([
        'openssl', 'req', '-new', '-x509',
        '-days', '2',
        '-subj', '/C=XX/ST=State/L=Locality/O=Org/OU=Unit/CN=localhost/emailAddress=test@email.address',
        '-key', key,
        '-out', cert,
    ])

    if openssl_proc.returncode > 0:
        print(f'error: openssl req: exit {openssl_proc.returncode}', file=sys.stderr)

    return openssl_proc.returncode


def serve(server_path='/ndt-server', *args):
    try:
        ndt_proc = subprocess.run([server_path] +
                                  (list(args) if args else sys.argv[1:]))
    except KeyboardInterrupt:
        return 0
    else:
        return ndt_proc.returncode


def main(cert, key):
    if generation_code := generate_certificate(cert, key):
        return generation_code

    return serve()


if __name__ == '__main__':
    args = parse_args(make_parser())
    returncode = main(**vars(args))
    sys.exit(returncode)
