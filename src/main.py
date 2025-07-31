import flet as ft
import google.generativeai as genai
import os

# --- Класс для сообщений в виде "пузырей" ---

class ChatMessage(ft.Row):
    def __init__(self, message_text: str, message_user: str, message_type: str):
        super().__init__()
        
        self.vertical_alignment = ft.CrossAxisAlignment.START
        self.controls = [
            ft.CircleAvatar(
                content=ft.Text(self.get_initials(message_user)),
                color=ft.colors.WHITE,
                bgcolor=self.get_avatar_color(message_user),
            ),
            ft.Column(
                [
                    ft.Text(message_user, weight=ft.FontWeight.BOLD, size=14),
                    ft.Container(
                        content=ft.Text(message_text, selectable=True, size=16, color=ft.colors.BLACK),
                        padding=ft.padding.all(12),
                        border_radius=ft.border_radius.all(15),
                    )
                ],
                spacing=5,
                expand=True,
            ),
        ]
        
        if message_type == "user":
            self.alignment = ft.MainAxisAlignment.END
            self.controls.reverse()
            bubble = self.controls[0].controls[1]
            bubble.border_radius = ft.border_radius.only(top_left=15, top_right=15, bottom_left=15)
            bubble.bgcolor = ft.colors.BLUE_100
        else: # Gemini or Error
            self.alignment = ft.MainAxisAlignment.START
            bubble = self.controls[1].controls[1]
            bubble.border_radius = ft.border_radius.only(top_left=15, top_right=15, bottom_right=15)
            bubble.bgcolor = ft.colors.GREY_200


    def get_initials(self, user_name: str):
        return user_name[:1].capitalize() if user_name else "G"

    def get_avatar_color(self, user_name: str):
        if user_name == "Gemini":
            return ft.colors.TEAL_700
        return ft.colors.BLUE_700

# --- Основная функция приложения ---

