# Messenger by Victor Grigorgev ver. alfa 0.5.3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from kivy.lang import Builder
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from datetime import datetime
import json
import os
import colorsys
from kivymd.uix.label import MDLabel
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import IconLeftWidget
from kivymd.app import MDApp
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.config import Config
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty
from kivymd.uix.list import MDList
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton


def normalize_key_to_32_bytes(key: str) -> bytes:
    if isinstance(key, str):
        key = key.encode('utf-8')
    return hashlib.sha256(key).digest()  # Возвращает 32 байта

def encrypt_aes256(text: str, key: str) -> str:
    key_bytes = normalize_key_to_32_bytes(key)
    iv = get_random_bytes(AES.block_size)  # Генерируем IV
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + encrypted).decode('utf-8')

def decrypt_aes256(encrypted_text: str, key: str) -> str:
    key_bytes = normalize_key_to_32_bytes(key)
    data = base64.b64decode(encrypted_text)
    iv, ciphertext = data[:AES.block_size], data[AES.block_size:]
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return decrypted.decode('utf-8')

def init_database():
    default_data = {
        "admin": {"password": "123", "messages": [], "unread": {}},
        "Подопытный 1": {"password": "123", "messages": [], "unread": {}},
        "Подопытный 2": {"password": "123", "messages": [], "unread": {}},
        "Виктор": {"password": "123", "messages": [], "unread": {}}
    }

    if not os.path.exists('users.json') or os.path.getsize('users.json') == 0:
        with open('users.json', 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data

    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except:
        with open('users.json', 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data


def load_users():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except:
        return init_database()


def save_users(data):
    try:
        with open('users.json', 'w') as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Ошибка сохранения: {e}")


# Инициализируем базу данных при старте
init_database()


class EncryptionKeyScreen(MDScreen):
    chat_with = StringProperty('')
    current_user = StringProperty('')
    modal_view = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.modal_view = None

    def on_pre_enter(self, *args):
        # Создаем диалог только если его еще нет
        if self.modal_view is None:
            self.create_dialog()

        chat_screen = self.manager.get_screen('chat')
        self.chat_with = chat_screen.chat_with

        if self.modal_view:
            self.modal_view.chat_with = self.chat_with
            self.modal_view.update_text()
            self.modal_view.open()

    def create_dialog(self):
        self.modal_view = EncryptionKeyDialog()
        self.modal_view.button.bind(on_release=self.verify_key)

    def verify_key(self, instance):
        if not self.modal_view:
            return

        key = self.modal_view.text_input.text
        if not key:
            return

        app = MDApp.get_running_app()
        app.chat_keys[f"{self.current_user}_{self.chat_with}"] = key
        app.chat_keys[f"{self.chat_with}_{self.current_user}"] = key

        self.modal_view.dismiss()
        self.manager.transition.direction = 'left'
        self.manager.current = 'chat'

    def on_leave(self, *args):
        if self.modal_view:
            self.modal_view.dismiss()
            self.modal_view = None


class EncryptionKeyDialog(ModalView):
    chat_with = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.8, 0.6)
        self.background_color = [0, 0, 0, 0]
        self.overlay_color = [0, 0, 0, 0.7]

        self.layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(15),
            padding=dp(20),
            radius=[dp(15), ],
            md_bg_color=MDApp.get_running_app().theme_cls.bg_normal
        )

        self.label = MDLabel(
            text="",
            halign='center',
            font_style='H5',
            size_hint_y=None,
            height=dp(50)
        )

        self.text_input = MDTextField(
            hint_text="Ключ шифрования",
            password=True,
            size_hint_x=1,
            mode="fill"
        )

        self.button = MDRaisedButton(
            text="Подтвердить",
            size_hint_x=1
        )

        self.layout.add_widget(self.label)
        self.layout.add_widget(self.text_input)
        self.layout.add_widget(self.button)
        self.add_widget(self.layout)

    def update_text(self):
        self.label.text = f"Введите ключ для чата с {self.chat_with}"

