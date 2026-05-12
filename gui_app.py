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
    QTabWidget,
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

from manage_people import add_contact, add_contact_to_label, get_or_create_label, read_google_sheet
from manage_chats import add_user_to_space, create_google_chat_space, list_spaces

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/chat.spaces.readonly',
    'https://www.googleapis.com/auth/chat.spaces.create',
    'https://www.googleapis.com/auth/chat.memberships',
]

DEFAULT_SPREADSHEET_ID = '1gXMz0Kj_t1FaoMyt2ygGjl9VTVfHuOHDzycycECefhQ'
DEFAULT_RANGE = 'Sheet1!A:G'
DEFAULT_CREDENTIALS_FILE = 'credentials.json'
DEFAULT_TOKEN_FILE = 'token.json'


class ContactsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Contacts & Google Chat Manager')
        self.setMinimumSize(1000, 700)

        self.creds: Optional[Credentials] = None
        self.sheets_service = None
        self.people_service = None
        self.chat_service = None
        self.sheet_data: List[List[str]] = []

        self._build_ui()

    def _build_ui(self):
        container = QWidget()
        container_layout = QVBoxLayout(container)

        tabs = QTabWidget()
        tabs.addTab(self._build_auth_tab(), 'Authentication')
        tabs.addTab(self._build_sheet_tab(), 'Google Sheet')
        tabs.addTab(self._build_chat_tab(), 'Google Chat')

        container_layout.addWidget(tabs)
        container_layout.addWidget(self._build_log_widget())

        self.setCentralWidget(container)

    def _build_auth_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        auth_group = QGroupBox('Google API authentication')
        form = QFormLayout()

        self.credentials_input = QLineEdit(DEFAULT_CREDENTIALS_FILE)
        self.credentials_input.setPlaceholderText('Path to credentials.json')
        browse_button = QPushButton('Browse...')
        browse_button.clicked.connect(self._browse_credentials)

        cred_layout = QHBoxLayout()
        cred_layout.addWidget(self.credentials_input)
        cred_layout.addWidget(browse_button)
        form.addRow('Credentials file:', cred_layout)

        self.token_input = QLineEdit(DEFAULT_TOKEN_FILE)
        self.token_input.setPlaceholderText('Path to token.json')
        form.addRow('Token file:', self.token_input)

        self.auth_status_label = QLabel('Not authenticated')
        self.auth_status_label.setStyleSheet('color: red;')
        form.addRow('Status:', self.auth_status_label)

        self.authenticate_button = QPushButton('Authenticate')
        self.authenticate_button.clicked.connect(self._authenticate)
        form.addRow('', self.authenticate_button)

        auth_group.setLayout(form)
        layout.addWidget(auth_group)
        layout.addStretch()
        return widget

    def _build_sheet_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        sheet_group = QGroupBox('Sheet settings')
        form = QFormLayout()

        self.spreadsheet_input = QLineEdit(DEFAULT_SPREADSHEET_ID)
        self.range_input = QLineEdit(DEFAULT_RANGE)
        form.addRow('Spreadsheet ID:', self.spreadsheet_input)
        form.addRow('Range:', self.range_input)

        load_button = QPushButton('Load Sheet Preview')
        load_button.clicked.connect(self._load_sheet)
        self.import_button = QPushButton('Import Contacts')
        self.import_button.clicked.connect(self._import_contacts)
        self.import_button.setEnabled(False)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(load_button)
        buttons_layout.addWidget(self.import_button)
        form.addRow('', buttons_layout)

        sheet_group.setLayout(form)
        layout.addWidget(sheet_group)

        self.sheet_table = QTableWidget()
        self.sheet_table.setColumnCount(7)
        self.sheet_table.setHorizontalHeaderLabels(
            ['First Name', 'Middle Name', 'Last Name', 'Family Name', 'Phone', 'Email', 'Labels']
        )
        layout.addWidget(self.sheet_table)
        return widget

    def _build_chat_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        chat_group = QGroupBox('Google Chat space sync')
        chat_layout = QVBoxLayout(chat_group)

        self.list_spaces_button = QPushButton('List Spaces')
        self.list_spaces_button.clicked.connect(self._list_chat_spaces)
        self.list_spaces_button.setEnabled(False)

        self.sync_spaces_button = QPushButton('Sync Users to Spaces')
        self.sync_spaces_button.clicked.connect(self._sync_chat_spaces)
        self.sync_spaces_button.setEnabled(False)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.list_spaces_button)
        buttons_layout.addWidget(self.sync_spaces_button)
        chat_layout.addLayout(buttons_layout)

        self.chat_table = QTableWidget()
        self.chat_table.setColumnCount(3)
        self.chat_table.setHorizontalHeaderLabels(['Display name', 'Space ID', 'Space Type'])
        chat_layout.addWidget(self.chat_table)

        chat_group.setLayout(chat_layout)
        layout.addWidget(chat_group)
        layout.addStretch()
        return widget

    def _build_log_widget(self) -> QWidget:
        log_group = QGroupBox('Activity log')
        log_layout = QVBoxLayout(log_group)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumBlockCount(1000)

        log_layout.addWidget(self.log_console)
        return log_group

    def _browse_credentials(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, 'Select Google credentials file', os.getcwd(), 'JSON Files (*.json)')
        if selected:
            self.credentials_input.setText(selected)

    def _authenticate(self) -> None:
        credentials_file = self.credentials_input.text().strip() or DEFAULT_CREDENTIALS_FILE
        token_file = self.token_input.text().strip() or DEFAULT_TOKEN_FILE

        if not os.path.exists(credentials_file):
            QMessageBox.critical(self, 'Missing credentials', f'Cannot find credentials file: {credentials_file}')
            return

        try:
            self.creds = self._get_credentials(credentials_file, token_file)
            if self.creds and self.creds.valid:
                self._build_google_services()
                self.auth_status_label.setText('Authenticated successfully')
                self.auth_status_label.setStyleSheet('color: green;')
                self.import_button.setEnabled(True)
                self.list_spaces_button.setEnabled(True)
                self.sync_spaces_button.setEnabled(True)
                self._append_log('✅ Authentication succeeded.')
        except Exception as exc:
            QMessageBox.critical(self, 'Authentication failed', str(exc))
            self._append_log(f'❌ Authentication failed: {exc}')

    def _get_credentials(self, credentials_file: str, token_file: str) -> Credentials:
        creds = None
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_file, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())

        return creds

    def _build_google_services(self) -> None:
        if not self.creds:
            raise RuntimeError('Credentials are missing')

        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.people_service = build('people', 'v1', credentials=self.creds)
        self.chat_service = build('chat', 'v1', credentials=self.creds)

    def _load_sheet(self) -> None:
        if not self.creds:
            QMessageBox.warning(self, 'Not authenticated', 'Please authenticate before loading sheet data.')
            return

        spreadsheet_id = self.spreadsheet_input.text().strip() or DEFAULT_SPREADSHEET_ID
        range_name = self.range_input.text().strip() or DEFAULT_RANGE

        try:
            values = read_google_sheet(self.sheets_service, spreadsheet_id, range_name)
            self.sheet_data = values
            self._render_sheet_preview(values)
            self._append_log(f'✅ Loaded {len(values)} rows from Google Sheet.')
        except Exception as exc:
            QMessageBox.critical(self, 'Load failed', f'Unable to load sheet: {exc}')
            self._append_log(f'❌ Sheet load failed: {exc}')

    def _render_sheet_preview(self, values: List[List[str]]) -> None:
        self.sheet_table.setRowCount(0)
        self.sheet_table.setRowCount(len(values))

        for row_index, row in enumerate(values):
            for col_index in range(7):
                cell_value = row[col_index] if col_index < len(row) else ''
                item = QTableWidgetItem(cell_value)
                self.sheet_table.setItem(row_index, col_index, item)

        self.sheet_table.resizeColumnsToContents()

    def _import_contacts(self) -> None:
        if not self.sheet_data:
            QMessageBox.warning(self, 'No data', 'Load sheet data before importing contacts.')
            return

        if not self.people_service:
            QMessageBox.warning(self, 'No service', 'Google People service is not available.')
            return

        failures = 0
        processed = 0
        for row in self.sheet_data:
            if len(row) < 4:
                self._append_log('⚠️ Skipping row with insufficient fields: ' + str(row))
                failures += 1
                continue

            first_name = ' '.join([row[0].strip(), row[1].strip(), row[2].strip()]).strip()
            last_name = row[3].strip()
            phone = row[4].strip() if len(row) > 4 else None
            email = row[5].strip() if len(row) > 5 else None
            labels = row[6].split(',') if len(row) > 6 and row[6].strip() else []

            try:
                contact_id = add_contact(self.people_service, first_name=first_name, last_name=last_name, phone=phone, email=email)
                for label in labels:
                    label_name = label.strip()
                    if not label_name:
                        continue
                    group_id = get_or_create_label(self.people_service, label_name)
                    add_contact_to_label(self.people_service, contact_id, group_id)

                processed += 1
                self._append_log(f'✅ Imported contact: {first_name} {last_name} | email={email or "N/A"}')
            except Exception as exc:
                failures += 1
                self._append_log(f'❌ Failed to import contact {first_name} {last_name}: {exc}')

        self._append_log(f'Finished importing contacts. Success: {processed}, Failed: {failures}')
        QMessageBox.information(self, 'Import complete', f'Imported {processed} contacts with {failures} failures.')

    def _list_chat_spaces(self) -> None:
        if not self.chat_service:
            QMessageBox.warning(self, 'Not authenticated', 'Please authenticate before listing spaces.')
            return

        try:
            spaces = list_spaces(self.chat_service) or []
            self._render_spaces_table(spaces)
            self._append_log(f'✅ Retrieved {len(spaces)} Google Chat spaces.')
        except Exception as exc:
            QMessageBox.critical(self, 'List failed', f'Unable to list spaces: {exc}')
            self._append_log(f'❌ List spaces failed: {exc}')

    def _render_spaces_table(self, spaces: List[dict]) -> None:
        self.chat_table.setRowCount(0)
        self.chat_table.setRowCount(len(spaces))

        for row_index, space in enumerate(spaces):
            display_name = space.get('displayName', '')
            space_id = space.get('name', '')
            space_type = space.get('spaceType', '')

            self.chat_table.setItem(row_index, 0, QTableWidgetItem(display_name))
            self.chat_table.setItem(row_index, 1, QTableWidgetItem(space_id))
            self.chat_table.setItem(row_index, 2, QTableWidgetItem(space_type))

        self.chat_table.resizeColumnsToContents()

    def _sync_chat_spaces(self) -> None:
        if not self.sheet_data:
            QMessageBox.warning(self, 'No data', 'Load sheet data before syncing chat spaces.')
            return

        if not self.chat_service:
            QMessageBox.warning(self, 'No service', 'Google Chat service is not available.')
            return

        spaces = list_spaces(self.chat_service) or []
        existing_spaces = {space.get('displayName'): space.get('name') for space in spaces}

        created_count = 0
        added_count = 0
        skipped_count = 0

        for row in self.sheet_data:
            if len(row) < 6:
                self._append_log('⚠️ Skipping row with missing email or labels: ' + str(row))
                skipped_count += 1
                continue

            email = row[5].strip()
            if not email:
                self._append_log('⚠️ Skipping user without email: ' + str(row))
                skipped_count += 1
                continue

            labels = [label.strip() for label in row[6].split(',')] if len(row) > 6 and row[6].strip() else []
            if not labels:
                self._append_log(f'⚠️ No labels for {email}; skipping chat sync.')
                skipped_count += 1
                continue

            for label in labels:
                if not label:
                    continue

                if label not in existing_spaces:
                    try:
                        new_space_id = create_google_chat_space(self.chat_service, label)
                        existing_spaces[label] = new_space_id
                        created_count += 1
                        self._append_log(f'✅ Created chat space for label: {label}')
                    except Exception as exc:
                        self._append_log(f'❌ Failed to create space {label}: {exc}')
                        continue

                space_id = existing_spaces[label]
                try:
                    add_user_to_space(self.chat_service, space_id, email)
                    added_count += 1
                    self._append_log(f'✅ Added {email} to space {label}')
                except Exception as exc:
                    self._append_log(f'❌ Failed to add {email} to {label}: {exc}')

        self._append_log(f'Finished chat sync. Spaces created: {created_count}, members added: {added_count}, skipped: {skipped_count}')
        QMessageBox.information(self, 'Chat sync complete', f'Created {created_count} spaces and added {added_count} members.')
        self._list_chat_spaces()

    def _append_log(self, text: str) -> None:
        self.log_console.appendPlainText(text)


def main() -> None:
    app = QApplication(sys.argv)
    window = ContactsApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
