from PyQt6.QtWidgets import (QMainWindow, QApplication, QTextEdit, QVBoxLayout, 
                           QWidget, QStatusBar, QFileDialog, QMenuBar,
                           QMessageBox, QDialog, QHBoxLayout, QPushButton, 
                           QLabel, QLineEdit, QInputDialog, QPlainTextEdit,
                           QScrollBar, QFontDialog)
from PyQt6.QtGui import (QAction, QFont, QTextCursor, QColor, QPainter, 
                        QTextCharFormat, QSyntaxHighlighter, QTextFormat, QTextDocument)
from PyQt6.QtCore import Qt, QRect, QSize, QTimer, QSettings
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPageSetupDialog
import sys
import os
from datetime import datetime

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), 
                self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
            self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        offset = self.contentOffset()
        top = self.blockBoundingGeometry(block).translated(offset).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(0, int(top), self.line_number_area.width(),
                    self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

class FindReplaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find and Replace")
        self.setFixedSize(400, 200)
        layout = QVBoxLayout()

        # Find input
        find_layout = QHBoxLayout()
        self.find_input = QLineEdit()
        find_layout.addWidget(QLabel("Find:"))
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)

        # Replace input
        replace_layout = QHBoxLayout()
        self.replace_input = QLineEdit()
        replace_layout.addWidget(QLabel("Replace with:"))
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)

        # Options
        options_layout = QHBoxLayout()
        self.case_sensitive = QPushButton("Match Case")
        self.case_sensitive.setCheckable(True)
        self.whole_words = QPushButton("Whole Words")
        self.whole_words.setCheckable(True)
        options_layout.addWidget(self.case_sensitive)
        options_layout.addWidget(self.whole_words)
        layout.addLayout(options_layout)

        # Buttons
        button_layout = QHBoxLayout()
        find_next = QPushButton("Find Next")
        find_prev = QPushButton("Find Previous")
        replace = QPushButton("Replace")
        replace_all = QPushButton("Replace All")

        find_next.clicked.connect(self.find_next)
        find_prev.clicked.connect(self.find_previous)
        replace.clicked.connect(self.replace)
        replace_all.clicked.connect(self.replace_all)

        button_layout.addWidget(find_next)
        button_layout.addWidget(find_prev)
        button_layout.addWidget(replace)
        button_layout.addWidget(replace_all)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def find_next(self):
        flags = self.get_find_flags()
        text = self.find_input.text()
        if not self.parent().text_edit.find(text, flags):
            cursor = self.parent().text_edit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.parent().text_edit.setTextCursor(cursor)
            self.parent().text_edit.find(text, flags)

    def find_previous(self):
        flags = self.get_find_flags() | QTextDocument.FindFlag.FindBackward
        text = self.find_input.text()
        if not self.parent().text_edit.find(text, flags):
            cursor = self.parent().text_edit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.parent().text_edit.setTextCursor(cursor)
            self.parent().text_edit.find(text, flags)

    def get_find_flags(self):
        flags = QTextDocument.FindFlag(0)
        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_words.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def replace(self):
        cursor = self.parent().text_edit.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self):
        cursor = self.parent().text_edit.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.parent().text_edit.setTextCursor(cursor)
        count = 0
        while self.parent().text_edit.find(self.find_input.text(), self.get_find_flags()):
            cursor = self.parent().text_edit.textCursor()
            cursor.insertText(self.replace_input.text())
            count += 1
        cursor.endEditBlock()
        QMessageBox.information(self, "Replace All", 
            f"Replaced {count} occurrence(s)")