class ChatListItem(MDBoxLayout):
    text = StringProperty("")
    secondary_text = StringProperty("")
    time_text = StringProperty("")
    unread_count = NumericProperty(0)
    avatar_icon = StringProperty("account-circle")
    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.register_event_type('on_item_press')
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.selected = True
            self.dispatch('on_item_press')
            return True
        return super().on_touch_down(touch)

    def on_item_press(self, *args):
        pass


class CreateKeyScreen(MDScreen):
    chat_with = StringProperty('')
    current_user = StringProperty('')

    def on_pre_enter(self, *args):
        # Очищаем оба поля при открытии экрана
        self.ids.new_key.text = ''
        self.ids.confirm_key.text = ''

    def create_key(self, key, confirm_key):
        if not key or not confirm_key:
            self.ids.new_key.error = True
            self.ids.new_key.helper_text = "Заполните оба поля"
            return

        if key != confirm_key:
            self.ids.confirm_key.error = True
            self.ids.confirm_key.helper_text = "Ключи не совпадают"
            return

        app = MDApp.get_running_app()
        app.chat_keys[f"{self.current_user}_{self.chat_with}"] = key
        app.chat_keys[f"{self.chat_with}_{self.current_user}"] = key

        # Очищаем поля после создания ключа
        self.ids.new_key.text = ''
        self.ids.confirm_key.text = ''

        chat_screen = self.manager.get_screen('chat')
        chat_screen.chat_with = self.chat_with
        chat_screen.current_user = self.current_user
        self.manager.transition.direction = 'left'
        self.manager.current = 'chat'


class CreateKeyScreen(MDScreen):
    def on_touch_down(self, touch):
        if self.ids.container.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        return False

    def create_key(self, key, confirm_key):
        if not key or key != confirm_key:
            self.ids.new_key.error = True
            self.ids.new_key.helper_text = "Ключи не совпадают или пустые"
            return

        app = MDApp.get_running_app()
        app.chat_keys[f"{self.current_user}_{self.chat_with}"] = key
        app.chat_keys[f"{self.chat_with}_{self.current_user}"] = key

        self.manager.transition.direction = 'left'
        self.manager.current = 'chat'

