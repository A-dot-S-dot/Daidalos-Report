"""Check for newbies of the Dortmunder-Stifti-group."""
import sys
import time

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                             QFormLayout, QGridLayout, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QPushButton,
                             QSpinBox, QTextEdit, QToolButton, QWidget)
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys


# Define Error classes for handling common errors.
class NoSettingsError(Exception):
    """Raise Error if no 'settings.txt' does not exist."""


class NoMemberListError(Exception):
    """Raise Error if 'memberlist.txt' does not exits."""


class NoMainPageError(Exception):
    """Raise Error if the report ist not on the main page after login.

    Common reasons are:
    - Wrong Credentials
    - Intern message appears in Daidalosnet
    """


class NoSpeakerLabelError(Exception):
    """Raise Error if the report does not find the Speaker label.

    Possible reasons are:
    - The user is not a Speaker
    - The waiting time is insufficient
    """


class NoPasswordError(Exception):
    """Raise Error if the password is not set."""


class DaidalosChecker():
    """Class for checking changes of user's university group."""

    def newMembers(self, externPassword=None):
        """Check if new members appeared.

        The argument 'extenPassword' is  made for reading a password 
        without saving it.

        Returns a bool if some changes appeared.
        """
        if externPassword == "":
            raise NoPasswordError
        else:
            self.externPassword = externPassword

        self.readSettings()
        self.buildDriver()
        self.driver.get("https://www.daidalosnet.de")
        self.login()
        self.navigateToTable()
        self.getOnlineMemberList()
        self.getLocalMemberList()
        self.driver.close()

        return self.compareMemberList()

    def readSettings(self):
        """Build attributes by reading 'settings.txt'."""
        try:
            with open("settings.txt", "r") as file:
                options = eval(file.read())
        except FileNotFoundError:
            raise NoSettingsError

        self.username = options["username"]

        if self.externPassword:
            self.password = self.externPassword
        else:
            self.password = options["password"]

        self.wait = options["wait"]
        self.browser = options["browser"]
        self.driverPath = options["driverPath"]
        self.hide = options["hide"]

    def buildDriver(self):
        """Generate driver attribute by distinguishing browsers."""
        if self.browser == "Firefox":
            self.buildFirefoxDriver()
        elif self.browser == "Chrome":
            self.buildChromeDriver()
        elif self.browser == "Edge":
            self.buildEdgeDriver()
        elif self.browser == "Safari":
            self.buildSafariDriver()

    def buildFirefoxDriver(self):
        """Generate Firefox driver attribute."""
        if self.hide:
            from selenium.webdriver.firefox.options import Options
            options = Options()
            options.add_argument("--headless")
        else:
            options = None

        self.driver = webdriver.Firefox(
            options=options,
            executable_path=self.driverPath
        )

    def buildChromeDriver(self):
        """Generate Chrome driver attribute."""
        if self.hide:
            from selenium.webdriver.chrome.options import Options
            options = Options()
            options.add_argument("--headless")
        else:
            options = None

        self.driver = webdriver.Chrome(
            options=options,
            executable_path=self.driverPath
        )

    def buildSafariDriver(self):
        """Generate Safari driver attribute.

        Notice, it is not possible to hide the browser
        while executing. It also needs further setup.
        """
        self.driver = webdriver.Safari()

    def buildEdgeDriver(self):
        """Generate Edge driver attribute.

        Notice, it is not possible to hide the browser
        while executing."""
        self.driver = webdriver.Edge(
            executable_path=self.driverPath
        )

    def login(self):
        """Log into Daidalosnet."""
        time.sleep(self.wait)

        self.insertTextInElement("Username", self.username)
        self.insertTextInElement("Password", self.password, enter=True)

    def insertTextInElement(self, elementName, text, enter=False):
        """Insert 'text' in element named 'elementName' and press 'enter' if needed."""
        element = self.driver.find_element_by_name(elementName)
        element.clear()
        element.send_keys(text)

        if enter:
            element.send_keys(Keys.ENTER)

    def navigateToTable(self):
        """Navigate to the memberlist of the users group."""
        time.sleep(self.wait)

        try:
            frameSwitch = self.driver.find_element_by_xpath(
                "/html/frameset/frameset/frameset/frame[2]")
        except NoSuchElementException:
            raise NoMainPageError

        self.driver.switch_to.frame(frameSwitch)

        try:
            self.driver.find_element_by_partial_link_text(
                "meine Sprecherregion").click()
        except NoSuchElementException:
            raise NoSpeakerLabelError

    def getOnlineMemberList(self):
        """Get the html code of the memeber list and save it as an attribute."""
        time.sleep(self.wait)

        memberListElement = self.driver.find_element_by_xpath(
            '//*[@id="viewmembers"]')
        self.onlineMemberList = memberListElement.get_attribute('innerHTML')

    def getLocalMemberList(self):
        """Load the locally saved memeber list."""
        try:
            with open("memberlist.txt", "r", encoding="utf-8") as file:
                self.localMemberList = file.read()

        except FileNotFoundError:
            # Create a new memberlist file
            with open("memberlist.txt", "w", encoding="utf-8") as file:
                file.write(self.onlineMemberList)
            raise NoMemberListError

    def compareMemberList(self):
        """Compate the local memberlist and the online one.

        Return a bool.
        """
        if self.localMemberList != self.onlineMemberList:
            with open("memberlist.txt", "w", encoding="utf-8") as file:
                file.write(self.onlineMemberList)
            return True

        else:
            return False


