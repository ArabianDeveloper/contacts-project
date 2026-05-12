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

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/contacts',
]

DEFAULT_SPREADSHEET_ID = '1gXMz0Kj_t1FaoMyt2ygGjl9VTVfHuOHDzycycECefhQ'
DEFAULT_RANGE = 'Sheet1!A:G'
DEFAULT_CREDENTIALS_FILE = 'credentials.json'
DEFAULT_TOKEN_FILE = 'token.json'


class ContactManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Google Contacts Manager')
        self.setMinimumSize(1180, 760)

        self.creds: Optional[Credentials] = None
        self.sheets_service = None
        self.people_service = None
        self.sheet_data: List[List[str]] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        container = QWidget()
        main_layout = QVBoxLayout(container)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_import_tab(), 'Import Contacts')
        self.tabs.addTab(self._build_label_tab(), 'Labels & Groups')
        self.tabs.addTab(self._build_auth_tab(), 'Authentication')

        main_layout.addWidget(self.tabs)
        main_layout.addWidget(self._build_log_panel())

        self.setCentralWidget(container)

    def _build_import_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        sheet_group = QGroupBox('Google Sheet Source')
        sheet_form = QFormLayout()

        self.spreadsheet_input = QLineEdit(DEFAULT_SPREADSHEET_ID)
        self.range_input = QLineEdit(DEFAULT_RANGE)

        browse_sheet_button = QPushButton('Open Example Sheet')
        browse_sheet_button.clicked.connect(self._open_spreadsheet_link)

        sheet_form.addRow('Spreadsheet ID:', self.spreadsheet_input)
        sheet_form.addRow('Range:', self.range_input)
        sheet_form.addRow('', browse_sheet_button)

        load_button = QPushButton('Load Preview')
        load_button.clicked.connect(self._load_sheet_preview)
        load_button.setDefault(True)

        self.import_button = QPushButton('Import All Contacts')
        self.import_button.clicked.connect(self._import_contacts)
        self.import_button.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(load_button)
        button_layout.addWidget(self.import_button)
        button_layout.addStretch()

        sheet_form.addRow('', button_layout)
        sheet_group.setLayout(sheet_form)

        self.preview_table = QTableWidget(0, 7)
        self.preview_table.setHorizontalHeaderLabels([
            'First Name', 'Middle Name', 'Last Name', 'Family Name', 'Phone', 'Email', 'Labels'
        ])
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(sheet_group)
        layout.addWidget(self.preview_table)
        return widget

    def _build_label_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label_group = QGroupBox('Contact Labels & Groups')
        label_layout = QVBoxLayout(label_group)

        top_layout = QHBoxLayout()
        self.label_name_input = QLineEdit()
        self.label_name_input.setPlaceholderText('Label name to create')
        self.create_label_button = QPushButton('Create Label')
        self.create_label_button.clicked.connect(self._create_label)
        self.create_label_button.setEnabled(False)
        self.refresh_labels_button = QPushButton('Refresh Labels')
        self.refresh_labels_button.clicked.connect(self._load_contact_groups)
        self.refresh_labels_button.setEnabled(False)

        top_layout.addWidget(QLabel('New label:'))
        top_layout.addWidget(self.label_name_input)
        top_layout.addWidget(self.create_label_button)
        top_layout.addWidget(self.refresh_labels_button)
        top_layout.addStretch()

        self.labels_table = QTableWidget(0, 3)
        self.labels_table.setHorizontalHeaderLabels(['Label Name', 'Group ID', 'Member Count'])
        self.labels_table.horizontalHeader().setStretchLastSection(True)
        self.labels_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.labels_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        label_layout.addLayout(top_layout)
        label_layout.addWidget(self.labels_table)
        layout.addWidget(label_group)
        return widget

    def _build_auth_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        auth_group = QGroupBox('Google API Authentication')
        auth_form = QFormLayout()

        self.credentials_input = QLineEdit(DEFAULT_CREDENTIALS_FILE)
        self.credentials_input.setPlaceholderText('Path to credentials.json')
        browse_credentials_button = QPushButton('Choose Credentials')
        browse_credentials_button.clicked.connect(self._choose_credentials_file)

        creds_layout = QHBoxLayout()
        creds_layout.addWidget(self.credentials_input)
        creds_layout.addWidget(browse_credentials_button)

        self.token_input = QLineEdit(DEFAULT_TOKEN_FILE)
        self.token_input.setPlaceholderText('Path to token.json')

        self.auth_status_label = QLabel('Not authenticated')
        self.auth_status_label.setProperty('status', 'error')
        self._set_status_style(self.auth_status_label)

        auth_button = QPushButton('Authenticate')
        auth_button.clicked.connect(self._authenticate)

        auth_form.addRow('Credentials file:', creds_layout)
        auth_form.addRow('Token file:', self.token_input)
        auth_form.addRow('Status:', self.auth_status_label)
        auth_form.addRow('', auth_button)
        auth_group.setLayout(auth_form)

        layout.addWidget(auth_group)
        layout.addStretch()
        return widget

    def _build_log_panel(self) -> QWidget:
        log_group = QGroupBox('Activity Log')
        log_layout = QVBoxLayout(log_group)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumBlockCount(1200)

        clear_button = QPushButton('Clear Log')
        clear_button.clicked.connect(self.log_console.clear)

        log_layout.addWidget(self.log_console)
        log_layout.addWidget(clear_button, alignment=Qt.AlignmentFlag.AlignRight)
        return log_group

    def _choose_credentials_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Select credentials.json file', os.getcwd(), 'JSON Files (*.json)')
        if path:
            self.credentials_input.setText(path)

    def _authenticate(self) -> None:
        credentials_path = self.credentials_input.text().strip() or DEFAULT_CREDENTIALS_FILE
        token_path = self.token_input.text().strip() or DEFAULT_TOKEN_FILE

        if not os.path.isfile(credentials_path):
            QMessageBox.critical(self, 'Missing File', f'Credentials file not found: {credentials_path}')
            return

        try:
            self.creds = self._load_credentials(credentials_path, token_path)
            self.people_service = build('people', 'v1', credentials=self.creds)
            self._update_authenticated_state(True)
            self._append_log('✅ Authenticated successfully.')
            self._load_contact_groups()
        except Exception as exc:
            self._update_authenticated_state(False)
            QMessageBox.critical(self, 'Authentication Error', str(exc))
            self._append_log(f'❌ Authentication failed: {exc}')

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

    def _update_authenticated_state(self, ok: bool) -> None:
        label = 'Authenticated' if ok else 'Not authenticated'
        self.auth_status_label.setText(label)
        self.auth_status_label.setProperty('status', 'ok' if ok else 'error')
        self._set_status_style(self.auth_status_label)
        self.import_button.setEnabled(ok)
        self.refresh_labels_button.setEnabled(ok)
        self.create_label_button.setEnabled(ok)

    def _set_status_style(self, label: QLabel) -> None:
        status = label.property('status')
        if status == 'ok':
            label.setStyleSheet('color: #1b5e20; font-weight: bold;')
        else:
            label.setStyleSheet('color: #b71c1c; font-weight: bold;')

    def _open_spreadsheet_link(self) -> None:
        url = f'https://docs.google.com/spreadsheets/d/{self.spreadsheet_input.text().strip() or DEFAULT_SPREADSHEET_ID}'
        QMessageBox.information(self, 'Sheet Link', f'Open this URL in your browser:\n{url}')

    def _load_sheet_preview(self) -> None:
        if not self.people_service:
            QMessageBox.warning(self, 'Authentication Required', 'Please authenticate before loading sheet data.')
            return

        spreadsheet_id = self.spreadsheet_input.text().strip() or DEFAULT_SPREADSHEET_ID
        range_name = self.range_input.text().strip() or DEFAULT_RANGE

        try:
            self.sheet_data = read_google_sheet(build('sheets', 'v4', credentials=self.creds), spreadsheet_id, range_name)
            self._populate_preview_table(self.sheet_data)
            self._append_log(f'✅ Loaded {len(self.sheet_data)} rows from Google Sheet.')
            self.import_button.setEnabled(bool(self.sheet_data))
        except Exception as exc:
            QMessageBox.critical(self, 'Load Error', str(exc))
            self._append_log(f'❌ Failed to load sheet data: {exc}')

    def _populate_preview_table(self, rows: List[List[str]]) -> None:
        self.preview_table.setRowCount(0)
        self.preview_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for col_index in range(7):
                value = row[col_index] if col_index < len(row) else ''
                self.preview_table.setItem(row_index, col_index, QTableWidgetItem(value))

        self.preview_table.resizeColumnsToContents()

    def _import_contacts(self) -> None:
        if not self.sheet_data:
            QMessageBox.warning(self, 'No Data', 'Load sheet preview before importing.')
            return

        if not self.people_service:
            QMessageBox.warning(self, 'Authentication Required', 'Please authenticate first.')
            return

        success_count = 0
        failure_count = 0

        for row in self.sheet_data:
            if len(row) < 4:
                self._append_log(f'⚠️ Skipping incomplete row: {row}')
                failure_count += 1
                continue

            given_name = ' '.join(item.strip() for item in row[:3] if item.strip())
            family_name = row[3].strip()
            phone = row[4].strip() if len(row) > 4 else None
            email = row[5].strip() if len(row) > 5 else None
            labels = [label.strip() for label in row[6].split(',')] if len(row) > 6 and row[6].strip() else []

            try:
                contact_id = add_contact(self.people_service, first_name=given_name, last_name=family_name, phone=phone, email=email)
                for label in labels:
                    if label:
                        group_id = get_or_create_label(self.people_service, label)
                        add_contact_to_label(self.people_service, contact_id, group_id)

                self._append_log(f'✅ Added contact: {given_name} {family_name} ({email or "no email"})')
                success_count += 1
            except Exception as exc:
                self._append_log(f'❌ Failed to add {given_name} {family_name}: {exc}')
                failure_count += 1

        QMessageBox.information(self, 'Import Completed', f'Imported {success_count} contacts, {failure_count} failures.')
        self._append_log(f'Import complete. Success: {success_count}, Failed: {failure_count}')
        self._load_contact_groups()

    def _load_contact_groups(self) -> None:
        if not self.people_service:
            return

        try:
            response = self.people_service.contactGroups().list(pageSize=200).execute()
            groups = response.get('contactGroups', [])
            self._populate_labels_table(groups)
            self._append_log(f'✅ Loaded {len(groups)} contact label groups.')
        except Exception as exc:
            self._append_log(f'❌ Could not refresh labels: {exc}')

    def _populate_labels_table(self, groups: List[dict]) -> None:
        self.labels_table.setRowCount(0)
        self.labels_table.setRowCount(len(groups))

        for row_index, group in enumerate(groups):
            self.labels_table.setItem(row_index, 0, QTableWidgetItem(group.get('name', '')))
            self.labels_table.setItem(row_index, 1, QTableWidgetItem(group.get('resourceName', '')))
            self.labels_table.setItem(row_index, 2, QTableWidgetItem(str(group.get('memberCount', 0))))

        self.labels_table.resizeColumnsToContents()

    def _create_label(self) -> None:
        if not self.people_service:
            QMessageBox.warning(self, 'Authenticate first', 'Please authenticate before creating labels.')
            return

        label_name = self.label_name_input.text().strip()
        if not label_name:
            QMessageBox.warning(self, 'Missing Label Name', 'Enter a label name before creating.')
            return

        try:
            group_body = {'contactGroup': {'name': label_name}}
            self.people_service.contactGroups().create(body=group_body).execute()
            self._append_log(f'✅ Created label: {label_name}')
            self.label_name_input.clear()
            self._load_contact_groups()
            QMessageBox.information(self, 'Label Created', f'Label {label_name} has been created successfully.')
        except Exception as exc:
            QMessageBox.critical(self, 'Create Label Failed', str(exc))
            self._append_log(f'❌ Failed to create label {label_name}: {exc}')

    def _append_log(self, message: str) -> None:
        self.log_console.appendPlainText(message)


def main() -> None:
    app = QApplication(sys.argv)
    window = ContactManagerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
