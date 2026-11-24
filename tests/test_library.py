from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from library import ROOT, SVG, build, icons, load_catalog, render_layout, sprite, validate, validate_svg


class LibraryTests(unittest.TestCase):
    def test_inventory_and_legacy_contract(self):
        result = validate()
        self.assertEqual(result, {"icons": 120, "aliases": 1, "references": 123,
                                  "legacyPreserved": 38, "routeTemplates": 10, "dynamicDimensions": 4})

    def test_duplicate_public_id_is_rejected(self):
        catalog = deepcopy(load_catalog())
        catalog["entries"]["2.4"]["representations"][1]["symbolId"] = "boulder"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate(catalog)

    def test_alias_has_identical_geometry_and_no_duplicate_ids(self):
        root = sprite()
        all_ids = [el.get("id") for el in root.iter() if el.get("id")]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        definitions = {el.get("id"): el for el in root}
        typo = deepcopy(definitions["minor-wather-channel"])
        corrected = deepcopy(definitions["minor-water-channel"])
        typo.attrib.pop("id")
        corrected.attrib.pop("id")
        self.assertEqual(ET.tostring(typo), ET.tostring(corrected))
        self.assertNotIn('fill="solid"', ET.tostring(root, encoding="unicode"))

    def test_legacy_boulder_and_corrected_variant_are_distinct(self):
        definitions = {el.get("id"): el for el in sprite()}
        self.assertIsNotNone(definitions["boulder"].find(f"{{{SVG}}}circle"))
        self.assertIsNotNone(definitions["boulder-iof-2024"].find(f"{{{SVG}}}path"))
        self.assertNotIn("fill", definitions["boulder"].attrib)

    def test_unexpected_paints_and_unresolved_references_fail(self):
        for markup in ['<circle fill="white"/>', '<rect fill="url(#missing)"/>', '<g id="x"/><g id="x"/>']:
            with self.subTest(markup=markup), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "bad.svg"
                path.write_text(f'<svg xmlns="{SVG}" viewBox="0 0 24 24">{markup}</svg>')
                with self.assertRaises(ValueError):
                    validate_svg(path)

    def test_dimensions_use_supplied_values(self):
        root = render_layout("9.3", values=["0.75", "4.2"])
        self.assertEqual([el.text for el in root.iter() if el.tag == f"{{{SVG}}}text"], ["0.75", "4.2"])
        self.assertEqual(len(root.findall(f"{{{SVG}}}path")), 1)
        root = render_layout("9.2", values=[12, 6])
        self.assertIn("12 × 6", ET.tostring(root, encoding="unicode"))

    def test_route_distance_is_required_and_dynamic(self):
        root = render_layout("15.1", distance=85)
        self.assertIn("85 m", ET.tostring(root, encoding="unicode"))
        self.assertNotIn("60 m", ET.tostring(root, encoding="unicode"))
        self.assertNotIn("data-field", ET.tostring(root, encoding="unicode"))
        with self.assertRaises(ValueError):
            render_layout("15.1")
        with self.assertRaises(ValueError):
            render_layout("15.3", distance=10)

    def test_bad_numeric_inputs_fail(self):
        for value in ["NaN", "Infinity", "-1", "<script>", True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_layout("9.1", values=[value])

    def test_sprite_build_is_deterministic_and_aliases_match(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            build(output)
            first = (output / "ioficons-sprite.svg").read_bytes()
            build(output)
            self.assertEqual(first, (output / "ioficons-sprite.svg").read_bytes())
            self.assertEqual(first, (output / "iofico.svg").read_bytes())
            self.assertEqual(first, (output / "ioficon-sprite.svg").read_bytes())
            self.assertEqual((output / "icons/boulder.svg").read_bytes(), (ROOT / "icons/boulder.svg").read_bytes())


if __name__ == "__main__":
    unittest.main()
