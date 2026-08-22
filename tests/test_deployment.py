from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.config import Config
from tools.prepare_vercel_public import prepare_public_assets


class DeploymentTests(unittest.TestCase):
    def test_vercel_config_selects_flask_framework(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        config = json.loads((repo_root / "vercel.json").read_text(encoding="utf-8"))

        self.assertEqual(config["framework"], "flask")
        self.assertEqual(config["buildCommand"], "python tools/prepare_vercel_public.py")

    def test_database_path_environment_variable_is_used_at_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "runtime" / "realtags.sqlite3"
            config = type(
                "DeploymentConfig",
                (Config,),
                {"TESTING": True, "SECRET_KEY": "test", "DEMO_MODE": True},
            )

            with patch.dict(os.environ, {"DATABASE_PATH": str(database)}):
                app = create_app(config)

            self.assertEqual(app.config["DATABASE"], str(database))
            self.assertTrue(database.is_file())

    def test_explicit_database_config_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "explicit.sqlite3"
            config = type(
                "ExplicitDatabaseConfig",
                (Config,),
                {
                    "TESTING": True,
                    "DATABASE": str(database),
                    "SECRET_KEY": "test",
                    "DEMO_MODE": True,
                },
            )

            with patch.dict(os.environ, {"DATABASE_PATH": str(Path(temp_dir) / "ignored.sqlite3")}):
                app = create_app(config)

            self.assertEqual(app.config["DATABASE"], str(database))

    def test_public_asset_build_excludes_qa_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            for directory_name in ("css", "img", "js", "qa"):
                directory = repo_root / "app" / "static" / directory_name
                directory.mkdir(parents=True)
                (directory / "asset.txt").write_text(directory_name, encoding="utf-8")

            target = prepare_public_assets(repo_root)

            self.assertEqual(
                sorted(path.name for path in target.iterdir()),
                ["css", "img", "js"],
            )
            self.assertFalse((target / "qa").exists())


if __name__ == "__main__":
    unittest.main()
