#
# Python native crypto implementation
#
# ============================================================================
# CRYPTO IMPLEMENTATION STRATEGY
# ============================================================================
#
# This module provides Python implementations of Fantom's crypto pod APIs.
# The implementation is structured in two tiers:
#
# TIER 1 - STDLIB ONLY (Current Implementation)
# ---------------------------------------------
# Using Python's standard library (hashlib, hmac, base64), we fully support:
#   - Hash digests: SHA-1, SHA-256, SHA-384, SHA-512, MD5
#   - HMAC computation
#   - Base64 encoding/decoding
#   - In-memory keystore operations (add/remove/list entries)
#
# TIER 2 - REQUIRES `cryptography` LIBRARY (Future Enhancement)
# -------------------------------------------------------------
# The following operations require the `cryptography` PyPI package and will
# raise UnsupportedErr until that dependency is added:
#   - RSA/EC key pair generation (genKeyPair)
#   - Certificate Signing Request generation (genCsr)
#   - Certificate signing (certSigner)
#   - X.509 certificate parsing (loadX509)
#   - PEM file loading (loadPem)
#   - JWK/JWKS loading (loadJwk, loadJwksForUri)
#   - PKCS12 keystore file read/write
#   - TLS certificate chain loading (loadCertsForUri)
#
# TO ADD FULL CRYPTO SUPPORT:
# ---------------------------
# 1. Add `cryptography` to pyproject.toml dependencies
# 2. Implement the Tier 2 methods using:
#    - cryptography.hazmat.primitives.asymmetric for RSA/EC
#    - cryptography.x509 for certificate handling
#    - cryptography.hazmat.primitives.serialization for PEM/PKCS12
# 3. Update the UnsupportedErr calls to actual implementations
#
# The `cryptography` library is the de-facto standard for Python crypto,
# already a transitive dependency of common packages (requests, urllib3,
# paramiko), and provides the same primitives as Java's JCE.
#
# ============================================================================

import hashlib
import hmac
import base64
from fan.sys.Obj import Obj
from fan.sys.Buf import Buf
from fan.sys.Err import UnsupportedErr


class PyCrypto(Obj):
    """Python implementation of crypto::Crypto.

    Provides cryptographic operations using Python's standard library.
    See module docstring for implementation strategy and limitations.
    """

    _instance = None

    @staticmethod
    def cur():
        """Get the current crypto service instance."""
        if PyCrypto._instance is None:
            PyCrypto._instance = PyCrypto()
        return PyCrypto._instance

    def digest(self, algorithm):
        """Get a Digest for the given algorithm.

        Fully implemented using hashlib. Supported algorithms:
        SHA-1, SHA-256, SHA-384, SHA-512, MD5

        Args:
            algorithm: Hash algorithm name

        Returns:
            PyDigest instance
        """
        return PyDigest(algorithm)

    def gen_csr(self, keys, subject_dn, opts=None):
        """Generate a Certificate Signing Request.

        REQUIRES: cryptography library (not yet implemented)

        Args:
            keys: KeyPair containing private and public keys
            subject_dn: Distinguished name for the certificate subject
            opts: Optional CSR options

        Raises:
            UnsupportedErr: Until cryptography library is added
        """
        raise UnsupportedErr.make(
            "genCsr requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable RSA/EC key operations."
        )

    def cert_signer(self, csr):
        """Get a certificate signer for the given CSR.

        REQUIRES: cryptography library (not yet implemented)

        Args:
            csr: Certificate Signing Request to sign

        Raises:
            UnsupportedErr: Until cryptography library is added
        """
        raise UnsupportedErr.make(
            "certSigner requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable certificate signing."
        )

    def gen_key_pair(self, algorithm, bits):
        """Generate a public/private key pair.

        REQUIRES: cryptography library (not yet implemented)

        Args:
            algorithm: Key algorithm (RSA, EC, etc.)
            bits: Key size in bits

        Raises:
            UnsupportedErr: Until cryptography library is added
        """
        raise UnsupportedErr.make(
            "genKeyPair requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable RSA/EC key generation."
        )

    def load_x509(self, in_stream):
        """Load an X.509 certificate from a stream.

        REQUIRES: cryptography library (not yet implemented)

        Args:
            in_stream: Input stream containing certificate data

        Raises:
            UnsupportedErr: Until cryptography library is added
        """
        raise UnsupportedErr.make(
            "loadX509 requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable X.509 certificate parsing."
        )

    def load_certs_for_uri(self, uri):
        """Load certificates for a URI (TLS certificate chain).

        REQUIRES: cryptography library (not yet implemented)

        Args:
            uri: URI to load certificates for

        Raises:
            UnsupportedErr: Until cryptography library is added
        """
        raise UnsupportedErr.make(
            "loadCertsForUri requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable TLS certificate loading."
        )

    def load_key_store(self, file=None, opts=None):
        """Load a key store.

        Returns an in-memory PyKeyStore. File-based PKCS12 keystores
        require the cryptography library - until then, this returns
        an empty in-memory keystore.

        Args:
            file: Optional file to load from (currently ignored)
            opts: Optional keystore options

        Returns:
            PyKeyStore instance (in-memory only)
        """
        return PyKeyStore(file)

    def load_pem(self, in_stream, algorithm="RSA"):
        """Load a private key from PEM format.

        REQUIRES: cryptography library (not yet implemented)

        Args:
            in_stream: Input stream containing PEM data
            algorithm: Key algorithm (default: RSA)

        Raises:
            UnsupportedErr: Until cryptography library is added
        """
        raise UnsupportedErr.make(
            "loadPem requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable PEM file loading."
        )

    def load_jwk(self, map_):
        """Load a key from JWK (JSON Web Key) format.

        REQUIRES: cryptography library (not yet implemented)

        Args:
            map_: Map containing JWK data

        Raises:
            UnsupportedErr: Until cryptography library is added
        """
        raise UnsupportedErr.make(
            "loadJwk requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable JWK loading."
        )

    def load_jwks_for_uri(self, uri, max_keys=10):
        """Load keys from a JWKS (JSON Web Key Set) URI.

        REQUIRES: cryptography library (not yet implemented)

        Args:
            uri: URI to load JWKS from
            max_keys: Maximum number of keys to load

        Raises:
            UnsupportedErr: Until cryptography library is added
        """
        raise UnsupportedErr.make(
            "loadJwksForUri requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable JWKS loading."
        )


