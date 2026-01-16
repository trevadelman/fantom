#
# Python native crypto implementation using hashlib
#

import hashlib
from fan.sys.Obj import Obj
from fan.sys.Buf import Buf
from fan.sys.Err import UnsupportedErr


class PyCrypto(Obj):
    """Python implementation of crypto::Crypto using hashlib"""

    _instance = None

    @staticmethod
    def cur():
        if PyCrypto._instance is None:
            PyCrypto._instance = PyCrypto()
        return PyCrypto._instance

    def digest(self, algorithm):
        """Get a Digest for the given algorithm (SHA-1, SHA-256, MD5, etc.)"""
        return PyDigest(algorithm)

    def gen_csr(self, keys, subject_dn, opts=None):
        raise UnsupportedErr.make("genCsr not implemented for Python runtime")

    def cert_signer(self, csr):
        raise UnsupportedErr.make("certSigner not implemented for Python runtime")

    def gen_key_pair(self, algorithm, bits):
        raise UnsupportedErr.make("genKeyPair not implemented for Python runtime")

    def load_x509(self, in_stream):
        raise UnsupportedErr.make("loadX509 not implemented for Python runtime")

    def load_certs_for_uri(self, uri):
        raise UnsupportedErr.make("loadCertsForUri not implemented for Python runtime")

    def load_key_store(self, file=None, opts=None):
        raise UnsupportedErr.make("loadKeyStore not implemented for Python runtime")

    def load_pem(self, in_stream, algorithm="RSA"):
        raise UnsupportedErr.make("loadPem not implemented for Python runtime")

    def load_jwk(self, map_):
        raise UnsupportedErr.make("loadJwk not implemented for Python runtime")

    def load_jwks_for_uri(self, uri, max_keys=10):
        raise UnsupportedErr.make("loadJwksForUri not implemented for Python runtime")


class PyDigest(Obj):
    """Python implementation of crypto::Digest using hashlib"""

    # Map Fantom algorithm names to hashlib names
    _ALGO_MAP = {
        'SHA-1': 'sha1',
        'SHA1': 'sha1',
        'SHA-256': 'sha256',
        'SHA256': 'sha256',
        'SHA-384': 'sha384',
        'SHA384': 'sha384',
        'SHA-512': 'sha512',
        'SHA512': 'sha512',
        'MD5': 'md5',
    }

    def __init__(self, algorithm):
        self._algorithm = algorithm
        algo_name = self._ALGO_MAP.get(algorithm.upper(), algorithm.lower())
        try:
            self._hasher = hashlib.new(algo_name)
        except ValueError:
            raise UnsupportedErr.make(f"Unsupported digest algorithm: {algorithm}")

    def algorithm(self):
        return self._algorithm

    def digest_size(self):
        return self._hasher.digest_size

    def digest(self):
        """Complete the digest and return as Buf. Resets afterward."""
        result = self._hasher.digest()
        # Reset for next use
        algo_name = self._ALGO_MAP.get(self._algorithm.upper(), self._algorithm.lower())
        self._hasher = hashlib.new(algo_name)
        # Return as Buf
        buf = Buf.make(len(result))
        for b in result:
            buf.write(b)
        buf.flip()
        return buf

    def update(self, buf):
        """Update with all bytes from Buf"""
        # Get the raw bytes from the Buf
        data = buf.read_all_buf().to_hex()
        # Convert hex to bytes
        self._hasher.update(bytes.fromhex(data))
        return self

    def update_ascii(self, s):
        """Update with ASCII string (8-bit chars)"""
        self._hasher.update(s.encode('ascii', errors='replace'))
        return self

    def update_byte(self, i):
        """Update with one byte"""
        self._hasher.update(bytes([i & 0xFF]))
        return self

    def update_i4(self, i):
        """Update with 4-byte integer (big-endian)"""
        self._hasher.update(i.to_bytes(4, byteorder='big', signed=True))
        return self

    def update_i8(self, i):
        """Update with 8-byte integer (big-endian)"""
        self._hasher.update(i.to_bytes(8, byteorder='big', signed=True))
        return self

    def reset(self):
        """Reset the digest"""
        algo_name = self._ALGO_MAP.get(self._algorithm.upper(), self._algorithm.lower())
        self._hasher = hashlib.new(algo_name)
        return self
