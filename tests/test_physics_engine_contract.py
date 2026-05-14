import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.holo.physics_engine import PhysicsState, PolyhedronPhysicsEngine, Trajectory


class PhysicsEngineContractTests(unittest.TestCase):
    def test_simulation_hash_matches_existing_sha256_contract(self):
        engine = object.__new__(PolyhedronPhysicsEngine)
        trajectory = Trajectory()

        for i in range(12):
            trajectory.states.append(
                PhysicsState(
                    position=np.array([float(i), float(i + 1), float(i + 2)]),
                    velocity=np.zeros(3),
                    orientation=np.array([1.0, 0.0, 0.0, float(i) / 10.0]),
                    angular_velocity=np.zeros(3),
                )
            )

        sampled = []
        for state in trajectory.states[::10]:
            sampled.extend(state.position.tolist())
            sampled.extend(state.orientation.tolist())

        expected = hashlib.sha256(np.array(sampled).tobytes()).hexdigest()
        self.assertEqual(engine._compute_simulation_hash(trajectory), expected)


if __name__ == "__main__":
    unittest.main()
