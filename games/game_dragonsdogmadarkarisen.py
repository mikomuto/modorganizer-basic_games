import os, re
from pathlib import Path
from typing import List, Optional

import mobase
from PyQt6.QtCore import QDir,qInfo
from PyQt6.QtWidgets import QMessageBox
from ..basic_game import BasicGame
from ..steam_utils import find_steam_path

class DragonsDogmaDarkArisenModDataChecker(mobase.ModDataChecker):
    gamePluginDebug = True
    ValidFileStructure = False
    RE_BODYFILE = re.compile('[fm]_[aiw]_\w+.arc')
    RE_DL1_BODYFILE = re.compile('[fm]_a_\w+820\d.arc')
    RE_HEXEXTENSION = re.compile('[\.0-9a-fA-F]{8}')
    VALID_ROOT_FOLDERS = ["rom", "movie", "sound"]
    VALID_CHILD_FOLDERS = ["dl1", "enemy", "eq", "etc", "event", "gui", "h_enemy", "ingamemanual", "item_b", 
            "map", "message", "mnpc", "npc", "npcfca", "npcfsm","om","pwnmsg","quest","shell","sk","sound",
            "stage","voice","wp","bbsrpg_core","bbs_rpg","game_main","Initialize","title",]
    VALID_FILE_EXTENSIONS = [".arc", ".gmd", ".ist", ".lvl", ".stm", ".shl", ".tex", ".qct", ".qr", "wmv"]
    NO_CHILDFOLDERS = ["a_acc", "i_body", "w_leg"]
    MoveList: list[tuple[mobase.FileTreeEntry, str]] = []
    DeleteList: list[tuple[mobase.FileTreeEntry, str]] = []
        
    def checkFiletreeEntry(self, path: str, entry: mobase.FileTreeEntry) -> mobase.IFileTree.WalkReturn:
        # we check to see if anany valid game file is contained within a valid root folder
        pathRoot = path.split(os.sep)[0]
        entryName, entryExt = os.path.splitext(entry.name())
        
        if self.gamePluginDebug:
            qInfo("checkFiletreeEntry: " + path + " : " + entry.name())
        if entry.isFile():
            if pathRoot.lower() in self.VALID_ROOT_FOLDERS:
                for extension in self.VALID_FILE_EXTENSIONS:
                    if entry.name().lower().endswith(extension.lower()):
                        self.ValidFileStructure = True
                        if self.gamePluginDebug:
                            qInfo("Valid file structure found")
                        return mobase.IFileTree.WalkReturn.STOP

        return mobase.IFileTree.WalkReturn.CONTINUE
        
    def checkFiletreeEntryAdvanced(self, path: str, entry: mobase.FileTreeEntry) -> mobase.IFileTree.WalkReturn:
        # we check to see if an .arc file is contained within a valid root folder
        pathRoot = path.split(os.sep)[0]
        entryName, entryExt = os.path.splitext(entry.name())
        
        if self.gamePluginDebug:
            qInfo("checkFiletreeEntryAdvanced: " + path + " : " + entry.name())

        if entry.isDir():            
            parent = entry.parent()
            if parent is not None:
                if pathRoot not in self.VALID_ROOT_FOLDERS:
                    if parent in self.VALID_ROOT_FOLDERS:                            
                        if self.gamePluginDebug:
                            qInfo(f"Adding parent to move list: {entry.name()} {parent.name()}")
                        self.MoveList.append((entry, parent.name() + os.sep))
                    elif entry in self.VALID_CHILD_FOLDERS and parent not in self.VALID_CHILD_FOLDERS:
                        if self.gamePluginDebug:
                            qInfo(f"Adding child to move list: {path} {entry.name()}")
                        self.MoveList.append((entry, "rom" + os.sep))
        else:
            isBodyFile = self.RE_BODYFILE.match(entry.name())
            isDl1BodyFile = self.RE_DL1_BODYFILE.match(entry.name())
            if isBodyFile:
                
                parentFolder = str(entry.name())[0]
                grandParentFolder = re.split(r'_(?=._)|[0-9]',str(entry.name()))[1]
                size = len(self.MoveList)
                if self.gamePluginDebug:
                    qInfo("Adding to move list: " + path + entry.name())
                if isDl1BodyFile:
                    targetPath = "/rom/dl1/eq/"  + grandParentFolder + os.sep + parentFolder + os.sep    
                    self.MoveList.append((entry, targetPath))
                elif grandParentFolder in self.NO_CHILDFOLDERS:
                    targetPath = "/rom/eq/" + grandParentFolder + os.sep    
                    self.MoveList.append((entry, targetPath))
                else:
                    targetPath = "/rom/eq/" + grandParentFolder + os.sep + parentFolder + os.sep
                    self.MoveList.append((entry, targetPath))
            hasHexFileExtension = self.RE_HEXEXTENSION.match(entryExt)
            qInfo(f"Entry ext: {entryExt}")
            # ignore sound and game manual files with hex extenstions
            if hasHexFileExtension: # and not ('sound' in path or 'ingamemanual' in path):
                qInfo("Invalid TEX file found: %s" % (path + entry.name()))
                #QMessageBox.information(None, "Test", "testing....")
                self.MoveList.append((entry, path + entryName + ".tex"))

        return mobase.IFileTree.WalkReturn.CONTINUE
        
    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        # advanced filetree check
        filetree.walk(self.checkFiletreeEntryAdvanced, os.sep)
        
        size_DeleteList = len(self.DeleteList)
        size_MoveList = len(self.MoveList)
        if self.gamePluginDebug:    
            qInfo("folder delete list size: " + str(size_DeleteList))
            qInfo("folder move list size: " + str(size_MoveList))
        if size_DeleteList > 0:
            for entry, path in reversed(self.DeleteList):
                if self.gamePluginDebug:
                    qInfo("Deleting: " + path + entry.name())
                filetree.move(entry, "/delete/" + entry.name(), policy=mobase.IFileTree.MERGE)
        if size_MoveList > 0:
            for entry, path in reversed(self.MoveList):
                entryPath = filetree.pathTo(entry, os.sep)
                pathRoot = entryPath.split(os.sep)[0]
                if self.gamePluginDebug:
                    qInfo(f"Moving: {entry.name()} to {path}")
                filetree.move(entry, path, policy=mobase.IFileTree.MERGE)
                filetree.remove(pathRoot) #remove empty branch

        # remove invalid root folders
        # for entry in filetree:
            # if entry is not None:
                # if entry.name() not in self.VALID_ROOT_FOLDERS:
                    # if self.gamePluginDebug:
                        # qInfo("Deleting invalid root: " + entry.name())
                    # filetree.remove(entry.name())
        
        return filetree

    def dataLooksValid(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        if self.gamePluginDebug:
            qInfo("Data validation start")
        self.ValidFileStructure = False
        self.MoveList.clear()
        self.DeleteList.clear()
       
        # check filetree
        tree.walk(self.checkFiletreeEntry, os.sep)

        if (self.ValidFileStructure == True):
            if self.gamePluginDebug:
                qInfo("Valid file structure found")
            return mobase.ModDataChecker.VALID
                
        return mobase.ModDataChecker.FIXABLE
     
class DragonsDogmaDarkArisen(BasicGame):
    Name = "Dragon's Dogma: Dark Arisen Support Plugin"
    Author = "Luca/EzioTheDeadPoet/MikoMuto"
    Version = "1.2.0"

    GameName = "Dragon's Dogma: Dark Arisen"
    GameShortName = "dragonsdogma"
    GaneNexusHame = "dragonsdogma"
    GameSteamId = 367500
    GameGogId = 1242384383
    GameBinary = "DDDA.exe"
    GameDataPath = "nativePC"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Dragon's-Dogma:-Dark-Arisen"
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
    def getCloudSaveDirectory():
        steamPath = Path(find_steam_path())
        userData = steamPath.joinpath("userdata")
        for child in userData.iterdir():
            name = child.name
            try:
                userID = int(name)
            except ValueError:
                userID = -1
            if userID == -1:
                continue
            cloudSaves = child.joinpath("367500", "remote")
            if cloudSaves.exists() and cloudSaves.is_dir():
                return str(cloudSaves)
        return None
    
    def savesDirectory(self) -> QDir:
        documentsSaves = QDir(str(os.getenv('LOCALAPPDATA')) + "\\GOG.com\\Galaxy\\Applications\\49987265717041704\\Storage\\Shared\\Files")
        if self.is_steam():
            cloudSaves = self.getCloudSaveDirectory()
            if cloudSaves is not None:
                return QDir(cloudSaves)
        return documentsSaves