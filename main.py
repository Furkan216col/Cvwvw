import os
import json
import threading
import webbrowser
from datetime import datetime
import requests

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform

# Android donanım ve API köprüsü
if platform == 'android':
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
    Context = autoclass('android.content.Context')
    BatteryManager = autoclass('android.os.BatteryManager')
    ActivityManager = autoclass('android.app.ActivityManager')

# Gemini API Anahtarı (Buraya kendi anahtarını ekle)
GEMINI_API_KEY = "BURAYA_GEMINI_API_KEY_GIRIN"
MEMORY_FILE = "jarvis_memory.json"

class AndroidSystemBridge:
    @staticmethod
    def get_battery():
        if platform != 'android':
            return "Android dışı platform (Test modu: %100)"
        try:
            context = PythonActivity.mActivity.getApplicationContext()
            bm = context.getSystemService(Context.BATTERY_SERVICE)
            level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
            return f"%{level}"
        except Exception as e:
            return f"Okunamadı ({e})"

    @staticmethod
    def get_ram_info():
        if platform != 'android':
            return "Test modu: 4GB / 8GB"
        try:
            context = PythonActivity.mActivity.getApplicationContext()
            act_mgr = context.getSystemService(Context.ACTIVITY_SERVICE)
            mi = autoclass('android.app.ActivityManager$MemoryInfo')()
            act_mgr.getMemoryInfo(mi)
            avail_gb = round(mi.availMem / (1024 ** 3), 2)
            total_gb = round(mi.totalMem / (1024 ** 3), 2)
            return f"{avail_gb} GB boş / {total_gb} GB toplam"
        except Exception as e:
            return f"Okunamadı ({e})"

    @staticmethod
    def open_app(package_name):
        if platform != 'android':
            return False
        try:
            activity = PythonActivity.mActivity
            pm = activity.getPackageManager()
            intent = pm.getLaunchIntentForPackage(package_name)
            if intent:
                activity.startActivity(intent)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def send_whatsapp(number, text):
        clean_num = "".join(filter(str.isdigit, number))
        url = f"https://api.whatsapp.com/send?phone={clean_num}&text={requests.utils.quote(text)}"
        if platform == 'android':
            try:
                intent = Intent(Intent.ACTION_VIEW)
                intent.setData(Uri.parse(url))
                PythonActivity.mActivity.startActivity(intent)
                return True
            except Exception:
                return False
        else:
            webbrowser.open(url)
            return True

    @staticmethod
    def open_url(url):
        if not url.startswith("http"):
            url = "https://" + url
        if platform == 'android':
            try:
                intent = Intent(Intent.ACTION_VIEW)
                intent.setData(Uri.parse(url))
                PythonActivity.mActivity.startActivity(intent)
                return True
            except Exception:
                return False
        webbrowser.open(url)
        return True


