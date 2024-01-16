import os
import re
from pathlib import Path

import mobase
from PyQt6.QtCore import QDir, qInfo
from PyQt6.QtWidgets import QMessageBox
from ..basic_game import BasicGame
from ..steam_utils import find_steam_path


class DragonsDogmaDarkArisenModDataChecker(mobase.ModDataChecker):
    plugin_debug = False
    valid_structure = False
    fixable_structure = False
    RE_BODYFILE = re.compile(r"[fm]_[aiw]_\w+.arc")
    RE_DL1_BODYFILE = re.compile(r"[fm]_a_\w+820\d.arc")
    RE_HEXEXTENSION = re.compile(r"[\.0-9a-fA-F]{8}")
    VALID_ROOT_FOLDERS = ["rom", "movie", "sound"]
    VALID_CHILD_FOLDERS = [
        "dl1",
        "enemy",
        "eq",
        "etc",
        "event",
        "gui",
        "h_enemy",
        "ingamemanual",
        "item_b",
        "map",
        "message",
        "mnpc",
        "npc",
        "npcfca",
        "npcfsm",
        "om",
        "pwnmsg",
        "quest",
        "shell",
        "sk",
        "sound",
        "stage",
        "voice",
        "wp",
        "bbsrpg_core",
        "bbs_rpg",
        "game_main",
        "Initialize",
        "title",
    ]
    VALID_FILE_EXTENSIONS = [
        ".arc",
        ".pck",
        ".wmv",
        ".sngw",
    ]
    NO_CHILDFOLDERS = ["a_acc", "i_body", "w_leg"]
    MoveList: list[tuple[mobase.FileTreeEntry, str]] = []
    DeleteList: list[tuple[mobase.FileTreeEntry, str]] = []

    def checkFiletreeEntry(
        self, path: str, entry: mobase.FileTreeEntry
    ) -> mobase.IFileTree.WalkReturn:
        # we check for valid game files within a valid root folder
        path_root = path.split(os.sep)[0]
        entry_name, entry_extension = os.path.splitext(entry.name())

        if self.plugin_debug:
            qInfo(
                f"checkFiletreeEntry path_root:{path_root} path:{path} entry:{entry.name()}"
            )
        if entry.isDir():
            parent = entry.parent()
            if path_root not in self.VALID_ROOT_FOLDERS:
                if (
                    parent in self.VALID_ROOT_FOLDERS
                    and entry in self.VALID_CHILD_FOLDERS
                ):
                    if self.plugin_debug:
                        qInfo(f"Adding child to move list: {path} {entry.name()}")
                    self.MoveList.append((entry, "rom" + os.sep))
                    self.fixable_structure = True
                    return mobase.IFileTree.WalkReturn.SKIP
        else:
            if path_root in self.VALID_ROOT_FOLDERS:
                for extension in self.VALID_FILE_EXTENSIONS:
                    if entry.name().endswith(extension):
                        self.valid_structure = True
                        if self.plugin_debug:
                            qInfo("checkFiletreeEntry valid")
                        return mobase.IFileTree.WalkReturn.STOP
            is_body_file = self.RE_BODYFILE.match(entry.name())
            if is_body_file:
                self.fixable_structure = True
                parent_folder = str(entry.name())[0]
                grandparent_folder = re.split(r"_(?=._)|[0-9]", str(entry.name()))[1]
                if self.plugin_debug:
                    qInfo(f"Adding to move list: {path + entry.name()}")
                if grandparent_folder in self.NO_CHILDFOLDERS:
                    target_path = os.path.join("/rom/eq/", grandparent_folder)
                    self.MoveList.append((entry, target_path))
                else:
                    target_path = os.path.join(
                        "/rom/eq/", grandparent_folder, parent_folder
                    )
                    self.MoveList.append((entry, target_path))
            has_hex_file_extension = self.RE_HEXEXTENSION.match(entry_extension)
            # ignore item, sound, and game manual files with hex extenstions
            folder_exlusions = ["sound", "ingamemanual", "item"]
            if has_hex_file_extension and not any(x in path for x in folder_exlusions):
                qInfo(f"Invalid TEX file found: {path + entry.name()}")
                self.MoveList.append((entry, path + entry_name + ".tex"))
        return mobase.IFileTree.WalkReturn.CONTINUE

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        size_delete_list = len(self.DeleteList)
        size_move_list = len(self.MoveList)
        if self.plugin_debug:
            qInfo(f"folder delete list size: {str(size_delete_list)}")
            qInfo(f"folder move list size: {str(size_move_list)}")
        if size_delete_list > 0 and size_move_list > 0:
            self.valid_structure = True
        if size_delete_list > 0:
            for entry, path in reversed(self.DeleteList):
                if self.plugin_debug:
                    qInfo(f"Deleting: {path + entry.name()}")
                filetree.move(
                    entry, "/delete/" + entry.name(), policy=mobase.IFileTree.MERGE
                )
        if size_move_list > 0:
            for entry, path in reversed(self.MoveList):
                entry_path = filetree.pathTo(entry, os.sep)
                path_root = entry_path.split(os.sep)[0]
                if self.plugin_debug:
                    qInfo(f"Moving: {entry.name()} to {path}")
                filetree.move(entry, path, policy=mobase.IFileTree.MERGE)
                filetree.remove(path_root)  # remove empty branch
        # remove invalid root folders
        filetree.remove("delete")
        return filetree

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if self.plugin_debug:
            qInfo(f"Data validation start: {tree.name()}")
        self.valid_structure = False
        self.fixable_structure = False
        self.MoveList.clear()
        self.DeleteList.clear()

        # check filetree
        tree.walk(self.checkFiletreeEntry, os.sep)
        if self.fixable_structure:
            if self.plugin_debug:
                qInfo("Fixable file structure")
            return mobase.ModDataChecker.FIXABLE
        if self.valid_structure:
            if self.plugin_debug:
                qInfo("Valid file structure")
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.INVALID


