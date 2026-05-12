import os
import sys
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
)

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import manage_chats

SCOPES = [
    'https://www.googleapis.com/auth/chat.spaces.readonly',
    'https://www.googleapis.com/auth/chat.spaces.create',
    'https://www.googleapis.com/auth/chat.memberships',
]

DEFAULT_CREDENTIALS_FILE = 'credentials.json'
DEFAULT_TOKEN_FILE = 'token.json'


class ChatManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Google Chat Manager')
        self.setMinimumSize(1100, 760)

        self.creds: Optional[Credentials] = None
        self.chat_service = None
        self.chat_spaces: List[dict] = []

        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        container_layout = QVBoxLayout(container)

        container_layout.addWidget(self._build_auth_panel())
        container_layout.addWidget(self._build_main_splitter())
        container_layout.addWidget(self._build_log_panel())

        self.setCentralWidget(container)

    def _build_auth_panel(self) -> QWidget:
        auth_group = QGroupBox('Authentication')
        auth_layout = QFormLayout(auth_group)

        self.credentials_input = QLineEdit(DEFAULT_CREDENTIALS_FILE)
        self.credentials_input.setPlaceholderText('Path to credentials.json')
        choose_credentials = QPushButton('Browse...')
        choose_credentials.clicked.connect(self._choose_credentials_file)

        credentials_layout = QHBoxLayout()
        credentials_layout.addWidget(self.credentials_input)
        credentials_layout.addWidget(choose_credentials)
        auth_layout.addRow('Credentials:', credentials_layout)

        self.token_input = QLineEdit(DEFAULT_TOKEN_FILE)
        self.token_input.setPlaceholderText('Path to token.json')
        choose_token = QPushButton('Browse...')
        choose_token.clicked.connect(self._choose_token_file)

        token_layout = QHBoxLayout()
        token_layout.addWidget(self.token_input)
        token_layout.addWidget(choose_token)
        auth_layout.addRow('Token file:', token_layout)

        self.auth_status = QLabel('Not authenticated')
        self.auth_status.setStyleSheet('color: #b71c1c; font-weight: bold;')
        auth_layout.addRow('Status:', self.auth_status)

        self.authenticate_button = QPushButton('Authenticate')
        self.authenticate_button.clicked.connect(self._authenticate)
        auth_layout.addRow('', self.authenticate_button)

        return auth_group

    def _build_main_splitter(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self._build_space_controls())
        left_layout.addWidget(self._build_space_table())
        left_layout.addStretch()

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(self._build_space_detail_panel())
        right_layout.addStretch()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([700, 400])

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.addWidget(splitter)
        return wrapper

    def _build_space_controls(self) -> QWidget:
        controls_group = QGroupBox('Chat Spaces')
        layout = QVBoxLayout(controls_group)

        buttons_layout = QHBoxLayout()
        self.refresh_button = QPushButton('Refresh Spaces')
        self.refresh_button.clicked.connect(self._load_spaces)
        self.refresh_button.setEnabled(False)

        self.create_space_button = QPushButton('Create Space')
        self.create_space_button.clicked.connect(self._create_space)
        self.create_space_button.setEnabled(False)

        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addWidget(self.create_space_button)
        buttons_layout.addStretch()

        form_layout = QFormLayout()
        self.new_space_name = QLineEdit()
        self.new_space_name.setPlaceholderText('Team or space name')
        form_layout.addRow('Space title:', self.new_space_name)

        layout.addLayout(buttons_layout)
        layout.addLayout(form_layout)
        controls_group.setLayout(layout)
        return controls_group

    def _build_space_table(self) -> QWidget:
        self.space_table = QTableWidget(0, 4)
        self.space_table.setHorizontalHeaderLabels(['Display Name', 'Space ID', 'Space Type', 'Members'])
        self.space_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.space_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.space_table.cellClicked.connect(self._on_space_selected)
        self.space_table.horizontalHeader().setStretchLastSection(True)

        wrapper = QGroupBox('Available Chat Spaces')
        layout = QVBoxLayout(wrapper)
        layout.addWidget(self.space_table)
        wrapper.setLayout(layout)
        return wrapper

    def _build_space_detail_panel(self) -> QWidget:
        details_group = QGroupBox('Space Details')
        layout = QVBoxLayout(details_group)

        self.selected_space_label = QLabel('Select a chat space to see details.')

        email_form = QFormLayout()
        self.member_email_input = QLineEdit()
        self.member_email_input.setPlaceholderText('user@example.com')
        self.add_member_button = QPushButton('Add Member to Space')
        self.add_member_button.clicked.connect(self._add_member)
        self.add_member_button.setEnabled(False)

        self.remove_members_button = QPushButton('Remove All Non-Manager Members')
        self.remove_members_button.clicked.connect(self._remove_members)
        self.remove_members_button.setEnabled(False)

        self.refresh_members_button = QPushButton('Refresh Members')
        self.refresh_members_button.clicked.connect(self._load_space_members)
        self.refresh_members_button.setEnabled(False)

        email_form.addRow('Member email:', self.member_email_input)
        email_form.addRow('', self.add_member_button)

        layout.addWidget(self.selected_space_label)
        layout.addLayout(email_form)
        layout.addWidget(self.refresh_members_button)
        layout.addWidget(self.remove_members_button)
        layout.addWidget(self._build_members_table())
        details_group.setLayout(layout)
        return details_group

    def _build_members_table(self) -> QWidget:
        self.members_table = QTableWidget(0, 3)
        self.members_table.setHorizontalHeaderLabels(['Display Name', 'Role', 'Member ID'])
        self.members_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.members_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.members_table.horizontalHeader().setStretchLastSection(True)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.addWidget(self.members_table)
        return wrapper

    def _build_log_panel(self) -> QWidget:
        log_group = QGroupBox('Activity Log')
        layout = QVBoxLayout(log_group)
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumBlockCount(1200)
        layout.addWidget(self.log_console)
        return log_group

    def _choose_credentials_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Select Google credentials file', os.getcwd(), 'JSON Files (*.json)')
        if path:
            self.credentials_input.setText(path)

    def _choose_token_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Select Google token file', os.getcwd(), 'JSON Files (*.json)')
        if path:
            self.token_input.setText(path)

    def _authenticate(self) -> None:
        credentials_path = self.credentials_input.text().strip() or DEFAULT_CREDENTIALS_FILE
        token_path = self.token_input.text().strip() or DEFAULT_TOKEN_FILE

        if not os.path.isfile(credentials_path):
            QMessageBox.critical(self, 'Missing Credentials', f'Cannot find credentials file: {credentials_path}')
            return

        try:
            self.creds = self._load_credentials(credentials_path, token_path)
            self.chat_service = build('chat', 'v1', credentials=self.creds)
            self._update_auth_ui(True)
            self._append_log('✅ Authentication completed successfully.')
            self._load_spaces()
        except Exception as exc:
            self._update_auth_ui(False)
            self._append_log(f'❌ Authentication failed: {exc}')
            QMessageBox.critical(self, 'Authentication Failed', str(exc))

    def _load_credentials(self, credentials_path: str, token_path: str) -> Credentials:
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w', encoding='utf-8') as token_file:
                token_file.write(creds.to_json())

        return creds

    def _update_auth_ui(self, authenticated: bool) -> None:
        self.auth_status.setText('Authenticated' if authenticated else 'Not authenticated')
        self.auth_status.setStyleSheet('color: #1b5e20; font-weight: bold;' if authenticated else 'color: #b71c1c; font-weight: bold;')
        self.refresh_button.setEnabled(authenticated)
        self.create_space_button.setEnabled(authenticated)
        self.add_member_button.setEnabled(authenticated and bool(self._get_selected_space_id()))
        self.refresh_members_button.setEnabled(authenticated and bool(self._get_selected_space_id()))
        self.remove_members_button.setEnabled(authenticated and bool(self._get_selected_space_id()))

    def _load_spaces(self) -> None:
        if not self.chat_service:
            return

        try:
            spaces = manage_chats.list_spaces(self.chat_service) or []
            self.chat_spaces = spaces
            self._populate_spaces_table(spaces)
            self._append_log(f'✅ Loaded {len(spaces)} chat spaces.')
        except Exception as exc:
            self._append_log(f'❌ Failed to load spaces: {exc}')
            QMessageBox.critical(self, 'Load Failure', str(exc))

    def _populate_spaces_table(self, spaces: List[dict]) -> None:
        self.space_table.setRowCount(0)
        self.space_table.setRowCount(len(spaces))
        for row_index, space in enumerate(spaces):
            display_name = space.get('displayName', '')
            space_id = space.get('name', '')
            space_type = space.get('spaceType', '')
            members = str(space.get('memberCount', '')) if space.get('memberCount') is not None else ''

            self.space_table.setItem(row_index, 0, QTableWidgetItem(display_name))
            self.space_table.setItem(row_index, 1, QTableWidgetItem(space_id))
            self.space_table.setItem(row_index, 2, QTableWidgetItem(space_type))
            self.space_table.setItem(row_index, 3, QTableWidgetItem(members))

        self.space_table.resizeColumnsToContents()

    def _on_space_selected(self, row: int, column: int) -> None:
        space_id = self.space_table.item(row, 1).text() if self.space_table.item(row, 1) else ''
        display_name = self.space_table.item(row, 0).text() if self.space_table.item(row, 0) else ''
        if space_id:
            self.selected_space_label.setText(f'<b>Selected Space:</b> {display_name}\n{space_id}')
            self._update_auth_ui(bool(self.creds))
            self._load_space_members()

    def _get_selected_space_id(self) -> str:
        selected_items = self.space_table.selectedItems()
        if not selected_items:
            return ''
        # Space ID is in the second column of the selected row
        return selected_items[1].text()

    def _create_space(self) -> None:
        title = self.new_space_name.text().strip()
        if not title:
            QMessageBox.warning(self, 'Missing Title', 'Please enter a chat space title.')
            return

        try:
            space_name = manage_chats.create_google_chat_space(self.chat_service, title)
            self._append_log(f'✅ Created space: {title} ({space_name})')
            self.new_space_name.clear()
            self._load_spaces()
            QMessageBox.information(self, 'Space Created', f'Google Chat space "{title}" has been created.')
        except Exception as exc:
            self._append_log(f'❌ Failed to create space: {exc}')
            QMessageBox.critical(self, 'Create Space Failed', str(exc))

    def _load_space_members(self) -> None:
        space_id = self._get_selected_space_id()
        if not space_id:
            return

        try:
            response = self.chat_service.spaces().members().list(parent=space_id).execute()
            memberships = response.get('memberships', [])
            self._populate_members_table(memberships)
            self._append_log(f'✅ Loaded {len(memberships)} members for {space_id}.')
        except Exception as exc:
            self._append_log(f'❌ Failed to load members: {exc}')
            QMessageBox.critical(self, 'Load Members Failed', str(exc))

    def _populate_members_table(self, memberships: List[dict]) -> None:
        self.members_table.setRowCount(0)
        self.members_table.setRowCount(len(memberships))
        for row_index, membership in enumerate(memberships):
            member = membership.get('member', {})
            display_name = member.get('displayName', member.get('name', ''))
            role = membership.get('role', '')
            member_id = member.get('name', '')

            self.members_table.setItem(row_index, 0, QTableWidgetItem(display_name))
            self.members_table.setItem(row_index, 1, QTableWidgetItem(role))
            self.members_table.setItem(row_index, 2, QTableWidgetItem(member_id))

        self.members_table.resizeColumnsToContents()

    def _add_member(self) -> None:
        space_id = self._get_selected_space_id()
        email = self.member_email_input.text().strip()

        if not space_id:
            QMessageBox.warning(self, 'No Space Selected', 'Please select a chat space first.')
            return
        if not email:
            QMessageBox.warning(self, 'Missing Email', 'Please enter the member email address.')
            return

        try:
            member_name = manage_chats.add_user_to_space(self.chat_service, space_id, email)
            self._append_log(f'✅ Added {email} to {space_id}: {member_name}')
            self.member_email_input.clear()
            self._load_space_members()
            QMessageBox.information(self, 'Member Added', f'{email} has been added to the selected chat space.')
        except Exception as exc:
            self._append_log(f'❌ Failed to add member: {exc}')
            QMessageBox.critical(self, 'Add Member Failed', str(exc))

    def _remove_members(self) -> None:
        space_id = self._get_selected_space_id()
        if not space_id:
            QMessageBox.warning(self, 'No Space Selected', 'Please select a chat space first.')
            return

        result = QMessageBox.question(
            self,
            'Confirm Removal',
            'Remove all non-manager members from this space? This action cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        try:
            manage_chats.remove_all_members(self.chat_service, space_id)
            self._append_log(f'✅ Removed non-manager members from {space_id}.')
            self._load_space_members()
            QMessageBox.information(self, 'Members Removed', 'Members have been removed from the selected chat space.')
        except Exception as exc:
            self._append_log(f'❌ Failed to remove members: {exc}')
            QMessageBox.critical(self, 'Remove Members Failed', str(exc))

    def _append_log(self, message: str) -> None:
        self.log_console.appendPlainText(message)


def main() -> None:
    app = QApplication(sys.argv)
    window = ChatManagerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
