"""Local GitHub Pages-like preview, including gzip and project subdirectory."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import gzip
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]/'dist'


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        prefix='/coastal-habitat'
        if urlsplit(path).path.startswith(prefix+'/'):
            path=path[len(prefix):]
        return super().translate_path(path)

    def do_GET(self):
        path=Path(self.translate_path(self.path))
        if path.is_dir():path=path/'index.html'
        if path.is_file() and 'gzip' in self.headers.get('Accept-Encoding','') and path.suffix in ('.html','.js','.css','.json','.geojson','.f32','.i16','.u8'):
            data=gzip.compress(path.read_bytes(),compresslevel=6,mtime=0)
            self.send_response(200);self.send_header('Content-Type',self.guess_type(str(path)));self.send_header('Content-Encoding','gzip');self.send_header('Vary','Accept-Encoding');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','max-age=600');self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
            return
        super().do_GET()

    def log_message(self,*args):pass


if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8765),partial(Handler,directory=str(ROOT)))
    print('Local: http://127.0.0.1:8765/coastal-habitat/',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
