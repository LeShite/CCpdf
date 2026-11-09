"""
visor_pdf.py — Widget de visualización de PDF (CustomTkinter + motor propio).

Envuelve DocumentoPDF con:
  - Navegación página a página (botones + teclado ←/→/Inicio/Fin)
  - Zoom con botones y Ctrl+rueda
  - Ajustar ancho / ajustar página
  - Salto directo por número de página
  - Búsqueda de texto (resalta páginas con coincidencias)
  - Caché LRU de páginas renderizadas (no explota con PDFs grandes)
"""
import os
import queue
import threading
import tkinter as tk
from collections import OrderedDict
from tkinter import filedialog, messagebox

from PIL import ImageTk
import customtkinter as ctk

from Motores.Visualizacion import (
    DocumentoPDF, abrir_pdf, ErrorVisor,
    ZOOM_MIN, ZOOM_MAX, ZOOM_DEFAULT,
)

COLOR_FONDO       = "#0F1218"
COLOR_ACENTO      = "#3B82F6"
COLOR_TEXTO_SUAVE = "#8A94A6"

ZOOM_PASO = 1.25
CACHE_MAX = 3
INTERVALO_SONDEO_MS = 30


class _Trabajador:
    """Un hilo que atiende solo la petición más reciente (BUG-011).

    Pasar 40 páginas seguidas encola 40 peticiones, pero cada una sustituye a la
    anterior si aún no empezó: se dibuja la última, no las 40. El hilo nunca toca
    Tk: deja los resultados en la cola del visor.
    """

    def __init__(self, nombre: str):
        self._cv = threading.Condition()
        self._pendiente = None
        self._activo = True
        self._hilo = threading.Thread(target=self._bucle, name=nombre, daemon=True)
        self._hilo.start()

    def pedir(self, funcion) -> None:
        with self._cv:
            self._pendiente = funcion
            self._cv.notify()

    def detener(self) -> None:
        with self._cv:
            self._activo = False
            self._pendiente = None
            self._cv.notify()

    def _bucle(self) -> None:
        while True:
            with self._cv:
                while self._activo and self._pendiente is None:
                    self._cv.wait()
                if not self._activo:
                    return
                funcion, self._pendiente = self._pendiente, None
            try:
                funcion()
            except Exception:
                pass   # cada tarea informa de sus errores por la cola


