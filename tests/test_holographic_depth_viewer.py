import tempfile
import unittest
from pathlib import Path

from src.holo.avatar_system.threejs_renderer import ThreeJSAvatarRenderer


class HolographicDepthViewerTests(unittest.TestCase):
    def test_threejs_renderer_uses_runtime_holographic_depth(self):
        avatar_data = {
            "avatar_id": "depth-test-avatar",
            "geometry_type": "quantum_sphere",
            "rarity_tier": "legendary",
            "vault_number": 42,
            "attributes": {
                "quantum_entropy": 50.0,
                "spinor_complexity": 60.0,
                "bell_verification": 70.0,
                "polyhedral_symmetry": 80.0,
                "temporal_stability": 90.0,
                "spatial_coherence": 55.0,
                "dimensional_depth": 3.2,
                "render_dimensional_depth": 5.0,
                "holographic_depth_level": 2,
                "fractal_dimension": 2.4,
                "energy_resonance": 44.0,
            },
            "binding": {"power_multiplier": 1.0},
            "effective_power": 4000,
        }

        renderer = ThreeJSAvatarRenderer(avatar_data)
        self.assertEqual(renderer.holographic_depth_level, 2)
        self.assertEqual(renderer.dimensional_depth, 5.0)
        self.assertEqual(renderer.dimension_layers, 5)

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "viewer.html"
            rendered_path = renderer.generate_html(str(output_path), auto_open=False)
            html = Path(rendered_path).read_text(encoding="utf-8")

        self.assertIn("Holo Depth", html)
        self.assertIn("L2 / 5.0D", html)
        self.assertIn("dimensional_depth: 5.0", html)
        self.assertIn("const holoDepthLevel = 2;", html)
        self.assertIn("Holographic depth tier visuals", html)

    def test_threejs_renderer_includes_high_tier_depth_artifacts(self):
        avatar_data = {
            "avatar_id": "depth-tier-seven-avatar",
            "geometry_type": "quantum_sphere",
            "rarity_tier": "mythical",
            "vault_number": 7,
            "attributes": {
                "dimensional_depth": 4.0,
                "render_dimensional_depth": 7.0,
                "holographic_depth_level": 7,
            },
            "binding": {"power_multiplier": 1.0},
            "effective_power": 7000,
        }

        renderer = ThreeJSAvatarRenderer(avatar_data)
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "viewer_depth7.html"
            rendered_path = renderer.generate_html(str(output_path), auto_open=False)
            html = Path(rendered_path).read_text(encoding="utf-8")

        self.assertIn("const holoDepthLevel = 7;", html)
        self.assertIn("depthArtifacts.push({ kind: 'halo'", html)
        self.assertIn("depthArtifacts.push({ kind: 'crown'", html)


if __name__ == "__main__":
    unittest.main()