class DaidalosOptionsGui(QWidget):
    """This class creates an option window."""

    def __init__(self):
        """Build option widget."""
        super().__init__()
        self.setWindowTitle("Optionen")
        self.layout = QFormLayout()
        self.loadOptions()
        self.addUsername()
        self.addPassword()
        self.addCheckNoEncrytption()
        self.addBrowser()
        self.addDriverPath()
        self.addHideOption()
        self.addWaitingTime()
        self.addSaveButton()
        self.setLayout(self.layout)

        # Disable Inputs in certain cases
        self.disablePasswordInput()
        self.disableBrowserOptions()

    def loadOptions(self):
        """Load Options by reading 'settings.txt'.

        If no 'settings.txt' exists the default values are:
        - username : None
        - password : None
        - noEncryption : True
        - browser : Firefox
        - driverPath : None
        - hide : False
        - waitingTime : 4 
        """
        try:
            with open("settings.txt", "r") as file:
                self.options = eval(file.read())

        except FileNotFoundError:
            self.usernameInput = ""
            self.passwordInput = ""
            self.noEncryptionInput = True
            self.browserInput = "Firefox"
            self.driverPathInput = ""
            self.hideInput = False
            self.waitInput = 4

        else:
            self.usernameInput = self.options["username"]
            self.passwordInput = self.options["password"]
            self.noEncryptionInput = self.options["noEncryption"]
            self.browserInput = self.options["browser"]
            self.driverPathInput = self.options["driverPath"]
            self.hideInput = self.options["hide"]
            self.waitInput = self.options["wait"]

    def addUsername(self):
        """Add username option."""
        self.username = QLineEdit()
        self.username.setText(self.usernameInput)
        self.layout.addRow(QLabel("Benutzername:"), self.username)

    def addPassword(self):
        """Add password option."""
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setText(self.passwordInput)
        self.layout.addRow(QLabel("Passwort:"), self.password)

    def addCheckNoEncrytption(self):
        """Add query for agreeing of not using encryption methods."""
        self.checkNoEncryption = QCheckBox()
        self.checkNoEncryption.setChecked(self.noEncryptionInput)
        self.checkNoEncryption.stateChanged.connect(self.disablePasswordInput)
        self.layout.addRow(QLabel("Keine Verschlüsselung:"),
                           self.checkNoEncryption)

    def disablePasswordInput(self):
        """Disable password query if unsave saving of password is not wanted."""
        encryptionWanted = not self.checkNoEncryption.isChecked()
        if encryptionWanted:
            self.password.clear()

        self.password.setDisabled(encryptionWanted)

    def addBrowser(self):
        """Add browser option."""
        self.browser = QComboBox()
        self.browser.addItems(["Firefox", "Chrome", "Edge", "Safari"])
        self.browser.setCurrentText(self.browserInput)
        self.browser.currentIndexChanged.connect(self.disableBrowserOptions)
        self.layout.addRow(QLabel("Browser:"), self.browser)

    def disableBrowserOptions(self):
        """Disable the 'driver path' and 'hide' query if 'Safari' is choosen."""
        isSafari = self.browser.currentText() == "Safari"
        isEdge = self.browser.currentText() == "Edge"

        if isSafari:
            self.driverPath.setText("")

        if isSafari or isEdge:
            self.hideOption.setChecked(False)

        self.driverPath.setDisabled(isSafari)
        self.driverToolButton.setDisabled(isSafari)
        self.hideOption.setDisabled(isSafari or isEdge)

    def addDriverPath(self):
        """Add query for driver path."""
        layout = QHBoxLayout()

        self.driverPath = QLineEdit()
        self.driverPath.setText(self.driverPathInput)
        self.driverToolButton = QToolButton()
        self.driverToolButton.clicked.connect(self.setDriverPath)

        layout.addWidget(self.driverPath)
        layout.addWidget(self.driverToolButton)

        self.layout.addRow(QLabel("Driver Pfad:"), layout)

    def setDriverPath(self):
        """Open a file dialog to choose a driver."""
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        self.driverPath.setText(dialog.getOpenFileName()[0])

    def addHideOption(self):
        """Add query for opening browser in the background."""
        self.hideOption = QCheckBox()
        self.hideOption.setChecked(self.hideInput)
        self.layout.addRow(QLabel("Hintergrundausführung:"), self.hideOption)

    def addWaitingTime(self):
        """Add query for time the report should wait between several steps."""
        self.wait = QSpinBox()
        self.wait.setValue(self.waitInput)
        self.wait.setMinimum(1)
        self.layout.addRow(
            QLabel("Wartezeit (in Sekunden):"), self.wait)

    def addSaveButton(self):
        """Add a button for saving content."""
        self.saveButton = QPushButton()
        self.saveButton.setText("Speichern")
        self.saveButton.clicked.connect(self.saveOptions)
        self.layout.addRow(self.saveButton)

    def saveOptions(self):
        """Save content of the options window in 'settings.txt'."""
        with open("settings.txt", "w") as file:
            file.write(str({
                "username": self.username.text(),
                "password": self.password.text(),
                "noEncryption": self.checkNoEncryption.isChecked(),
                "browser": self.browser.currentText(),
                "driverPath": self.driverPath.text(),
                "hide": self.hideOption.isChecked(),
                "wait": self.wait.value()
            }))

        self.close()


