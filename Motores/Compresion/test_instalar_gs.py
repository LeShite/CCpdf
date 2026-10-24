"""Mejoras extras: instalar Ghostscript bajo demanda. Sin instalar nada de verdad: la
descarga va contra un servidor local y en Linux se usan un pkexec y un apt-get falsos.
Uso: python3 test_instalar_gs.py"""
import hashlib
import http.server
import os
import stat
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Motores.Compresion import instalar_gs as I
from Motores.Compresion.pdf_compresor import ErrorCompresion, olvidar_ghostscript

DATOS = os.urandom(300_000)


def servidor():
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(DATOS)))
            self.end_headers()
            self.wfile.write(DATOS)

        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_port}/gs.exe"


def script(carpeta, nombre, cuerpo):
    ruta = os.path.join(carpeta, nombre)
    with open(ruta, "w") as f:
        f.write("#!/bin/sh\n" + cuerpo + "\n")
    os.chmod(ruta, os.stat(ruta).st_mode | stat.S_IEXEC)
    return ruta


def main() -> int:
    fallos = 0

    def check(nombre, bien, detalle=""):
        nonlocal fallos
        fallos += not bien
        print(f"  {nombre:55s} {detalle:20s} -> {'OK' if bien else 'FALLA'}")

    url = servidor()
    with tempfile.TemporaryDirectory() as tmp:
        # --- descarga: SHA-256 bueno, malo y cancelación ---
        destino = os.path.join(tmp, "gs.exe")
        I._descargar(url, destino, hashlib.sha256(DATOS).hexdigest(), lambda *a: None, None)
        check("descarga con SHA-256 correcto", open(destino, "rb").read() == DATOS)
        try:
            I._descargar(url, destino, "0" * 64, lambda *a: None, None)
            check("SHA-256 distinto: no se acepta", False)
        except ErrorCompresion:
            check("SHA-256 distinto: no se acepta", True)
        cancelado = threading.Event()
        cancelado.set()
        try:
            I._descargar(url, destino, "0" * 64, lambda *a: None, cancelado)
            check("Detener corta la descarga", False)
        except I._Cancelado:
            check("Detener corta la descarga", True)

        # --- Windows: el instalador se lanza elevado y en silencio ---
        if not sys.platform.startswith("win"):
            ejecutado = []
            orig = (I.platform.machine, I._descargar, I._ejecutar)
            I.platform.machine = lambda: "AMD64"
            I._descargar = lambda *a: None
            I._ejecutar = lambda cmd, log: ejecutado.append(cmd) or 0
            try:
                I._instalar_windows(lambda m: None, lambda *a: None, None)
            finally:
                I.platform.machine, I._descargar, I._ejecutar = orig
            orden = ejecutado[0][-1] if ejecutado else ""
            check("Windows: Start-Process -Verb RunAs con /S",
                  "-Verb RunAs" in orden and "'/S'" in orden and "-Wait" in orden)

        # --- Linux: pkexec + gestor de paquetes (falsos). El PATH solo tiene los
        # falsos, así el gs del sistema no cuenta y se simula que falta ---
        if sys.platform.startswith("linux"):
            bin_ = os.path.join(tmp, "bin")
            os.mkdir(bin_)
            path_orig = os.environ["PATH"]
            os.environ["PATH"] = bin_
            try:
                script(bin_, "apt-get", 'echo "apt-get $*"')
                script(bin_, "pkexec", "exit 126")       # el usuario cierra la ventana
                olvidar_ghostscript()
                r = I.instalar_ghostscript()
                check("Linux: cancelar la contraseña no es un error", r.cancelado)

                # pkexec "instala": ejecuta el gestor y deja un gs falso en el PATH
                script(bin_, "pkexec", f'"$@" && printf \'#!/bin/sh\\necho 10.08.0\\n\' > {bin_}/gs '
                                       f'&& /bin/chmod +x {bin_}/gs')
                olvidar_ghostscript()
                registro = []
                r = I.instalar_ghostscript(callback_log=registro.append)
                check("Linux: instala y encuentra gs",
                      r.ruta == os.path.join(bin_, "gs") and r.version == "10.08.0", f"v={r.version}")
                check("Linux: usa apt-get install -y ghostscript",
                      any("install -y ghostscript" in l for l in registro))

                os.remove(os.path.join(bin_, "apt-get"))
                os.remove(os.path.join(bin_, "gs"))
                olvidar_ghostscript()
                try:
                    I.instalar_ghostscript()
                    check("Linux: sin gestor de paquetes da un error claro", False)
                except ErrorCompresion as e:
                    check("Linux: sin gestor de paquetes da un error claro", "ghostscript" in str(e))
            finally:
                os.environ["PATH"] = path_orig
                olvidar_ghostscript()

    print("RESULTADO:", "OK" if not fallos else f"{fallos} FALLO(S)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