class JarvisCore:
    def __init__(self):
        self.memory = self.load_memory()

    def load_memory(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_memory(self):
        try:
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def call_gemini(self, prompt):
        if not GEMINI_API_KEY or "BURAYA" in GEMINI_API_KEY:
            return "Gemini API anahtarı girilmedi. Lütfen geçerli bir anahtar ekleyin."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"Sen Jarvis adında akıllı bir asistansın. Kısa, zeki, net yanıtlar ver. Soru: {prompt}"}]}]
        }
        try:
            res = requests.post(url, json=payload, timeout=12)
            data = res.json()
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            return f"Gemini bağlantı hatası: {e}"

    def execute(self, text):
        raw = text.strip()
        cmd = raw.lower()

        # Sistem / Donanım
        if "pil" in cmd or "şarj" in cmd:
            return f"Pil Seviyesi: {AndroidSystemBridge.get_battery()}"
        
        if "ram" in cmd or "bellek durumu" in cmd:
            return f"RAM Durumu: {AndroidSystemBridge.get_ram_info()}"
        
        if "saat" in cmd or "tarih" in cmd:
            now = datetime.now().strftime("%d.%m.%Y - %H:%M:%S")
            return f"Tarih ve Saat: {now}"

        # Uygulamalar
        if "spotify aç" in cmd or "spotify'ı aç" in cmd:
            if AndroidSystemBridge.open_app("com.spotify.music"):
                return "Spotify başlatılıyor."
            AndroidSystemBridge.open_url("https://open.spotify.com")
            return "Spotify tarayıcıda açılıyor."

        if "youtube aç" in cmd or "youtube'u aç" in cmd:
            if AndroidSystemBridge.open_app("com.google.android.youtube"):
                return "YouTube açılıyor."
            AndroidSystemBridge.open_url("https://youtube.com")
            return "YouTube webde açılıyor."

        if "whatsapp aç" in cmd:
            if AndroidSystemBridge.open_app("com.whatsapp"):
                return "WhatsApp açılıyor."
            return "WhatsApp uygulaması bulunamadı."

        # Müzik ve Video Arama
        if cmd.startswith("youtube'da ") and ("çal" in cmd or "ara" in cmd):
            query = raw[11:].replace("çal", "").replace("ara", "").strip()
            AndroidSystemBridge.open_url(f"https://www.youtube.com/results?search_query={query}")
            return f"YouTube'da aranıyor: {query}"

        if cmd.startswith("spotify'da ") and "çal" in cmd:
            query = raw[11:].replace("çal", "").strip()
            AndroidSystemBridge.open_url(f"https://open.spotify.com/search/{query}")
            return f"Spotify'da aranıyor: {query}"

        # WhatsApp Mesajı: "mesaj at 05xxxx: mesaj metni"
        if cmd.startswith("mesaj at ") or cmd.startswith("whatsapp mesaj:"):
            try:
                payload = raw.split(":", 1)
                target = payload[0].replace("mesaj at", "").replace("whatsapp mesaj", "").strip()
                msg_body = payload[1].strip()
                AndroidSystemBridge.send_whatsapp(target, msg_body)
                return f"{target} numarasına mesaj aktarılıyor..."
            except Exception:
                return "Biçim hatası. Örnek kullanım: 'mesaj at 905xxxxxxxxx: Selam'"

        # Web Arama
        if cmd.startswith("ara ") or ("nedir" in cmd and len(cmd.split()) <= 3):
            query = raw.replace("ara", "").strip()
            AndroidSystemBridge.open_url(f"https://www.google.com/search?q={query}")
            return f"Google araması yapılıyor: {query}"

        # Bellek Modülü
        if cmd.startswith("bunu hatırla:"):
            content = raw.split(":", 1)[1].strip()
            parts = content.split("=", 1)
            if len(parts) == 2:
                k, v = parts[0].strip(), parts[1].strip()
            else:
                k, v = f"not_{len(self.memory) + 1}", content
            self.memory[k] = v
            self.save_memory()
            return f"Hafızaya kaydedildi: [{k} -> {v}]"

        if "ne hatırlıyorsun" in cmd or "hafıza" in cmd:
            if not self.memory:
                return "Hafızada kayıtlı bilgi yok."
            return "Kayıtlı Bilgiler:\n" + "\n".join([f"• {k}: {v}" for k, v in self.memory.items()])

        # Hava Durumu
        if "hava durumu" in cmd or "hava nasıl" in cmd:
            loc = "Ankara"
            words = raw.split()
            for w in words:
                if w.lower() not in ["hava", "durumu", "nasıl", "bugün"]:
                    loc = w
                    break
            AndroidSystemBridge.open_url(f"https://www.google.com/search?q={loc}+hava+durumu")
            return f"{loc} için hava durumu açılıyor."

        # Eşleşmeyen durumlarda Gemini devreye girer
        return self.call_gemini(raw)


class JarvisUI(BoxLayout):
    def __init__(self, **kwargs):
        super(JarvisUI, self).__init__(orientation='vertical', padding=12, spacing=8, **kwargs)
        self.jarvis = JarvisCore()

        # Üst Panel
        self.header = Label(
            text="[b]J.A.R.V.I.S[/b] — Sistem Aktif", 
            markup=True, 
            size_hint_y=0.08, 
            font_size='18sp'
        )
        self.add_widget(self.header)

        # Çıktı / Log Alanı
        self.scroll = ScrollView(size_hint_y=0.76)
        self.log_label = Label(
            text="Jarvis Android Arayüzü Hazır.\nKomut girin veya doğrudan soru sorun.\n",
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        self.log_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
        self.log_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        self.scroll.add_widget(self.log_label)
        self.add_widget(self.scroll)

        # Alt Giriş Paneli
        self.input_layout = BoxLayout(size_hint_y=0.16, spacing=6)
        self.text_input = TextInput(
            hint_text="Komut veya soru yazın...", 
            multiline=False,
            font_size='16sp'
        )
        self.text_input.bind(on_text_validate=self.on_send)
        
        self.send_btn = Button(
            text="İlet", 
            size_hint_x=0.25,
            bold=True
        )
        self.send_btn.bind(on_press=self.on_send)

        self.input_layout.add_widget(self.text_input)
        self.input_layout.add_widget(self.send_btn)
        self.add_widget(self.input_layout)

    def write_log(self, text):
        self.log_label.text += f"\n{text}"

    def on_send(self, instance):
        query = self.text_input.text.strip()
        if not query:
            return
        self.write_log(f"\n[Sen]: {query}")
        self.text_input.text = ""
        threading.Thread(target=self._process_worker, args=(query,)).start()

    def _process_worker(self, query):
        reply = self.jarvis.execute(query)
        Clock.schedule_once(lambda dt: self.write_log(f"[Jarvis]: {reply}"))


class MainApp(App):
    def build(self):
        return JarvisUI()

if __name__ == '__main__':
    MainApp().run()