def main(page: ft.Page):
    page.title = "Chat with Gemini"
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.bgcolor = ft.colors.BLUE_GREY_50 # Фон страницы

    # --- Переменные для хранения состояния чата ---
    chat_session = None

    # --- Элементы UI ---
    chat_history = ft.ListView(expand=True, spacing=20, auto_scroll=True, padding=ft.padding.all(20))
    message_input = ft.TextField(
        hint_text="Ask something...",
        autofocus=True,
        shift_enter=True,
        min_lines=1,
        max_lines=5,
        filled=True,
        expand=True,
        border_color=ft.colors.TRANSPARENT,
        border_radius=ft.border_radius.all(30),
        bgcolor=ft.colors.BLUE_GREY_100,
    )
    api_key_input = ft.TextField(
        hint_text="Enter your Google AI API Key...",
        password=True,
        can_reveal_password=True,
    )
    model_selector = ft.Dropdown(
        options=[
            ft.dropdown.Option("gemini-1.5-flash-latest"),
            ft.dropdown.Option("gemini-2.5-flash-lite"),
            ft.dropdown.Option("gemini-2.5-flash"),
            ft.dropdown.Option("gemini-2.5-pro"),
            ft.dropdown.Option("gemini-2.0-flash"),
            ft.dropdown.Option("gemini-2.0-flash-lite"),
            ft.dropdown.Option("gemma-3n-e2b-it"),
            ft.dropdown.Option("gemma-3n-e4b-it"),
            ft.dropdown.Option("gemma-3-27b-it"),
        ],
        value="gemini-1.5-flash-latest",
        label="Select Model",
    )
    status_text = ft.Text()
    chat_title = ft.Text("Chat", size=20, weight=ft.FontWeight.BOLD)
    
    # --- Загрузка настроек при старте ---
    def on_page_load(e):
        if page.client_storage.contains_key("api_key"):
            api_key_input.value = page.client_storage.get("api_key")
        if page.client_storage.contains_key("model_name"):
            model_selector.value = page.client_storage.get("model_name")
        page.update()
    
    page.on_connect = on_page_load

    # --- Функции-обработчики ---

    def send_message_click(e):
        nonlocal chat_session
        user_message = message_input.value
        if not user_message or not chat_session:
            return

        chat_history.controls.append(ChatMessage(message_text=user_message, message_user="You", message_type="user"))
        message_input.value = ""

        loading = ft.Row([ft.ProgressRing(width=20, height=20, stroke_width=2), ft.Text("Gemini is thinking...")], alignment=ft.MainAxisAlignment.CENTER)
        chat_history.controls.append(loading)
        page.update()

        try:
            response = chat_session.send_message(user_message, stream=True)
            
            gemini_response_text = ""
            gemini_response_message = ChatMessage(message_text="", message_user="Gemini", message_type="gemini")
            chat_history.controls.append(gemini_response_message)
            page.update()

            for chunk in response:
                gemini_response_text += chunk.text
                text_container = gemini_response_message.controls[1].controls[1]
                text_container.content.value = gemini_response_text
                page.update()
            
        except Exception as err:
            chat_history.controls.append(ft.Row([ft.Icon(ft.icons.ERROR, color=ft.colors.RED), ft.Text(f"An error occurred: {err}")]))
        
        finally:
            chat_history.controls.remove(loading)
            message_input.focus()
            page.update()

    message_input.on_submit = send_message_click

    def start_chat_click(e):
        nonlocal chat_session
        api_key = api_key_input.value
        selected_model = model_selector.value

        if not api_key:
            status_text.value = "Please enter your API key."
            status_text.color = ft.colors.RED
            page.update()
            return
        
        try:
            status_text.value = "Configuring Gemini..."
            status_text.color = ft.colors.GREY
            page.update()

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(selected_model)
            chat_session = model.start_chat(history=[])
            
            # Сохраняем настройки
            page.client_storage.set("api_key", api_key)
            page.client_storage.set("model_name", selected_model)
            
            settings_view.visible = False
            chat_view.visible = True
            chat_title.value = f"Chat with {selected_model}"
            
            chat_history.controls.clear()
            chat_history.controls.append(ChatMessage(message_text="Hello! How can I help you today?", message_user="Gemini", message_type="gemini"))
            message_input.focus()
            page.update()

        except Exception as err:
            status_text.value = f"Configuration failed. The API key is likely invalid."
            status_text.color = ft.colors.RED
            page.update()

    def show_settings_click(e):
        chat_view.visible = False
        settings_view.visible = True
        page.update()

    # --- Слои UI ---
    
    settings_view = ft.Column(
        [
            ft.Icon(ft.icons.SETTINGS_SUGGEST, size=64, color=ft.colors.BLUE_GREY_400),
            ft.Text("Configure Chat", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Select a model and enter your Google AI API key.", text_align=ft.TextAlign.CENTER, color=ft.colors.GREY),
            model_selector,
            api_key_input,
            ft.FilledButton("Start Chatting", on_click=start_chat_click, icon=ft.icons.ROCKET_LAUNCH, height=48),
            status_text
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20,
        visible=True,
        expand=True,
    )

    chat_view = ft.Column(
        [
            ft.Container(
                content=ft.Row(
                    [
                        chat_title,
                        ft.IconButton(ft.icons.SETTINGS, on_click=show_settings_click, tooltip="Settings")
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                padding=ft.padding.symmetric(horizontal=20, vertical=10)
            ),
            ft.Divider(height=1),
            chat_history,
            ft.Container(
                content=ft.Row(
                    [
                        message_input,
                        ft.IconButton(icon=ft.icons.SEND_ROUNDED, tooltip="Send message", on_click=send_message_click, icon_size=24, bgcolor=ft.colors.BLUE_500, icon_color=ft.colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(vertical=10, horizontal=20),
            )
        ],
        visible=False,
        expand=True,
    )
    
    page.add(ft.Container(
        content=ft.Stack([settings_view, chat_view]),
        width=700,
        height=800,
        padding=20,
        border_radius=10,
        bgcolor=ft.colors.WHITE,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.colors.BLUE_GREY_300,
            offset=ft.Offset(0, 0),
            blur_style=ft.ShadowBlurStyle.OUTER,
        )
    ))
    page.update()

# --- Запуск приложения ---
if __name__ == "__main__":
    ft.app(target=main)
    # ft.app(target=main, port=9002, view=ft.AppView.WEB_BROWSER, assets_dir="assets")
