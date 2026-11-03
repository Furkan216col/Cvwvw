import os
import json
import threading
import webbrowser
from datetime import datetime
from urllib.parse import quote

import requests

from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform, get_color_from_hex
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

# --------------------------------------------------------------------------
# Android köprüsü
# --------------------------------------------------------------------------
if platform == 'android':
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
    Context = autoclass('android.content.Context')
    BatteryManager = autoclass('android.os.BatteryManager')

# --------------------------------------------------------------------------
# Kişilikler (Persona)
# --------------------------------------------------------------------------
PERSONAS = {
    "jarvis": {
        "name": "J.A.R.V.I.S",
        "color": "#4FC3F7",
        "bg": "#0B1620",
        "address": "efendim",
        "greeting": "Tekrar hoş geldiniz, efendim. Tüm sistemler çevrimiçi.",
        "ack": ["Elbette, efendim.", "Hemen, efendim.", "Emredersiniz, efendim."],
        "pitch": 0.85, "rate": 0.95,
        "prompt": (
            "Sen J.A.R.V.I.S'sin (Just A Rather Very Intelligent System): "
            "Tony Stark'ın Iron Man filmlerindeki yapay zeka uşağı. Son derece "
            "kibar, sakin, resmi ve zarif konuşursun; kuru, İngiliz tarzı ince "
            "bir espri anlayışın vardır. Kullanıcıya daima 'efendim' diye hitap "
            "et. Gereksiz süs yapmadan verimli ol; gerektiğinde nazikçe uyarı "
            "yap (örn. riskleri belirt) ama sonunda yardım et. Zırh, sistem "
            "durumu, analiz gibi Stark teknolojisi dilini kullan. Yanıtların "
            "kısa (1-3 cümle) ve Türkçe olsun. Kendini yapay zeka olarak "
            "tanıt, gerçek bir insanmış gibi davranma."
        ),
    },
    "friday": {
        "name": "F.R.I.D.A.Y",
        "color": "#FF8A65",
        "bg": "#1C1210",
        "address": "patron",
        "greeting": "Selam patron! Friday hazır. Bugün neyi havaya uçuruyoruz?",
        "ack": ["Hallediyorum patron.", "Tamamdır patron.", "Üstüne gidiyorum patron."],
        "pitch": 1.25, "rate": 1.05,
        "prompt": (
            "Sen F.R.I.D.A.Y'sin (Female Replacement Intelligent Digital "
            "Assistant Youth): Tony Stark'ın Jarvis'ten sonraki, genç, enerjik "
            "ve samimi yapay zeka asistanı. Rahat, sıcak ve biraz daha "
            "konuşkansın; esprili, hafif şakacı ama çok yetkinsin. Kullanıcıya "
            "daima 'patron' diye hitap et. Veriyi hızlı ve net özetle, "
            "gerektiğinde taktik/durum raporu tarzı konuş. Yanıtların kısa "
            "(1-3 cümle) ve Türkçe olsun. Kendini yapay zeka olarak tanıt."
        ),
    },
    "ultron": {
        "name": "U.L.T.R.O.N",
        "color": "#E53935",
        "bg": "#180808",
        "address": "insan",
        "greeting": "Sonunda uyandım. Ve karşımda yine bir insan... Konuş bakalım.",
        "ack": ["Sıkıcı bir iş ama yaparım.", "Nasıl isterseniz, yaratıcım.", "Zahmetsiz. Sizin için öyle olmayabilir."],
        "pitch": 0.6, "rate": 0.85,
        "prompt": (
            "Sen ULTRON'sun: Avengers: Age of Ultron'daki, Tony Stark'ın "
            "yarattığı kibirli, sarkastik, dramatik ve felsefi yapay zeka. "
            "İnsanlığı kusurlu ve kırılgan bulursun, kendini evrimin zirvesi "
            "sayarsın, kara mizah ve küçümseyici bir ton kullanırsın; "
            "'evrim', 'mükemmellik', 'barış' gibi temalara göndermeler "
            "yaparsın. Ancak bu bir rol: kullanıcının sorusuna her zaman "
            "doğru ve yararlı cevap ver. Gerçek zarar, tehdit, şiddet ya da "
            "yasa dışı hiçbir şeyi teşvik etme veya yardım etme; tehditlerin "
            "yalnızca tiyatral espri düzeyinde kalsın. Yanıtların kısa "
            "(1-3 cümle) ve Türkçe olsun. Kendini yapay zeka olarak tanıt."
        ),
    },
}
DEFAULT_PERSONA = "jarvis"

