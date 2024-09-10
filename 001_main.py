from kivy.core.text import LabelBase
from kivy.config import Config
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.treeview import TreeView, TreeViewLabel
from kivy.uix.treeview import TreeViewNode
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from kivy.clock import Clock
from functools import partial
import json
import csv
import os
from gtts import gTTS
import pygame
import random


class CustomTreeViewNode(TreeViewLabel):
    def __init__(self, text="", **kwargs):
        super().__init__(text=text, **kwargs)
        self.children = []

class FolderTree:
    def __init__(self):
        self.tree_view = TreeView(size_hint=(0.3, 1)) 
        self.root = CustomTreeViewNode(text="Root")
        self.tree_view.add_node(self.root)

    def add_node(self, node, parent=None):
        # node가 문자열인 경우 CustomTreeViewNode로 변환
        if isinstance(node, str):
            node = CustomTreeViewNode(text=node)
        elif not isinstance(node, TreeViewNode):
            raise ValueError("Node must be a string or an instance of TreeViewNode")
        
        # 부모 노드가 지정되지 않은 경우 루트로 설정
        if parent is None:
            parent = self.root
        
        self.tree_view.add_node(node, parent)
        print(f"Node '{node.text}' added under '{parent.text}'")  # 디버깅 메시지
        return node

    def clear_children(self):
        for child in list(self.root.nodes):
            self.tree_view.remove_node(child)
            print(f"Node '{child.text}' removed from TreeView")

