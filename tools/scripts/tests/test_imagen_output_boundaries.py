import base64
import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("aas_imagen", ROOT / "skills/imagen/scripts/generate_image.py")
imagen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(imagen)


class ImagenBoundaries(unittest.TestCase):
    def test_model_input_cannot_change_endpoint_or_inject_headers(self):
        for value in (None, "../model", "model?key=secret", "model\nheader"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                imagen.get_api_endpoint(value)

    def test_image_can_follow_text_only_candidate(self):
        data = base64.b64encode(b"\x89PNG\r\n\x1a\nsynthetic").decode()
        response = [{"candidates": []}, {"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "image/png", "data": data}}
        ]}}]}]
        self.assertEqual(imagen.extract_image_data(response), data)
        with self.assertRaises(ValueError):
            imagen.extract_image_data({"candidates": [{"content": None}]})
        with self.assertRaises(ValueError):
            imagen.extract_image_data({})

    def test_private_output_preserves_existing_file_and_symlink_target(self):
        data = base64.b64encode(b"\x89PNG\r\n\x1a\nsynthetic").decode()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "image.png"
            imagen.save_image(data, output)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                imagen.save_image(data, output)
            link = Path(directory) / "link.png"
            link.symlink_to(output)
            with self.assertRaises(FileExistsError):
                imagen.save_image(data, link)
            self.assertEqual(output.read_bytes(), before)
            with self.assertRaises(ValueError):
                imagen.save_image(base64.b64encode(b"not an image").decode(), Path(directory) / "bad.png")

    def test_transport_uses_private_header_and_refuses_redirects(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                self.limit = limit
                return b'{"candidates": []}'

        class Opener:
            def open(self, request, timeout):
                self.request = request
                self.timeout = timeout
                return Response()

        opener = Opener()
        with patch.object(imagen.urllib.request, "build_opener", return_value=opener) as build:
            imagen.make_api_request("synthetic-private-key", "fixture-model", imagen.build_request_body("fixture", "2K"))
        self.assertNotIn("synthetic-private-key", opener.request.full_url)
        self.assertEqual(opener.request.get_header("X-goog-api-key"), "synthetic-private-key")
        self.assertIsNone(build.call_args.args[0].redirect_request(None, None, 302, None, None, "https://example.invalid"))
        payload = json.loads(opener.request.data)
        self.assertEqual(payload["generationConfig"]["imageConfig"]["imageSize"], "2K")


if __name__ == "__main__":
    unittest.main()
