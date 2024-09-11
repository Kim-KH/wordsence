import os
import sys
import json
import random
import csv
import shutil
import tempfile
import threading
from google.cloud import texttospeech

from kivy.config import Config
from kivy.core.text import LabelBase
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.text import LabelBase
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.treeview import TreeView, TreeViewLabel
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.filechooser import FileChooserListView
from functools import partial
from kivy.resources import resource_add_path
resource_add_path('C:/PT/fonts/NanumGothic-Regular.ttf')  # 폰트 파일이 있는 경로로 수정해주세요
LabelBase.register(name='NanumGothic', fn_regular='C:/PT/fonts/NanumGothic-Regular.ttf')
Config.set('kivy', 'default_font', ['NanumGothic','C:/PT/fonts/NanumGothic-Regular.ttf'])

# LabelBase.register(name='NanumGothic', fn_regular='C:/PT/fonts/NanumGothic-Regular.ttf')

class VocabularyApp(App):
    def build(self):
        self.title = "단어.문장 암기장"
        self.filename = ""
        self.tts_event = threading.Event()
        self.current_row = 0
        self.current_column = 1
        self.folders = self.load_folders()
        if "복습 절실" not in self.folders:
            self.folders["복습 절실"] = {
                "name": "복습 절실",
                "words": [],
                "children": {}
            }
        self.current_folder = self.folders["복습 절실"]
        self.current_words = self.current_folder["words"]
        self.word_hidden = {}
        self.meaning_hidden = {}
        self.original_words = self.current_words.copy()
        self.is_shuffled = False
        self.temp_dir = tempfile.mkdtemp()
        self.font_size = 14
        self.completed_words = {folder: set() for folder in self.folders}

        self.word_column_visible = True
        self.meaning_column_visible = True

        self.tts_client = texttospeech.TextToSpeechClient()

        self.voice_options = {
            "en-US": ["en-US-Neural2-A", "en-US-Standard-B", "en-US-Neural2-C", "en-US-Neural2-D", "en-US-Neural2-E"],
            "fr-FR": ["fr-FR-Standard-A", "fr-FR-Standard-B", "fr-FR-Standard-C", "fr-FR-Standard-D", "fr-FR-Standard-E"],
            "de-DE": ["de-DE-Standard-A", "de-DE-Standard-B", "de-DE-Standard-C", "de-DE-Standard-D", "de-DE-Standard-E", "de-DE-Standard-F"],
            "ko-KR": ["ko-KR-Neural2-A", "ko-KR-Neural2-B", "ko-KR-Neural2-C"],
            "cmn-CN": ["cmn-CN-Standard-A", "cmn-CN-Standard-B", "cmn-CN-Standard-C", "cmn-CN-Standard-D"],
            "ja-JP": ["ja-JP-Standard-A", "ja-JP-Standard-B", "ja-JP-Standard-C", "ja-JP-Standard-D"]
        }

        self.word_voice = self.voice_options["en-US"][0]
        self.meaning_voice = self.voice_options["ko-KR"][0]
        self.word_language = "en-US"
        self.meaning_language = "ko-KR"
        self.repeat_count = 1
        self.start_row = 1
        self.end_row = 0
        self.is_playing = False
        self.is_paused = False
        self.current_index = 0
        self.current_end_index = 0
        self.current_remaining_repeats = 0
        self.auto_play_index = 0

        # UI 구성
        self.main_layout = BoxLayout(orientation='vertical')

        # 메뉴 바
        menu_bar = BoxLayout(size_hint_y=None, height=30)
        menu_bar.add_widget(Button(text="파일", font_name="NanumGothic", on_press=self.show_file_menu))
        menu_bar.add_widget(Button(text="언어", font_name="NanumGothic", on_press=self.show_language_menu))
        menu_bar.add_widget(Button(text="보기", font_name="NanumGothic", on_press=self.show_view_menu))
        self.main_layout.add_widget(menu_bar)

        # 폴더 및 단어 관리 버튼
        management_bar = BoxLayout(size_hint_y=None, height=30)
        management_bar.add_widget(Button(text="폴더 관리", font_name="NanumGothic", on_press=self.show_folder_management))
        management_bar.add_widget(Button(text="폴더 정렬", font_name="NanumGothic", on_press=self.show_folder_sort))
        management_bar.add_widget(Button(text="단어 관리", font_name="NanumGothic", on_press=self.show_word_management))
        management_bar.add_widget(Button(text="단어 정렬", font_name="NanumGothic", on_press=self.show_word_sort))
        management_bar.add_widget(Button(text="단어/뜻 위치 바꾸기", font_name="NanumGothic", on_press=self.swap_word_meaning))
        self.main_layout.add_widget(management_bar)

        # 메인 콘텐츠 영역
        content_layout = BoxLayout()

        # 폴더 트리뷰
        self.folder_tree = TreeView(root_options=dict(text='Root'))
        content_layout.add_widget(self.folder_tree)

        # 단어 목록
        self.word_list_scroll = ScrollView(size_hint_x=0.7)
        self.word_list = GridLayout(cols=3, spacing=[10, 10], size_hint_y=None)
        self.word_list.bind(minimum_height=self.word_list.setter('height'))
        self.word_list_scroll.add_widget(self.word_list)
        content_layout.add_widget(self.word_list_scroll)

        self.main_layout.add_widget(content_layout)

        # 자동 재생 컨트롤
        auto_play_layout = BoxLayout(size_hint_y=None, height=30)
        auto_play_layout.add_widget(Label(text="반복 횟수:", font_name="NanumGothic"))
        self.repeat_count_input = TextInput(text=str(self.repeat_count), multiline=False, size_hint_x=0.1)
        auto_play_layout.add_widget(self.repeat_count_input)
        auto_play_layout.add_widget(Label(text="시작 행:", font_name="NanumGothic"))
        self.start_row_input = TextInput(text=str(self.start_row), multiline=False, size_hint_x=0.1, font_name="NanumGothic")
        auto_play_layout.add_widget(self.start_row_input)
        auto_play_layout.add_widget(Label(text="끝 행:", font_name="NanumGothic"))
        self.end_row_input = TextInput(text=str(self.end_row), multiline=False, size_hint_x=0.1, font_name="NanumGothic")
        auto_play_layout.add_widget(self.end_row_input)
        auto_play_layout.add_widget(Button(text="자동 재생 시작", font_name="NanumGothic", on_press=self.start_auto_play))
        auto_play_layout.add_widget(Button(text="자동 재생 중지", font_name="NanumGothic", on_press=self.stop_auto_play))
        auto_play_layout.add_widget(Button(text="자동 재생 멈춤", font_name="NanumGothic", on_press=self.pause_auto_play))
        auto_play_layout.add_widget(Button(text="자동 재생 재개", font_name="NanumGothic", on_press=self.resume_auto_play))
        auto_play_layout.add_widget(Button(text="단어만 연속 재생", font_name="NanumGothic", on_press=self.repeat_words))
        self.main_layout.add_widget(auto_play_layout)

        self.load_folder_tree()
        self.load_progress()

        return self.main_layout

    # Part 2

    def load_folders(self):
        try:
            if os.path.exists("vocabulary.json"):
                with open("vocabulary.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print("vocabulary.json 파일이 없습니다. 새로운 파일을 생성합니다.")
                return {"root": {"name": "root", "words": [], "children": {}}}
        except Exception as e:
            print(f"폴더 로딩 중 오류 발생: {e}")
            return {"root": {"name": "root", "words": [], "children": {}}}

    def save_folders(self):
        try:
            cleaned_folders = self.clean_folder_structure(self.folders)
            with open("vocabulary.json", "w", encoding="utf-8") as f:
                json.dump(cleaned_folders, f, ensure_ascii=False, indent=2)
            print("vocabulary.json 파일이 성공적으로 저장되었습니다.")
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {e}")

    def clean_folder_structure(self, folders):
        cleaned = {}
        for key, value in folders.items():
            if key not in ["root", "name"]:
                if isinstance(value, dict):
                    cleaned[key] = {
                        "name": key,
                        "words": value.get("words", []),
                        "children": self.clean_folder_structure(value.get("children", {}))
                    }
        return cleaned

    def load_folder_tree(self):
        self.folder_tree.clear_widgets()
        root = self.folder_tree.add_node(TreeViewLabel(text="Root", font_name='NanumGothic'))
        self._load_folder_recursive(root, self.folders)

    def _load_folder_recursive(self, parent_node, folder_data):
        if isinstance(folder_data, dict):
            for name, data in folder_data.items():
                if name != 'words' and name != 'name':
                    node = self.folder_tree.add_node(TreeViewLabel(text=name, font_name='NanumGothic'), parent_node)
                    if isinstance(data, dict):
                        self._load_folder_recursive(node, data)

    #def refresh_folder_tree(self):
        #self.folder_tree.clear_widgets()
        #root = self.folder_tree.add_node(TreeViewLabel(text="Root", font_name='NanumGothic'))
        #self.load_subfolders(root, self.folders)
        #self.current_words = []
        #self.show_words()

    def load_subfolders(self, parent_node, children):
        for child_name, child_data in children.items():
            if isinstance(child_data, dict) and 'name' in child_data:
                child_node = self.folder_tree.add_node(TreeViewLabel(text=child_data['name'], font_name='NanumGothic'), parent_node)
                if "children" in child_data and isinstance(child_data["children"], dict):
                    self.load_subfolders(child_node, child_data["children"])

    def show_words(self):
        self.word_list.clear_widgets()
        self.word_list.cols = 3  # 3열로 설정 (번호, 단어, 의미)
        self.word_list.spacing = [10, 10]  # 열과 행 사이의 간격 설정
        
        for i, word in enumerate(self.current_words, start=1):
            word_text = '********' if self.word_hidden.get(str(i), False) else word.get('word', '')
            meaning_text = '********' if self.meaning_hidden.get(str(i), False) else word.get('meaning', '')

            self.word_list.add_widget(Label(text=str(i), size_hint_y=None, height=40, font_name='NanumGothic'))
            self.word_list.add_widget(Button(text=word_text, size_hint_y=None, height=40, on_press=lambda x, idx=i: self.on_word_press(idx), font_name='NanumGothic'))
            self.word_list.add_widget(Button(text=meaning_text, size_hint_y=None, height=40, on_press=lambda x, idx=i: self.on_meaning_press(idx), font_name='NanumGothic'))

        # 빈 공간 채우기
        while len(self.word_list.children) % 3 != 0:
            self.word_list.add_widget(Widget())

    def on_word_press(self, index):
        word_data = self.current_words[index - 1]
        self.play_tts(word_data['word'], word_data.get('word_lang', self.word_language), self.word_voice)

    def on_meaning_press(self, index):
        word_data = self.current_words[index - 1]
        self.play_tts(word_data['meaning'], word_data.get('meaning_lang', self.meaning_language), self.meaning_voice)

    def show_file_menu(self, instance):
        menu = BoxLayout(orientation='vertical')
        menu.add_widget(Button(text="파일 불러오기", font_name="NanumGothic", on_press=self.load_words_from_file))
        menu.add_widget(Button(text="단어장 백업", font_name="NanumGothic", on_press=self.backup_vocabulary))
        menu.add_widget(Button(text="백업 파일 불러오기", font_name="NanumGothic", on_press=self.load_backup_file))
        menu.add_widget(Button(text="단어장 내보내기", font_name="NanumGothic", on_press=self.export_vocabulary))

        popup = Popup(title="파일 메뉴", content=menu, size_hint=(0.4, 0.4))
        popup.open()

    def show_language_menu(self, instance):
        menu = BoxLayout(orientation='vertical')
        word_lang_spinner = Spinner(text='단어 언어', font_name="NanumGothic", values=list(self.voice_options.keys()))
        word_lang_spinner.bind(text=self.on_word_language_select)
        menu.add_widget(word_lang_spinner)

        meaning_lang_spinner = Spinner(text='의미 언어', font_name="NanumGothic", values=list(self.voice_options.keys()))
        meaning_lang_spinner.bind(text=self.on_meaning_language_select)
        menu.add_widget(meaning_lang_spinner)

        popup = Popup(title="언어 설정", content=menu, size_hint=(0.4, 0.4))
        popup.open()

    def on_word_language_select(self, spinner, text):
        self.word_language = text
        self.word_voice = self.voice_options[text][0]

    def on_meaning_language_select(self, spinner, text):
        self.meaning_language = text
        self.meaning_voice = self.voice_options[text][0]

    def show_view_menu(self, instance):
        menu = BoxLayout(orientation='vertical')
        menu.add_widget(Button(text="폰트 크게 (+)", font_name="NanumGothic", on_press=self.increase_font))
        menu.add_widget(Button(text="폰트 작게 (-)", font_name="NanumGothic", on_press=self.decrease_font))

        popup = Popup(title="보기 메뉴", content=menu, size_hint=(0.4, 0.4))
        popup.open()

    def show_folder_management(self, instance):
        menu = BoxLayout(orientation='vertical')
        menu.add_widget(Button(text="새 폴더", font_name="NanumGothic", on_press=self.create_folder))
        menu.add_widget(Button(text="하위 폴더", font_name="NanumGothic", on_press=self.create_subfolder))
        menu.add_widget(Button(text="이름 변경", font_name="NanumGothic", on_press=self.rename_folder))
        menu.add_widget(Button(text="삭제", font_name="NanumGothic", on_press=self.delete_folder))

        popup = Popup(title="폴더 관리", content=menu, size_hint=(0.4, 0.4))
        popup.open()


    # Part 3:

    def show_folder_sort(self, instance):
        menu = BoxLayout(orientation='vertical')
        menu.add_widget(Button(text="생성순 정렬", font_name="NanumGothic", on_press=lambda x: self.sort_folders("creation")))
        menu.add_widget(Button(text="오름차순 정렬", font_name="NanumGothic", on_press=lambda x: self.sort_folders("asc")))
        menu.add_widget(Button(text="내림차순 정렬", font_name="NanumGothic", on_press=lambda x: self.sort_folders("desc")))

        popup = Popup(title="폴더 정렬", content=menu, size_hint=(0.4, 0.4))
        popup.open()

    def show_word_management(self, instance):
        menu = BoxLayout(orientation='vertical')
        menu.add_widget(Button(text="단어 추가", font_name="NanumGothic", on_press=self.add_word))
        menu.add_widget(Button(text="단어 수정", font_name="NanumGothic", on_press=self.edit_word))
        menu.add_widget(Button(text="섞기", font_name="NanumGothic", on_press=self.shuffle_words))
        menu.add_widget(Button(text="복귀", font_name="NanumGothic", on_press=self.restore_words))
        menu.add_widget(Button(text="단어 삭제", font_name="NanumGothic", on_press=self.delete_word))
        menu.add_widget(Button(text="단어 전체 삭제", font_name="NanumGothic", on_press=self.delete_all_words))

        popup = Popup(title="단어 관리", content=menu, size_hint=(0.4, 0.4))
        popup.open()

    def show_word_sort(self, instance):
        menu = BoxLayout(orientation='vertical')
        menu.add_widget(Button(text="단어 오름차순", font_name="NanumGothic", on_press=lambda x: self.sort_words('word', False)))
        menu.add_widget(Button(text="단어 내림차순", font_name="NanumGothic", on_press=lambda x: self.sort_words('word', True)))
        menu.add_widget(Button(text="의미 오름차순", font_name="NanumGothic", on_press=lambda x: self.sort_words('meaning', False)))
        menu.add_widget(Button(text="의미 내림차순", font_name="NanumGothic", on_press=lambda x: self.sort_words('meaning', True)))
        menu.add_widget(Button(text="복귀", on_press=self.restore_original_order))

        popup = Popup(title="단어 정렬", content=menu, size_hint=(0.4, 0.4))
        popup.open()

    def swap_word_meaning(self, instance):
        for word in self.current_words:
            word['word'], word['meaning'] = word['meaning'], word['word']
            word['word_lang'], word['meaning_lang'] = self.meaning_language, self.word_language

        self.word_language, self.meaning_language = self.meaning_language, self.word_language
        self.word_voice, self.meaning_voice = self.meaning_voice, self.word_voice
        
        self.show_words()

    def start_auto_play(self, instance):
        self.repeat_count = int(self.repeat_count_input.text)
        self.start_row = int(self.start_row_input.text)
        self.end_row = int(self.end_row_input.text)
        
        if not self.is_playing and self.current_words:
            self.is_playing = True
            self.is_paused = False
            start_index = max(0, self.start_row - 1)
            end_index = min(self.end_row - 1, len(self.current_words) - 1)
            self.play_word(start_index, end_index, self.repeat_count)

    def stop_auto_play(self, instance):
        self.is_playing = False
        self.is_paused = False

    def pause_auto_play(self, instance):
        self.is_paused = True

    def resume_auto_play(self, instance):
        if self.is_paused:
            self.is_paused = False
            self.play_word(self.current_index, self.current_end_index, self.current_remaining_repeats)

    def repeat_words(self, instance):
        self.repeat_count = int(self.repeat_count_input.text)
        self.start_row = int(self.start_row_input.text)
        self.end_row = int(self.end_row_input.text)
        
        if not self.is_playing and self.current_words:
            self.is_playing = True
            self.is_paused = False
            start_index = max(0, self.start_row - 1)
            end_index = min(self.end_row - 1, len(self.current_words) - 1)
            self.current_index = start_index
            self.current_remaining_repeats = self.repeat_count
            self.play_only_words(end_index)

    def play_word(self, index, end_index, remaining_repeats):
        if not self.is_playing or index > end_index:
            self.is_playing = False
            return
        
        self.current_index = index
        self.current_end_index = end_index
        self.current_remaining_repeats = remaining_repeats

        if self.is_paused:
            return

        word = self.current_words[index]
        self.play_tts(word['word'], word.get('word_lang', self.word_language), self.word_voice,
                       lambda: self.play_meaning(index, end_index, remaining_repeats))

# Part 4:

    def play_meaning(self, index, end_index, remaining_repeats):
        if not self.is_playing or self.is_paused:
            return

        word = self.current_words[index]
        self.play_tts(word['meaning'], word.get('meaning_lang', self.meaning_language), self.meaning_voice,
                       lambda: self.next_iteration(index, end_index, remaining_repeats))

    def next_iteration(self, index, end_index, remaining_repeats):
        if not self.is_playing or self.is_paused:
            return

        remaining_repeats -= 1
        if remaining_repeats > 0:
            Clock.schedule_once(lambda dt: self.play_word(index, end_index, remaining_repeats), 1)
        else:
            next_index = index + 1
            if next_index <= end_index:
                Clock.schedule_once(lambda dt: self.play_word(next_index, end_index, self.repeat_count), 1)
            else:
                self.is_playing = False

    def play_only_words(self, end_index):
        if not self.is_playing or self.current_index > end_index:
            self.is_playing = False
            return

        word = self.current_words[self.current_index]
        self.play_tts(word['word'], word.get('word_lang', self.word_language), self.word_voice,
                       lambda: self.next_word(end_index))

    def next_word(self, end_index):
        self.current_remaining_repeats -= 1
        if self.current_remaining_repeats > 0:
            Clock.schedule_once(lambda dt: self.play_only_words(end_index), 1)
        else:
            self.current_index += 1
            self.current_remaining_repeats = self.repeat_count
            Clock.schedule_once(lambda dt: self.play_only_words(end_index), 1)

    def play_tts(self, text, language, voice_name, callback=None):
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language,
            name=voice_name
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        try:
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
        except Exception as e:
            print(f"TTS 오류: {e}")
            return

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.write(response.audio_content)
        temp_file.close()

        sound = SoundLoader.load(temp_file.name)
        if sound:
            sound.play()
            sound.bind(on_stop=lambda instance: self.on_sound_stop(temp_file.name, callback))

    def on_sound_stop(self, filename, callback):
        try:
            os.unlink(filename)
        except PermissionError:
            print(f"Error deleting file {filename}: file being used.")
        if callback:
            callback()

    def create_folder(self, instance):
        content = BoxLayout(orientation='vertical')
        folder_name_input = TextInput(multiline=False, font_name='NanumGothic')
        content.add_widget(Label(text='폴더 이름:', font_name='NanumGothic'))
        content.add_widget(folder_name_input)
        button = Button(text='생성', font_name='NanumGothic')
        content.add_widget(button)
        
        popup = Popup(title='폴더 생성', content=content, size_hint=(None, None), size=(400, 200))
        
        def on_create(instance):
            folder_name = folder_name_input.text
            if folder_name and folder_name not in self.folders:
                self.folders[folder_name] = {"words": []}
                self.save_folders()
                self.load_folder_tree()
            popup.dismiss()
        
        button.bind(on_press=on_create)
        popup.open()

    def create_subfolder(self, instance):
        if not self.folder_tree.selected_node or self.folder_tree.selected_node.text == "Root":
            Popup(title='오류', content=Label(text='상위 폴더를 선택해주세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            return

        content = BoxLayout(orientation='vertical')
        subfolder_name_input = TextInput(multiline=False, font_name='NanumGothic')
        content.add_widget(Label(text='하위 폴더 이름:', font_name='NanumGothic'))
        content.add_widget(subfolder_name_input)
        button = Button(text='생성', font_name='NanumGothic')
        content.add_widget(button)
        
        popup = Popup(title='하위 폴더 생성', content=content, size_hint=(None, None), size=(400, 200))
        
        def on_create(instance):
            subfolder_name = subfolder_name_input.text
            if subfolder_name:
                parent_path = self.get_folder_path(self.folder_tree.selected_node)
                parent_folder = self.get_folder_from_path(parent_path)
                if parent_folder is not None:
                    if subfolder_name not in parent_folder:
                        parent_folder[subfolder_name] = {"words": []}
                        self.save_folders()
                        self.load_folder_tree()
                else:
                    Popup(title='오류', content=Label(text='상위 폴더를 찾을 수 없습니다.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            popup.dismiss()
        
        button.bind(on_press=on_create)
        popup.open()

# Part 5:

    def rename_folder(self, instance):
        if not self.folder_tree.selected_node:
            Popup(title='오류', content=Label(text='폴더를 선택해주세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            return

        content = BoxLayout(orientation='vertical')
        self.new_folder_name_input = TextInput(multiline=False, text=self.folder_tree.selected_node.text)
        content.add_widget(Label(text='새 폴더 이름:',font_name="NanumGothic"))
        content.add_widget(self.new_folder_name_input)
        button = Button(text='변경',font_name="NanumGothic")
        content.add_widget(button)
        
        popup = Popup(title='폴더 이름 변경', content=content, size_hint=(None, None), size=(400, 200))
        
        def on_rename(instance):
            new_name = self.new_folder_name_input.text
            if new_name and new_name != self.folder_tree.selected_node.text:
                old_name = self.folder_tree.selected_node.text
                parent_path = self.get_folder_path(self.folder_tree.selected_node.parent_node)
                parent_folder = self.get_folder_from_path(parent_path)
                if parent_folder:
                    if 'children' in parent_folder:
                        parent_folder['children'][new_name] = parent_folder['children'].pop(old_name)
                        parent_folder['children'][new_name]['name'] = new_name
                    else:
                        parent_folder[new_name] = parent_folder.pop(old_name)
                        parent_folder[new_name]['name'] = new_name
                else:
                    self.folders[new_name] = self.folders.pop(old_name)
                    self.folders[new_name]['name'] = new_name
                self.save_folders()
                self.load_folder_tree()
            popup.dismiss()
        
        button.bind(on_press=on_rename)
        popup.open()

    def delete_folder(self, instance):
        if not self.folder_tree.selected_node or self.folder_tree.selected_node.text == "Root":
            Popup(title='오류', content=Label(text='삭제할 폴더를 선택해주세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            return

        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=f"'{self.folder_tree.selected_node.text}' 폴더를 삭제하시겠습니까?", font_name='NanumGothic'))
        buttons = BoxLayout()
        yes_button = Button(text='예', font_name='NanumGothic')
        no_button = Button(text='아니오', font_name='NanumGothic')
        buttons.add_widget(yes_button)
        buttons.add_widget(no_button)
        content.add_widget(buttons)
        
        popup = Popup(title='폴더 삭제 확인', content=content, size_hint=(None, None), size=(300, 200))
        
        def on_yes(instance):
            folder_path = self.get_folder_path(self.folder_tree.selected_node)
            if len(folder_path) > 0:
                parent_folder = self.get_folder_from_path(folder_path[:-1])
                folder_name = folder_path[-1]
                if parent_folder is not None:
                    if folder_name in parent_folder:
                        del parent_folder[folder_name]
                        self.save_folders()
                        self.load_folder_tree()
                    else:
                        Popup(title='오류', content=Label(text='폴더를 찾을 수 없습니다.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
                else:
                    if folder_name in self.folders:
                        del self.folders[folder_name]
                        self.save_folders()
                        self.load_folder_tree()
                    else:
                        Popup(title='오류', content=Label(text='폴더를 찾을 수 없습니다.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            popup.dismiss()
        
        def on_no(instance):
            popup.dismiss()
        
        yes_button.bind(on_press=on_yes)
        no_button.bind(on_press=on_no)
        popup.open()


    def get_folder_path(self, node):
        path = []
        while node is not None and node.text != "Root":
            path.insert(0, node.text)
            node = node.parent_node
        return path

    def get_folder_from_path(self, path):
        folder = self.folders
        for name in path:
            if name in folder:
                folder = folder[name]
            elif 'children' in folder and name in folder['children']:
                folder = folder['children'][name]
            else:
                return None
        return folder
    
    def add_word(self, instance):
        content = BoxLayout(orientation='vertical')
        word_input = TextInput(multiline=False, font_name='NanumGothic')
        meaning_input = TextInput(multiline=False, font_name='NanumGothic')
        content.add_widget(Label(text='단어:', font_name='NanumGothic'))
        content.add_widget(word_input)
        content.add_widget(Label(text='의미:', font_name='NanumGothic'))
        content.add_widget(meaning_input)
        button = Button(text='추가', font_name='NanumGothic')
        content.add_widget(button)
        
        popup = Popup(title='단어 추가', content=content, size_hint=(None, None), size=(400, 300))
        
        def on_add(instance):
            word = word_input.text
            meaning = meaning_input.text
            if word and meaning:
                self.current_words.append({"word": word, "meaning": meaning, "word_lang": self.word_language, "meaning_lang": self.meaning_language})
                self.show_words()
                self.save_folders()
            popup.dismiss()
        
        button.bind(on_press=on_add)
        popup.open()

    # Par6 6:

    def edit_word(self, instance):
        if not self.current_words:
            Popup(title='오류', content=Label(text='수정할 단어가 없습니다.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            return

        content = BoxLayout(orientation='vertical')
        self.word_index_input = TextInput(multiline=False)
        self.edit_word_input = TextInput(multiline=False)
        self.edit_meaning_input = TextInput(multiline=False)
        content.add_widget(Label(text='수정할 단어 번호:', font_name='NanumGothic'))
        content.add_widget(self.word_index_input)
        content.add_widget(Label(text='새 단어:', font_name='NanumGothic'))
        content.add_widget(self.edit_word_input)
        content.add_widget(Label(text='새 뜻:', font_name='NanumGothic'))
        content.add_widget(self.edit_meaning_input)
        button = Button(text='수정', font_name='NanumGothic')
        content.add_widget(button)
        
        popup = Popup(title='단어 수정', content=content, size_hint=(None, None), size=(300, 300))
        
        def on_edit(instance):
            try:
                index = int(self.word_index_input.text) - 1
                if 0 <= index < len(self.current_words):
                    new_word = self.edit_word_input.text
                    new_meaning = self.edit_meaning_input.text
                    if new_word and new_meaning:
                        self.current_words[index]['word'] = new_word
                        self.current_words[index]['meaning'] = new_meaning
                        self.show_words()
                        self.save_folders()
                        popup.dismiss()
                    else:
                        Popup(title='오류', content=Label(text='단어와 뜻을 모두 입력하세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
                else:
                    Popup(title='오류', content=Label(text='올바른 단어 번호를 입력하세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            except ValueError:
                Popup(title='오류', content=Label(text='올바른 숫자를 입력하세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
        
        button.bind(on_press=on_edit)
        popup.open()

    def shuffle_words(self, instance):
        random.shuffle(self.current_words)
        self.is_shuffled = True
        self.show_words()

    def restore_words(self, instance):
        if self.is_shuffled:
            self.current_words = self.original_words[:]
            self.is_shuffled = False
            self.show_words()

    def delete_word(self, instance):
        if not self.current_words:
            Popup(title='오류', content=Label(text='삭제할 단어가 없습니다.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            return

        content = BoxLayout(orientation='vertical')
        self.delete_word_index_input = TextInput(multiline=False)
        content.add_widget(Label(text='삭제할 단어 번호:', font_name="NanumGothic"))
        content.add_widget(self.delete_word_index_input)
        button = Button(text='삭제', font_name="NanumGothic")
        content.add_widget(button)
        
        popup = Popup(title='단어 삭제', content=content, size_hint=(None, None), size=(300, 200))
        
        def on_delete(instance):
            try:
                index = int(self.delete_word_index_input.text) - 1
                if 0 <= index < len(self.current_words):
                    del self.current_words[index]
                    self.show_words()
                    self.save_folders()
                    popup.dismiss()
                else:
                    Popup(title='오류', content=Label(text='올바른 단어 번호를 입력하세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            except ValueError:
                Popup(title='오류', content=Label(text='올바른 숫자를 입력하세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
        
        button.bind(on_press=on_delete)
        popup.open()

    def delete_all_words(self, instance):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text='모든 단어를 삭제하시겠습니까?',font_name="NanumGothic"))
        buttons = BoxLayout()
        yes_button = Button(text='예',font_name="NanumGothic")
        no_button = Button(text='아니오',font_name="NanumGothic")
        buttons.add_widget(yes_button)
        buttons.add_widget(no_button)
        content.add_widget(buttons)
        
        popup = Popup(title='전체 단어 삭제 확인', content=content, size_hint=(None, None), size=(300, 200))
        
        def on_yes(instance):
            self.current_words.clear()
            self.show_words()
            self.save_folders()
            popup.dismiss()
        
        def on_no(instance):
            popup.dismiss()
        
        yes_button.bind(on_press=on_yes)
        no_button.bind(on_press=on_no)
        popup.open()

# Part 7:

    def sort_words(self, key, reverse):
        self.current_words.sort(key=lambda x: x[key].lower(), reverse=reverse)
        self.show_words()

    def restore_original_order(self, instance):
        if hasattr(self, 'original_words'):
            self.current_words = self.original_words[:]
            self.show_words()

    def load_words_from_file(self, instance):
        if not self.folder_tree.selected_node:
            Popup(title='오류', content=Label(text='폴더를 선택해주세요.', font_name='NanumGothic'), size_hint=(None, None), size=(300, 150)).open()
            return

        filechooser = FileChooserListView(filters=['*.csv', '*.txt'])
        
        def load(instance, selection, touch):
            if selection:
                file_path = selection[0]
                try:
                    folder_path = self.get_folder_path(self.folder_tree.selected_node)
                    current_folder = self.get_folder_from_path(folder_path)
                    if current_folder is None:
                        raise ValueError("선택된 폴더를 찾을 수 없습니다.")
                    
                    with open(file_path, 'r', encoding='utf-8') as file:
                        reader = csv.reader(file)
                        if 'words' not in current_folder:
                            current_folder['words'] = []
                        for row in reader:
                            if len(row) >= 2:
                                current_folder['words'].append({
                                    "word": row[0], 
                                    "meaning": row[1], 
                                    "word_lang": self.word_language, 
                                    "meaning_lang": self.meaning_language
                                })
                    self.current_words = current_folder['words']
                    self.show_words()
                    self.save_folders()
                    popup.dismiss()
                except Exception as e:
                    error_popup = Popup(title='오류', content=Label(text=f'파일 로드 중 오류 발생: {str(e)}', font_name='NanumGothic'),
                                        size_hint=(None, None), size=(400, 200))
                    error_popup.open()
        
        filechooser.bind(on_submit=load)
        popup = Popup(title="파일 선택", content=filechooser, size_hint=(0.9, 0.9))
        popup.open()

    def backup_vocabulary(self, instance):
        content = BoxLayout(orientation='vertical')
        file_chooser = FileChooserListView(filters=['*.json'])
        content.add_widget(file_chooser)
        button = Button(text='백업',font_name="NanumGothic")
        content.add_widget(button)
        
        popup = Popup(title='백업 위치 선택', content=content, size_hint=(0.9, 0.9))
        
        def on_backup(instance):
            path = file_chooser.path
            file_path = os.path.join(path, "vocabulary_backup.json")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.folders, f, ensure_ascii=False, indent=2)
                popup.dismiss()
                Popup(title='완료', font_name='NanumGothic', content=Label(text=f"백업이 완료되었습니다: {file_path}"), size_hint=(None, None), size=(300, 150)).open()
            except Exception as e:
                Popup(title='오류', font_name='NanumGothic', content=Label(text=f"백업 중 오류가 발생했습니다: {str(e)}"), size_hint=(None, None), size=(300, 150)).open()
        
        button.bind(on_press=on_backup)
        popup.open()

    def load_backup_file(self, instance):
        content = BoxLayout(orientation='vertical')
        file_chooser = FileChooserListView(filters=['*.json'])
        content.add_widget(file_chooser)
        button = Button(text='불러오기',font_name="NanumGothic")
        content.add_widget(button)
        
        popup = Popup(title='백업 파일 선택', content=content, size_hint=(0.9, 0.9))
        
        def on_load(instance):
            if file_chooser.selection:
                file_path = file_chooser.selection[0]
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.folders = json.load(f)
                    self.save_folders()
                    self.load_folder_tree()
                    popup.dismiss()
                    Popup(title='완료', font_name='NanumGothic', content=Label(text="백업 파일을 성공적으로 불러왔습니다."), size_hint=(None, None), size=(300, 150)).open()
                except Exception as e:
                    Popup(title='오류', font_name='NanumGothic', content=Label(text=f"백업 파일을 불러오는 중 오류가 발생했습니다: {str(e)}"), size_hint=(None, None), size=(300, 150)).open()
        
        button.bind(on_press=on_load)
        popup.open()

    def export_vocabulary(self, instance):
        content = BoxLayout(orientation='vertical')
        file_chooser = FileChooserListView()
        content.add_widget(file_chooser)
        button = Button(text='내보내기',font_name="NanumGothic")
        content.add_widget(button)
        
        popup = Popup(title='내보내기 위치 선택', content=content, size_hint=(0.9, 0.9))
        
        def on_export(instance):
            path = file_chooser.path
            file_path = os.path.join(path, "vocabulary_export.csv")
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Folder", "Word", "Meaning"])
                    self.export_folder(self.folders, "", writer)
                popup.dismiss()
                Popup(title='완료', font_name='NanumGothic', content=Label(text=f"내보내기가 완료되었습니다: {file_path}"), size_hint=(None, None), size=(300, 150)).open()
            except Exception as e:
                Popup(title='오류', font_name='NanumGothic', content=Label(text=f"내보내기 중 오류가 발생했습니다: {str(e)}"), size_hint=(None, None), size=(300, 150)).open()
        
        button.bind(on_press=on_export)
        popup.open()

    def export_folder(self, folder, path, writer):
        if isinstance(folder, dict):
            if 'words' in folder and isinstance(folder['words'], list):
                for word in folder['words']:
                    writer.writerow([path, word.get('word', ''), word.get('meaning', '')])
            if 'children' in folder:
                for child_name, child_folder in folder['children'].items():
                    new_path = f"{path}/{child_name}" if path else child_name
                    self.export_folder(child_folder, new_path, writer)
        elif isinstance(folder, list):
            for word in folder:
                writer.writerow([path, word.get('word', ''), word.get('meaning', '')])

    def increase_font(self, instance):
        if self.font_size < 24:
            self.font_size += 2
            self.update_font()

    def decrease_font(self, instance):
        if self.font_size > 8:
            self.font_size -= 2
            self.update_font()

    def update_font(self):
        for child in self.word_list.children:
            if isinstance(child, Label) or isinstance(child, Button):
                child.font_size = self.font_size

    def sort_folders(self, sort_type):
        def sort_dict(d, reverse=False):
            return dict(sorted(d.items(), key=lambda x: x[0].lower(), reverse=reverse))

        def sort_folder_recursive(folder, sort_type):
            if isinstance(folder, dict) and 'children' in folder:
                if sort_type == "creation":
                    pass  # 생성순은 변경하지 않음
                elif sort_type == "asc":
                    folder['children'] = sort_dict(folder['children'])
                elif sort_type == "desc":
                    folder['children'] = sort_dict(folder['children'], reverse=True)

                for child in folder['children'].values():
                    sort_folder_recursive(child, sort_type)

        if sort_type == "creation":
            pass  # 생성순은 변경하지 않음
        elif sort_type == "asc":
            self.folders = sort_dict(self.folders)
        elif sort_type == "desc":
            self.folders = sort_dict(self.folders, reverse=True)

        sort_folder_recursive(self.folders, sort_type)
        self.save_folders()
        self.load_folder_tree()

    def load_progress(self):
        if os.path.exists("progress.json"):
            with open("progress.json", "r", encoding="utf-8") as f:
                progress = json.load(f)
                folder_name = progress.get("current_folder")
                if folder_name in self.folders:
                    self.current_folder = self.folders[folder_name]
                else:
                    self.current_folder = self.folders["복습 절실"]

                self.current_words = progress.get("current_words", [])
                self.word_hidden = progress.get("word_hidden", {})
                self.meaning_hidden = progress.get("meaning_hidden", {})

                self.completed_words = {folder: set() for folder in self.folders}
                for folder, words in progress.get("completed_words", {}).items():
                    if folder in self.completed_words:
                        self.completed_words[folder] = set(words)

                self.current_row = progress.get("current_row", 0)
                self.current_column = progress.get("current_column", 1)
                
                self.show_words()

    def save_progress(self):
        progress = {
            "current_folder": self.current_folder["name"],
            "current_words": self.current_words,
            "word_hidden": self.word_hidden,
            "meaning_hidden": self.meaning_hidden,
            "completed_words": {folder: list(words) for folder, words in self.completed_words.items()},
            "current_row": self.current_row,
            "current_column": self.current_column,
        }
        with open("progress.json", "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def on_stop(self):
        self.save_progress()
        self.save_folders()
        shutil.rmtree(self.temp_dir)

if __name__ == '__main__':
    VocabularyApp().run()