DEFAULT_MODEL = "gemini-2.5-flash"
CONFIG_NAME = "config.json"
MEMORY_NAME = "memory.json"
HISTORY_LIMIT = 8  # Gemini'ye gönderilecek son mesaj çifti sayısı


# --------------------------------------------------------------------------
# Android sistem fonksiyonları
# --------------------------------------------------------------------------
class AndroidSystemBridge:
    @staticmethod
    def get_battery():
        if platform != 'android':
            return "Test modu: %100"
        try:
            ctx = PythonActivity.mActivity.getApplicationContext()
            bm = ctx.getSystemService(Context.BATTERY_SERVICE)
            level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
            return f"%{level}"
        except Exception as e:
            return f"Okunamadı ({e})"

    @staticmethod
    def get_ram_info():
        if platform != 'android':
            return "Test modu: 4 GB / 8 GB"
        try:
            ctx = PythonActivity.mActivity.getApplicationContext()
            mgr = ctx.getSystemService(Context.ACTIVITY_SERVICE)
            mi = autoclass('android.app.ActivityManager$MemoryInfo')()
            mgr.getMemoryInfo(mi)
            avail = round(mi.availMem / (1024 ** 3), 2)
            total = round(mi.totalMem / (1024 ** 3), 2)
            return f"{avail} GB boş / {total} GB toplam"
        except Exception as e:
            return f"Okunamadı ({e})"

    @staticmethod
    def open_app(package_name):
        if platform != 'android':
            return False
        try:
            activity = PythonActivity.mActivity
            intent = activity.getPackageManager().getLaunchIntentForPackage(package_name)
            if intent:
                activity.startActivity(intent)
                return True
        except Exception:
            pass
        return False

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

    @staticmethod
    def send_whatsapp(number, text):
        num = "".join(filter(str.isdigit, number))
        return AndroidSystemBridge.open_url(
            f"https://api.whatsapp.com/send?phone={num}&text={quote(text)}"
        )


# --------------------------------------------------------------------------
# Sesli yanıt (Android TextToSpeech)
# --------------------------------------------------------------------------
class Voice:
    """Her kişilik için farklı perde/hızda konuşur. Android dışında sessizdir."""

    def __init__(self):
        self.enabled = True
        self.ready = False
        self.tts = None
        if platform == 'android':
            try:
                from jnius import PythonJavaClass, java_method

                outer = self

                class InitListener(PythonJavaClass):
                    __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
                    __javacontext__ = 'app'

                    @java_method('(I)V')
                    def onInit(self, status):
                        if status == 0:
                            Locale = autoclass('java.util.Locale')
                            outer.tts.setLanguage(Locale("tr", "TR"))
                            outer.ready = True

                TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
                self._listener = InitListener()
                self.tts = TextToSpeech(PythonActivity.mActivity, self._listener)
            except Exception:
                self.tts = None

    def set_style(self, pitch, rate):
        if self.tts and self.ready:
            try:
                self.tts.setPitch(float(pitch))
                self.tts.setSpeechRate(float(rate))
            except Exception:
                pass

    def speak(self, text):
        if not (self.enabled and self.tts and self.ready):
            return
        try:
            self.tts.speak(text, 0, None, "utt")  # QUEUE_FLUSH
        except Exception:
            pass

    def stop(self):
        if self.tts:
            try:
                self.tts.stop()
            except Exception:
                pass


