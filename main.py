import os
import tempfile
import tkinter as tk
from tkinter import filedialog, simpledialog
from PIL import Image, ImageGrab, ImageTk
import customtkinter as ctk

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class MediaPlayerLogic:
    def __init__(self, root):
        self.root = root
        self.playlist = []
        self.current_index = -1
        self.is_dragging = False
        self.photo_playlist = []
        self.current_p_index = -1
        self.is_slideshow_running = False
        self.zoom_scale = 1.0

    def init_heavy_components(self):
        """Carga VLC diferida para que la ventana aparezca de inmediato."""
        global vlc
        import vlc
        self.vlc_instance = vlc.Instance(["--avcodec-hw=any"])
        self.player = self.vlc_instance.media_player_new()

        self.root.update_idletasks()
        if os.name == "nt" and hasattr(self, "video_frame"):
            try:
                self.player.set_hwnd(self.video_frame.winfo_id())
            except Exception:
                pass

        self.update_timer()
        self.slideshow_timer()

    def update_timer(self):
        if hasattr(self, "player") and self.player.is_playing() and not self.is_dragging:
            total = self.player.get_length()
            if total > 0:
                self.seek_bar.set((self.player.get_time() / total) * 100)
        self.root.after(1000, self.update_timer)

    def set_dragging(self, v):
        self.is_dragging = v

    def on_seek(self, v):
        if self.is_dragging and hasattr(self, "player"):
            total = self.player.get_length()
            if total > 0:
                self.player.set_time(int((float(v) / 100) * total))

    def load_videos(self):
        files = filedialog.askopenfilenames(filetypes=[("Vídeos", "*.mp4 *.avi *.mkv")])
        for f in files:
            if f not in self.playlist:
                self.playlist.append(f)
                self.v_listbox.insert(tk.END, os.path.basename(f))

    def play_index(self, idx):
        if 0 <= idx < len(self.playlist) and hasattr(self, "player"):
            self.current_index = idx
            path = self.playlist[idx]
            self.player.set_media(self.vlc_instance.media_new(path))
            self.player.play()
            self.v_listbox.selection_clear(0, tk.END)
            self.v_listbox.selection_set(idx)
            self.v_listbox.see(idx)
            self.update_file_details(path, "video")

    def play_selected_event(self, e=None):
        sel = self.v_listbox.curselection()
        if sel and sel[0] != self.current_index:
            self.play_index(sel[0])

    def next_video(self):
        if self.playlist:
            self.play_index((self.current_index + 1) % len(self.playlist))

    def prev_video(self):
        if self.playlist:
            self.play_index((self.current_index - 1) % len(self.playlist))

    def adjust_volume(self, delta):
        if hasattr(self, "player"):
            self.player.audio_set_volume(max(0, min(100, self.player.audio_get_volume() + delta)))

    def play_video(self):
        if hasattr(self, "player"):
            if self.player.get_state() == vlc.State.Paused:
                self.player.play()
            elif self.current_index != -1:
                self.play_index(self.current_index)

    def pause_video(self):
        if hasattr(self, "player"):
            self.player.pause()

    def load_photos(self):
        files = filedialog.askopenfilenames(filetypes=[("Imágenes", "*.jpg *.png *.jpeg *.bmp")])
        for f in files:
            if f not in self.photo_playlist:
                self.photo_playlist.append(f)
                self.p_listbox.insert(tk.END, os.path.basename(f))

    def show_photo_selected(self):
        sel = self.p_listbox.curselection()
        if sel:
            self.show_photo(sel[0])

    def show_photo(self, idx):
        if 0 <= idx < len(self.photo_playlist):
            self.current_p_index = idx
            path = self.photo_playlist[idx]
            self.original_img = Image.open(path)
            self.canvas.update_idletasks()
            cw, ch = max(500, self.canvas.winfo_width()), max(320, self.canvas.winfo_height())
            base_img = self.original_img.copy()
            base_img.thumbnail((cw, ch))
            self.base_w, self.base_h = base_img.size
            self.zoom_scale = 1.0
            self.update_zoomed_image()
            self.p_listbox.selection_clear(0, tk.END)
            self.p_listbox.selection_set(idx)
            self.p_listbox.see(idx)
            self.update_file_details(path, "photo")

    def zoom_image(self, e):
        if hasattr(self, "original_img"):
            if (hasattr(e, "delta") and e.delta > 0) or (hasattr(e, "num") and e.num == 4):
                self.adjust_zoom_by(1.15)
            elif (hasattr(e, "delta") and e.delta < 0) or (hasattr(e, "num") and e.num == 5):
                self.adjust_zoom_by(1 / 1.15)

    def adjust_zoom_by(self, factor):
        if hasattr(self, "original_img"):
            self.zoom_scale = max(0.2, self.zoom_scale * factor)
            self.update_zoomed_image()

    def update_zoomed_image(self):
        if hasattr(self, "original_img"):
            nw, nh = int(self.base_w * self.zoom_scale), int(self.base_h * self.zoom_scale)
            if nw >= 10 and nh >= 10:
                self.tk_img = ImageTk.PhotoImage(
                    self.original_img.resize((nw, nh), Image.Resampling.LANCZOS)
                )
                self.canvas.delete("photo")
                cw, ch = max(500, self.canvas.winfo_width()), max(320, self.canvas.winfo_height())
                self.canvas.create_image(
                    cw // 2, ch // 2, image=self.tk_img, anchor=tk.CENTER, tags="photo"
                )

    def next_photo(self):
        if self.photo_playlist:
            self.show_photo((self.current_p_index + 1) % len(self.photo_playlist))

    def prev_photo(self):
        if self.photo_playlist:
            self.show_photo((self.current_p_index - 1) % len(self.photo_playlist))

    def toggle_slideshow(self):
        self.is_slideshow_running = not self.is_slideshow_running
        self.btn_slide.configure(
            text="⏸ Pausa" if self.is_slideshow_running else "▶ Slideshow"
        )

    def slideshow_timer(self):
        if self.is_slideshow_running and self.photo_playlist:
            self.next_photo()
        self.root.after(3000, self.slideshow_timer)

    def toggle_fullscreen(self):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def show_video_list_context_menu(self, event):
        try:
            index = self.v_listbox.nearest(event.y)
            if index >= 0:
                self.v_listbox.selection_clear(0, tk.END)
                self.v_listbox.selection_set(index)
                self.v_listbox.see(index)
                self.play_selected_event()
                self.video_list_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.video_list_context_menu.grab_release()

    def rename_selected_video(self):
        sel = self.v_listbox.curselection()
        if not sel: return
        idx = sel[0]
        old_path = self.playlist[idx]
        dir_name, file_name = os.path.split(old_path)
        name_only, ext = os.path.splitext(file_name)
        new_name = simpledialog.askstring("Cambiar Nombre", "Ingrese el nuevo nombre:", initialvalue=name_only, parent=self.root)
        if new_name:
            new_filename = new_name.strip() + ext
            new_path = os.path.join(dir_name, new_filename)
            try:
                if idx == self.current_index and hasattr(self, "player"):
                    self.player.stop()
                os.rename(old_path, new_path)
                self.playlist[idx] = new_path
                self.v_listbox.delete(idx)
                self.v_listbox.insert(idx, new_filename)
                self.v_listbox.selection_set(idx)
                if idx == self.current_index: self.play_index(idx)
                else: self.update_file_details(new_path, "video")
            except Exception as e:
                print(f"Error al renombrar: {e}")

    def show_list_context_menu(self, event):
        try:
            index = self.p_listbox.nearest(event.y)
            if index >= 0:
                self.p_listbox.selection_clear(0, tk.END)
                self.p_listbox.selection_set(index)
                self.p_listbox.see(index)
                self.show_photo_selected()
                self.list_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.list_context_menu.grab_release()

    def rename_selected_photo(self):
        sel = self.p_listbox.curselection()
        if not sel: return
        idx = sel[0]
        old_path = self.photo_playlist[idx]
        dir_name, file_name = os.path.split(old_path)
        name_only, ext = os.path.splitext(file_name)
        new_name = simpledialog.askstring("Cambiar Nombre", "Ingrese el nuevo nombre:", initialvalue=name_only, parent=self.root)
        if new_name:
            new_filename = new_name.strip() + ext
            new_path = os.path.join(dir_name, new_filename)
            try:
                os.rename(old_path, new_path)
                self.photo_playlist[idx] = new_path
                self.p_listbox.delete(idx)
                self.p_listbox.insert(idx, new_filename)
                self.p_listbox.selection_set(idx)
                if idx == self.current_p_index: self.show_photo(idx)
            except Exception as e:
                print(f"Error al renombrar foto: {e}")

    def start_pan(self, e):
        self.pan_start_x, self.pan_start_y = e.x, e.y

    def do_pan(self, e):
        dx, dy = e.x - self.pan_start_x, e.y - self.pan_start_y
        self.pan_start_x, self.pan_start_y = e.x, e.y
        self.canvas.move("photo", dx, dy)

    def show_context_menu(self, e):
        try:
            self.context_menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_photo(self):
        if 0 <= self.current_p_index < len(self.photo_playlist):
            self.root.clipboard_clear()
            self.root.clipboard_append(self.photo_playlist[self.current_p_index])

    def paste_photo(self):
        try:
            cb = ImageGrab.grabclipboard()
            if isinstance(cb, list):
                for f in cb:
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp", ".heic")) and f not in self.photo_playlist:
                        self.photo_playlist.append(f)
                        self.p_listbox.insert(tk.END, os.path.basename(f))
                if cb: self.show_photo(len(self.photo_playlist) - 1)
            elif isinstance(cb, Image.Image):
                tp = os.path.join(tempfile.gettempdir(), "clipboard_img.png")
                cb.save(tp, "PNG")
                if tp not in self.photo_playlist:
                    self.photo_playlist.append(tp)
                    self.p_listbox.insert(tk.END, "Clipboard.png")
                self.show_photo(len(self.photo_playlist) - 1)
            else:
                text = self.root.clipboard_get()
                if os.path.isfile(text) and text.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp", ".heic")) and text not in self.photo_playlist:
                    self.photo_playlist.append(text)
                    self.p_listbox.insert(tk.END, os.path.basename(text))
                    self.show_photo(len(self.photo_playlist) - 1)
        except Exception as e:
            print(f"Error al pegar imagen: {e}")


