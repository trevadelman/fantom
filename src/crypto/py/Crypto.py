#
# crypto::Crypto
# Hand-written Python native to use PyCrypto instead of NilCrypto
#

import sys as sys_module
sys_module.path.insert(0, '.')

from fan.sys.Obj import Obj
from fan.sys.ObjUtil import ObjUtil
from fan.sys import Bool
from fan.sys.Num import Num
from fan.sys.Int import Int
from fan.sys.Float import Float
from fan.sys.Str import Str
from fan.sys.Range import Range
from fan.sys.Map import Map
from fan.sys.List import List
from fan.sys.Duration import Duration
from fan.sys.Locale import Locale
from fan.sys.StrBuf import StrBuf
from fan.sys.Type import Type
from fan.sys.Pod import Pod
from fan.sys.Slot import Slot
from fan.sys.Method import Method
from fan.sys.Field import Field
from fan.sys.Func import Func
from fan.sys.Env import Env
from fan.sys.Unsafe import Unsafe, make
from fan.sys.Err import Err, ParseErr, NullErr, CastErr, ArgErr, IndexErr, UnsupportedErr, UnknownTypeErr, UnknownPodErr, UnknownSlotErr, UnknownServiceErr, ReadonlyErr, IOErr, NotImmutableErr, CancelledErr, ConstErr, InterruptedErr, NameErr, TimeoutErr, TestErr, ReturnErr, NotFilterErr, UnknownNameErr, UnknownKeyErr, UnresolvedErr
from fan.sys.Buf import Buf
from fan.sys.File import File
from fan.sys.Zip import Zip
from fan.sys.Process import Process
from fan.sys.Service import Service
from fan.sys.Regex import Regex, RegexMatcher
from fan.sys.Uri import Uri, UriScheme
from fan.sys.Unit import Unit
from fan.sys.MimeType import MimeType
from fan.sys.Charset import Charset
from fan.sys.Log import Log, LogLevel, LogRec
from fan.sys.Version import Version
from fan.sys.Weekday import Weekday
from fan.sys.TimeZone import TimeZone
from fan.sys.DateTime import DateTime, Month, Date, Time
from fan.sys.Uuid import Uuid
from fan.sys.Depend import Depend
from fan.sys.Decimal import Decimal
from fan.sys.Endian import Endian
from fan.sys.Enum import Enum
from fan.sys.Facet import Facet
from fan.sys.OutStream import OutStream

class Crypto(Obj):

  _cur = None

  @staticmethod
  def cur():
    if Crypto._cur is None:
      Crypto._static_init()
      if Crypto._cur is None:
        Crypto._cur = None
    return Crypto._cur

  @staticmethod
  def _static_init():
    if hasattr(Crypto, '_static_init_in_progress') and Crypto._static_init_in_progress:
      return
    Crypto._static_init_in_progress = True
    if True:
      try:
        runtime = Env.cur().runtime()
        if runtime == "java":
          Crypto._cur = ObjUtil.coerce(Type.find("cryptoJava::JCrypto").make(), "crypto::Crypto")
        elif runtime == "py":
          # PYTHON-FANTOM: Use PyCrypto for Python runtime
          from fan.crypto.PyCrypto import PyCrypto
          Crypto._cur = PyCrypto.cur()
        else:
          Crypto._cur = ObjUtil.coerce(__import__('fan.crypto.NilCrypto', fromlist=['NilCrypto']).NilCrypto.make(), "crypto::Crypto")
      except Err as err:
        err.trace()
        raise err
    Crypto._static_init_in_progress = False

  @staticmethod
  def make():
    return Crypto()

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)


  def load_certs_for_uri(self, uri):
    raise UnsupportedErr.make()


# Type metadata registration for reflection
from fan.sys.Param import Param
from fan.sys.Slot import FConst
_t = Type.find('crypto::Crypto')
_t.tf_({}, 140289, [], None)
_t.af_('cur', 10241, 'crypto::Crypto', {})
_t.am_('digest', 5121, 'crypto::Digest', [Param('algorithm', Type.find('sys::Str'), False)], {})
_t.am_('gen_csr', 5121, 'crypto::Csr', [Param('keys', Type.find('crypto::KeyPair'), False), Param('subject_dn', Type.find('sys::Str'), False), Param('opts', Type.find('[sys::Str:sys::Obj]'), True)], {})
_t.am_('cert_signer', 5121, 'crypto::CertSigner', [Param('csr', Type.find('crypto::Csr'), False)], {})
_t.am_('gen_key_pair', 5121, 'crypto::KeyPair', [Param('algorithm', Type.find('sys::Str'), False), Param('bits', Type.find('sys::Int'), False)], {})
_t.am_('load_x509', 5121, 'crypto::Cert[]', [Param('in_', Type.find('sys::InStream'), False)], {})
_t.am_('load_certs_for_uri', 4097, 'crypto::Cert[]', [Param('uri', Type.find('sys::Uri'), False)], {})
_t.am_('load_key_store', 5121, 'crypto::KeyStore', [Param('file', Type.find('sys::File?'), True), Param('opts', Type.find('[sys::Str:sys::Obj]'), True)], {})
_t.am_('load_pem', 5121, 'sys::Obj?', [Param('in_', Type.find('sys::InStream'), False), Param('algorithm', Type.find('sys::Str'), True)], {})
_t.am_('load_jwk', 5121, 'crypto::Jwk?', [Param('map_', Type.find('[sys::Str:sys::Obj]'), False)], {})
_t.am_('load_jwks_for_uri', 5121, 'crypto::Jwk[]', [Param('uri', Type.find('sys::Uri'), False), Param('max_keys', Type.find('sys::Int'), True)], {})
