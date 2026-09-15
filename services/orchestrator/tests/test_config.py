import unittest

from pydantic import ValidationError

from app.config import Settings


class SettingsBoundsTests(unittest.TestCase):
    def test_defaults_remain_valid(self) -> None:
        settings = Settings(_env_file=None)
        self.assertEqual(settings.port, 8012)
        self.assertEqual(settings.autonomous_max_subagents, 5)
        self.assertEqual(settings.autonomous_read_parallelism, 2)

    def test_rejects_out_of_range_runtime_values(self) -> None:
        invalid = {
            "port": 70000,
            "request_timeout_seconds": 0,
            "autonomous_interval_minutes": 1441,
            "autonomous_cycles_per_run": 101,
            "autonomous_max_subagents": 17,
            "autonomous_read_parallelism": 0,
            "autonomous_task_timeout_seconds": 3601,
            "autonomous_model_timeout_seconds": 1801,
            "autonomous_workspace": "",
            "autonomous_git_remote": "x" * 1001,
        }
        for field, value in invalid.items():
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    Settings(_env_file=None, **{field: value})


if __name__ == "__main__":
    unittest.main()