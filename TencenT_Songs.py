# TencenT_Songs.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pygame
import os
import json
from mutagen.mp3 import MP3
import time
import threading
from PIL import Image

# Pygame mixer başlat
pygame.mixer.init()

class TencenTSongs(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TencenT Songs")
        self.geometry("900x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        
        # Veri yapıları
        self.music_library = []  # [{"path": ..., "title": ..., "artist": ..., "category": ...}]
        self.current_playlist = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.categories = ["Tümü", "Phonk", "Natural", "Lo-Fi", "Rock", "Pop"]
        self.playlists = {}
        
        # Verileri yükle
        self.load_data()
        
        # UI oluştur
        self.create_widgets()
        self.update_song_list()
        
        # Müzik güncelleme thread'i
        self.running = True
        self.update_thread = threading.Thread(target=self.music_updater, daemon=True)
        self.update_thread.start()
    
    def create_widgets(self):
        # Ana container
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sol panel - Kategoriler ve Playlistler
        self.left_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        self.left_frame.grid_rowconfigure(3, weight=1)
        
        ctk.CTkLabel(self.left_frame, text="KATEGORİLER", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Kategori butonları
        self.category_buttons = {}
        for cat in self.categories:
            btn = ctk.CTkButton(self.left_frame, text=cat, 
                                command=lambda c=cat: self.filter_by_category(c))
            btn.pack(pady=2, padx=10, fill="x")
            self.category_buttons[cat] = btn
        
        ctk.CTkLabel(self.left_frame, text="PLAYLİSTLER", font=("Arial", 14, "bold")).pack(pady=(20,10))
        
        self.playlist_frame = ctk.CTkScrollableFrame(self.left_frame)
        self.playlist_frame.pack(fill="both", expand=True, padx=5)
        
        self.btn_new_playlist = ctk.CTkButton(self.left_frame, text="+ Yeni Playlist", 
                                              command=self.create_playlist)
        self.btn_new_playlist.pack(pady=10, padx=10, fill="x")
        
        # Orta panel - Şarkı listesi
        self.center_frame = ctk.CTkFrame(self)
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.center_frame.grid_rowconfigure(0, weight=1)
        self.center_frame.grid_columnconfigure(0, weight=1)
        
        self.song_listbox = ctk.CTkScrollableFrame(self.center_frame)
        self.song_listbox.grid(row=0, column=0, sticky="nsew")
        
        # Alt panel - Kontroller
        self.bottom_frame = ctk.CTkFrame(self, height=100)
        self.bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.bottom_frame.grid_columnconfigure(1, weight=1)
        
        # Butonlar
        self.btn_prev = ctk.CTkButton(self.bottom_frame, text="⏮", width=50, command=self.prev_song)
        self.btn_prev.grid(row=0, column=0, padx=5, pady=10)
        
        self.btn_play = ctk.CTkButton(self.bottom_frame, text="▶", width=50, command=self.play_pause)
        self.btn_play.grid(row=0, column=1, padx=5, pady=10)
        
        self.btn_next = ctk.CTkButton(self.bottom_frame, text="⏭", width=50, command=self.next_song)
        self.btn_next.grid(row=0, column=2, padx=5, pady=10)
        
        # Ses kontrolü
        self.volume_slider = ctk.CTkSlider(self.bottom_frame, from_=0, to=1, 
                                          command=self.set_volume, width=150)
        self.volume_slider.grid(row=0, column=3, padx=10)
        self.volume_slider.set(0.7)
        pygame.mixer.music.set_volume(0.7)
        
        # Şarkı bilgisi
        self.song_info_label = ctk.CTkLabel(self.bottom_frame, text="Şarkı seçilmedi", 
                                           font=("Arial", 12))
        self.song_info_label.grid(row=0, column=4, padx=20, sticky="w")
        
        # Progress bar
        self.progress_slider = ctk.CTkSlider(self.bottom_frame, from_=0, to=100, 
                                            command=self.seek_music)
        self.progress_slider.grid(row=1, column=0, columnspan=5, padx=10, pady=5, sticky="ew")
        
        self.time_label = ctk.CTkLabel(self.bottom_frame, text="00:00 / 00:00")
        self.time_label.grid(row=1, column=5, padx=10)
        
        # Menü çubuğu
        self.menu_frame = ctk.CTkFrame(self, height=30)
        self.menu_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        ctk.CTkButton(self.menu_frame, text="Müzik Ekle", command=self.add_music).pack(side="left", padx=5, pady=2)
        ctk.CTkButton(self.menu_frame, text="Klasör Ekle", command=self.add_folder).pack(side="left", padx=5, pady=2)
        
        # Kategori seçici (şarkı eklerken)
        self.category_var = ctk.StringVar(value="Phonk")
        ctk.CTkOptionMenu(self.menu_frame, values=self.categories[1:], 
                         variable=self.category_var).pack(side="right", padx=10)
        ctk.CTkLabel(self.menu_frame, text="Kategori:").pack(side="right")
    
    def load_data(self):
        try:
            with open("music_library.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.music_library = data.get("library", [])
                self.playlists = data.get("playlists", {})
        except FileNotFoundError:
            self.music_library = []
            self.playlists = {}
    
    def save_data(self):
        data = {
            "library": self.music_library,
            "playlists": self.playlists
        }
        with open("music_library.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_music(self):
        files = filedialog.askopenfilenames(
            title="Müzik Dosyalarını Seç",
            filetypes=[("MP3 Dosyaları", "*.mp3"), ("Tüm Dosyalar", "*.*")]
        )
        category = self.category_var.get()
        for file in files:
            if file not in [song["path"] for song in self.music_library]:
                try:
                    audio = MP3(file)
                    title = os.path.basename(file)
                    artist = "Bilinmiyor"
                    if audio.tags:
                        # TIT2: Başlık, TPE1: Sanatçı
                        title = str(audio.tags.get("TIT2", title))
                        artist = str(audio.tags.get("TPE1", artist))
                    self.music_library.append({
                        "path": file,
                        "title": title,
                        "artist": artist,
                        "category": category,
                        "duration": audio.info.length
                    })
                except Exception as e:
                    print(f"Hata: {e}")
        self.save_data()
        self.update_song_list()
    
    def add_folder(self):
        folder = filedialog.askdirectory(title="Müzik Klasörünü Seç")
        if folder:
            category = self.category_var.get()
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.mp3'):
                        full_path = os.path.join(root, file)
                        if full_path not in [song["path"] for song in self.music_library]:
                            try:
                                audio = MP3(full_path)
                                title = file
                                artist = "Bilinmiyor"
                                if audio.tags:
                                    title = str(audio.tags.get("TIT2", title))
                                    artist = str(audio.tags.get("TPE1", artist))
                                self.music_library.append({
                                    "path": full_path,
                                    "title": title,
                                    "artist": artist,
                                    "category": category,
                                    "duration": audio.info.length
                                })
                            except:
                                pass
            self.save_data()
            self.update_song_list()
    
    def update_song_list(self, category_filter="Tümü"):
        # Listeyi temizle
        for widget in self.song_listbox.winfo_children():
            widget.destroy()
        
        filtered_songs = self.music_library if category_filter == "Tümü" else \
                        [s for s in self.music_library if s["category"] == category_filter]
        
        for i, song in enumerate(filtered_songs):
            frame = ctk.CTkFrame(self.song_listbox)
            frame.pack(fill="x", padx=5, pady=2)
            
            info = f"{song['title']} - {song['artist']} [{song['category']}]"
            label = ctk.CTkLabel(frame, text=info, anchor="w")
            label.pack(side="left", fill="x", expand=True, padx=10)
            
            # Çift tıklama olayı
            label.bind("<Double-Button-1>", lambda e, idx=i, s=song: self.play_song(s))
            
            # Playlist'e ekle butonu
            btn_add = ctk.CTkButton(frame, text="+", width=30, 
                                   command=lambda s=song: self.add_to_playlist_menu(s))
            btn_add.pack(side="right", padx=5)
        
        self.current_playlist = filtered_songs
    
    def filter_by_category(self, category):
        self.update_song_list(category)
    
    def play_song(self, song):
        try:
            pygame.mixer.music.load(song["path"])
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self.btn_play.configure(text="⏸")
            self.song_info_label.configure(text=f"{song['title']} - {song['artist']}")
            self.current_index = self.current_playlist.index(song)
            
            # Süre bilgisini ayarla
            self.total_length = song.get("duration", 0)
            self.progress_slider.set(0)
        except Exception as e:
            messagebox.showerror("Hata", f"Şarkı çalınamadı: {e}")
    
    def play_pause(self):
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.btn_play.configure(text="▶")
        elif self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.btn_play.configure(text="⏸")
        elif self.current_playlist:
            self.play_song(self.current_playlist[0])
    
    def next_song(self):
        if self.current_playlist and self.current_index < len(self.current_playlist)-1:
            self.play_song(self.current_playlist[self.current_index+1])
    
    def prev_song(self):
        if self.current_playlist and self.current_index > 0:
            self.play_song(self.current_playlist[self.current_index-1])
    
    def set_volume(self, value):
        pygame.mixer.music.set_volume(value)
    
    def seek_music(self, value):
        if self.is_playing and hasattr(self, 'total_length') and self.total_length:
            pos = (float(value) / 100) * self.total_length
            try:
                pygame.mixer.music.rewind()
                pygame.mixer.music.set_pos(pos)
            except:
                pass
    
    def music_updater(self):
        while self.running:
            if self.is_playing and not self.is_paused:
                try:
                    pos = pygame.mixer.music.get_pos() / 1000  # saniye
                    if hasattr(self, 'total_length') and self.total_length > 0:
                        progress = (pos / self.total_length) * 100
                        self.progress_slider.set(progress)
                        self.time_label.configure(text=f"{self.format_time(pos)} / {self.format_time(self.total_length)}")
                except:
                    pass
            time.sleep(0.5)
    
    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    
    def create_playlist(self):
        dialog = ctk.CTkInputDialog(text="Playlist adı:", title="Yeni Playlist")
        name = dialog.get_input()
        if name and name not in self.playlists:
            self.playlists[name] = []
            self.save_data()
            self.update_playlist_buttons()
    
    def update_playlist_buttons(self):
        for widget in self.playlist_frame.winfo_children():
            widget.destroy()
        
        for pl_name in self.playlists:
            btn = ctk.CTkButton(self.playlist_frame, text=pl_name,
                               command=lambda n=pl_name: self.show_playlist(n))
            btn.pack(fill="x", padx=5, pady=2)
    
    def show_playlist(self, name):
        # Playlist içeriğini göster
        songs = self.playlists[name]
        # Şimdilik basit bir bilgi mesajı
        messagebox.showinfo("Playlist", f"{name}: {len(songs)} şarkı")
    
    def add_to_playlist_menu(self, song):
        # Eğer playlist varsa basit bir seçim yap (ilk playlist'e ekle)
        if self.playlists:
            pl_names = list(self.playlists.keys())
            # İleride bir seçim penceresi yapılabilir. Şimdi ilk playlist'e ekleyelim.
            self.playlists[pl_names[0]].append(song["path"])
            self.save_data()
            messagebox.showinfo("Eklendi", f"{song['title']} {pl_names[0]} playlistine eklendi.")
        else:
            messagebox.showinfo("Playlist Yok", "Lütfen önce bir playlist oluşturun.")
    
    def on_closing(self):
        self.running = False
        pygame.mixer.quit()
        self.destroy()

if __name__ == "__main__":
    app = TencenTSongs()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