class VisorPDF(ctk.CTkFrame):
    """Panel completo para abrir y navegar un PDF."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLOR_FONDO, corner_radius=8, **kwargs)

        self._doc: DocumentoPDF | None = None
        self._pagina = 0
        self._zoom = ZOOM_DEFAULT
        self._ajuste = "pagina"         # "pagina" | "ancho" | "libre"
        self._cache: OrderedDict = OrderedDict()
        self._img_ref = None
        self._render_gen = 0            # contador monotónico anti-race
        self._gen_busqueda = 0          # ídem para la búsqueda: cancela la anterior

        # Hilos de trabajo (uno para dibujar, otro para buscar) y la cola por la que
        # devuelven resultados. Solo el hilo de Tk lee la cola (BUG-011/BUG-018).
        self._resultados: queue.Queue = queue.Queue()
        # pypdf no es thread-safe: un acceso a la vez POR DOCUMENTO. Cada PDF abierto
        # tiene su propio lock, así el nuevo no espera a un render lento del viejo.
        self._lock_doc = threading.Lock()
        self._trab_render = _Trabajador("visor-render")
        self._trab_buscar = _Trabajador("visor-buscar")
        self._vivo = True

        self._construir_ui()
        self._actualizar_estado()
        self.bind("<Destroy>", self._al_destruir, add="+")
        self._sondeo_id = self.after(INTERVALO_SONDEO_MS, self._sondear)

    # ------------------------------------------------------------------
    # Cola de resultados (solo hilo de Tk)
    # ------------------------------------------------------------------
    def _sondear(self):
        if not self._vivo:
            return
        while True:
            try:
                accion = self._resultados.get_nowait()
            except queue.Empty:
                break
            try:
                accion()
            except Exception:
                pass
        self._sondeo_id = self.after(INTERVALO_SONDEO_MS, self._sondear)

    def _al_destruir(self, _evento=None):
        if not self._vivo:
            return
        self._vivo = False
        self._render_gen += 1
        self._gen_busqueda += 1
        self._trab_render.detener()
        self._trab_buscar.detener()
        try:
            self.after_cancel(self._sondeo_id)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _construir_ui(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(barra, text="📂 Abrir PDF…", width=130, height=28,
                      fg_color=COLOR_ACENTO, command=self._elegir_archivo
                      ).pack(side="left", padx=(0, 12))

        self.btn_prev = ctk.CTkButton(barra, text="◀", width=36, height=28,
                                      command=self.pagina_anterior)
        self.btn_prev.pack(side="left")

        self.entry_pagina = ctk.CTkEntry(barra, width=52, height=28, justify="center")
        self.entry_pagina.pack(side="left", padx=4)
        self.entry_pagina.bind("<Return>", lambda e: self._ir_a_entry())

        self.lbl_total = ctk.CTkLabel(barra, text="/ 0", text_color=COLOR_TEXTO_SUAVE)
        self.lbl_total.pack(side="left", padx=(0, 6))

        self.btn_next = ctk.CTkButton(barra, text="▶", width=36, height=28,
                                      command=self.pagina_siguiente)
        self.btn_next.pack(side="left")

        # Búsqueda
        self.entry_buscar = ctk.CTkEntry(barra, width=160, height=28,
                                         placeholder_text="Buscar en el PDF…")
        self.entry_buscar.pack(side="left", padx=(20, 4))
        self.entry_buscar.bind("<Return>", lambda e: self._buscar())

        self.btn_buscar = ctk.CTkButton(barra, text="🔎", width=36, height=28,
                                        fg_color=COLOR_ACENTO, command=self._buscar)
        self.btn_buscar.pack(side="left")

        # Zoom a la derecha
        ctk.CTkButton(barra, text="⚙ Página", width=90, height=28,
                      command=self.ajustar_pagina).pack(side="right")
        ctk.CTkButton(barra, text="↔ Ancho", width=90, height=28,
                      command=self.ajustar_ancho).pack(side="right", padx=(0, 6))
        ctk.CTkButton(barra, text="+", width=36, height=28,
                      command=lambda: self._zoom_x(ZOOM_PASO)
                      ).pack(side="right", padx=(6, 0))
        self.lbl_zoom = ctk.CTkLabel(barra, text="—", width=52,
                                     text_color=COLOR_TEXTO_SUAVE)
        self.lbl_zoom.pack(side="right", padx=4)
        ctk.CTkButton(barra, text="−", width=36, height=28,
                      command=lambda: self._zoom_x(1 / ZOOM_PASO)
                      ).pack(side="right")

        # Área del canvas
        area = ctk.CTkFrame(self, fg_color=COLOR_FONDO)
        area.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        area.grid_rowconfigure(0, weight=1)
        area.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(area, bg=COLOR_FONDO, highlightthickness=0,
                                borderwidth=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.sb_v = tk.Scrollbar(area, orient="vertical", command=self.canvas.yview)
        self.sb_v.grid(row=0, column=1, sticky="ns")
        self.sb_h = tk.Scrollbar(area, orient="horizontal", command=self.canvas.xview)
        self.sb_h.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=self.sb_v.set, xscrollcommand=self.sb_h.set)

        # Teclado
        self.canvas.configure(takefocus=True)
        self.canvas.bind("<Left>", lambda e: self.pagina_anterior())
        self.canvas.bind("<Right>", lambda e: self.pagina_siguiente())
        self.canvas.bind("<Prior>", lambda e: self.pagina_anterior())
        self.canvas.bind("<Next>", lambda e: self.pagina_siguiente())
        self.canvas.bind("<Home>", lambda e: self.ir_a(0))
        self.canvas.bind("<End>", lambda e: self.ir_a(self.num_paginas - 1))
        self.canvas.bind("<Control-plus>", lambda e: self._zoom_x(ZOOM_PASO))
        self.canvas.bind("<Control-equal>", lambda e: self._zoom_x(ZOOM_PASO))
        self.canvas.bind("<Control-minus>", lambda e: self._zoom_x(1 / ZOOM_PASO))
        self.canvas.bind("<Control-0>", lambda e: self._zoom_reset())

        # Rueda del ratón
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel_linux)
        self.canvas.bind("<Button-5>", self._on_wheel_linux)

        # Placeholder
        self._placeholder = ctk.CTkLabel(
            self.canvas,
            text="Sin PDF cargado\n\nUsa «📂 Abrir PDF…» o llama a .cargar(ruta)",
            text_color=COLOR_TEXTO_SUAVE, justify="center",
        )
        self.canvas.create_window(0, 0, window=self._placeholder, anchor="nw",
                                  tags=("placeholder",))

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    @property
    def num_paginas(self) -> int:
        return self._doc.num_paginas if self._doc else 0

    @property
    def pagina(self) -> int:
        return self._pagina

    @property
    def ruta(self) -> str:
        return self._doc.ruta if self._doc else ""

    def cargar(self, ruta: str):
        if not ruta or not os.path.isfile(ruta):
            messagebox.showwarning("Atención", "El archivo no existe.")
            return
        self.cerrar()
        try:
            self._doc = abrir_pdf(ruta)
        except ErrorVisor as e:
            messagebox.showerror("Error al abrir", str(e))
            return
        self._pagina = 0
        self._zoom = ZOOM_DEFAULT
        self._ajuste = "pagina"
        self._cache.clear()
        self.lbl_total.configure(text=f"/ {self._doc.num_paginas}")
        self._ocultar_placeholder()


        self._ajustar_y_render()

    def cerrar(self):
        self._render_gen += 1
        self._gen_busqueda += 1          # cancela la búsqueda en curso
        self._fin_busqueda()
        if self._doc is not None:
            # Se cierra en segundo plano: si hay un render en curso (con el motor
            # de respaldo puede tardar segundos), la ventana no lo espera. El
            # resultado de ese render se descarta por la generación.
            viejo, lock_viejo = self._doc, self._lock_doc

            def cerrar_viejo():
                try:
                    with lock_viejo:
                        viejo.cerrar()
                except Exception:
                    pass

            threading.Thread(target=cerrar_viejo, name="visor-cerrar", daemon=True).start()

            # Hilos nuevos para el siguiente documento: los del viejo terminan lo
            # que estén haciendo (resultado descartado) y salen. Así el PDF nuevo
            # no espera a un render lento del anterior.
            self._trab_render.detener()
            self._trab_buscar.detener()
            self._trab_render = _Trabajador("visor-render")
            self._trab_buscar = _Trabajador("visor-buscar")
        self._doc = None
        self._lock_doc = threading.Lock()
        self._cache.clear()
        self._img_ref = None
        self.canvas.delete("all")
        self._placeholder = ctk.CTkLabel(
            self.canvas,
            text="Sin PDF cargado\n\nUsa «📂 Abrir PDF…» o llama a .cargar(ruta)",
            text_color=COLOR_TEXTO_SUAVE, justify="center",
        )
        self.canvas.create_window(0, 0, window=self._placeholder, anchor="nw",
                                  tags=("placeholder",))
        self._actualizar_estado()

    def ir_a(self, indice: int):
        if self._doc is None:
            return
        indice = max(0, min(self.num_paginas - 1, indice))
        if indice == self._pagina:
            return
        self._pagina = indice
        if self._ajuste in ("pagina", "ancho"):
            self._ajustar_y_render()
        else:
            self._render()

    def pagina_siguiente(self):
        self.ir_a(self._pagina + 1)

    def pagina_anterior(self):
        self.ir_a(self._pagina - 1)

    def ajustar_pagina(self):
        self._ajuste = "pagina"
        self._ajustar_y_render()

    def ajustar_ancho(self):
        self._ajuste = "ancho"
        self._ajustar_y_render()

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------
    def _buscar(self):
        if self._doc is None:
            messagebox.showinfo("Sin PDF", "Abre un PDF antes de buscar.")
            return
        termino = self.entry_buscar.get().strip()
        if not termino:
            return

        # Extraer el texto de todas las páginas tarda con PDFs grandes: va en su
        # hilo, página a página, y se cancela si se abre otro PDF o se busca otra
        # cosa (antes el resultado viejo se aplicaba al PDF nuevo, BUG-011).
        self._gen_busqueda += 1
        gen = self._gen_busqueda
        doc, lock = self._doc, self._lock_doc
        self.btn_buscar.configure(text="⏳")

        def vigente():
            return gen == self._gen_busqueda

        def tarea():
            hits, ilegibles = [], []
            try:
                for i in range(doc.num_paginas):
                    if not vigente():
                        return
                    with lock:                    # deja dibujar entre página y página
                        if not vigente():
                            return
                        if doc.buscar(termino, pagina=i):
                            hits.append(i)
                        ilegibles.extend(doc.paginas_ilegibles)
            except ErrorVisor as e:
                msg = str(e)
                self._resultados.put(lambda: self._error_busqueda(msg, gen))
                return
            self._resultados.put(lambda: self._mostrar_resultado_busqueda(
                termino, hits, gen, doc, ilegibles))

        self._trab_buscar.pedir(tarea)

    def _fin_busqueda(self):
        try:
            self.btn_buscar.configure(text="🔎")
        except Exception:
            pass

    def _error_busqueda(self, msg: str, gen: int):
        if gen != self._gen_busqueda:
            return
        self._fin_busqueda()
        messagebox.showwarning("Búsqueda", msg)

    def _mostrar_resultado_busqueda(self, termino: str, hits: list,
                                    gen: int | None = None, doc=None,
                                    ilegibles: list | None = None):
        if gen is not None and (gen != self._gen_busqueda or doc is not self._doc):
            return   # búsqueda cancelada o de otro documento
        self._fin_busqueda()
        aviso = ""
        if ilegibles:
            aviso = ("\n\n⚠ No se pudo leer el texto de "
                     f"{len(ilegibles)} página(s): "
                     + ", ".join(str(p + 1) for p in ilegibles[:20])
                     + ("…" if len(ilegibles) > 20 else "")
                     + ". Puede que el término esté ahí.")
        if not hits:
            (messagebox.showwarning if ilegibles else messagebox.showinfo)(
                "Búsqueda", f"No se encontró «{termino}» en el documento." + aviso)
            return
        siguiente = next((p for p in hits if p >= self._pagina), hits[0])
        self.ir_a(siguiente)
        messagebox.showinfo(
            "Búsqueda",
            f"«{termino}» aparece en {len(hits)} página(s): "
            + ", ".join(str(p + 1) for p in hits[:30])
            + ("…" if len(hits) > 30 else "") + aviso)

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------
    def _zoom_x(self, factor: float):
        nuevo = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom * factor))
        if abs(nuevo - self._zoom) < 1e-3:
            return
        self._zoom = nuevo
        self._ajuste = "libre"
        self._render()

    def _zoom_reset(self):
        self._zoom = ZOOM_DEFAULT
        self._ajuste = "libre"
        self._render()

    def _ajustar_y_render(self):
        if self._doc is None:
            return
        self.update_idletasks()
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        try:
            w_pt, h_pt = self._doc.tamano_pagina(self._pagina)
        except ErrorVisor as e:
            messagebox.showerror("Error", str(e))
            return

        if self._ajuste == "ancho":
            self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, cw / w_pt))
        elif self._ajuste == "pagina":
            self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, min(cw / w_pt, ch / h_pt)))
        self._render()

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def _render(self):
        if self._doc is None:
            return

        clave = (self._pagina, round(self._zoom, 3))
        pil = self._cache.get(clave)

        if pil is not None:
            self._render_gen += 1  # invalida renders pendientes
            self._cache.move_to_end(clave)
            self._pintar(pil)
            return

        self._render_gen += 1
        gen = self._render_gen
        pagina_req = self._pagina
        zoom_req = self._zoom
        doc, lock = self._doc, self._lock_doc

        def tarea():
            if gen != self._render_gen:          # ya se pidió otra página
                return
            try:
                with lock:
                    if gen != self._render_gen:
                        return
                    img = doc.renderizar(pagina_req, zoom=zoom_req)
            except Exception as e:
                msg = str(e)
                self._resultados.put(lambda: self._error_render(msg, gen))
                return
            self._resultados.put(lambda: self._recibir_render(clave, img, gen))

        # Un solo hilo de render: si llegan varias peticiones antes de empezar,
        # solo se atiende la última.
        self._trab_render.pedir(tarea)

    def _error_render(self, msg, gen):
        if gen == self._render_gen:
            messagebox.showerror("Error de render", msg)

    def _recibir_render(self, clave, img, gen):
        # solo pinta si ningún render más reciente se lanzó
        if gen != self._render_gen:
            return
        self._cache[clave] = img
        while len(self._cache) > CACHE_MAX:
            self._cache.popitem(last=False)
        self._pintar(img)

    def _pintar(self, pil):
        self.canvas.delete("pagina")
        self._img_ref = ImageTk.PhotoImage(pil)
        self.canvas.create_image(0, 0, anchor="nw", image=self._img_ref, tags=("pagina",))
        self.canvas.configure(scrollregion=(0, 0, pil.size[0], pil.size[1]))
        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)
        self._actualizar_estado()

    def _actualizar_estado(self):
        if self._doc is None:
            self.entry_pagina.configure(state="disabled")
            self.btn_prev.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            self.lbl_total.configure(text="/ 0")
            self.lbl_zoom.configure(text="—")
            return
        self.entry_pagina.configure(state="normal")
        self.entry_pagina.delete(0, "end")
        self.entry_pagina.insert(0, str(self._pagina + 1))
        self.btn_prev.configure(state="normal" if self._pagina > 0 else "disabled")
        self.btn_next.configure(
            state="normal" if self._pagina < self.num_paginas - 1 else "disabled")
        self.lbl_zoom.configure(text=f"{int(self._zoom * 100)} %")

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def _elegir_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Abrir PDF",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")])
        if ruta:
            self.cargar(ruta)

    def _ir_a_entry(self):
        if self._doc is None:
            return
        try:
            n = int(self.entry_pagina.get().strip())
        except ValueError:
            self._actualizar_estado()
            return
        self.ir_a(n - 1)
        self.canvas.focus_set()

    def _on_wheel(self, event):
        ctrl = bool(event.state & 0x0004)
        if ctrl:
            self._zoom_x(ZOOM_PASO if event.delta > 0 else 1 / ZOOM_PASO)
        else:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _on_wheel_linux(self, event):
        ctrl = bool(event.state & 0x0004)
        arriba = (event.num == 4)
        if ctrl:
            self._zoom_x(ZOOM_PASO if arriba else 1 / ZOOM_PASO)
        else:
            self.canvas.yview_scroll(-1 if arriba else 1, "units")

    def _ocultar_placeholder(self):
        self.canvas.delete("placeholder")
