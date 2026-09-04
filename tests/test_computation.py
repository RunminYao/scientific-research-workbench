from test_helpers import *  # noqa: F403,F401

class RestartableComputationAssetTests(unittest.TestCase):
    def copy_template(self, root: Path, relative: str, name: str) -> Path:
        source = PLUGIN / relative
        target = root / name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return target

    def test_checkpoint_template_rejects_changed_inputs_and_round_trips_arrays(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.copy_template(
                root,
                "skills/implement-scientific-computations/assets/node_checkpoint_store.py.template",
                "node_checkpoint_store.py",
            )
            module = load_python_path("smw_checkpoint_asset", path)
            store = module.NodeCheckpointStore(root / "checkpoints")
            fingerprint = store.initialize(inputs={"mass": 1.0, "seed": 7})
            store.save("node-a", {"observable": 2.5})
            self.assertEqual(store.load("node-a"), {"observable": 2.5})
            resumed = module.NodeCheckpointStore(root / "checkpoints")
            self.assertEqual(
                resumed.initialize(inputs={"mass": 1.0, "seed": 7}), fingerprint,
            )
            with self.assertRaises(module.CheckpointError):
                module.NodeCheckpointStore(root / "checkpoints").initialize(
                    inputs={"mass": 2.0, "seed": 7},
                )
            try:
                import numpy as np
            except ImportError:
                return
            store.save_arrays("node-b", {"state": np.eye(2)}, metadata={"step": 3})
            arrays, metadata = store.load_arrays("node-b")
            np.testing.assert_array_equal(arrays["state"], np.eye(2))
            self.assertEqual(metadata, {"step": 3})

    def test_chunk_plan_template_has_exact_multi_grid_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.copy_template(
                root,
                "skills/implement-scientific-computations/assets/chunk_plan.py.template",
                "chunk_plan.py",
            )
            module = load_python_path("smw_chunk_plan_asset", path)
            counts = {"coarse": 5, "fine": 9}
            plan = module.build_chunk_plan(
                node_counts=counts, chunk_sizes={"coarse": 2, "fine": 3},
            )
            module.validate_exact_coverage(plan, node_counts=counts)
            self.assertEqual([row.label for row in plan], ["000", "001", "002"])
            self.assertEqual(plan[-1].for_grid("coarse"), (4, 5))
            self.assertEqual(plan[-1].for_grid("fine"), (6, 9))
