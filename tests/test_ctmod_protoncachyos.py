from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

from pupgui2.resources.ctmods.ctmod_protoncachyos import CtInstaller


class DummyMainWindow:
    def __init__(self, web_access_tokens: dict[str, str]) -> None:
        self.web_access_tokens = web_access_tokens


def test_fetch_releases_skips_unexpected_asset_formats(monkeypatch) -> None:
    existing_app = QApplication.instance()
    app = existing_app or QApplication([])

    try:
        installer = CtInstaller(main_window=DummyMainWindow({}))
        monkeypatch.setattr(installer, 'get_hwcaps', lambda: {'x86_64', 'x86_64_v3'})

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'tag_name': 'cachyos-11.0-20261125-nightly',
                'assets': [
                    {'name': 'proton-cachyos-11.0-20261125-base-247-gf18434dc-x86_64.tar.xz'},
                    {'name': 'proton-cachyos-11.0-20261125-base-247-gf18434dc-x86_64-llvm.tar.xz'},
                    {'name': 'proton-cachyos-11.0-20261125-base-247-gf18434dc-x86_64_v3.tar.xz'},
                    {'name': 'proton-cachyos-11.0-20261125-base-247-gf18434dc-arm64.tar.xz'},
                ],
            },
            {
                'tag_name': 'cachyos-11.0-20261015-slr',
                'assets': [
                    {'name': 'proton-cachyos-11.0-20261015-slr-x86_64.tar.xz'},
                    {'name': 'proton-cachyos-11.0-20261015-slr-x86_64_v3.tar.xz'},
                    {'name': 'proton-cachyos-11.0-20261015-slr-arm64.tar.xz'},
                    {'name': 'proton-cachyos-11.0-20261015-slr-x86_64.sha512sum'},
                ],
            },
        ]
        monkeypatch.setattr(installer.rs, 'get', lambda url: mock_response)

        releases = installer.fetch_releases()

        assert releases == ['11.0-20261015-x86_64', '11.0-20261015-x86_64_v3']
    finally:
        if existing_app is None:
            QApplication.shutdown(app)