class DragonsDogmaDarkArisen(BasicGame):
    Name = "Dragon's Dogma: Dark Arisen Support Plugin"
    Author = "Luca/EzioTheDeadPoet/MikoMuto"
    Version = "1.2.0"

    GameName = "Dragon's Dogma: Dark Arisen"
    GameShortName = "dragonsdogma"
    GameNexusName = "dragonsdogma"
    GameSteamId = 367500
    GameGogId = 1242384383
    GameBinary = "DDDA.exe"
    GameDataPath = "nativePC"
    GameSupportURL = (
        "https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        + "Game:-Dragon's-Dogma:-Dark-Arisen"
    )
    GameSaveExtension = "sav"

    def __init__(self):
        BasicGame.__init__(self)
        self._organizer = None

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._organizer = organizer
        self._featureMap[mobase.ModDataChecker] = DragonsDogmaDarkArisenModDataChecker()
        return True

    @staticmethod
    def get_cloud_save_directory():
        steam_path = Path(find_steam_path())
        user_data = steam_path.joinpath("user_data")
        for child in user_data.iterdir():
            name = child.name
            try:
                steam_ident = int(name)
            except ValueError:
                steam_ident = -1
            if steam_ident == -1:
                continue
            cloud_saves = child.joinpath("367500", "remote")
            if cloud_saves.exists() and cloud_saves.is_dir():
                return str(cloud_saves)
        return None

    def savesDirectory(self) -> QDir:
        documents_saves = QDir(
            str(os.getenv("LOCALAPPDATA"))
            + "\\GOG.com\\Galaxy\\Applications\\49987265717041704"
            + "\\Storage\\Shared\\Files"
        )
        if self.is_steam():
            cloud_saves = self.get_cloud_save_directory()
            if cloud_saves is not None:
                return QDir(cloud_saves)
        return documents_saves
