#
# web::FilePack
# Python native implementation - handles missing compiler pods gracefully
#

import sys as sys_module
sys_module.path.insert(0, '.')

from typing import Optional, Callable, List as TypingList, Dict as TypingDict

from pathlib import Path

from fan import sys
from fan.sys.Obj import Obj
from fan.sys.ObjUtil import ObjUtil
from fan.web.Weblet import Weblet
from fan import concurrent
from fan import inet


# PYTHON-FANTOM: Cache for extracted asset directories
_extracted_js_dir = None
_extracted_res_dir = None

def _find_extracted_assets_dir():
    """Find the directory containing extracted JS/CSS assets.

    During transpilation, fanc py extracts JS/CSS from pods into:
      gen/py/fan/_assets/js/     - JavaScript files
      gen/py/fan/_assets/res/    - Resources (CSS, images, etc.)

    For pip-installed packages, these are at:
      {site-packages}/fan/_assets/js/
      {site-packages}/fan/_assets/res/

    This follows Python packaging best practices by keeping static assets
    co-located with the code that serves them (fan/web/FilePack.py).

    Returns tuple of (js_dir, res_dir) as Path objects, or (None, None) if not found.
    """
    global _extracted_js_dir, _extracted_res_dir

    if _extracted_js_dir is not None or _extracted_res_dir is not None:
        return (_extracted_js_dir, _extracted_res_dir)

    # Find assets relative to this module (fan/web/FilePack.py)
    # Structure: fan/web/FilePack.py -> fan/web -> fan -> fan/_assets/
    module_path = Path(__file__).resolve()
    fan_dir = module_path.parent.parent  # fan/web -> fan/
    assets_dir = fan_dir / '_assets'

    js_dir = assets_dir / 'js'
    res_dir = assets_dir / 'res'

    if js_dir.exists():
        _extracted_js_dir = js_dir
    if res_dir.exists():
        _extracted_res_dir = res_dir

    return (_extracted_js_dir, _extracted_res_dir)

