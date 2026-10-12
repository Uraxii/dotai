import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "generate_plugin_manifests", Path(__file__).with_name("generate-plugin-manifests.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BannedModelTest(unittest.TestCase):
    def test_astra_models_match(self) -> None:
        for text in ("gpt-6-astra", "GPT-6-Astra", "openai/gpt-6.1-astra", "use astra here"):
            self.assertTrue(module.BANNED_MODEL.search(text), text)

    def test_lookalikes_do_not_match(self) -> None:
        for text in ("astral", "pilastra", "lastRange", "fastRandom", "astranger", "Astra DB"):
            self.assertIsNone(module.BANNED_MODEL.search(text), text)


if __name__ == "__main__":
    unittest.main()