Builder.load_string('''
<EncryptionKeyScreen>:
    chat_with: ''
    current_user: app.current_user
    
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.7
        Rectangle:
            pos: self.pos
            size: self.size

    # Основной контейнер с полем ввода
    MDBoxLayout:
        id: container
        orientation: 'vertical'
        size_hint: 0.8, 0.6
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        spacing: dp(15)
        padding: dp(20)
        radius: [dp(15),]
        md_bg_color: app.theme_cls.bg_normal
        
        MDLabel:
            text: f"Введите ключ для чата с {root.chat_with}"
            halign: 'center'
            font_style: 'H5'
            size_hint_y: None
            height: self.texture_size[1]

        MDTextField:
            id: encryption_key
            hint_text: "Ключ шифрования"
            password: True
            size_hint_x: 1
            mode: "fill"
            focus: True  # Автоматически фокусируемся на поле ввода
            on_text_validate: root.verify_key(encryption_key.text)

        MDRaisedButton:
            id: confirm_button
            text: "Подтвердить"
            size_hint_x: 1
            on_release: root.verify_key(encryption_key.text)
            
<CreateKeyScreen>:
    chat_with: ''
    current_user: app.current_user
    
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.7
        Rectangle:
            pos: self.pos
            size: self.size

    MDBoxLayout:
        id: container
        orientation: 'vertical'
        size_hint: 0.8, 0.6
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        spacing: dp(15)
        padding: dp(20)
        radius: [dp(15),]
        md_bg_color: app.theme_cls.bg_normal
        
        MDLabel:
            text: f"Создать ключ для чата с {root.chat_with}"
            halign: 'center'
            font_style: 'H5'
            size_hint_y: None
            height: self.texture_size[1]

        MDTextField:
            id: new_key
            hint_text: "Придумайте ключ шифрования"
            password: True
            size_hint_x: 1
            mode: "fill"
            focus: True

        MDTextField:
            id: confirm_key
            hint_text: "Повторите ключ"
            password: True
            size_hint_x: 1
            mode: "fill"

        MDRaisedButton:
            text: "Создать ключ"
            size_hint_x: 1
            on_release: root.create_key(new_key.text, confirm_key.text)
            
<LoginScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(15)

        # Заголовок с фиксированной высотой
        MDBoxLayout:
            size_hint_y: None
            height: dp(100)
            padding: dp(10)

            MDLabel:
                text: "Вход в систему"
                halign: 'center'
                font_style: 'H4'
                size_hint_y: None
                height: self.texture_size[1]

        # Остальные элементы с прокруткой
        ScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(15)

                MDTextField:
                    id: login
                    hint_text: "Логин"
                    icon_left: "account"
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}

                MDTextField:
                    id: password
                    hint_text: "Пароль"
                    icon_left: "lock"
                    password: True
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}

                MDRaisedButton:  # Было MMDRaisedButton
                    text: "Войти"
                    size_hint_x: 0.5
                    pos_hint: {'center_x': 0.5}
                    on_release: root.login()

                MDRectangleFlatButton:
                    text: "Создать аккаунт"
                    size_hint_x: 0.5
                    pos_hint: {'center_x': 0.5}
                    on_release: 
                        root.manager.transition.direction = 'left'
                        root.manager.current = 'register'


<RegisterScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(15)

        # Заголовок с фиксированной высотой
        MDBoxLayout:
            size_hint_y: None
            height: dp(100)
            padding: dp(10)

            MDLabel:
                text: "Регистрация"
                halign: 'center'
                font_style: 'H4'
                size_hint_y: None
                height: self.texture_size[1]

        # Остальные элементы с прокруткой
        ScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(15)

                MDTextField:
                    id: new_login
                    hint_text: "Придумайте логин"
                    icon_left: "account-plus"
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}

                MDTextField:
                    id: new_password
                    hint_text: "Придумайте пароль"
                    icon_left: "lock-plus"
                    password: True
                    size_hint_x: 0.8
                    pos_hint: {'center_x': 0.5}

                MDRaisedButton:
                    text: "Зарегистрироваться"
                    size_hint_x: 0.5
                    pos_hint: {'center_x': 0.5}
                    on_release: root.register()

                MDRectangleFlatButton:
                    text: "Назад"
                    size_hint_x: 0.5
                    pos_hint: {'center_x': 0.5}
                    on_release: 
                        root.manager.transition.direction = 'right'
                        root.manager.current = 'login'


<CircularAvatar@MDBoxLayout>
    size_hint: None, None
    size: dp(40), dp(40)
    radius: [dp(20),]
    canvas.before:
        Color:
            rgba: app.theme_cls.primary_color
        Ellipse:
            size: self.size
            pos: self.pos
    MDLabel:
        text: ""
        halign: "center"
        valign: "center"
        theme_text_color: "Custom"
        text_color: [1, 1, 1, 1]
        font_style: "H6"

<ChatListItem>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(80)
    spacing: dp(10)
    padding: dp(10)
    md_bg_color: [0.95, 0.95, 0.95, 1] if root.selected else [1, 1, 1, 1]

    IconLeftWidget:
        icon: root.avatar_icon
        theme_text_color: "Custom"
        text_color: app.theme_cls.primary_color
        size_hint_x: None
        width: dp(40)

    RelativeLayout:
        size_hint_x: 0.8
        size_hint_y: 1

        # Имя пользователя (левый верхний угол)
        MDLabel:
            text: root.text
            halign: 'left'
            font_style: 'Subtitle1'
            size_hint: (0.7, None)
            height: dp(30)
            pos_hint: {'top': 1, 'left': 1}
            text_size: (self.width, None)

        # Время (правый верхний угол)
        MDLabel:
            id: time_label
            text: root.time_text
            halign: 'right'
            font_style: 'Caption'
            theme_text_color: 'Secondary'
            size_hint: (None, None)
            size: (dp(50), dp(20))
            pos_hint: {'top': 1, 'right': 1}

        # Текст сообщения (левый нижний угол)
        MDLabel:
            text: root.secondary_text
            halign: 'left'
            font_style: 'Body2'
            theme_text_color: 'Secondary'
            size_hint: (0.7, None)
            height: dp(40)
            pos_hint: {'y': 0, 'left': 1}
            text_size: (self.width, None)
            shorten: True
            shorten_from: 'right'

        # Бейдж непрочитанных (правый нижний угол)
        MDBoxLayout:
            id: unread_badge
            size_hint: (None, None)
            size: (dp(24), dp(24)) if root.unread_count > 0 else (0, 0)
            radius: [dp(12)]
            md_bg_color: app.theme_cls.primary_color
            opacity: 1 if root.unread_count > 0 else 0
            pos_hint: {'right': 1, 'y': 0}

            MDLabel:
                text: str(root.unread_count) if root.unread_count > 0 else ""
                halign: 'center'
                valign: 'center'
                theme_text_color: 'Custom'
                text_color: [1, 1, 1, 1]
                font_style: 'Caption'
                bold: True
                size_hint: (1, 1)

<MainScreen>:
    current_user: app.current_user

    MDBoxLayout:
        orientation: 'vertical'
        spacing: dp(10)
        padding: dp(10)

        MDTopAppBar:
            title: f"Чаты"
            left_action_items: [['logout', lambda x: root.logout()]]
            elevation: 10

        MDTextField:
            id: recipient_input
            hint_text: "Поиск пользователя"
            size_hint_x: 0.9
            pos_hint: {'center_x': 0.5}
            icon_left: "account-search"
            mode: "round"
            line_color_focus: app.theme_cls.primary_color

        MDRaisedButton:
            text: "Открыть чат"
            size_hint_x: 0.5
            pos_hint: {'center_x': 0.5}
            on_release: root.open_chat(recipient_input.text)

        ScrollView:
            MDList:
                id: chats_list
                spacing: dp(10)
                padding: dp(5)
                size_hint_y: None
                height: self.minimum_height


<ChatScreen>:
    chat_with: ''
    current_user: app.current_user

    MDBoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            title: f"{root.chat_with}"
            left_action_items: [['arrow-left', lambda x: root.back_to_main()]]
            elevation: 10

        ScrollView:
            MDList:
                id: messages_list
                spacing: dp(5)
                padding: dp(10)
                size_hint_y: None
                height: self.minimum_height
                md_bg_color: [0.95, 0.95, 0.95, 1]  

        MDBoxLayout:
            size_hint_y: None
            height: dp(80)
            padding: dp(10)
            spacing: dp(10)

            MDTextField:
                id: message_input
                hint_text: "Сообщение"
                size_hint_x: 0.8
                on_text_validate: root.send_message(self.text)  # Добавьте эту строку
                multiline: False  # Чтобы Enter сразу отправлял сообщение

            MDRaisedButton:
                text: "Отправить"
                size_hint_x: 0.2
                on_release: root.send_message(message_input.text)
''')