class FilePack(Weblet):

  @staticmethod
  def make_files(files, mime_type=None):
    if mime_type is None:
      mime_type = None
    total_size = ObjUtil.cvar(0)
    def _closure_0(f=None):
      total_size._val = total_size._val + ObjUtil.coerce(((lambda _v: _v if _v is not None else ObjUtil.coerce(0, "sys::Int?"))(f.size())), "sys::Int")
      return

    _closure_0 = sys.Func.make_closure({"returns": "sys::Void", "immutable": "never", "params": [{"name": "f", "type": "sys::File"}]}, _closure_0)
    files.each(_closure_0)
    buf = sys.Buf.make(ObjUtil.div(total_size._val, 4))
    if mime_type is None:
      mime_type = ((lambda _v: _v if _v is not None else ObjUtil.throw_(sys.Err.make(sys.Str.plus("Ext to mimeType: ", files.first()))))(files[0].mime_type()))
    out = sys.Zip.gzip_out_stream(buf.out())
    FilePack.pack(files, out).close()
    return FilePack.make(ObjUtil.coerce(buf, "sys::Buf"), ObjUtil.coerce(mime_type, "sys::MimeType"))

  @staticmethod
  def make(buf, mime_type):
    return FilePack(buf, mime_type)

  def _make_files_body(self, files, mime_type=None):
    if mime_type is None:
      mime_type = None
    total_size = ObjUtil.cvar(0)
    def _closure_1(f=None):
      total_size._val = total_size._val + ObjUtil.coerce(((lambda _v: _v if _v is not None else ObjUtil.coerce(0, "sys::Int?"))(f.size())), "sys::Int")
      return

    _closure_1 = sys.Func.make_closure({"returns": "sys::Void", "immutable": "never", "params": [{"name": "f", "type": "sys::File"}]}, _closure_1)
    files.each(_closure_1)
    buf = sys.Buf.make(ObjUtil.div(total_size._val, 4))
    if mime_type is None:
      mime_type = ((lambda _v: _v if _v is not None else ObjUtil.throw_(sys.Err.make(sys.Str.plus("Ext to mimeType: ", files.first()))))(files[0].mime_type()))
    out = sys.Zip.gzip_out_stream(buf.out())
    FilePack.pack(files, out).close()
    return self.make(ObjUtil.coerce(buf, "sys::Buf"), ObjUtil.coerce(mime_type, "sys::MimeType"))

  def _ctor_init(self):
    self._buf = None
    self._etag = None
    self._modified = None
    self._mime_type = None
    self._uri = None
    self._uri_ref = __import__('fan.concurrent.AtomicRef', fromlist=['AtomicRef']).AtomicRef.make()
    self._uri_ref = __import__('fan.concurrent.AtomicRef', fromlist=['AtomicRef']).AtomicRef.make()
    return

  def __init__(self, buf, mime_type):
    super().__init__()
    self._buf = None
    self._etag = None
    self._modified = None
    self._mime_type = None
    self._uri = None
    self._uri_ref = __import__('fan.concurrent.AtomicRef', fromlist=['AtomicRef']).AtomicRef.make()
    self._uri_ref = __import__('fan.concurrent.AtomicRef', fromlist=['AtomicRef']).AtomicRef.make()
    buf = ObjUtil.coerce(ObjUtil.to_immutable(buf.trim()), "sys::Buf")
    self._buf = ObjUtil.coerce(ObjUtil.to_immutable(buf), "sys::Buf")
    self._etag = buf.to_digest("SHA-1").to_base64_uri()
    self._modified = sys.DateTime.now()
    self._mime_type = mime_type


  def buf(self, _val_: 'Buf' = None) -> 'Buf':
    if _val_ is None:
      return self._buf
    else:
      self._buf = _val_

  def etag(self, _val_: 'str' = None) -> 'str':
    if _val_ is None:
      return self._etag
    else:
      self._etag = _val_

  def modified(self, _val_: 'DateTime' = None) -> 'DateTime':
    if _val_ is None:
      return self._modified
    else:
      self._modified = _val_

  def mime_type(self, _val_: 'MimeType' = None) -> 'MimeType':
    if _val_ is None:
      return self._mime_type
    else:
      self._mime_type = _val_

  def uri_ref(self, _val_: 'AtomicRef' = None) -> 'AtomicRef':
    if _val_ is None:
      return self._uri_ref
    else:
      self._uri_ref = _val_

  def uri(self, _val_=None):

    if _val_ is None:
      return ObjUtil.coerce(((lambda _v: _v if _v is not None else ObjUtil.throw_(sys.Err.make("No uri configured")))(self._uri_ref.val())), "sys::Uri")
    else:
      it = _val_
      self._uri_ref.val(it)
      return

  def on_get(self) -> None:
    if self.res().is_done():
      return
    if ObjUtil.compare_ne(self.req().method(), "GET"):
      return self.res().send_err(501)
    self.res().headers()["ETag"] = self._etag
    self.res().headers()["Last-Modified"] = self._modified.to_http_str()
    if __import__('fan.web.FileWeblet', fromlist=['FileWeblet']).FileWeblet.do_check_not_modified(self.req(), self.res(), self._etag, self._modified):
      return
    self.res().status_code(200)
    self.res().headers()["Content-Encoding"] = "gzip"
    self.res().headers()["Content-Type"] = self._mime_type.to_str()
    self.res().headers()["Content-Length"] = sys.Int.to_str(self._buf.size())
    ObjUtil.coerce(self.res().out().write_buf(self._buf), "web::WebOutStream").close()
    return

  @staticmethod
  def pack(files: 'List', out: 'OutStream') -> 'OutStream':
    def _closure_2(f=None):
      FilePack.pipe_to_pack(f, out)
      return

    _closure_2 = sys.Func.make_closure({"returns": "sys::Void", "immutable": "never", "params": [{"name": "f", "type": "sys::File"}]}, _closure_2)
    files.each(_closure_2)
    return out

  @staticmethod
  def pipe_to_pack(f: 'File', out: 'OutStream') -> None:
    chunk_size = sys.Int.min_(ObjUtil.coerce(f.size(), "sys::Int"), 4096)
    if ObjUtil.equals(chunk_size, 0):
      return
    buf = sys.Buf.make(chunk_size)
    in_ = f.in_(ObjUtil.coerce(chunk_size, "sys::Int?"))
    try:
      last_is_newline = False
      while True:
        n = in_.read_buf(ObjUtil.coerce(ObjUtil.coerce(buf.clear(), "sys::Buf?"), "sys::Buf"), chunk_size)
        if n is None:
          break
        if ObjUtil.compare_gt(n, 0):
          last_is_newline = ObjUtil.equals(buf[-1], 10)
        out.write_buf(ObjUtil.coerce(ObjUtil.coerce(buf.flip(), "sys::Buf?"), "sys::Buf"), buf.remaining())
      if not last_is_newline:
        out.write_char(10)
    finally:
      in_.close()
    return

  @staticmethod
  def to_app_js_files(pods: 'List') -> 'List':
    pods = sys.Pod.flatten_depends(pods)
    pods = sys.Pod.order_by_depends(pods)
    files = FilePack.to_pod_js_files(pods)
    sys_index = ((lambda _v: _v if _v is not None else ObjUtil.throw_(sys.Err.make("Missing sys.js")))(files.find_index(sys.Func.make_closure({"returns": "sys::Bool", "immutable": "always", "params": [{"name": "f", "type": "sys::File"}]}, (lambda f=None: ObjUtil.equals(f.name(), "sys.js"))))))
    files.insert_all((ObjUtil.coerce(sys_index, "sys::Int") + 1), FilePack.to_etc_js_files())
    return files

  @staticmethod
  def to_pod_js_file(pod: 'Pod') -> 'Optional[File]':
    """Get the JavaScript file for a pod.

    PYTHON-FANTOM: First checks for extracted JS files (from fanc py),
    then falls back to reading from pod file.
    """
    pod_name = pod.name()

    # First try extracted JS directory
    js_dir, _ = _find_extracted_assets_dir()
    if js_dir is not None:
      js_path = js_dir / f'{pod_name}.js'
      if js_path.exists():
        return sys.File.make(sys.Uri.from_str(f"file:{js_path}"))

    # Fallback to pod file
    uri = (sys.Uri.from_str("/js/") if __import__('fan.web.WebJsMode', fromlist=['WebJsMode']).WebJsMode.cur().is_es() else sys.Uri.from_str("/")).plus(sys.Str.to_uri((("" + pod_name) + ".js")))
    return pod.file(uri, False)

  @staticmethod
  def to_pod_js_files(pods: 'List') -> 'List':
    """Get JavaScript files for a list of pods.

    PYTHON-FANTOM: Uses extracted JS files when available.
    """
    acc = sys.List.from_literal([], "sys::File")
    acc.capacity = pods.size

    # Check for extracted JS directory
    js_dir, _ = _find_extracted_assets_dir()

    def _closure_3(pod=None):
      pod_name = pod.name()

      # For sys pod, also include fan.js (ES6 module bootstrap)
      if ObjUtil.equals(pod_name, "sys") and __import__('fan.web.WebJsMode', fromlist=['WebJsMode']).WebJsMode.cur().is_es():
        # Try extracted fan.js first
        if js_dir is not None:
          fan_js_path = js_dir / 'fan.js'
          if fan_js_path.exists():
            acc.add(sys.File.make(sys.Uri.from_str(f"file:{fan_js_path}")))
          else:
            # Fallback to pod file
            fan_js = pod.file(sys.Uri.from_str("/js/fan.js"), False)
            if fan_js is not None:
              acc.add(ObjUtil.coerce(fan_js, "sys::File"))
        else:
          fan_js = pod.file(sys.Uri.from_str("/js/fan.js"), False)
          if fan_js is not None:
            acc.add(ObjUtil.coerce(fan_js, "sys::File"))

      # Get main pod JS file
      js = FilePack.to_pod_js_file(pod)
      if js is not None:
        acc.add(ObjUtil.coerce(js, "sys::File"))
      return

    _closure_3 = sys.Func.make_closure({"returns": "sys::Void", "immutable": "maybe", "params": [{"name": "pod", "type": "sys::Pod"}]}, _closure_3)
    pods.each(_closure_3)
    return acc

  @staticmethod
  def to_etc_js_files() -> 'List':
    return sys.List.from_literal([FilePack.to_mime_js_file(), FilePack.to_units_js_file(), FilePack.to_index_props_js_file()], "sys::File")

  @staticmethod
  def module_system() -> 'Obj':
    # PYTHON-FANTOM: compilerEs pod is not transpiled to Python
    # Return None - callers must handle this gracefully
    compiler_type = sys.Type.find("compilerEs::CommonJs", False)
    if compiler_type is None:
      return None
    return compiler_type.make(sys.List.from_literal([sys.Env.cur().temp_dir().plus(sys.Uri.from_str("file_pack/"))], "sys::File"))

  @staticmethod
  def compile_js_file(cname: 'str', fname: 'Uri', arg: 'Optional[Obj]' = None) -> 'File':
    """Compile a JavaScript file using the compiler pods.

    PYTHON-FANTOM: The compilerEs and compilerJs pods are Java-only and not
    transpiled to Python. When running in Python, we return stub JavaScript
    files that provide minimal functionality to allow the shell to load.
    """
    if arg is None:
      arg = None
    buf = sys.Buf.make(4096)

    # Check which mode we're in and try to find the compiler type
    is_es = __import__('fan.web.WebJsMode', fromlist=['WebJsMode']).WebJsMode.cur().is_es()
    compiler_qname = ("compilerEs::" + cname) if is_es else ("compilerJs::" + cname)
    compiler_type = sys.Type.find(compiler_qname, False)

    # PYTHON-FANTOM: If compiler type not found, return stub JavaScript file
    if compiler_type is None:
      # Generate minimal stub content based on the file type
      stub_content = FilePack._generate_stub_js(cname, fname)
      buf.print_(stub_content)
      return buf.to_file(fname)

    # Normal path: use the compiler to generate the JS file
    if is_es:
      module_sys = FilePack.module_system()
      if module_sys is None:
        # Fallback to stub if module system unavailable
        stub_content = FilePack._generate_stub_js(cname, fname)
        buf.print_(stub_content)
        return buf.to_file(fname)
      c = compiler_type.make(sys.List.from_literal([module_sys], "sys::Obj"))
    else:
      c = compiler_type.make()

    ObjUtil.trap(c, "write", [buf.out(), arg])
    return buf.to_file(fname)

  @staticmethod
  def _generate_stub_js(cname: 'str', fname) -> 'str':
    """Generate stub JavaScript content for when compiler pods aren't available.

    These stubs provide minimal functionality to allow the browser shell to load.
    The actual functionality (MIME types, units, indexed props) won't be available,
    but the shell will at least render.
    """
    fname_str = fname.to_str() if hasattr(fname, 'to_str') else str(fname)

    if cname == "JsExtToMime":
      # Stub MIME type initialization - empty cache init
      return """// PYTHON-FANTOM: Stub mime.js - compilerEs not available
(function () {
const __require = (m) => {
  const name = m.split('.')[0];
  const fan = this.fan;
  if (typeof require === 'undefined') return name == "fan" ? fan : fan[name];
  try { return require(`${m}`); } catch (e) { /* ignore */ }
}
const sys = __require('sys.ext');
// No MIME types loaded - stub file
}).call(this);
"""

    elif cname == "JsUnitDatabase":
      # Stub unit database - empty
      return """// PYTHON-FANTOM: Stub units.js - compilerEs not available
(function () {
const __require = (m) => {
  const name = m.split('.')[0];
  const fan = this.fan;
  if (typeof require === 'undefined') return name == "fan" ? fan : fan[name];
  try { return require(`${m}`); } catch (e) { /* ignore */ }
}
const sys = __require('sys.ext');
// No units loaded - stub file
}).call(this);
"""

    elif cname == "JsIndexedProps":
      # Stub indexed props - empty
      return """// PYTHON-FANTOM: Stub index-props.js - compilerEs not available
(function () {
const __require = (m) => {
  const name = m.split('.')[0];
  const fan = this.fan;
  if (typeof require === 'undefined') return name == "fan" ? fan : fan[name];
  try { return require(`${m}`); } catch (e) { /* ignore */ }
}
const sys = __require('sys.ext');
// No indexed props loaded - stub file
}).call(this);
"""

    elif cname == "JsProps":
      # Stub locale props
      return """// PYTHON-FANTOM: Stub locale props - compilerEs not available
(function () {
const __require = (m) => {
  const name = m.split('.')[0];
  const fan = this.fan;
  if (typeof require === 'undefined') return name == "fan" ? fan : fan[name];
  try { return require(`${m}`); } catch (e) { /* ignore */ }
}
const sys = __require('sys.ext');
// No locale props loaded - stub file
}).call(this);
"""

    else:
      # Generic stub for unknown compiler classes
      return f"""// PYTHON-FANTOM: Stub {fname_str} - compilerEs not available
(function () {{
// Stub file - compiler pods not available in Python runtime
}}).call(this);
"""

  @staticmethod
  def to_mime_js_file() -> 'File':
    return FilePack.compile_js_file("JsExtToMime", sys.Uri.from_str("mime.js"))

  @staticmethod
  def to_units_js_file() -> 'File':
    return FilePack.compile_js_file("JsUnitDatabase", sys.Uri.from_str("units.js"))

  @staticmethod
  def to_index_props_js_file(pods: 'List' = None) -> 'File':
    if pods is None:
      pods = sys.Pod.list_()
    return FilePack.compile_js_file("JsIndexedProps", sys.Uri.from_str("index-props.js"), pods)

  @staticmethod
  def to_timezones_js_file() -> 'File':
    return sys.Buf.make().to_file(sys.Uri.from_str("tz.js"))

  @staticmethod
  def to_locale_js_file(locale: 'Locale', pods: 'List' = None) -> 'File':
    """Generate locale JavaScript file.

    PYTHON-FANTOM: Falls back to stub if compiler pods unavailable.
    """
    if pods is None:
      pods = sys.Pod.list_()
    buf = sys.Buf.make(1024)
    path = sys.Str.to_uri((("locale/" + locale.to_str()) + ".props"))

    is_es = __import__('fan.web.WebJsMode', fromlist=['WebJsMode']).WebJsMode.cur().is_es()

    if is_es:
      compiler_type = sys.Type.find("compilerEs::JsProps", False)
      if compiler_type is None:
        # Return stub locale file
        stub_content = FilePack._generate_stub_js("JsProps", path)
        buf.print_(stub_content)
        return buf.to_file(sys.Str.to_uri((sys.Str.plus("", locale) + ".js")))

      module_sys = FilePack.module_system()
      if module_sys is None:
        stub_content = FilePack._generate_stub_js("JsProps", path)
        buf.print_(stub_content)
        return buf.to_file(sys.Str.to_uri((sys.Str.plus("", locale) + ".js")))

      c = compiler_type.make(sys.List.from_literal([module_sys], "sys::Obj"))
      ObjUtil.trap(c, "write", [buf.out(), path, pods])
    else:
      m = sys.Slot.find_method("compilerJs::JsProps.writeProps", False)
      if m is None:
        # Return stub locale file
        stub_content = FilePack._generate_stub_js("JsProps", path)
        buf.print_(stub_content)
        return buf.to_file(sys.Str.to_uri((sys.Str.plus("", locale) + ".js")))

      def _closure_4(pod=None):
        m.call(buf.out(), pod, path, sys.Duration.make(1000000000))
        return

      _closure_4 = sys.Func.make_closure({"returns": "sys::Void", "immutable": "maybe", "params": [{"name": "pod", "type": "sys::Pod"}]}, _closure_4)
      pods.each(_closure_4)

    return buf.to_file(sys.Str.to_uri((sys.Str.plus("", locale) + ".js")))

  @staticmethod
  def to_pod_js_map_file(files: 'List', options: 'Optional[Dict[str, Obj]]' = None) -> 'File':
    """Generate source map file.

    PYTHON-FANTOM: Falls back to empty map if compiler pods unavailable.
    """
    if options is None:
      options = None
    buf = sys.Buf.make(4194304)

    is_es = __import__('fan.web.WebJsMode', fromlist=['WebJsMode']).WebJsMode.cur().is_es()
    method_qname = "compilerEs::SourceMap.pack" if is_es else "compilerJs::SourceMap.pack"

    m = sys.Slot.find_method(method_qname, False)
    if m is None:
      # Return empty source map
      buf.print_('{"version":3,"sources":[],"mappings":""}')
      return buf.to_file(sys.Uri.from_str("js.map"))

    m.call(files, buf.out(), options)
    return buf.to_file(sys.Uri.from_str("js.map"))

  @staticmethod
  def to_app_css_files(pods: 'List') -> 'List':
    pods = sys.Pod.flatten_depends(pods)
    pods = sys.Pod.order_by_depends(pods)
    return FilePack.to_pod_css_files(pods)

  @staticmethod
  def to_pod_css_files(pods: 'List') -> 'List':
    """Get CSS files for a list of pods.

    PYTHON-FANTOM: First checks for extracted CSS files (from fanc py),
    then falls back to reading from pod file.
    """
    acc = sys.List.from_literal([], "sys::File")

    # Check for extracted resources directory
    _, res_dir = _find_extracted_assets_dir()

    def _closure_5(pod=None):
      pod_name = pod.name()

      # First try extracted CSS (in res/css/)
      if res_dir is not None:
        css_path = res_dir / 'css' / f'{pod_name}.css'
        if css_path.exists():
          acc.add(sys.File.make(sys.Uri.from_str(f"file:{css_path}")))
          return

      # Fallback to pod file (try both res/css/ and res/)
      css = pod.file(sys.Str.to_uri((("/res/css/" + pod_name) + ".css")), False)
      if css is None:
        css = pod.file(sys.Str.to_uri((("/res/" + pod_name) + ".css")), False)
      if css is not None:
        acc.add(ObjUtil.coerce(css, "sys::File"))
      return

    _closure_5 = sys.Func.make_closure({"returns": "sys::Void", "immutable": "maybe", "params": [{"name": "pod", "type": "sys::Pod"}]}, _closure_5)
    pods.each(_closure_5)
    return acc

  @staticmethod
  def main(args: 'List') -> None:
    pods = args.map_(sys.Func.make_closure({"returns": "sys::Pod", "immutable": "always", "params": [{"name": "n", "type": "sys::Str"}]}, (lambda n=None: ObjUtil.coerce(sys.Pod.find(n), "sys::Pod"))))
    FilePack.main_report(FilePack.to_app_js_files(ObjUtil.coerce(pods, "sys::Pod[]")))
    FilePack.main_report(FilePack.to_app_css_files(ObjUtil.coerce(pods, "sys::Pod[]")))
    return

  @staticmethod
  def main_report(f: 'List') -> None:
    b = FilePack.make_files(f)
    gzip = sys.Int.to_locale(b._buf.size(), "B")
    sys.Obj.echo(sys.Str.plus((((sys.Str.plus((sys.Str.plus("", f.first().ext()) + ": "), ObjUtil.coerce(f.size, "sys::Obj?")) + " files, ") + gzip) + ", "), b._mime_type))
    return


