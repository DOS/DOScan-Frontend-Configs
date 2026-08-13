import base64
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from validate_assets import validate_png, validate_svg


VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class TokenIconValidationTest(unittest.TestCase):
    def write(self, name: str, content: str | bytes) -> Path:
        path = Path(self.directory.name) / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_accepts_internal_svg_fragment(self) -> None:
        path = self.write(
            "valid.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"/></defs><path fill="url(#g)"/></svg>',
        )
        validate_svg(path)

    def test_rejects_external_css_import(self) -> None:
        path = self.write(
            "external.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url("https://example.com/a.css");</style></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_external_style_url(self) -> None:
        path = self.write(
            "external.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:url(https://example.com/a.svg)"/></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_css_escaped_url_function(self) -> None:
        path = self.write(
            "escaped-url.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:u\\72l(evil.svg)"/></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_css_escaped_external_url(self) -> None:
        path = self.write(
            "escaped-external.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:u\\72l(h\\74tps\\3a\\2f\\2f example.com/a.svg)"/></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_css_escaped_import(self) -> None:
        path = self.write(
            "escaped-import.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><style>@im\\70ort "evil.css"</style></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_css_escaped_fill_attribute(self) -> None:
        path = self.write(
            "escaped-fill.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><path fill="u\\72l(evil.svg)"/></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_css_escaped_filter_attribute(self) -> None:
        path = self.write(
            "escaped-filter.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><path filter="u\\72l(h\\74tps\\3a\\2f\\2f example.com/f.svg#x)"/></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_css_comment_obfuscated_url(self) -> None:
        path = self.write(
            "comment-url.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><path fill="u/**/rl(evil.svg)"/></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_css_escape_generated_comment(self) -> None:
        path = self.write(
            "escaped-comment.svg",
            '<svg xmlns="http://www.w3.org/2000/svg"><path fill="u\\2f\\2a x\\2a\\2f rl(evil.svg)"/></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_xml_stylesheet_processing_instruction(self) -> None:
        path = self.write(
            "processing-instruction.svg",
            '<?xml-stylesheet type="text/css" href="https://example.com/evil.css"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg"><path/></svg>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_rejects_event_handler(self) -> None:
        path = self.write(
            "event.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
        )
        with self.assertRaises(ValueError):
            validate_svg(path)

    def test_accepts_structurally_valid_png(self) -> None:
        validate_png(self.write("valid.png", VALID_PNG))

    def test_rejects_fake_png(self) -> None:
        with self.assertRaises(ValueError):
            validate_png(self.write("fake.png", b"not a png"))

    def test_wdos_icon_has_safe_area_for_circular_crop(self) -> None:
        icon_path = Path(__file__).parents[2] / "configs" / "token-icons" / "WDOS.svg"
        view_box = tuple(
            float(value)
            for value in ET.parse(icon_path).getroot().attrib["viewBox"].split()
        )
        view_x, view_y, view_width, view_height = view_box
        center_x = view_x + view_width / 2
        center_y = view_y + view_height / 2
        radius = min(view_width, view_height) / 2
        production_slot_size = 30
        minimum_clearance = view_width * 0.5 / production_slot_size
        artwork_bounds = (0.0, 0.0, 5808.6, 5808.6)
        artwork_x, artwork_y, artwork_width, artwork_height = artwork_bounds
        artwork_bounding_corners = (
            (artwork_x, artwork_y),
            (artwork_x + artwork_width, artwork_y),
            (artwork_x, artwork_y + artwork_height),
            (artwork_x + artwork_width, artwork_y + artwork_height),
        )

        for point_x, point_y in artwork_bounding_corners:
            distance_from_center = math.hypot(point_x - center_x, point_y - center_y)
            self.assertLessEqual(distance_from_center, radius - minimum_clearance)


if __name__ == "__main__":
    unittest.main()
