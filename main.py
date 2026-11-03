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