class PyDigest(Obj):
    """Python implementation of crypto::Digest using hashlib.

    Fully implemented - no additional dependencies required.
    """

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
        """Create a digest for the given algorithm.

        Args:
            algorithm: Hash algorithm name (SHA-256, SHA-512, MD5, etc.)

        Raises:
            UnsupportedErr: If the algorithm is not supported
        """
        self._algorithm = algorithm
        algo_name = self._ALGO_MAP.get(algorithm.upper(), algorithm.lower())
        try:
            self._hasher = hashlib.new(algo_name)
        except ValueError:
            raise UnsupportedErr.make(f"Unsupported digest algorithm: {algorithm}")

    def algorithm(self):
        """Get the algorithm name."""
        return self._algorithm

    def digest_size(self):
        """Get the digest size in bytes."""
        return self._hasher.digest_size

    def digest(self):
        """Complete the digest and return as Buf.

        Resets the digest state afterward for reuse.

        Returns:
            Buf containing the digest bytes
        """
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
        """Update with all bytes from Buf.

        Args:
            buf: Buf containing bytes to hash

        Returns:
            self for chaining
        """
        # Get the raw bytes from the Buf
        data = buf.read_all_buf().to_hex()
        # Convert hex to bytes
        self._hasher.update(bytes.fromhex(data))
        return self

    def update_ascii(self, s):
        """Update with ASCII string (8-bit chars).

        Args:
            s: String to hash

        Returns:
            self for chaining
        """
        self._hasher.update(s.encode('ascii', errors='replace'))
        return self

    def update_byte(self, i):
        """Update with one byte.

        Args:
            i: Byte value (0-255)

        Returns:
            self for chaining
        """
        self._hasher.update(bytes([i & 0xFF]))
        return self

    def update_i4(self, i):
        """Update with 4-byte integer (big-endian).

        Args:
            i: 32-bit integer

        Returns:
            self for chaining
        """
        self._hasher.update(i.to_bytes(4, byteorder='big', signed=True))
        return self

    def update_i8(self, i):
        """Update with 8-byte integer (big-endian).

        Args:
            i: 64-bit integer

        Returns:
            self for chaining
        """
        self._hasher.update(i.to_bytes(8, byteorder='big', signed=True))
        return self

    def reset(self):
        """Reset the digest state.

        Returns:
            self for chaining
        """
        algo_name = self._ALGO_MAP.get(self._algorithm.upper(), self._algorithm.lower())
        self._hasher = hashlib.new(algo_name)
        return self