class DaidalosMainGui(QWidget):
    """Provide the main gui."""

    def __init__(self):
        """Build main gui."""
        super().__init__()
        self.checker = DaidalosChecker()
        self.options = DaidalosOptionsGui()
        self.addMessageBox()
        self.addButtons()
        self.addDesign()

        # Set icon
        self.setWindowIcon(QIcon("add_member.ico"))

        # Determine users name
        self.name = self.options.usernameInput.split(" ")[0]

    def addMessageBox(self):
        """Add a message box which provides the report informations."""
        self.messageBox = QTextEdit(self)
        self.messageBox.setReadOnly(True)
        self.messageBox.setText(
            "Herzlich Willkommen beim Daidalos-Report!")

    def addButtons(self):
        """Add several buttons."""
        self.addRunButton()
        self.addOptionButton()
        self.addCloseButton()

    def addRunButton(self):
        """Add the run button for initializing the check process."""
        self.runButton = QPushButton(self)
        self.runButton.setText("Report Starten")
        self.runButton.clicked.connect(self.runCheck)

    def addOptionButton(self):
        """Add option button for opening an option window."""
        self.optionButton = QPushButton(self)
        self.optionButton.setText("Optionen")
        self.optionButton.clicked.connect(self.options.show)

    def addCloseButton(self):
        """Add a close button for closing the entire app."""
        self.closeButton = QPushButton(self)
        self.closeButton.setText("Beenden")
        self.closeButton.clicked.connect(self.closeAll)

    def closeAll(self):
        """Close the options window and the app itself."""
        self.options.close()
        self.close()

    def addDesign(self):
        """Add style like gridding and titling."""
        self.setWindowTitle("Daidalos Report")
        layout = QGridLayout()
        layout.addWidget(self.messageBox, 0, 0, 3, 2)
        layout.addWidget(self.runButton, 0, 2)
        layout.addWidget(self.optionButton, 1, 2)
        layout.addWidget(self.closeButton, 2, 2)
        self.setLayout(layout)

    def getPassword(self):
        """Obtain a password using an input dialog."""
        password, okPressed = QInputDialog.getText(
            self, "Passwort Abfrage", "Gebe bitte dein Passwort ein:",
            QLineEdit.Password)
        if okPressed:
            return password
        else:
            return ""

    def runCheck(self):
        """Run a check.

        All errors which are raised while selenium runs are handled
        and displayed.
        """
        if not self.options.checkNoEncryption.isChecked():
            self.messageBox.setText("Ich benötige dein Passwort.")
            password = self.getPassword()
        else:
            password = None

        try:
            newMembers = self.checker.newMembers(externPassword=password)

        except NoSettingsError:
            self.messageBox.setText(
                "Herzlich Willkommen! Ich bin Daidalos-Report! "
                + "Vielen Dank, dass du dich für mich entschieden hast. "
                + "Ich informiere dich, "
                + "ob deine Hochschulgruppe einen Neuzugang hat oder nicht. "
                + "Stelle mich bitte ein, damit ich sofort loslegen kann!"
            )
            self.options.show()

        except NoMemberListError:
            self.messageBox.setText(
                "Ich habe nun alles eingestellt! "
                + "Es hat alles funktioniert und ich freue mich, "
                + "in deinen Diensten stehen zu dürfen."
                + "\n\n Bis bald!"
            )
            self.checker.driver.close()

        except NoPasswordError:
            self.messageBox.setText("Du hast kein Passwort eingegeben...")

        except NoMainPageError:
            self.messageBox.setText(
                "Anscheinend ist die Startseite vom Daidalosnet nach "
                + "meinem Anmeldeversuch nicht erschienen. "
                + "Sind deine Anmeldedaten korrekt? "
                + "Oder hat das Daidalosnet eine Mitteilung für dich?")
            self.checker.driver.close()

        except NoSpeakerLabelError:
            self.messageBox.setText(
                "Ich habe unten rechts nicht die Option "
                + "\"meine Sprecherregion:\" gefunden...\n\n"
                + "Vielleicht sollte ich länger warten, "
                + "damit die Seite anständig gelade ist.\n\n"
                + "Oder bist du noch nicht als Sprechender eingetragen?"
                + "\n\nIch habe dir deinen Browser offen gelassen, "
                + "damit du nachschauen kannst."
            )

        except Exception as e:
            self.messageBox.setText(
                "Irgendetwas stimmt hier nicht... "
                + "Ich habe folgenden Fehler erhalten:"
                + "\n\n" + str(e) + "\n\n"
            )

        else:
            if newMembers:
                self.messageBox.setText(
                    f"Hey {self.name}! Ich glaube in deiner Hochschulgruppe "
                    + "hat sich was getan! "
                    + "Schaue gleich mal rein!")
            else:
                self.messageBox.setText(
                    f"Tja {self.name}. "
                    + "Wie es aussieht, ist alles wie beim Alten..."
                )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    report = DaidalosMainGui()
    report.runCheck()
    report.show()
    sys.exit(app.exec_())