class MediaApp(MediaPlayerLogic):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.root.title("Reproductor Multimedia Universal")
        self.root.geometry("880x530")

        self.root.update_idletasks()

        # 1. BARRA SUPERIOR
        top_bar = ctk.CTkFrame(self.root, fg_color="transparent")
        top_bar.pack(side="top", fill="x", padx=10, pady=5)

        self.lbl_details = ctk.CTkLabel(
            top_bar, text="📁 Ningún archivo seleccionado", font=("Arial", 12, "bold")
        )
        self.lbl_details.pack(side="left", padx=5)

        self.theme_menu = ctk.CTkOptionMenu(
            top_bar, values=["System", "Dark", "Light"], command=self.change_theme_mode, width=110
        )
        self.theme_menu.set("System")
        self.theme_menu.pack(side="right", padx=5)

        lbl_theme = ctk.CTkLabel(top_bar, text="🎨 Tema:")
        lbl_theme.pack(side="right", padx=2)

        # 2. CONTENEDOR PRINCIPAL
        content_area = ctk.CTkFrame(self.root, fg_color="transparent")
        content_area.pack(fill="both", expand=True, padx=5, pady=0)

        # PANEL IZQUIERDO
        self.left_sidebar = ctk.CTkFrame(content_area)
        self.left_sidebar.pack(side="left", fill="y", padx=5, pady=5)

        self.view_switcher = ctk.CTkSegmentedButton(
            self.left_sidebar, values=["🎬 Vídeos", "🖼️ Fotos"], command=self.switch_view
        )
        self.view_switcher.set("🎬 Vídeos")
        self.view_switcher.pack(fill="x", padx=10, pady=(10, 5))

        self.sidebar_dynamic = ctk.CTkFrame(self.left_sidebar, fg_color="transparent")
        self.sidebar_dynamic.pack(fill="both", expand=True)
        self.sidebar_dynamic.grid_rowconfigure(0, weight=1)
        self.sidebar_dynamic.grid_columnconfigure(0, weight=1)

        self.video_sidebar = ctk.CTkFrame(self.sidebar_dynamic, fg_color="transparent")
        self.video_sidebar.grid(row=0, column=0, sticky="nsew")

        self.photo_sidebar = ctk.CTkFrame(self.sidebar_dynamic, fg_color="transparent")
        self.photo_sidebar.grid(row=0, column=0, sticky="nsew")

        # PANEL DERECHO
        self.right_main = ctk.CTkFrame(content_area, fg_color="transparent")
        self.right_main.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        self.right_main.grid_rowconfigure(0, weight=1)
        self.right_main.grid_columnconfigure(0, weight=1)

        self.video_right = ctk.CTkFrame(self.right_main, fg_color="transparent")
        self.video_right.grid(row=0, column=0, sticky="nsew")

        self.photo_right = ctk.CTkFrame(self.right_main, fg_color="transparent")
        self.photo_right.grid(row=0, column=0, sticky="nsew")

        # Construcción de la interfaz
        self.build_video_ui(self.video_sidebar)
        self.build_video_controls(self.video_right)
        self.build_photo_ui(self.photo_sidebar)
        self.build_photo_controls(self.photo_right)

        self.update_listbox_colors(ctk.get_appearance_mode())
        self.switch_view("🎬 Vídeos")

        # Arranque diferido súper rápido de componentes pesados (VLC)
        self.root.after(5, self.init_heavy_components)

    def build_video_ui(self, parent_frame):
        btn_load = ctk.CTkButton(
            parent_frame, text="📂 Cargar Vídeos", command=self.load_videos
        )
        btn_load.pack(side="top", fill="x", padx=10, pady=(10, 5))

        self.v_listbox = tk.Listbox(
            parent_frame, width=32, selectmode=tk.SINGLE
        )
        self.v_listbox.pack(
            side="top", fill="both", expand=True, padx=10, pady=(0, 10)
        )
        self.v_listbox.bind("<<ListboxSelect>>", self.play_selected_event)

        self.video_list_context_menu = tk.Menu(self.root, tearoff=0)
        self.video_list_context_menu.add_command(
            label="✏️ Cambiar Nombre", command=self.rename_selected_video
        )
        self.v_listbox.bind("<Button-3>", self.show_video_list_context_menu)
        self.v_listbox.bind("<Button-2>", self.show_video_list_context_menu)

    def build_video_controls(self, parent_frame):
        self.video_frame = tk.Frame(parent_frame, bg="black")
        self.video_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.seek_bar = ctk.CTkSlider(
            parent_frame, from_=0, to=100, command=self.on_seek
        )
        self.seek_bar.set(0)
        self.seek_bar.pack(fill="x", padx=5, pady=5)
        self.seek_bar.bind("<ButtonPress-1>", lambda event: self.set_dragging(True))
        self.seek_bar.bind(
            "<ButtonRelease-1>", lambda event: self.set_dragging(False)
        )

        controls_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        controls_frame.pack(fill="x", pady=5)

        ctk.CTkButton(
            controls_frame, text="⏮", width=40, command=self.prev_video
        ).pack(side="left", padx=2)
        self.btn_play = ctk.CTkButton(
            controls_frame,
            text="▶ Play",
            width=80,
            hover_color="#e74c3c",
            command=self.play_video,
        )
        self.btn_play.pack(side="left", padx=2)
        ctk.CTkButton(
            controls_frame, text="⏸ Pausa", width=80, command=self.pause_video
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            controls_frame, text="⏭", width=40, command=self.next_video
        ).pack(side="left", padx=2)

        ctk.CTkLabel(controls_frame, text=" 🔊").pack(side="left", padx=2)
        ctk.CTkButton(
            controls_frame,
            text="🔉 -",
            width=50,
            command=lambda: self.adjust_volume(-10),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            controls_frame,
            text="🔊 +",
            width=50,
            command=lambda: self.adjust_volume(10),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            controls_frame,
            text="⛶ Maximizar",
            width=100,
            command=self.toggle_fullscreen,
        ).pack(side="right", padx=3)

    def build_photo_ui(self, parent_frame):
        btn_load_p = ctk.CTkButton(
            parent_frame, text="🖼️ Cargar Fotos", command=self.load_photos
        )
        btn_load_p.pack(side="top", fill="x", padx=10, pady=(10, 5))

        self.p_listbox = tk.Listbox(
            parent_frame, width=32, selectmode=tk.SINGLE
        )
        self.p_listbox.pack(
            side="top", fill="both", expand=True, padx=10, pady=(0, 10)
        )

        def delayed_select(e):
            self.root.after(10, self.show_photo_selected)

        for ev in ["<<ListboxSelect>>", "<Up>", "<Down>", "<MouseWheel>", "<Button-4>", "<Button-5>"]:
            self.p_listbox.bind(ev, delayed_select)

        self.list_context_menu = tk.Menu(self.root, tearoff=0)
        self.list_context_menu.add_command(
            label="✏️ Cambiar Nombre", command=self.rename_selected_photo
        )
        self.p_listbox.bind("<Button-3>", self.show_list_context_menu)
        self.p_listbox.bind("<Button-2>", self.show_list_context_menu)

    def build_photo_controls(self, parent_frame):
        self.canvas = tk.Canvas(parent_frame, bg="black", cursor="hand2")
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="⏭ Siguiente Foto", command=self.next_photo)
        self.context_menu.add_command(label="⏮ Anterior Foto", command=self.prev_photo)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copiar Ruta", command=self.copy_photo)
        self.context_menu.add_command(label="📋 Pegar Imagen", command=self.paste_photo)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔍 Zoom +", command=lambda: self.adjust_zoom_by(1.15))
        self.context_menu.add_command(label="🔍 Zoom -", command=lambda: self.adjust_zoom_by(1 / 1.15))

        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.do_pan)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<Button-2>", self.show_context_menu)
        self.canvas.bind("<MouseWheel>", self.zoom_image)
        self.canvas.bind("<Button-4>", self.zoom_image)
        self.canvas.bind("<Button-5>", self.zoom_image)

        p_controls_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        p_controls_frame.pack(fill="x", pady=5)

        ctk.CTkButton(
            p_controls_frame, text="⏮ Anterior", command=self.prev_photo, hover_color="#2980b9"
        ).pack(side="left", padx=5)
        self.btn_slide = ctk.CTkButton(
            p_controls_frame, text="▶ Slideshow", command=self.toggle_slideshow, hover_color="#2980b9"
        )
        self.btn_slide.pack(side="left", padx=5)
        ctk.CTkButton(
            p_controls_frame, text="Siguiente ⏭", command=self.next_photo, hover_color="#2980b9"
        ).pack(side="left", padx=5)

    def switch_view(self, value):
        if value == "🎬 Vídeos":
            self.video_sidebar.tkraise()
            self.video_right.tkraise()
        else:
            self.photo_sidebar.tkraise()
            self.photo_right.tkraise()

    def change_theme_mode(self, new_mode: str):
        ctk.set_appearance_mode(new_mode)
        self.update_listbox_colors(ctk.get_appearance_mode())

    def update_listbox_colors(self, mode: str):
        is_dark = mode.lower() == "dark"
        lb_bg = "#000000" if is_dark else "#ffffff"
        lb_fg = "#ffffff" if is_dark else "#000000"
        sel_bg = "#007acc" if is_dark else "#0078d7"

        for lb in [getattr(self, 'v_listbox', None), getattr(self, 'p_listbox', None)]:
            if lb:
                lb.config(
                    bg=lb_bg, fg=lb_fg, selectbackground=sel_bg, selectforeground="#ffffff", bd=1
                )

    def update_file_details(self, file_path, file_type=""):
        if not file_path or not os.path.exists(file_path):
            self.lbl_details.configure(text="📁 Ningún archivo seleccionado")
            return

        filename = os.path.basename(file_path)
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        except Exception:
            size_str = "Desconocido"

        extra_info = ""
        if file_type == "photo":
            try:
                with Image.open(file_path) as img:
                    w, h = img.size
                    extra_info = f"  |  📐 {w}x{h} px"
            except Exception:
                pass

        self.lbl_details.configure(text=f"📄 {filename}  |  💾 {size_str}{extra_info}")


if __name__ == "__main__":
    root = ctk.CTk()
    app = MediaApp(root)
    root.mainloop()