class FolderNode(TreeViewNode):
    def __init__(self, text="", **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.children = []

    def clear_children(self):
        self.children.clear()

       
class FileManager:
    def __init__(self, folder_tree):
        self.folders = {"Root": {"name": "Root", "words": [], "children": {}}}
        self.folder_tree = folder_tree

    def load_folders(self):
        if os.path.exists('folders.json'):
            with open('folders.json', 'r', encoding='utf-8') as f:
                self.folders = json.load(f)
        else:
            self.save_folders()

    def save_folders(self):
        with open('folders.json', 'w', encoding='utf-8') as f:
            json.dump(self.folders, f, ensure_ascii=False, indent=2)

    def save_folder_words(self, folder_name, words):
        if folder_name in self.folders:
            self.folders[folder_name]["words"] = words
            self.save_folders()

    def load_folder_words(self, folder_name):
        if folder_name in self.folders:
            return self.folders[folder_name]["words"]
        return []

    def ensure_folder_structure(self):
        for folder_name in self.folders:
            if "children" not in self.folders[folder_name]:
                self.folders[folder_name]["children"] = {}
            if "words" not in self.folders[folder_name]:
                self.folders[folder_name]["words"] = []
        self.save_folders()

    def load_txt_file(self, file_path):
        word_list = []
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                word, meaning = line.strip().split('\t')
                word_list.append({'word': word, 'meaning': meaning})
        return word_list

    def load_csv_file(self, file_path):
        word_list = []
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                if len(row) >= 2:
                    word_list.append({'word': row[0], 'meaning': row[1]})
        return word_list

    def backup_vocabulary(self, word_list):
        with open('vocabulary_backup.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for item in word_list:
                writer.writerow([item['word'], item['meaning']])

    def export_vocabulary(self, word_list):
        with open('vocabulary_export.txt', 'w', encoding='utf-8') as file:
            for item in word_list:
                file.write(f"{item['word']}\t{item['meaning']}\n")

    def load_words_from_file(self, file_path, folder_name):
        if folder_name not in self.folders:
            print("선택된 폴더가 존재하지 않습니다.")
            return []

        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            self.folders[folder_name]["words"] = []  # 기존 단어 초기화
            for row in reader:
                if len(row) >= 2:
                    self.folders[folder_name]["words"].append({"word": row[0], "meaning": row[1]})
        
        self.save_folders()
        return self.folders[folder_name]["words"]
    

class LanguageManager:
    def __init__(self):
        self.word_language = 'en'
        self.meaning_language = 'ko'
        self.language_codes = {
            '한국어': 'ko', 
            '영어': 'en', 
            '프랑스어': 'fr', 
            '일본어': 'ja', 
            '중국어': 'zh-cn', 
            '독일어': 'de'
        }
        self.voice_options = {
            "en-US": ["en-US-Neural2-A", "en-US-Standard-B", "en-US-Neural2-C", "en-US-Neural2-D", "en-US-Neural2-E"],
            "fr-FR": ["fr-FR-Standard-A", "fr-FR-Standard-B", "fr-FR-Standard-C", "fr-FR-Standard-D", "fr-FR-Standard-E"],
            "de-DE": ["de-DE-Standard-A", "de-DE-Standard-B", "de-DE-Standard-C", "de-DE-Standard-D", "de-DE-Standard-E", "de-DE-Standard-F"],
            "ko-KR": ["ko-KR-Neural2-A", "ko-KR-Neural2-B", "ko-KR-Neural2-C"],
            "cmn-CN": ["cmn-CN-Standard-A", "cmn-CN-Standard-B", "cmn-CN-Standard-C", "cmn-CN-Standard-D"],
            "ja-JP": ["ja-JP-Standard-A", "ja-JP-Standard-B", "ja-JP-Standard-C", "ja-JP-Standard-D"]
        }

    def select_word_language(self):
        dropdown = DropDown()
        for lang in self.language_manager.get_supported_languages():
            btn = Button(text=lang, size_hint_y=None, height=44)
            btn.bind(on_release=lambda btn: self.set_word_language(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(self.ids.word_language_button)

    def select_meaning_language(self):
        dropdown = DropDown()
        for lang in self.language_manager.get_supported_languages():
            btn = Button(text=lang, size_hint_y=None, height=44)
            btn.bind(on_release=lambda btn: self.set_meaning_language(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(self.ids.meaning_language_button)

    def set_word_language(self, language):
        self.language_manager.set_word_language(language)

    def set_meaning_language(self, language):
        self.language_manager.set_meaning_language(language)

    def set_word_language(self, language):
        if language in self.language_codes:
            self.word_language = self.language_codes[language]
        else:
            print(f"지원하지 않는 언어입니다: {language}")

    def set_meaning_language(self, language):
        if language in self.language_codes:
            self.meaning_language = self.language_codes[language]
        else:
            print(f"지원하지 않는 언어입니다: {language}")

    def swap_languages(self):
        self.word_language, self.meaning_language = self.meaning_language, self.word_language

    def get_word_language(self):
        return self.word_language

    def get_meaning_language(self):
        return self.meaning_language

    def get_supported_languages(self):
        return list(self.language_codes.keys())


class FolderManager:
    def __init__(self, folder_tree, file_manager):
        self.folder_tree = folder_tree
        self.file_manager = file_manager
        self.update_folder_tree()

    def create_new_folder(self, folder_name):
        if folder_name and folder_name not in self.folders:
            self.folders[folder_name] = {"name": folder_name, "words": [], "children": {}}
            new_node = self.folder_tree.add_node(folder_name)  # 트리에 노드 추가
            self.file_manager.save_folders()  # 폴더 구조 저장
            print(f"폴더 '{folder_name}' 생성됨")  # 디버거용 메시지
            return True
        else:
            print(f"폴더 '{folder_name}' 생성 실패")  # 디버거용 메시지
            return False

    def update_folder_tree(self):
        self.folder_tree.clear_children()
        for folder_name in self.file_manager.folders:
            self.folder_tree.add_node(folder_name) 


    def create_subfolder(self, parent_folder_name, subfolder_name):
        print(f"Creating subfolder: {subfolder_name} under {parent_folder_name}")  # 디버그 출력
        if parent_folder_name not in self.folders:
            print(f"Parent folder '{parent_folder_name}' does not exist.")  # 디버그 출력
            return False

        if subfolder_name in self.folders[parent_folder_name]["children"]:
            print(f"Subfolder '{subfolder_name}' already exists.")  # 디버그 출력
            return False

        new_folder = {"name": subfolder_name, "words": [], "children": {}}
        self.folders[parent_folder_name]["children"][subfolder_name] = new_folder
        print(f"Subfolder '{subfolder_name}' created successfully.")  # 디버그 출력

        # 부모 노드를 찾아서 하위 노드를 추가합니다.
        parent_node = self.find_node_by_name(self.folder_tree.root, parent_folder_name)
        if parent_node:
            sub_node = self.folder_tree.add_node(subfolder_name, parent_node)
            if sub_node:
                print(f"Subfolder '{subfolder_name}' added to TreeView under '{parent_folder_name}'.")
        else:
            print(f"Parent node for '{parent_folder_name}' not found in tree.")  # 디버그 출력

        self.file_manager.save_folders()
        return True

    def rename_folder(self, old_name, new_name):
        if old_name in self.folders:
            self.folders[new_name] = self.folders.pop(old_name)
            node = self.find_node_by_name(self.folder_tree.root, old_name)
            if node:
                node.text = new_name
                print(f"Folder '{old_name}' renamed to '{new_name}'.")
            self.file_manager.save_folders()

    def delete_folder(self, folder_name):
        if folder_name in self.folders:
            del self.folders[folder_name]
            node = self.find_node_by_name(self.folder_tree.root, folder_name)
            if node:
                self.folder_tree.tree_view.remove_node(node)
                print(f"Folder '{folder_name}' removed from TreeView.")
            self.file_manager.save_folders()

    def sort_folders(self, key_func=lambda x: x.lower(), reverse=False):
        sorted_folders = sorted(set(self.folders.keys()), key=key_func, reverse=reverse)
        self.file_manager.save_folders()
        self.update_folder_tree()

    def set_folder_tree(self, folder_tree):
        self.folder_tree = folder_tree
        self.update_folder_tree()

    def add_folders_to_tree(self, parent_node, children):
        for child_name, child_info in children.items():
            child_node = self.folder_tree.add_node(child_name, parent_node)
            if child_node:
                print(f"Added folder '{child_name}' under '{parent_node.text}'.")  # 디버깅 메시지
                self.add_folders_to_tree(child_node, child_info["children"])

    def find_node_by_name(self, node, name):
        if node.text == name:
            return node
        for child in node.nodes:
            result = self.find_node_by_name(child, name)
            if result:
                return result
        return None

    def get_folder_path(self, node):
        path = []
        while node and node.text != 'Root':
            path.insert(0, node.text)
            node = node.parent_node
        return path

    def get_folder_from_path(self, path):
        return self.folders.get(path[0], {}) if path else {}
    

class WordManager:
    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.word_list = []

    def add_word(self, folder_name, word, meaning):
        if folder_name in self.file_manager.folders:
            self.file_manager.folders[folder_name]["words"].append({'word': word, 'meaning': meaning})
            self.file_manager.save_folders()  # 데이터 저장
            print(f"'{word}' 단어가 '{folder_name}' 폴더에 추가되었습니다.")

    def edit_word(self, folder_name, index, new_word, new_meaning):
        if folder_name not in self.file_manager.folders:
            print("선택된 폴더가 존재하지 않습니다.")
            return False
        if 0 <= index < len(self.file_manager.folders[folder_name]["words"]):
            self.file_manager.folders[folder_name]["words"][index] = {"word": new_word, "meaning": new_meaning}
            self.file_manager.save_folders()
            self.word_list = self.file_manager.folders[folder_name]["words"]
            return True
        else:
            print("잘못된 인덱스입니다.")
            return False

    def shuffle_words(self, folder_name):
        if folder_name not in self.file_manager.folders:
            print("선택된 폴더가 존재하지 않습니다.")
            return False
        random.shuffle(self.file_manager.folders[folder_name]["words"])
        self.file_manager.save_folders()
        self.word_list = self.file_manager.folders[folder_name]["words"]
        return True

    def restore_words(self, folder_name):
        if folder_name not in self.file_manager.folders:
            print("선택된 폴더가 존재하지 않습니다.")
            return False
        self.file_manager.folders[folder_name]["words"].sort(key=lambda x: x['word'])
        self.file_manager.save_folders()
        self.word_list = self.file_manager.folders[folder_name]["words"]
        return True

    def sort_words(self, folder_name, key='word', reverse=False):
        if folder_name not in self.file_manager.folders:
            print("선택된 폴더가 존재하지 않습니다.")
            return

        self.file_manager.folders[folder_name]["words"].sort(key=lambda x: x[key], reverse=reverse)
        self.file_manager.save_folders()
        self.word_list = self.file_manager.folders[folder_name]["words"]

    def swap_word_meaning(self, folder_name):
        if folder_name not in self.file_manager.folders:
            print("선택된 폴더가 존재하지 않습니다.")
            return

        for item in self.file_manager.folders[folder_name]["words"]:
            item['word'], item['meaning'] = item['meaning'], item['word']
        self.file_manager.save_folders()
        self.word_list = self.file_manager.folders[folder_name]["words"]

    def get_words(self, folder_name):
        if folder_name not in self.file_manager.folders:
            print("선택된 폴더가 존재하지 않습니다.")
            return []

        return self.file_manager.folders[folder_name]["words"]        

class VocabularyApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.folder_tree = FolderTree()
        self.file_manager = FileManager(self.folder_tree)
        self.folder_manager = FolderManager(self.folder_tree, self.file_manager)
        #self.folder_manager.clear_children() 
        self.language_manager = LanguageManager()
        self.file_manager.ensure_folder_structure()  # 폴더 구조 확인
        self.folder_manager = None  # build 메서드에서 초기화
        self.word_manager = WordManager(self.file_manager)
        self.current_folder = None
        self.font_size = 14
        #self.file_manager = None
        self.folder_tree = self.folder_tree  

        pygame.mixer.init()

    def build(self):
        self.folder_manager.update_folder_tree()
        self.folder_tree = FolderTree()
        # self.folder_manager = FolderManager(self.folder_tree, self.file_manager)

        self.title = '단어.문장 암기장'
        layout = BoxLayout(orientation='vertical')

        # 메뉴 바 생성
        menu_bar = BoxLayout(size_hint=(1, 0.05))
        menu_bar.add_widget(Button(text='파일', font_name="NanumGothic", on_press=self.show_file_menu))
        menu_bar.add_widget(Button(text='언어', font_name="NanumGothic", on_press=self.show_language_menu))
        menu_bar.add_widget(Button(text='보기', font_name="NanumGothic", on_press=self.show_view_menu))
        menu_bar.add_widget(Button(text='폴더관리', font_name="NanumGothic", on_press=self.show_folder_menu))
        menu_bar.add_widget(Button(text='폴더 정렬', font_name="NanumGothic", on_press=self.show_folder_sort_menu))
        menu_bar.add_widget(Button(text='단어관리', font_name="NanumGothic", on_press=self.show_word_management_menu))
        menu_bar.add_widget(Button(text='단어정렬', font_name="NanumGothic", on_press=self.show_word_sort_menu))
        menu_bar.add_widget(Button(text='단어/뜻 위치 바꾸기', font_name="NanumGothic", on_press=self.swap_word_meaning))
        layout.add_widget(menu_bar)
        
        # 메인 영역 (폴더 트리와 단어 목록)
        main_area = BoxLayout()
        
        # 왼쪽 폴더 트리
        main_area = BoxLayout(orientation='horizontal')
        main_area.add_widget(self.folder_tree.tree_view)
        self.folder_tree.tree_view.bind(selected_node=self.on_folder_select)

        # FolderManager 초기화
        self.folder_manager = FolderManager(self.folder_tree, self.file_manager)
        self.folder_manager.update_folder_tree()

        # FolderManager에 folder_tree 설정
        self.folder_manager.set_folder_tree(self.folder_tree)

        # 오른쪽 단어 목록
        self.word_grid = GridLayout(cols=3, size_hint=(0.7, 1))
        self.word_grid.bind(minimum_height=self.word_grid.setter('height'))
        word_scroll = ScrollView(size_hint=(1, 1))
        word_scroll.add_widget(self.word_grid)
        main_area.add_widget(word_scroll)

        # 예제 노드 추가
        self.folder_tree.add_node("AA")  # 'AA'라는 새 노드 추가
        self.folder_tree.add_node("BB", parent=self.folder_tree.root)  # 루트 아래 'BB' 추가

        layout.add_widget(main_area)
        
        # 하단 컨트롤 영역
        control_area = BoxLayout(size_hint=(1, 0.1))
        control_area.add_widget(Label(text='반복횟수', font_name="NanumGothic"))
        self.repeat_input = TextInput(multiline=False)
        control_area.add_widget(self.repeat_input)
        control_area.add_widget(Label(text='시작 행', font_name="NanumGothic"))
        self.start_row_input = TextInput(multiline=False)
        control_area.add_widget(self.start_row_input)
        control_area.add_widget(Label(text='끝 행', font_name="NanumGothic"))
        self.end_row_input = TextInput(multiline=False)
        control_area.add_widget(self.end_row_input)
        
        control_area.add_widget(Button(text='자동재생', font_name="NanumGothic", on_press=self.start_auto_play))
        control_area.add_widget(Button(text='재생멈춤', font_name="NanumGothic", on_press=self.stop_play))
        control_area.add_widget(Button(text='재생일시멈춤', font_name="NanumGothic", on_press=self.pause_play))
        control_area.add_widget(Button(text='재생멈춤해제', font_name="NanumGothic", on_press=self.resume_play))
        control_area.add_widget(Button(text='단어만 재생', font_name="NanumGothic", on_press=self.play_words_only))
        

        layout.add_widget(control_area)
        self.load_data()
        return layout
        #return super().build()
    
    def create_new_folder(self):
        content = BoxLayout(orientation='vertical')
        new_folder_input = TextInput(multiline=False)
        content.add_widget(new_folder_input)

        def on_create(instance):
            folder_name = new_folder_input.text.strip()
            if folder_name:
                success = self.folder_manager.create_new_folder(folder_name)  # 이 부분은 이제 FolderManager가 아닌 VocabularyApp의 메서드를 호출하게 되어야 합니다.
                if success:
                    self.folder_manager.update_folder_tree()
                    popup.dismiss()
                else:
                    error_label.text = f"폴더 '{folder_name}' 생성 실패."
            else:
                error_label.text = "폴더 이름을 입력해주세요."

        create_button = Button(text='생성', size_hint_y=None, height=50)
        create_button.bind(on_release=on_create)
        content.add_widget(create_button)

        error_label = Label(text='', color=(1, 0, 0, 1))  # 빨간색 텍스트
        content.add_widget(error_label)

        popup = Popup(title='새 폴더 생성', content=content, size_hint=(0.5, 0.4))
        popup.open()

    def load_data(self):
        self.folder_manager.folders = self.file_manager.load_folders()
        self.folder_manager.update_folder_tree()

    # 메뉴 관련 메서드 ######################################################################
    def show_file_menu(self, instance):
        dropdown = DropDown(size_hint=(None, None), width=150)
        options = ['파일 불러오기', '단어장 백업', '백업파일 불러오기', '단어장 내보내기']
        for option in options:
            btn = Button(text=option, size_hint_y=None, height=44, font_name="NanumGothic")
            btn.bind(on_release=lambda btn: dropdown.select(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(instance)
        dropdown.bind(on_select=lambda instance, x: self.file_menu_action(x))

    def show_language_menu(self, instance):
        dropdown = DropDown()
        options = ['단어 언어', '의미 언어']
        for option in options:
            btn = Button(text=option, size_hint_y=None, height=44, font_name="NanumGothic")
            btn.bind(on_release=lambda btn: self.language_menu_action(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(instance)

    def show_view_menu(self, instance):
        dropdown = DropDown()
        options = ['폰트 크게(+)', '폰트 작게(-)']
        for option in options:
            btn = Button(text=option, size_hint_y=None, height=44, font_name="NanumGothic")
            btn.bind(on_release=lambda btn: self.view_menu_action(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(instance)

    def show_folder_menu(self, instance):
        dropdown = DropDown()
        options = ['새 폴더', '하위 폴더', '이름 변경', '삭제']
        for option in options:
            btn = Button(text=option, size_hint_y=None, height=44, font_name="NanumGothic")
            btn.bind(on_release=lambda btn: self.folder_menu_action(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(instance)

    def show_folder_sort_menu(self, instance):
        dropdown = DropDown()
        options = ['생성순 정렬', '오름차순 정렬', '내림차순 정렬']
        for option in options:
            btn = Button(text=option, size_hint_y=None, height=44, font_name="NanumGothic")
            btn.bind(on_release=lambda btn: self.folder_sort_action(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(instance)

    def show_word_management_menu(self, instance):
        dropdown = DropDown()
        options = ['단어 추가', '단어 수정', '섞기', '원상 복귀', '단어 삭제', '단어 전체 삭제']
        for option in options:
            btn = Button(text=option, size_hint_y=None, height=44, font_name="NanumGothic")
            btn.bind(on_release=lambda btn: self.word_management_action(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(instance)

    def show_word_sort_menu(self, instance):
        dropdown = DropDown()
        options = ['단어 오름차순', '단어 내림차순', '의미 오름차순', '의미 내림차순']
        for option in options:
            btn = Button(text=option, size_hint_y=None, height=44, font_name="NanumGothic")
            btn.bind(on_release=lambda btn: self.word_sort_action(btn.text))
            dropdown.add_widget(btn)
        dropdown.open(instance)

    def file_menu_action(self, action):
        if action == '파일 불러오기':
            self.load_file()
        elif action == '단어장 백업':
            self.backup_vocabulary()
        elif action == '백업파일 불러오기':
            self.load_backup()
        elif action == '단어장 내보내기':
            self.export_vocabulary()

    def language_menu_action(self, action):
        if action == '단어 언어':
            self.select_word_language()
        elif action == '의미 언어':
            self.select_meaning_language()

    def view_menu_action(self, action):
        if action == '폰트 크게(+)':
            self.increase_font_size()
        elif action == '폰트 작게(-)':
            self.decrease_font_size()

    def folder_menu_action(self, action):
        if action == '새 폴더':
            self.create_new_folder()
        elif action == '하위 폴더':
            self.create_subfolder()
        elif action == '이름 변경':
            self.rename_folder()
        elif action == '삭제':
            self.delete_folder()

    def folder_sort_action(self, action):
        if action == '생성순 정렬':
            self.folder_manager.sort_folders()
        elif action == '오름차순 정렬':
            self.folder_manager.sort_folders(key_func=lambda x: x.lower())
        elif action == '내림차순 정렬':
            self.folder_manager.sort_folders(key_func=lambda x: x.lower(), reverse=True)

    def word_management_action(self, action):
        if action == '단어 추가':
            self.add_word()
        elif action == '단어 수정':
            self.edit_word()
        elif action == '섞기':
            self.shuffle_words()
        elif action == '원상 복귀':
            self.restore_words()
        elif action == '단어 삭제':
            self.delete_word()
        elif action == '단어 전체 삭제':
            self.delete_all_words()

    def word_sort_action(self, action):
        if not self.current_folder:
            return
        if action == '단어 오름차순':
            self.word_manager.sort_words(self.current_folder, key='word')
        elif action == '단어 내림차순':
            self.word_manager.sort_words(self.current_folder, key='word', reverse=True)
        elif action == '의미 오름차순':
            self.word_manager.sort_words(self.current_folder, key='meaning')
        elif action == '의미 내림차순':
            self.word_manager.sort_words(self.current_folder, key='meaning', reverse=True)
        self.update_word_grid(self.word_manager.get_words(self.current_folder))

    # 파일 관리, 단어 관리, 그리고 기타 유틸리티 메서드 ###########################################
    def load_file(self):
        filechooser = FileChooserListView(path='/', filters=['*.txt', '*.csv'])
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(filechooser)
        select_button = Button(text="선택", size_hint_y=None, height=44, font_name="NanumGothic")
        layout.add_widget(select_button)
        popup = Popup(title='파일 선택', content=layout, size_hint=(0.9, 0.9))
        select_button.bind(on_release=lambda x: self.on_file_select(filechooser.selection, popup))
        popup.open()

    def on_file_select(self, selection, popup):
        try:
            if selection:
                self.load_selected_file(selection[0])
            else:
                print("파일이 선택되지 않았습니다.")
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            popup.dismiss()

    def load_selected_file(self, file_path):
        _, file_extension = os.path.splitext(file_path)
        if file_extension.lower() == '.txt':
            self.word_manager.word_list = self.file_manager.load_txt_file(file_path)
        elif file_extension.lower() == '.csv':
            self.word_manager.word_list = self.file_manager.load_csv_file(file_path)
        self.update_word_grid(self.word_manager.word_list)

    def backup_vocabulary(self):
        self.file_manager.backup_vocabulary(self.word_manager.word_list)

    def load_backup(self):
        self.word_manager.word_list = self.file_manager.load_csv_file('vocabulary_backup.csv')
        self.update_word_grid(self.word_manager.word_list)

    def export_vocabulary(self):
        self.file_manager.export_vocabulary(self.word_manager.word_list)

    def create_subfolder(self):
        if not self.folder_tree.tree_view.selected_node:
            Popup(title='오류', content=Label(text='상위 폴더를 선택해주세요.'), size_hint=(None, None), size=(300, 200)).open()
            return

        content = BoxLayout(orientation='vertical')
        new_folder_input = TextInput(multiline=False)
        content.add_widget(new_folder_input)
        
        def on_create(instance):
            subfolder_name = new_folder_input.text.strip()
            if subfolder_name:
                parent_folder = self.folder_tree.tree_view.selected_node.text
                success = self.folder_manager.create_subfolder(parent_folder, subfolder_name)
                if success:
                    self.folder_manager.update_folder_tree()
                    popup.dismiss()
                else:
                    error_label.text = f"하위 폴더 '{subfolder_name}' 생성에 실패했습니다."
            else:
                error_label.text = "폴더 이름을 입력해주세요."
        
        create_button = Button(text='생성', font_name="NanumGothic", size_hint_y=None, height=50)
        create_button.bind(on_release=on_create)
        content.add_widget(create_button)
        
        error_label = Label(text='', color=(1, 0, 0, 1))  # 빨간색 텍스트
        content.add_widget(error_label)
        
        popup = Popup(title='하위 폴더 생성', content=content, size_hint=(0.5, 0.3))
        popup.open()

    def rename_folder(self):
        if not self.folder_tree.selected_node:
            return
        content = BoxLayout(orientation='vertical')
        new_name_input = TextInput(text=self.folder_tree.selected_node.text, multiline=False)
        content.add_widget(new_name_input)
        rename_button = Button(text='변경', font_name="NanumGothic", size_hint_y=None, height=50)
        rename_button.bind(on_release=lambda x: self.folder_manager.rename_folder(self.folder_tree.selected_node.text, new_name_input.text))
        content.add_widget(rename_button)
        popup = Popup(title='폴더 이름 변경', content=content, size_hint=(0.5, 0.3))
        popup.open()

    def add_word(self):
        if not self.current_folder:
            return
        content = BoxLayout(orientation='vertical')
        word_input = TextInput(multiline=False)
        meaning_input = TextInput(multiline=False)
        content.add_widget(Label(text='단어', font_name="NanumGothic"))
        content.add_widget(word_input)
        content.add_widget(Label(text='뜻', font_name="NanumGothic"))
        content.add_widget(meaning_input)

        def on_add(instance):
            word = word_input.text.strip()
            meaning = meaning_input.text.strip()
            if word and meaning:
                self.word_manager.add_word(self.current_folder, word, meaning)
                popup.dismiss()
            else:
                print("단어와 뜻을 입력해 주세요.")

        add_button = Button(text='추가', font_name="NanumGothic", size_hint_y=None, height=50)
        add_button.bind(on_release=on_add)
        content.add_widget(add_button)

        popup = Popup(title='단어 추가', content=content, size_hint=(0.5, 0.5))
        popup.open()
    
    def edit_word(self):
        if not self.word_grid.selected_node:
            return
        index = self.word_grid.children.index(self.word_grid.selected_node) // 3
        content = BoxLayout(orientation='vertical')
        word_input = TextInput(text=self.word_manager.word_list[index]['word'], multiline=False)
        meaning_input = TextInput(text=self.word_manager.word_list[index]['meaning'], multiline=False)
        content.add_widget(Label(text='단어', font_name="NanumGothic"))
        content.add_widget(word_input)
        content.add_widget(Label(text='뜻', font_name="NanumGothic"))
        content.add_widget(meaning_input)
        edit_button = Button(text='수정', font_name="NanumGothic", size_hint_y=None, height=50)
        edit_button.bind(on_release=lambda x: self.word_manager.edit_word(self.current_folder, index, word_input.text, meaning_input.text))
        content.add_widget(edit_button)
        popup = Popup(title='단어 수정', content=content, size_hint=(0.5, 0.5))
        popup.open()

    def shuffle_words(self):
        if self.current_folder:
            if self.word_manager.shuffle_words(self.current_folder):
                self.update_word_grid(self.word_manager.get_words(self.current_folder))

    def restore_words(self):
        if self.current_folder:
            if self.word_manager.restore_words(self.current_folder):
                self.update_word_grid(self.word_manager.get_words(self.current_folder))

    def delete_word(self):
        if not self.word_grid.selected_node or not self.current_folder:
            return

        index = self.word_grid.children.index(self.word_grid.selected_node) // 3
        word = self.word_manager.get_words(self.current_folder)[index]['word']

        # 확인 대화 상자 표시
        confirm = Popup(title='확인',
                        content=Label(text=f"'{word}' 단어를 삭제하시겠습니까?"),
                        size_hint=(None, None), size=(300, 200))
        
        def confirm_delete(instance):
            if self.word_manager.delete_word(self.current_folder, index):
                self.update_word_grid(self.word_manager.get_words(self.current_folder))
            else:
                error_popup = Popup(title='오류',
                                    content=Label(text="단어 삭제 중 오류가 발생했습니다."),
                                    size_hint=(None, None), size=(300, 200))
                error_popup.open()
            confirm.dismiss()

        confirm.add_widget(Button(text='예', on_press=confirm_delete))
        confirm.add_widget(Button(text='아니오', on_press=confirm.dismiss))
        confirm.open()

    def delete_all_words(self):
        if self.current_folder:
            if self.word_manager.delete_all_words(self.current_folder):
                self.update_word_grid([])

    def update_word_grid(self, instance):
        if self.current_folder:
            self.word_manager.swap_word_meaning(self.current_folder)
            self.update_word_grid(self.word_manager.get_words(self.current_folder))

    def update_word_grid(self, words):
        self.word_grid.clear_widgets()
        self.word_grid.cols = 3
        for index, item in enumerate(words):
            self.word_grid.add_widget(Label(text=str(index + 1), size_hint_y=None, height=40))
            word_btn = Button(text=item['word'], size_hint_y=None, height=40)
            word_btn.bind(on_press=self.play_word_tts)
            self.word_grid.add_widget(word_btn)
            meaning_btn = Button(text=item['meaning'], size_hint_y=None, height=40)
            meaning_btn.bind(on_press=self.play_meaning_tts)
            self.word_grid.add_widget(meaning_btn)
        self.word_grid.height = len(words) * 40

    def swap_word_meaning(self, instance):
        if self.current_folder:
            if self.word_manager.swap_word_meaning(self.current_folder):
                self.update_word_grid(self.word_manager.get_words(self.current_folder))
                # 언어 설정도 함께 변경
                self.language_manager.swap_languages()
            else:
                popup = Popup(title='오류',
                              content=Label(text="단어와 뜻 위치 바꾸기 중 오류가 발생했습니다."),
                              size_hint=(None, None), size=(300, 200))
                popup.open()

    def on_folder_select(self, instance, value):
        if value:
            folder_name = value.text
            if folder_name in self.folder_manager.folders:
                self.current_folder = folder_name
                print(f"현재 폴더: '{self.current_folder}'")
                words = self.word_manager.get_words(self.current_folder)
                self.update_word_grid(words)
            else:
                print(f"선택된 폴더 '{folder_name}'가 존재하지 않습니다.")

    def play_word_tts(self, instance):
        word = instance.text
        tts = gTTS(text=word, lang=self.language_manager.get_word_language())
        temp_file = f"temp_word_{hash(word)}.mp3"
        tts.save(temp_file)
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        def remove_temp_file(dt):
            try:
                os.remove(temp_file)
            except PermissionError:
                # 파일이 사용 중이면 다시 시도
                Clock.schedule_once(remove_temp_file, 1)
        
        Clock.schedule_once(remove_temp_file, 5)  # 5초 후 임시 파일 삭제 시도

    def play_meaning_tts(self, instance):
        meaning = instance.text
        tts = gTTS(text=meaning, lang=self.language_manager.get_meaning_language())
        temp_file = f"temp_meaning_{hash(meaning)}.mp3"
        tts.save(temp_file)
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        def remove_temp_file(dt):
            try:
                os.remove(temp_file)
            except PermissionError:
                # 파일이 사용 중이면 다시 시도
                Clock.schedule_once(remove_temp_file, 1)
        
        Clock.schedule_once(remove_temp_file, 5)  # 5초 후 임시 파일 삭제 시도

    def start_auto_play(self, instance):
        try:
            repeat = int(self.repeat_input.text)
            start = int(self.start_row_input.text)
            end = int(self.end_row_input.text)
            Clock.schedule_once(partial(self.auto_play_word, repeat, start, end, 0), 0)
        except ValueError:
            print("올바른 숫자를 입력하세요.")

    def auto_play_word(self, repeat, start, end, current_index, dt):
        if current_index >= end - start + 1:
            repeat -= 1
            current_index = 0
        if repeat <= 0:
            return
        word = self.word_manager.word_list[start - 1 + current_index]['word']
        meaning = self.word_manager.word_list[start - 1 + current_index]['meaning']
        tts_word = gTTS(text=word, lang=self.language_manager.get_word_language())
        tts_word.save("temp_word.mp3")
        pygame.mixer.music.load("temp_word.mp3")
        pygame.mixer.music.play()
        def play_meaning(dt):
            tts_meaning = gTTS(text=meaning, lang=self.language_manager.get_meaning_language())
            tts_meaning.save("temp_meaning.mp3")
            pygame.mixer.music.load("temp_meaning.mp3")
            pygame.mixer.music.play()
            Clock.schedule_once(partial(self.auto_play_word, repeat, start, end, current_index + 1), 2)
        Clock.schedule_once(play_meaning, 2)

    def stop_play(self, instance):
        pygame.mixer.music.stop()

    def pause_play(self, instance):
        pygame.mixer.music.pause()

    def resume_play(self, instance):
        pygame.mixer.music.unpause()

    def play_words_only(self, instance):
        repeat = int(self.repeat_input.text)
        start = int(self.start_row_input.text)
        end = int(self.end_row_input.text)
        for _ in range(repeat):
            for i in range(start - 1, end):
                word = self.word_manager.word_list[i]['word']
                tts_word = gTTS(text=word, lang=self.language_manager.get_word_language())
                tts_word.save("temp_word.mp3")
                pygame.mixer.music.load("temp_word.mp3")
                pygame.mixer.music.play()
                pygame.time.wait(int(pygame.mixer.music.get_length() * 1000))

    def increase_font_size(self):
        self.font_size += 2
        self.update_word_grid(self.word_manager.get_words(self.current_folder))

    def decrease_font_size(self):
        if self.font_size > 2:
            self.font_size -= 2
            self.update_word_grid(self.word_manager.get_words(self.current_folder))

if __name__ == '__main__':
    LabelBase.register(name='NanumGothic', 
                       fn_regular='C:/PT/fonts/NanumGothic-Regular.ttf',
                       fn_bold='C:/PT/fonts/NanumGothic-Bold.ttf')
    Config.set('kivy', 'default_font', ['NanumGothic', 'C:/PT/fonts/NanumGothic-Regular.ttf'])
    
    VocabularyApp().run()