class Notepad(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Notepad")
        self.setMinimumSize(200, 150)  # Smaller minimum size
        self.current_file = None
        self.settings = QSettings('EnhancedNotepad', 'Notepad')

        # Main text editor
        self.text_edit = CodeEditor()
        self.text_edit.setFont(QFont("Consolas", 10))
        self.setCentralWidget(self.text_edit)

        # Setup UI components
        self.create_menubar()
        self.create_toolbar()
        self.create_statusbar()
        self.load_style()
        
        # Auto-save setup
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(60000)  # Auto-save every minute

        # Restore previous session
        self.restore_settings()

        # Enable drag and drop
        self.setAcceptDrops(True)

    def create_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.text_edit.cursorPositionChanged.connect(self.update_status)
        self.update_status()

    def update_status(self):
        cursor = self.text_edit.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.status_bar.showMessage(f"Ln {line}, Col {col}")

    def create_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)

        # Add common actions
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # Add text formatting actions
        font_action = QAction("Font", self)
        font_action.triggered.connect(self.change_font)
        toolbar.addAction(font_action)

    def change_font(self):
        font, ok = QFontDialog.getFont(self.text_edit.font(), self)
        if ok:
            self.text_edit.setFont(font)

    def create_menubar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        file_actions = [
            ("New", self.new_file, "Ctrl+N"),
            ("Open...", self.open_file, "Ctrl+O"),
            ("Save", self.save_file, "Ctrl+S"),
            ("Save As...", self.save_file_as, "Ctrl+Shift+S"),
            (None, None, None),
            ("Page Setup...", self.page_setup, None),
            ("Print...", self.print_document, "Ctrl+P"),
            (None, None, None),
            ("Exit", self.close, "Alt+F4")
        ]
        
        self.add_actions(file_menu, file_actions)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        edit_actions = [
            ("Undo", self.text_edit.undo, "Ctrl+Z"),
            ("Redo", self.text_edit.redo, "Ctrl+Y"),
            (None, None, None),
            ("Cut", self.text_edit.cut, "Ctrl+X"),
            ("Copy", self.text_edit.copy, "Ctrl+C"),
            ("Paste", self.text_edit.paste, "Ctrl+V"),
            ("Delete", lambda: self.text_edit.textCursor().removeSelectedText(), "Del"),
            (None, None, None),
            ("Find...", self.show_find_replace, "Ctrl+F"),
            ("Replace...", self.show_find_replace, "Ctrl+H"),
            ("Go To...", self.goto_line, "Ctrl+G"),
            (None, None, None),
            ("Select All", self.text_edit.selectAll, "Ctrl+A"),
            ("Time/Date", self.insert_datetime, "F5")
        ]
        
        self.add_actions(edit_menu, edit_actions)

        # Format menu
        format_menu = menubar.addMenu("Format")
        format_actions = [
            ("Word Wrap", self.toggle_word_wrap, None),
            ("Font...", self.change_font, None)
        ]
        
        self.add_actions(format_menu, format_actions)

        # View menu
        view_menu = menubar.addMenu("View")
        view_actions = [
            ("Zoom In", self.zoom_in, "Ctrl++"),
            ("Zoom Out", self.zoom_out, "Ctrl+-"),
            ("Restore Default Zoom", self.zoom_reset, "Ctrl+0")
        ]
        
        self.add_actions(view_menu, view_actions)

    def add_actions(self, menu, actions):
        for text, slot, shortcut in actions:
            if text is None:
                menu.addSeparator()
                continue
            action = QAction(text, self)
            if shortcut:
                action.setShortcut(shortcut)
            if isinstance(slot, bool):
                action.setCheckable(True)
                action.setChecked(slot)
            action.triggered.connect(slot)
            menu.addAction(action)

    def zoom_in(self):
        self.text_edit.zoomIn(1)

    def zoom_out(self):
        self.text_edit.zoomOut(1)

    def zoom_reset(self):
        self.text_edit.setFont(QFont("Consolas", 10))

    def show_find_replace(self):
        dialog = FindReplaceDialog(self)
        dialog.exec()

    def goto_line(self):
        line, ok = QInputDialog.getInt(self, "Go to Line", "Line number:",
            1, 1, self.text_edit.document().lineCount())
        if ok:
            block = self.text_edit.document().findBlockByLineNumber(line - 1)
            cursor = self.text_edit.textCursor()
            cursor.setPosition(block.position())
            self.text_edit.setTextCursor(cursor)
            self.text_edit.centerCursor()

    def page_setup(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPageSetupDialog(printer, self)
        dialog.exec()

    def print_document(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self.text_edit.print_(printer)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

            def dropEvent(self, event):
                files = [u.toLocalFile() for u in event.mimeData().urls()]
                if files:
                    if self.maybe_save():
                        self.open_file(files[0])

    def auto_save(self):
        if self.current_file and self.text_edit.document().isModified():
            self._save_to_file(self.current_file)

    def save_settings(self):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        self.settings.setValue('lastFile', self.current_file)

    def restore_settings(self):
        if self.settings.value('geometry'):
            self.restoreGeometry(self.settings.value('geometry'))
        if self.settings.value('windowState'):
            self.restoreState(self.settings.value('windowState'))
        last_file = self.settings.value('lastFile')
        if last_file and os.path.exists(last_file):
            self.open_file(last_file)

    def load_style(self):
        style_path = "style.qss"
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())

    def new_file(self):
        if self.maybe_save():
            self.text_edit.clear()
            self.current_file = None
            self.setWindowTitle("Enhanced Notepad")

    def open_file(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open File", "", 
                "Text Documents (*.txt);;All Files (*.*)"
            )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.text_edit.setPlainText(content)
                    self.current_file = path
                    self.setWindowTitle(f"Enhanced Notepad - {os.path.basename(path)}")
                    self.status_bar.showMessage(f"Opened {path}", 2000)
            except UnicodeDecodeError:
                try:
                    with open(path, 'r', encoding='cp1252') as file:
                        content = file.read()
                        self.text_edit.setPlainText(content)
                        self.current_file = path
                        self.setWindowTitle(f"Enhanced Notepad - {os.path.basename(path)}")
                        self.status_bar.showMessage(f"Opened {path}", 2000)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")

    def save_file(self):
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", 
            "Text Documents (*.txt);;All Files (*.*)"
        )
        if file_path:
            self._save_to_file(file_path)

    def _save_to_file(self, file_path):
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.text_edit.toPlainText())
            self.current_file = file_path
            self.setWindowTitle(f"Enhanced Notepad - {os.path.basename(file_path)}")
            self.status_bar.showMessage(f"Saved {file_path}", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")

    def maybe_save(self):
        if not self.text_edit.document().isModified():
            return True

        reply = QMessageBox.warning(
            self, "Enhanced Notepad",
            "The document has been modified.\nDo you want to save your changes?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Save:
            return self.save_file()
        elif reply == QMessageBox.StandardButton.Cancel:
            return False
        return True

    def toggle_word_wrap(self, checked):
        self.text_edit.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if checked 
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def insert_datetime(self):
        self.text_edit.insertPlainText(datetime.now().strftime("%I:%M %p %m/%d/%Y"))

    def closeEvent(self, event):
        if self.maybe_save():
            self.save_settings()
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Notepad()
    window.show()
    sys.exit(app.exec())