class LoginScreen(MDScreen):
    def login(self):
        login = self.ids.login.text.strip()
        password = self.ids.password.text.strip()

        try:
            users = load_users()

            if login in users and users[login]["password"] == password:
                app = MDApp.get_running_app()
                app.current_user = login

                # Инициализируем поля если их нет
                if "messages" not in users[login]:
                    users[login]["messages"] = []
                if "unread" not in users[login]:
                    users[login]["unread"] = {}

                save_users(users)

                self.manager.transition.direction = 'left'
                self.manager.current = 'main'
            else:
                self.ids.password.error = True
                self.ids.password.helper_text = "Неверный логин или пароль"
        except Exception as e:
            print(f"Ошибка входа: {e}")
            self.ids.password.error = True
            self.ids.password.helper_text = "Ошибка системы"


class RegisterScreen(MDScreen):
    def register(self):
        login = self.ids.new_login.text
        password = self.ids.new_password.text

        if not login or not password:
            return

        with open('users.json', 'r+') as f:
            users = json.load(f)

            if login in users:
                self.ids.new_login.error = True
                self.ids.new_login.helper_text = "Логин уже занят"
                return

            users[login] = {"password": password, "messages": []}
            f.seek(0)
            json.dump(users, f)
            f.truncate()

        self.manager.transition.direction = 'right'
        self.manager.current = 'login'


