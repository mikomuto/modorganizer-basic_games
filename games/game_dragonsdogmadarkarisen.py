import os, re
from pathlib import Path
from typing import List, Optional

import mobase
from PyQt6.QtCore import QDateTime, QDir, QFile, QFileInfo, Qt, qInfo
from ..basic_game import BasicGame

class DragonsDogmaDarkArisenModDataChecker(mobase.ModDataChecker):
    gamePluginDebug = False
    ValidFileStructure = False
    FixableFileStructure = False
    RE_BODYFILE = re.compile('[fm]_[aiw]_\w+.arc')
    RE_BACKUP = re.compile('.*BACK *UP.*', re.IGNORECASE)
    VALID_ROOT_FOLDERS = ["rom", "movie", "sound"]
    VALID_FILE_EXTENSIONS = [".arc", ".gmd", ".ist", ".lvl", ".stm", ".shl", ".tex", ".qct", ".qr", "wmv"]
    NO_CHILDFOLDERS = ["a_acc", "i_body", "w_leg"]
    FilesToMove: list[tuple[mobase.FileTreeEntry, str]] = []
    FoldersToMove: list[tuple[mobase.FileTreeEntry, str]] = []
    FoldersToDelete: list[tuple[mobase.FileTreeEntry, str]] = []
        
    def checkEntry(self, path: str, entry: mobase.FileTreeEntry) -> mobase.IFileTree.WalkReturn:
        # we check to see if an .arc file is contained within a valid root folder
        pathRoot = path.split(os.sep)[0]
        entryExt = entry.suffix().lower()
        
        if self.gamePluginDebug:
            qInfo("Tree walk (path : entry): " + path + " : " + entry.name())
                
        
        #if we reach this point, we can start collecting info on modifications needed
        if entry.isDir():
            parent = entry.parent()
            if parent is not None:
                isBackup = self.RE_BACKUP.match(entry.name())
                if isBackup:
                    self.FixableFileStructure = True
                    size = len(self.FoldersToDelete)
                    if (entry, path) not in self.FoldersToDelete:
                        if self.gamePluginDebug:
                            qInfo("Adding to folder delete list: " + str(size) + ": " + path + entry.name())
                        self.FoldersToDelete.append((entry, path))
                else:
                    if pathRoot.lower() not in self.VALID_ROOT_FOLDERS:
                        if parent in self.VALID_ROOT_FOLDERS:
                            self.FixableFileStructure = True
                            size = len(self.FoldersToMove)
                            if self.gamePluginDebug:
                                qInfo("Adding to folder move list: " + str(size) + ": " + path + entry.name())
                            self.FoldersToMove.append((entry, parent.name()))
        else:
            if pathRoot.lower() in self.VALID_ROOT_FOLDERS:
                for extension in self.VALID_FILE_EXTENSIONS:
                    if entry.name().lower().endswith(extension.lower()):
                        self.ValidFileStructure = True
                        if self.gamePluginDebug:
                            qInfo("Valid file structure found")
                        return mobase.IFileTree.WalkReturn.STOP
            isBodyFile = self.RE_BODYFILE.match(entry.name())
            if isBodyFile:
                self.FixableFileStructure = True
                parentFolder = str(entry.name())[0]
                grandParentFolder = re.split(r'_(?=._)|[0-9]',str(entry.name()))[1]
                size = len(self.FilesToMove)
                if self.gamePluginDebug:
                    qInfo("Adding to file move list: " + str(size) + ": " + path + entry.name())
                if grandParentFolder in self.NO_CHILDFOLDERS:
                    targetPath = "/rom/eq/" + grandParentFolder + "/"    
                    self.FilesToMove.append((entry, targetPath))
                else:
                    targetPath = "/rom/eq/" + grandParentFolder + "/" + parentFolder + "/"
                    self.FilesToMove.append((entry, targetPath))
             
        return mobase.IFileTree.WalkReturn.CONTINUE
        
    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        size_folderstodelete = len(self.FoldersToDelete)
        if self.gamePluginDebug:
            qInfo("folder delete list size: " + str(size_folderstodelete))
        size_folderstomove = len(self.FoldersToMove)
        if self.gamePluginDebug:
            qInfo("folder move list size: " + str(size_folderstomove))
        size_filestomove = len(self.FilesToMove)
        if self.gamePluginDebug:
            qInfo("file move list size: " + str(size_filestomove))
        if size_folderstodelete > 0:
            for entry, path in self.FoldersToDelete:
                if self.gamePluginDebug:
                    qInfo("Deleting folder: " + path + entry.name())
                filetree.move(entry, "/delete/" + entry.name(), policy=mobase.IFileTree.MERGE)
        if size_folderstomove > 0:
            for entry, path in self.FoldersToMove:
                entryPath = filetree.pathTo(entry, os.sep)
                pathRoot = entryPath.split(os.sep)[0]
                if self.gamePluginDebug:
                    qInfo("Moving folder: " + path + "/" + entry.name())
                filetree.move(entry, path + "/" + entry.name(), policy=mobase.IFileTree.MERGE)
                filetree.remove(pathRoot) #remove empty branch
        else:
            for entry, path in self.FilesToMove:
                if self.gamePluginDebug:
                    qInfo("Moving file: " + path + entry.name())
                filetree.move(entry, path, policy=mobase.IFileTree.MERGE)

        #remove invalid root folders
        for entry in filetree:
            if entry is not None:
                if entry.name() not in self.VALID_ROOT_FOLDERS:
                    if self.gamePluginDebug:
                        qInfo("Deleting invalid root: " + entry.name())
                    filetree.remove(entry.name())
        
        return filetree

    def dataLooksValid(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        if self.gamePluginDebug:
            qInfo("Data validation start")
        self.ValidFileStructure = False
        self.FixableFileStructure = False
        self.FilesToMove.clear()
        self.FoldersToMove.clear()
        self.FoldersToDelete.clear()
       
        #check filetree
        tree.walk(self.checkEntry, os.sep)
        
        #fix if needed
        if (self.FixableFileStructure == True):
                if self.gamePluginDebug:
                    qInfo("Fixable file structure found")
                return mobase.ModDataChecker.FIXABLE
        else:
            if (self.ValidFileStructure == True):
                if self.gamePluginDebug:
                    qInfo("Valid file structure found")
                return mobase.ModDataChecker.VALID
        if self.gamePluginDebug:
            qInfo("Invalid file structure found")
        return mobase.ModDataChecker.INVALID
     
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
            if cloudSaves is None:
                return documentsSaves
            return QDir(cloudSaves)
        
        return documentsSaves