# Type metadata registration for reflection
from fan.sys.Param import Param
from fan.sys.Slot import FConst
_t = sys.Type.find('web::FilePack')
_t.tf_({}, 8194, ['web::Weblet'], None)
_t.af_('buf', 8194, 'sys::Buf', {'sys::NoDoc': {}})
_t.af_('etag', 8194, 'sys::Str', {'sys::NoDoc': {}})
_t.af_('modified', 8194, 'sys::DateTime', {'sys::NoDoc': {}})
_t.af_('mime_type', 8194, 'sys::MimeType', {'sys::NoDoc': {}})
_t.af_('uri', 8192, 'sys::Uri', {'sys::NoDoc': {}})
_t.af_('uri_ref', 2050, 'concurrent::AtomicRef', {})
_t.am_('makeFiles', 40964, 'web::FilePack?', [Param('files', sys.Type.find('sys::File[]'), False), Param('mime_type', sys.Type.find('sys::MimeType?'), True)], {})
_t.am_('make', 2052, 'sys::Void', [Param('buf', sys.Type.find('sys::Buf'), False), Param('mime_type', sys.Type.find('sys::MimeType'), False)], {})
_t.am_('onGet', 271360, 'sys::Void', [], {})
_t.am_('pack', 40960, 'sys::OutStream', [Param('files', sys.Type.find('sys::File[]'), False), Param('out', sys.Type.find('sys::OutStream'), False)], {})
_t.am_('pipeToPack', 34816, 'sys::Void', [Param('f', sys.Type.find('sys::File'), False), Param('out', sys.Type.find('sys::OutStream'), False)], {})
_t.am_('toAppJsFiles', 40960, 'sys::File[]', [Param('pods', sys.Type.find('sys::Pod[]'), False)], {})
_t.am_('toPodJsFile', 40960, 'sys::File?', [Param('pod', sys.Type.find('sys::Pod'), False)], {})
_t.am_('toPodJsFiles', 40960, 'sys::File[]', [Param('pods', sys.Type.find('sys::Pod[]'), False)], {})
_t.am_('toEtcJsFiles', 40960, 'sys::File[]', [], {})
_t.am_('moduleSystem', 40960, 'sys::Obj', [], {'sys::NoDoc': {}})
_t.am_('compileJsFile', 34816, 'sys::File', [Param('cname', sys.Type.find('sys::Str'), False), Param('fname', sys.Type.find('sys::Uri'), False), Param('arg', sys.Type.find('sys::Obj?'), True)], {})
_t.am_('toMimeJsFile', 40960, 'sys::File', [], {})
_t.am_('toUnitsJsFile', 40960, 'sys::File', [], {})
_t.am_('toIndexPropsJsFile', 40960, 'sys::File', [Param('pods', sys.Type.find('sys::Pod[]'), True)], {})
_t.am_('toTimezonesJsFile', 40960, 'sys::File', [], {'sys::Deprecated': {'msg': "tz.js is now included by default in sys.js"}})
_t.am_('toLocaleJsFile', 40960, 'sys::File', [Param('locale', sys.Type.find('sys::Locale'), False), Param('pods', sys.Type.find('sys::Pod[]'), True)], {})
_t.am_('toPodJsMapFile', 40960, 'sys::File', [Param('files', sys.Type.find('sys::File[]'), False), Param('options', sys.Type.find('[sys::Str:sys::Obj]?'), True)], {})
_t.am_('toAppCssFiles', 40960, 'sys::File[]', [Param('pods', sys.Type.find('sys::Pod[]'), False)], {})
_t.am_('toPodCssFiles', 40960, 'sys::File[]', [Param('pods', sys.Type.find('sys::Pod[]'), False)], {})
_t.am_('main', 40960, 'sys::Void', [Param('args', sys.Type.find('sys::Str[]'), False)], {'sys::NoDoc': {}})
_t.am_('mainReport', 34816, 'sys::Void', [Param('f', sys.Type.find('sys::File[]'), False)], {})


if __name__ == "__main__":
  import sys as sys_mod
  from fan.sys.List import List
  args = List.from_literal(sys_mod.argv[1:], 'sys::Str')
  exit_code = FilePack.main(args)
  sys_mod.exit(exit_code if exit_code is not None else 0)
