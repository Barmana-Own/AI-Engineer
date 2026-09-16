import unittest

from app.services.terminal import _command_environment


class CommandEnvironmentTests(unittest.TestCase):
    def test_strips_control_plane_variables(self):
        base = {
            "APP_NAME": "AI Engineer Local Agent",
            "PORT": "8011",
            "HOST": "127.0.0.1",
            "AUTONOMOUS_MODE_ENABLED": "true",
            "MODEL_GATEWAY_URL": "http://127.0.0.1:8010",
            "BARMANA_API_KEY": "service-only",
            "PATH": "toolchain",
            "PROJECT_FLAG": "preserve",
        }

        environment = _command_environment(base)

        for key in (
            "PORT",
            "HOST",
            "AUTONOMOUS_MODE_ENABLED",
            "MODEL_GATEWAY_URL",
            "BARMANA_API_KEY",
        ):
            self.assertNotIn(key, environment)
        self.assertEqual(environment["PATH"], "toolchain")
        self.assertEqual(environment["PROJECT_FLAG"], "preserve")

    def test_sets_stable_encoding_and_loopback_proxy(self):
        environment = _command_environment({"NO_PROXY": "external", "no_proxy": "external"})

        self.assertEqual(environment["PYTHONUTF8"], "1")
        self.assertEqual(environment["NO_PROXY"], "localhost,127.0.0.1,::1")
        self.assertEqual(environment["no_proxy"], "localhost,127.0.0.1,::1")


if __name__ == "__main__":
    unittest.main()