class MainScreen(MDScreen):
    current_user = StringProperty('')

    def get_initials(self, name):
        """Генерирует инициалы из имени пользователя"""
        if not name:
            return ""

        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return name[:2].upper() if len(name) >= 2 else name[0].upper()

    def get_user_color(self, name):
        """Возвращает цвет на основе хэша имени"""
        if not name:
            return (0.5, 0.5, 0.5, 1)  # Серый по умолчанию - возвращаем кортеж вместо списка

        # Простая хэш-функция для генерации цвета
        h = hash(name) % 360
        return colorsys.hls_to_rgb(h / 360, 0.6, 0.8) + (1,)  # Возвращаем кортеж

    def on_pre_enter(self):
        # Устанавливаем текущего пользователя при входе на экран
        self.current_user = MDApp.get_running_app().current_user
        self.update_chats_list()

    def update_chats_list(self):
        try:
            users = load_users()
            print(f"[DEBUG] Все данные для {self.current_user}: {users.get(self.current_user, {})}")

            self.ids.chats_list.clear_widgets()

            if not hasattr(self, 'current_user') or not self.current_user:
                return

            current_user_data = users.get(self.current_user, {})
            messages = current_user_data.get("messages", [])
            unread_counts = current_user_data.get("unread", {})

            # Получаем уникальных собеседников
            partners = set()
            for msg in messages:
                if msg.get("from") != self.current_user:
                    partners.add(msg["from"])
                if msg.get("to") != self.current_user:
                    partners.add(msg["to"])

            # Сортируем по времени последнего сообщения
            sorted_partners = sorted(
                partners,
                key=lambda p: self.get_last_message_time(p) or datetime.min,
                reverse=True
            )

            for partner in sorted_partners:
                last_msg = self.get_last_message(partner)
                last_text = last_msg['text'][:50] + "..." if last_msg else "Нет сообщений"
                time_str = last_msg['time'].split()[1][:5] if last_msg else ""

                # Получаем количество непрочитанных сообщений
                unread = unread_counts.get(partner, 0)
                print(f"[DEBUG] Для {self.current_user} чат с {partner}: непрочитано={unread}")

                item = ChatListItem(
                    text=partner,
                    secondary_text=last_text,
                    time_text=time_str,
                    unread_count=unread
                )
                item.bind(on_item_press=lambda instance, p=partner: self.open_chat(p))
                self.ids.chats_list.add_widget(item)

        except Exception as e:
            print(f"Ошибка обновления списка: {str(e)}")

    def get_last_message(self, partner):
        with open('users.json', 'r') as f:
            users = json.load(f)

        messages = [msg for msg in users[self.current_user]["messages"]
                    if msg.get("from") == partner or msg.get("to") == partner]

        if messages:
            messages.sort(key=lambda x: datetime.strptime(x['time'], "%d.%m.%Y %H:%M"))
            return messages[-1]
        return None

    def get_last_message_time(self, partner):
        last_msg = self.get_last_message(partner)
        if last_msg:
            return datetime.strptime(last_msg['time'], "%d.%m.%Y %H:%M")
        return None

    def open_chat(self, recipient):
        if not recipient or not self.current_user:
            return

        # Проверяем существование получателя
        users = load_users()
        if recipient not in users:
            print(f"Пользователь {recipient} не найден")
            return

        app = MDApp.get_running_app()

        # Очищаем предыдущий ключ для этого чата
        app.chat_keys.pop(f"{self.current_user}_{recipient}", None)

        # Получаем экран чата и настраиваем его
        chat_screen = self.manager.get_screen('chat')
        chat_screen.chat_with = recipient
        chat_screen.current_user = self.current_user

        # Получаем экран ввода ключа
        encryption_screen = self.manager.get_screen('encryption_key')
        encryption_screen.current_user = self.current_user

        # Проверяем, есть ли сообщения в этом чате
        has_messages = any(
            msg for msg in users[self.current_user].get("messages", [])
            if msg.get("from") == recipient or msg.get("to") == recipient
        )

        if has_messages:
            # Если есть история сообщений - открываем экран ввода ключа
            self.manager.transition.direction = 'left'
            self.manager.current = 'encryption_key'
            encryption_screen.on_pre_enter()
        else:
            # Если чат новый - открываем экран создания ключа
            if 'create_key' not in self.manager.screen_names:
                self.manager.add_widget(CreateKeyScreen(name='create_key'))

            key_screen = self.manager.get_screen('create_key')
            key_screen.chat_with = recipient
            key_screen.current_user = self.current_user
            self.manager.transition.direction = 'left'
            self.manager.current = 'create_key'

    def logout(self):
        app = MDApp.get_running_app()
        app.logout()  # Вызываем метод очистки в приложении
        self.manager.transition.direction = 'right'
        self.manager.current = 'login'


