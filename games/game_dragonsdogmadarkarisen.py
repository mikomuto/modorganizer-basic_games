import os, re
from pathlib import Path
from typing import List, Optional

import mobase
from PyQt6.QtCore import QDateTime, QDir, QFile, QFileInfo, Qt, qInfo
from ..basic_game import BasicGame

class DragonsDogmaDarkArisenModDataChecker(mobase.ModDataChecker):
    ValidFileStructure = False
    FixableFileStructure = False
    RE_BODYFILE = re.compile('[fm]_[aiw]_\w+.arc')
    RE_BACKUP = re.compile('.*BACK *UP.*', re.IGNORECASE)
    VALID_ROOT_FOLDERS = ["rom", "movie", "sound"]
    VALID_FILE_EXTENSIONS = [".arc", ".ist", ".lvl", ".stm", ".shl", ".tex", ".qct", ".qr", "wmv"]
    NO_CHILDFOLDERS = ["a_acc", "i_body", "w_leg"]
    FilesToMove: list[tuple[mobase.FileTreeEntry, str]] = []
    FoldersToMove: list[tuple[mobase.FileTreeEntry, str]] = []
        
    def checkEntry(self, path: str, entry: mobase.FileTreeEntry) -> mobase.IFileTree.WalkReturn:
        # we check to see if an .arc file is contained within a valid root folder
        pathRoot = path.split(os.sep)[0]
        entryExt = entry.suffix().lower()
                
        if pathRoot.lower() in self.VALID_ROOT_FOLDERS:
            for extension in self.VALID_FILE_EXTENSIONS:
                if entry.name().lower().endswith(extension.lower()):
                    self.ValidFileStructure = True
                    #if bool(DragonsDogmaDarkArisen()._get_setting("debug")):
                    #    qInfo("Valid file structure found")
                    return mobase.IFileTree.WalkReturn.STOP
        else:
            #if we reach this point, we can start collecting info on modifications needed
            isBackup = self.RE_BACKUP.match(path)
            if not isBackup:
                if entry.isDir():
                    parent = entry.parent()
                    if parent is not None:
                        if parent in self.VALID_ROOT_FOLDERS:
                            self.FixableFileStructure = True
                            size = len(self.FoldersToMove)
                            #qInfo("Adding to folder move list: " + str(size) + ": " + path + entry.name())
                            self.FoldersToMove.append((entry, parent.name()))
                else:
                    isBodyFile = self.RE_BODYFILE.match(entry.name())
                    if isBodyFile:
                        self.FixableFileStructure = True
                        parentFolder = str(entry.name())[0]
                        grandParentFolder = re.split(r'_(?=._)|[0-9]',str(entry.name()))[1]
                        size = len(self.FilesToMove)
                        #qInfo("Adding to file move list: " + str(size) + ": " + path + entry.name())
                        if grandParentFolder in self.NO_CHILDFOLDERS:
                            targetPath = "/rom/eq/" + grandParentFolder + "/"    
                            self.FilesToMove.append((entry, targetPath))
                        else:
                            targetPath = "/rom/eq/" + grandParentFolder + "/" + parentFolder + "/"
                            self.FilesToMove.append((entry, targetPath))
                     
        return mobase.IFileTree.WalkReturn.CONTINUE

    def dataLooksValid(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        #qInfo("Data validation start")
        self.ValidFileStructure = False
        self.FixableFileStructure = False
        self.FilesToMove.clear()
        self.FoldersToMove.clear()
       
        #check filetree
        #qInfo("Starting tree walk")
        tree.walk(self.checkEntry, os.sep)
        
        #fix if needed
        if (self.FixableFileStructure == True):
                #qInfo("Fixable file structure found")
                return mobase.ModDataChecker.FIXABLE
        
        #all good?
        if (self.ValidFileStructure == True):
                #qInfo("Valid file structure found")
                return mobase.ModDataChecker.VALID

        #qInfo("Invalid file structure found")
        return mobase.ModDataChecker.INVALID
        
    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        size_folderstomove = len(self.FoldersToMove)
        #qInfo("folder move list size: " + str(size_folderstomove))
        size_filestomove = len(self.FilesToMove)
        #qInfo("file move list size: " + str(size_filestomove))
        if size_folderstomove > 0:
            for entry, path in self.FoldersToMove:
                entryPath = filetree.pathTo(entry, os.sep)
                pathRoot = entryPath.split(os.sep)[0]
                #qInfo("Moving folder: " + path + "/" + entry.name())
                filetree.move(entry, path + "/" + entry.name(), policy=mobase.IFileTree.MERGE)
                filetree.remove(pathRoot) #remove empty branch
        else:
            for entry, path in self.FilesToMove:
                #qInfo("Moving file: " + path + entry.name())
                filetree.move(entry, path, policy=mobase.IFileTree.MERGE)

        #remove invalid root folders
        for entry in filetree:
            if entry is not None:
                if entry.name() not in self.VALID_ROOT_FOLDERS:
                    #qInfo("Deleting: " + entry.name())
                    filetree.remove(entry.name())
        
        return filetree

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
        self._featureMap[
            mobase.ModDataChecker
        ] = DragonsDogmaDarkArisenModDataChecker()
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
        
    def settings(self) -> list[mobase.PluginSetting]:
        return [
            mobase.PluginSetting(
                "debug",
                'Enable verbose logging',
                False,
            ),
        ]

    def _get_setting(self, key: str) -> mobase.MoVariant:
        return self._organizer.pluginSetting(self.name(), key)

    def _set_setting(self, key: str, value: mobase.MoVariant):
        self._organizer.setPluginSetting(self.name(), key, value)