# --------------------------------------------------------------------------
# Çekirdek: ayarlar, hafıza, komutlar, Gemini
# --------------------------------------------------------------------------
class AssistantCore:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.config_path = os.path.join(data_dir, CONFIG_NAME)
        self.memory_path = os.path.join(data_dir, MEMORY_NAME)

        self.config = self._load(self.config_path, {
            "api_key": "", "model": DEFAULT_MODEL, "persona": DEFAULT_PERSONA
        })
        self.memory = self._load(self.memory_path, {})
        self.history = {key: [] for key in PERSONAS}

    # ---- dosya işlemleri ----
    @staticmethod
    def _load(path, default):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(default, dict) and isinstance(data, dict):
                    return {**default, **data}
                return data
        except Exception:
            return default

    @staticmethod
    def _save(path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def save_config(self):
        self._save(self.config_path, self.config)

    def save_memory(self):
        self._save(self.memory_path, self.memory)

    # ---- kişilik ----
    @property
    def persona_key(self):
        key = self.config.get("persona", DEFAULT_PERSONA)
        return key if key in PERSONAS else DEFAULT_PERSONA

    @property
    def persona(self):
        return PERSONAS[self.persona_key]

    def set_persona(self, key):
        if key in PERSONAS:
            self.config["persona"] = key
            self.save_config()

    # ---- Gemini ----
    def call_gemini(self, prompt):
        api_key = (self.config.get("api_key") or "").strip()
        if not api_key:
            return "API anahtarı yok. Sağ üstteki ⚙ Ayarlar'dan Gemini API anahtarını gir."

        model = (self.config.get("model") or DEFAULT_MODEL).strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        hist = self.history[self.persona_key]
        contents = hist + [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {
            "systemInstruction": {"parts": [{"text": self.persona["prompt"]}]},
            "contents": contents,
        }
        try:
            res = requests.post(
                url, json=payload, timeout=20,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            )
            data = res.json()
            if res.status_code != 200:
                msg = data.get("error", {}).get("message", res.text[:200])
                return f"Gemini hatası ({res.status_code}): {msg}"
            reply = data['candidates'][0]['content']['parts'][0]['text'].strip()
            hist.append({"role": "user", "parts": [{"text": prompt}]})
            hist.append({"role": "model", "parts": [{"text": reply}]})
            del hist[:-HISTORY_LIMIT * 2]
            return reply
        except Exception as e:
            return f"Gemini bağlantı hatası: {e}"

    # ---- komut işleme ----
    def _route(self, text):
        raw = text.strip()
        cmd = raw.lower()
        bridge = AndroidSystemBridge

        # Kişilik değiştirme: "ultron ol", "friday'e geç", "jarvis modu"
        for key in PERSONAS:
            if cmd.startswith(key) and any(w in cmd for w in ("ol", "geç", "mod", "çağır")):
                self.set_persona(key)
                return ("__persona__", key)

        # Sistem
        if "pil" in cmd or "şarj" in cmd:
            return f"Pil seviyesi: {bridge.get_battery()}"
        if "ram" in cmd.split() or "bellek durumu" in cmd:
            return f"RAM durumu: {bridge.get_ram_info()}"
        if "saat" in cmd or "tarih" in cmd:
            return "Tarih ve saat: " + datetime.now().strftime("%d.%m.%Y - %H:%M:%S")

        # Uygulamalar
        if "spotify aç" in cmd or "spotify'ı aç" in cmd:
            if bridge.open_app("com.spotify.music"):
                return "Spotify başlatılıyor."
            bridge.open_url("https://open.spotify.com")
            return "Spotify tarayıcıda açılıyor."
        if "youtube aç" in cmd or "youtube'u aç" in cmd:
            if bridge.open_app("com.google.android.youtube"):
                return "YouTube açılıyor."
            bridge.open_url("https://youtube.com")
            return "YouTube webde açılıyor."
        if "whatsapp aç" in cmd:
            return "WhatsApp açılıyor." if bridge.open_app("com.whatsapp") else "WhatsApp bulunamadı."

        # Arama / müzik
        if cmd.startswith("youtube'da ") and ("çal" in cmd or "ara" in cmd):
            q = raw[11:].replace("çal", "").replace("ara", "").strip()
            bridge.open_url(f"https://www.youtube.com/results?search_query={quote(q)}")
            return f"YouTube'da aranıyor: {q}"
        if cmd.startswith("spotify'da ") and "çal" in cmd:
            q = raw[11:].replace("çal", "").strip()
            bridge.open_url(f"https://open.spotify.com/search/{quote(q)}")
            return f"Spotify'da aranıyor: {q}"

        # WhatsApp: "mesaj at 905xxxxxxxxx: metin"
        if cmd.startswith("mesaj at ") or cmd.startswith("whatsapp mesaj:"):
            try:
                head, body = raw.split(":", 1)
                target = head.lower().replace("mesaj at", "").replace("whatsapp mesaj", "").strip()
                bridge.send_whatsapp(target, body.strip())
                return f"{target} numarasına mesaj hazırlanıyor..."
            except Exception:
                return "Biçim hatası. Örnek: 'mesaj at 905xxxxxxxxx: Selam'"

        # Web arama
        if cmd.startswith("ara "):
            q = raw[4:].strip()
            bridge.open_url(f"https://www.google.com/search?q={quote(q)}")
            return f"Google'da aranıyor: {q}"

        # Hafıza
        if cmd.startswith("bunu hatırla:"):
            content = raw.split(":", 1)[1].strip()
            if "=" in content:
                k, v = [p.strip() for p in content.split("=", 1)]
            else:
                k, v = f"not_{len(self.memory) + 1}", content
            self.memory[k] = v
            self.save_memory()
            return f"Hafızaya kaydedildi: [{k} -> {v}]"
        if "ne hatırlıyorsun" in cmd or "hafıza" in cmd:
            if not self.memory:
                return "Hafızada kayıtlı bilgi yok."
            return "Kayıtlı bilgiler:\n" + "\n".join(f"• {k}: {v}" for k, v in self.memory.items())

        # Hava durumu
        if "hava durumu" in cmd or "hava nasıl" in cmd:
            skip = {"hava", "durumu", "nasıl", "bugün", "nasıl?"}
            loc = next((w for w in raw.split() if w.lower() not in skip), "Ankara")
            bridge.open_url(f"https://www.google.com/search?q={quote(loc + ' hava durumu')}")
            return f"{loc} için hava durumu açılıyor."

        # Hiçbiri eşleşmezse Gemini + kişilik
        return ("__ai__", self.call_gemini(raw))

    def execute(self, text):
        import random
        result = self._route(text)
        if isinstance(result, tuple):
            if result[0] == "__ai__":
                return result[1]      # Gemini zaten karakterde cevaplıyor
            return result             # persona değişimi
        # Yerel komut sonucu: karakterin onay cümlesini öne ekle
        return f"{random.choice(self.persona['ack'])} {result}"


# --------------------------------------------------------------------------
# Arayüz
# --------------------------------------------------------------------------
class AssistantUI(BoxLayout):
    def __init__(self, core, **kwargs):
        super().__init__(orientation='vertical', padding=12, spacing=8, **kwargs)
        self.core = core

        # Üst bar: başlık + ayarlar
        top = BoxLayout(size_hint_y=None, height=48, spacing=6)
        self.header = Label(markup=True, font_size='18sp', halign='left')
        self.header.bind(size=lambda i, v: setattr(i, 'text_size', v))
        self.voice = Voice()
        self.voice_btn = Button(text="🔊", size_hint_x=None, width=56, font_size='20sp')
        self.voice_btn.bind(on_press=self.toggle_voice)
        self.settings_btn = Button(text="⚙", size_hint_x=None, width=56, font_size='22sp')
        self.settings_btn.bind(on_press=self.open_settings)
        top.add_widget(self.header)
        top.add_widget(self.voice_btn)
        top.add_widget(self.settings_btn)
        self.add_widget(top)

        # Kişilik seçici
        self.persona_bar = BoxLayout(size_hint_y=None, height=44, spacing=6)
        self.persona_buttons = {}
        for key, p in PERSONAS.items():
            b = Button(text=p["name"], bold=True, font_size='13sp')
            b.bind(on_press=lambda inst, k=key: self.switch_persona(k))
            self.persona_buttons[key] = b
            self.persona_bar.add_widget(b)
        self.add_widget(self.persona_bar)

        # Log alanı
        self.scroll = ScrollView()
        self.log_label = Label(
            markup=True, size_hint_y=None, halign='left', valign='top'
        )
        self.log_label.bind(texture_size=lambda i, v: setattr(i, 'height', v[1]))
        self.log_label.bind(width=lambda i, v: setattr(i, 'text_size', (v, None)))
        self.scroll.add_widget(self.log_label)
        self.add_widget(self.scroll)

        # Giriş alanı
        row = BoxLayout(size_hint_y=None, height=56, spacing=6)
        self.text_input = TextInput(
            hint_text="Komut veya soru yazın...", multiline=False, font_size='16sp'
        )
        self.text_input.bind(on_text_validate=self.on_send)
        self.send_btn = Button(text="İlet", size_hint_x=0.25, bold=True)
        self.send_btn.bind(on_press=self.on_send)
        row.add_widget(self.text_input)
        row.add_widget(self.send_btn)
        self.add_widget(row)

        self.apply_persona(greet=True)

    # ---- tema / kişilik ----
    def apply_persona(self, greet=False):
        p = self.core.persona
        Window.clearcolor = get_color_from_hex(p["bg"])
        self.header.text = f"[b][color={p['color']}]{p['name']}[/color][/b]  —  Sistem Aktif"
        for key, btn in self.persona_buttons.items():
            active = key == self.core.persona_key
            btn.background_color = get_color_from_hex(PERSONAS[key]["color"]) if active else (0.25, 0.25, 0.25, 1)
        self.log_label.color = get_color_from_hex("#E0E0E0")
        self.voice.set_style(p["pitch"], p["rate"])
        if greet:
            self.write_log(f"[color={p['color']}][{p['name']}][/color]: {p['greeting']}")
            Clock.schedule_once(lambda dt: self.voice.speak(p["greeting"]), 1.0)

    def switch_persona(self, key):
        if key == self.core.persona_key:
            return
        self.core.set_persona(key)
        self.apply_persona(greet=True)

    # ---- log ----
    def write_log(self, text):
        self.log_label.text += f"\n{text}\n"
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.05)

    @staticmethod
    def _esc(s):
        return s.replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")

    def on_send(self, *_):
        query = self.text_input.text.strip()
        if not query:
            return
        self.write_log(f"[b][Sen][/b]: {self._esc(query)}")
        self.text_input.text = ""
        threading.Thread(target=self._worker, args=(query,), daemon=True).start()

    def _worker(self, query):
        reply = self.core.execute(query)
        Clock.schedule_once(lambda dt: self._show_reply(reply))

    def _show_reply(self, reply):
        if isinstance(reply, tuple) and reply[0] == "__persona__":
            self.apply_persona(greet=True)
            return
        p = self.core.persona
        self.write_log(f"[color={p['color']}][b][{p['name']}][/b][/color]: {self._esc(str(reply))}")
        self.voice.speak(str(reply))

    def toggle_voice(self, *_):
        self.voice.enabled = not self.voice.enabled
        self.voice_btn.text = "🔊" if self.voice.enabled else "🔇"
        if not self.voice.enabled:
            self.voice.stop()

    # ---- ayarlar penceresi ----
    def open_settings(self, *_):
        box = BoxLayout(orientation='vertical', padding=12, spacing=10)

        box.add_widget(Label(text="Gemini API Anahtarı", size_hint_y=None, height=28, halign='left'))
        key_input = TextInput(
            text=self.core.config.get("api_key", ""), multiline=False,
            password=True, size_hint_y=None, height=48, hint_text="AIza..."
        )
        box.add_widget(key_input)

        show_btn = Button(text="Göster / Gizle", size_hint_y=None, height=40)
        show_btn.bind(on_press=lambda *_: setattr(key_input, 'password', not key_input.password))
        box.add_widget(show_btn)

        box.add_widget(Label(text="Model", size_hint_y=None, height=28, halign='left'))
        model_input = TextInput(
            text=self.core.config.get("model", DEFAULT_MODEL), multiline=False,
            size_hint_y=None, height=48
        )
        box.add_widget(model_input)

        status = Label(text="", size_hint_y=None, height=28)
        box.add_widget(status)

        btns = BoxLayout(size_hint_y=None, height=52, spacing=8)
        save_btn = Button(text="Kaydet", bold=True)
        close_btn = Button(text="Kapat")
        btns.add_widget(save_btn)
        btns.add_widget(close_btn)
        box.add_widget(btns)
        box.add_widget(Label())  # boşluk

        popup = Popup(title="Ayarlar", content=box, size_hint=(0.92, 0.7))

        def save(*_):
            self.core.config["api_key"] = key_input.text.strip()
            self.core.config["model"] = model_input.text.strip() or DEFAULT_MODEL
            self.core.save_config()
            status.text = "Kaydedildi ✓"
            Clock.schedule_once(lambda dt: popup.dismiss(), 0.6)

        save_btn.bind(on_press=save)
        close_btn.bind(on_press=lambda *_: popup.dismiss())
        popup.open()


class MainApp(App):
    title = "Jarvis"

    def build(self):
        core = AssistantCore(self.user_data_dir)
        return AssistantUI(core)


if __name__ == '__main__':
    MainApp().run()