class ChatScreen(MDScreen):
    chat_with = StringProperty('')
    current_user = StringProperty('')

    def show_encrypted_background(self):
        try:
            encrypted_view = ScrollView(size_hint=(1, 1))
            encrypted_list = MDList()

            with open('users.json', 'r') as f:
                users = json.load(f)

            messages = users.get(self.current_user, {}).get("messages", [])
            dialog_messages = [
                msg for msg in messages
                if msg.get("from") == self.chat_with or msg.get("to") == self.chat_with
            ]

            for msg in dialog_messages:
                try:
                    msg_time = datetime.strptime(msg['time'], "%d.%m.%Y %H:%M")
                    label = MDLabel(
                        text=f"{msg['from']} ({msg_time.strftime('%H:%M')}): [зашифрованное сообщение]",
                        size_hint_y=None,
                        height=dp(40),
                        halign="left" if msg['from'] != self.current_user else "right",
                        valign="center",
                        theme_text_color="Secondary",
                        font_style="Caption"
                    )
                    encrypted_list.add_widget(label)
                except Exception as e:
                    print(f"Ошибка создания зашифрованного вида: {e}")

            encrypted_view.add_widget(encrypted_list)
            return encrypted_view
        except Exception as e:
            print(f"Ошибка показа зашифрованного фона: {e}")
            return None

    def on_pre_enter(self):
        # Проверяем, есть ли ключ
        app = MDApp.get_running_app()
        if f"{self.current_user}_{self.chat_with}" not in app.chat_keys:
            # Если ключа нет - сразу открываем экран ввода ключа
            self.manager.current = 'encryption_key'

    def back_to_main(self):
        try:
            self.manager.transition.direction = 'right'
            self.manager.current = 'main'
        except Exception as e:
            print(f"Ошибка при возврате на главный экран: {e}")

    def on_pre_enter(self):
        try:
            app = MDApp.get_running_app()
            app.current_chat = self.chat_with

            # Обнуляем счетчик непрочитанных при открытии чата
            with open('users.json', 'r+') as f:
                users = json.load(f)

                if (self.current_user in users and
                        "unread" in users[self.current_user] and
                        self.chat_with in users[self.current_user]["unread"]):
                    users[self.current_user]["unread"][self.chat_with] = 0
                    f.seek(0)
                    json.dump(users, f, indent=4)
                    f.truncate()

            # Загружаем сообщения
            self.load_messages()

        except Exception as e:
            print(f"Ошибка при входе в чат: {e}")

        self.load_messages()

    def on_leave(self):
        # Фиксируем закрытие чата
        app = MDApp.get_running_app()  # Получаем app напрямую
        app.current_chat = None

    def send_message(self, message_text):
        if not message_text.strip():
            return

        try:
            app = MDApp.get_running_app()
            chat_key = app.chat_keys.get(f"{self.current_user}_{self.chat_with}")

            if not chat_key:
                # Проверяем, есть ли экран создания ключа
                if 'create_key' not in self.manager.screen_names:
                    self.manager.add_widget(CreateKeyScreen(name='create_key'))

                key_screen = self.manager.get_screen('create_key')
                key_screen.chat_with = self.chat_with
                key_screen.current_user = self.current_user
                self.manager.transition.direction = 'left'
                self.manager.current = 'create_key'
                return

            # Остальная часть метода без изменений
            encrypted_text = encrypt_aes256(message_text, chat_key)
            users = load_users()
            time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
            new_message = {
                "from": self.current_user,
                "to": self.chat_with,
                "text": encrypted_text,
                "time": time_str,
                "read": False
            }

            # Добавляем сообщение получателю
            if self.chat_with in users:
                users[self.chat_with].setdefault("messages", []).append(new_message)
                users[self.chat_with].setdefault("unread", {})

                if app.current_user != self.chat_with:
                    users[self.chat_with]["unread"][self.current_user] = \
                        users[self.chat_with]["unread"].get(self.current_user, 0) + 1

            # Добавляем сообщение отправителю
            if self.current_user in users:
                users[self.current_user].setdefault("messages", []).append(new_message)

            save_users(users)
            self.ids.message_input.text = ''
            self.load_messages()

            main_screen = self.manager.get_screen('main')
            main_screen.update_chats_list()

        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")

    def load_messages(self):
        try:
            self.ids.messages_list.clear_widgets()
            app = MDApp.get_running_app()
            chat_key = app.chat_keys.get(f"{self.current_user}_{self.chat_with}")

            try:
                with open('users.json', 'r') as f:
                    users = json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки users.json: {e}")
                return

            if self.current_user not in users:
                return

            # Помечаем сообщения как прочитанные
            try:
                for msg in users[self.current_user].get("messages", []):
                    if msg.get("from") == self.chat_with:
                        msg["read"] = True

                with open('users.json', 'w') as f:
                    json.dump(users, f, indent=4)
            except Exception as e:
                print(f"Ошибка обновления статуса сообщений: {e}")

            last_date = None
            dialog_messages = [
                msg for msg in users[self.current_user].get("messages", [])
                if msg.get("from") == self.chat_with or msg.get("to") == self.chat_with
            ]

            for msg in dialog_messages:
                try:
                    msg_time = datetime.strptime(msg['time'], "%d.%m.%Y %H:%M")
                    current_date = msg_time.strftime("%d.%m.%Y")

                    if current_date != last_date:
                        last_date = current_date
                        date_label = MDLabel(
                            text=current_date,
                            halign="center",
                            size_hint_y=None,
                            height=dp(30),
                            bold=True,
                            theme_text_color="Secondary"
                        )
                        self.ids.messages_list.add_widget(date_label)

                    # Пытаемся расшифровать сообщение
                    text_to_show = ""
                    try:
                        if chat_key:
                            decrypted_text = decrypt_aes256(msg['text'], chat_key)
                            text_to_show = f"{msg['from']} ({msg_time.strftime('%H:%M')}): {decrypted_text}"
                        else:
                            text_to_show = f"{msg['from']} ({msg_time.strftime('%H:%M')}): [зашифрованное сообщение]"
                    except Exception as decrypt_error:
                        text_to_show = f"{msg['from']} ({msg_time.strftime('%H:%M')}): [ошибка расшифровки]"
                        print(f"Ошибка расшифровки: {decrypt_error}")

                    label = MDLabel(
                        text=text_to_show,
                        size_hint_y=None,
                        height=dp(40),
                        halign="left" if msg['from'] != self.current_user else "right",
                        valign="center"
                    )
                    self.ids.messages_list.add_widget(label)

                except (KeyError, ValueError) as e:
                    print(f"Ошибка обработки сообщения: {e}")

        except Exception as e:
            print(f"Общая ошибка загрузки сообщений: {e}")


class MessengerApp(MDApp):
    def logout(self):
        """Очищаем все ключи при выходе"""
        self.chat_keys.clear()
        self.current_user = ''
        self.current_chat = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Messenger by Victor Grigorgev ver. Alfa 0.5.3"
        self._current_user = ''
        self.current_chat = None
        self.chat_keys = {}  # Словарь для хранения ключей в формате "user1_user2": "key"

    @property
    def current_user(self):
        return self._current_user

    @current_user.setter
    def current_user(self, value):
        self._current_user = value
        # Обновляем current_user во всех экранах при изменении
        if hasattr(self, 'root'):
            for screen in self.root.screens:
                if hasattr(screen, 'current_user'):
                    screen.current_user = value

    def build(self):
        init_database()
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"

        sm = MDScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(ChatScreen(name='chat'))

        encryption_screen = EncryptionKeyScreen(name='encryption_key')
        sm.add_widget(encryption_screen)

        return sm

if __name__ == '__main__':
    from kivy.core.window import Window

    Window.size = (400, 700)
    MessengerApp().run()