class PyKeyStore(Obj):
    """Python implementation of crypto::KeyStore.

    This is a fully functional in-memory keystore. All operations for
    adding, removing, and querying entries are implemented.

    LIMITATION: PKCS12 file persistence requires the cryptography library.
    Until that dependency is added, keystores are in-memory only and do
    not persist across restarts.

    TO ADD FILE PERSISTENCE:
    - Add cryptography library dependency
    - Implement _load_from_file() using cryptography.hazmat.primitives.serialization
    - Implement save() to write PKCS12 format
    """

    def __init__(self, file=None):
        """Create a new keystore.

        Args:
            file: Optional file to load from (currently not supported)
        """
        super().__init__()
        self._file = file
        self._entries = {}  # alias -> KeyStoreEntry (case-insensitive by lookup)
        self._format = "PyKeyStore"

        # Note: File loading requires cryptography library
        # If file is provided and exists, log a warning
        if file is not None and hasattr(file, 'exists') and file.exists():
            import sys
            print(
                f"[crypto] Warning: Cannot load keystore from {file} - "
                "PKCS12 parsing requires the 'cryptography' library",
                file=sys.stderr
            )

    def format(self):
        """Get the format that this keystore stores entries in."""
        return self._format

    def aliases(self):
        """Get all the aliases in the key store."""
        from fan.sys.List import List
        return List.from_literal(list(self._entries.keys()), "sys::Str")

    def size(self):
        """Get the number of entries in the key store."""
        return len(self._entries)

    def save(self, out, options=None):
        """Save the entries in the keystore to the output stream.

        LIMITATION: PKCS12 serialization requires cryptography library.
        Currently a no-op that logs a warning.

        Args:
            out: Output stream to write to
            options: Save options
        """
        import sys
        print(
            "[crypto] Warning: KeyStore.save() is a no-op - "
            "PKCS12 serialization requires the 'cryptography' library",
            file=sys.stderr
        )

    def get(self, alias, checked=True):
        """Get the entry with the given alias.

        Lookup is case-insensitive per the Fantom KeyStore contract.

        Args:
            alias: Entry alias to look up
            checked: If True, throw error if not found

        Returns:
            KeyStoreEntry or None
        """
        from fan.sys.Err import Err
        # Case-insensitive lookup
        alias_lower = alias.lower()
        for key, value in self._entries.items():
            if key.lower() == alias_lower:
                return value
        if checked:
            raise Err.make(f"KeyStore entry not found: {alias}")
        return None

    def get_trust(self, alias, checked=True):
        """Convenience to get a TrustEntry from the keystore."""
        return self.get(alias, checked)

    def get_priv_key(self, alias, checked=True):
        """Convenience to get a PrivKeyEntry from the keystore."""
        return self.get(alias, checked)

    def contains_alias(self, alias):
        """Return true if the key store has an entry with the given alias."""
        return self.get(alias, False) is not None

    def set_priv_key(self, alias, priv, chain):
        """Adds a PrivKeyEntry to the keystore with the given alias.

        Args:
            alias: Entry alias
            priv: Private key
            chain: Certificate chain

        Returns:
            self for chaining
        """
        entry = PyPrivKeyEntry(priv, chain)
        self._entries[alias] = entry
        return self

    def set_trust(self, alias, cert):
        """Adds a TrustEntry to the keystore with the given alias.

        Args:
            alias: Entry alias
            cert: Trusted certificate

        Returns:
            self for chaining
        """
        entry = PyTrustEntry(cert)
        self._entries[alias] = entry
        return self

    def set_(self, alias, entry):
        """Set an alias to have the given entry.

        Args:
            alias: Entry alias
            entry: KeyStoreEntry to set

        Returns:
            self for chaining
        """
        self._entries[alias] = entry
        return self

    def remove(self, alias):
        """Remove the entry with the given alias.

        Args:
            alias: Entry alias to remove
        """
        alias_lower = alias.lower()
        for key in list(self._entries.keys()):
            if key.lower() == alias_lower:
                del self._entries[key]
                return


class PyKeyStoreEntry(Obj):
    """Base class for keystore entries.

    Implements the KeyStoreEntry mixin from crypto pod.
    """

    def __init__(self):
        super().__init__()
        self._attrs = {}

    def attrs(self):
        """Get the attributes associated with this entry.

        Returns:
            Immutable Map[Str,Str] of attributes
        """
        from fan.sys.Map import Map
        m = Map.make_with_type("sys::Str", "sys::Str")
        for k, v in self._attrs.items():
            m.set_(k, v)
        return m.to_immutable()


class PyPrivKeyEntry(PyKeyStoreEntry):
    """A PrivKeyEntry stores a private key and certificate chain.

    Implements the PrivKeyEntry mixin from crypto pod.
    """

    def __init__(self, priv_key, cert_chain):
        """Create a private key entry.

        Args:
            priv_key: Private key
            cert_chain: List of certificates (end entity first)
        """
        super().__init__()
        self._priv = priv_key
        self._chain = cert_chain

    def priv(self):
        """Get the private key from this entry."""
        return self._priv

    def cert_chain(self):
        """Get the certificate chain from this entry."""
        return self._chain

    def cert(self):
        """Get the end entity certificate (first in chain)."""
        if self._chain and len(self._chain) > 0:
            return self._chain[0]
        return None

    def pub(self):
        """Get the public key from the certificate."""
        cert = self.cert()
        if cert:
            return cert.pub()
        return None

    def key_pair(self):
        """Get the KeyPair for the entry.

        REQUIRES: cryptography library for full implementation.
        """
        raise UnsupportedErr.make(
            "KeyPair requires the 'cryptography' library. "
            "Add 'cryptography' to dependencies to enable key pair operations."
        )


class PyTrustEntry(PyKeyStoreEntry):
    """Keystore entry for a trusted certificate.

    Implements the TrustEntry mixin from crypto pod.
    """

    def __init__(self, cert):
        """Create a trust entry.

        Args:
            cert: Trusted certificate
        """
        super().__init__()
        self._cert = cert

    def cert(self):
        """Get the trusted certificate from this entry."""
        return self._cert
