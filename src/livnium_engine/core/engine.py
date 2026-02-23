from __future__ import annotations

import hashlib
import random
import struct
from dataclasses import dataclass

from .coords import Coords, build_coords
from .rotations import ROTATIONS, inverse_rotation_index, mat_vec


LastAction = tuple[str, ...]


@dataclass(slots=True)
class AxionGridCore:
    N: int
    coords: Coords
    grid: list[int]
    rot_index_map: list[list[int]]
    last_op_id: int | None
    last_action: tuple | None

    def __init__(self, N: int):
        self.N = N
        self.coords = build_coords(N)
        n3 = N**3
        self.grid = list(range(n3))
        self.rot_index_map = self._build_rot_index_maps()
        self.last_op_id = None
        self.last_action = None

    def _build_rot_index_maps(self) -> list[list[int]]:
        maps: list[list[int]] = []
        idx_to_coord = self.coords.index_to_coord
        coord_to_idx = self.coords.coord_to_index
        for m in ROTATIONS:
            mp = [0] * (self.N**3)
            for old_i, c in enumerate(idx_to_coord):
                new_c = mat_vec(m, c)
                try:
                    new_i = coord_to_idx[new_c]
                except KeyError as e:
                    raise AssertionError(f"rotation maps coord out of domain: {new_c}") from e
                mp[old_i] = new_i
            maps.append(mp)
        if len(maps) != 24:
            raise AssertionError("rotations must be exactly 24")
        return maps

    def randomize(self, seed: int) -> None:
        rng = random.Random(seed)
        rng.shuffle(self.grid)
        self.last_op_id = None
        self.last_action = None

    def apply(self, op_id: int) -> None:
        if not (0 <= op_id < 24):
            raise ValueError("op_id must be in [0..23]")
        mp = self.rot_index_map[op_id]
        old = self.grid
        new = [0] * len(old)
        for old_i, tok in enumerate(old):
            new_i = mp[old_i]
            new[new_i] = tok
        self.grid = new
        self.last_op_id = op_id
        self.last_action = ("global", op_id)

    def inverse_op(self, op_id: int) -> int:
        if not (0 <= op_id < 24):
            raise ValueError("op_id must be in [0..23]")
        return inverse_rotation_index(op_id)

    def inverse_local(
        self,
        op_id: int,
        center: tuple[int, int, int],
        radius: int,
    ) -> tuple[int, tuple[int, int, int], int]:
        return (self.inverse_op(op_id), center, radius)

    def apply_local(self, op_id: int, center: tuple[int, int, int], radius: int) -> None:
        if not (0 <= op_id < 24):
            raise ValueError("op_id must be in [0..23]")
        if center not in self.coords.coord_to_index:
            raise ValueError("center must be a valid lattice coordinate")
        if radius < 1:
            raise ValueError("radius must be >= 1")

        k = self.coords.k
        cx, cy, cz = center
        if max(abs(cx), abs(cy), abs(cz)) > k:
            raise ValueError("center out of bounds")

        # Region must lie fully inside bounds.
        if abs(cx) + radius > k or abs(cy) + radius > k or abs(cz) + radius > k:
            raise ValueError("region out of bounds")

        mapping = self._local_index_mapping(op_id, center, radius)

        old = self.grid
        new = list(old)  # outside region unchanged
        for old_i, new_i in mapping.items():
            new[new_i] = old[old_i]
        self.grid = new
        self.last_op_id = None
        self.last_action = ("local", op_id, center, radius)

    def state(self) -> dict:
        return {
            "N": self.N,
            "grid": list(self.grid),
            "last_op_id": self.last_op_id,
            "last_action": self.last_action,
        }

    def _canonical_bytes(self) -> bytes:
        # little-endian uint32 array: [N] + grid
        fmt = "<" + "I" * (1 + len(self.grid))
        return struct.pack(fmt, self.N, *self.grid)

    def hash(self) -> str:
        return hashlib.sha256(self._canonical_bytes()).hexdigest()

    def audit(self) -> None:
        # NON-MUTATING: must restore exactly.
        before_grid = list(self.grid)
        before_last = self.last_op_id
        before_action = self.last_action
        before_hash = self.hash()

        try:
            self._audit_permutation()
            self._audit_rot_maps()
            self._audit_inverse_roundtrip()
        finally:
            # Restore regardless of success; then ensure truly non-mutating.
            self.grid = before_grid
            self.last_op_id = before_last
            self.last_action = before_action
            after_hash = self.hash()
            if after_hash != before_hash:
                raise AssertionError("audit() mutated engine state (hash mismatch)")

    def _local_index_mapping(
        self,
        op_id: int,
        center: tuple[int, int, int],
        radius: int,
    ) -> dict[int, int]:
        """Return mapping old_index -> new_index induced by local rotation on region."""
        cx, cy, cz = center
        m = ROTATIONS[op_id]
        idx_to_coord = self.coords.index_to_coord
        coord_to_idx = self.coords.coord_to_index

        # Enumerate region coords and map via relative rotation.
        mapping: dict[int, int] = {}
        for x in range(cx - radius, cx + radius + 1):
            for y in range(cy - radius, cy + radius + 1):
                for z in range(cz - radius, cz + radius + 1):
                    if max(abs(x - cx), abs(y - cy), abs(z - cz)) > radius:
                        continue
                    old_c = (x, y, z)
                    old_i = coord_to_idx[old_c]
                    rx, ry, rz = mat_vec(m, (x - cx, y - cy, z - cz))
                    new_c = (cx + rx, cy + ry, cz + rz)
                    new_i = coord_to_idx[new_c]
                    mapping[old_i] = new_i

        # Sanity: mapping size equals region size (cube under Chebyshev metric)
        expected = (2 * radius + 1) ** 3
        if len(mapping) != expected:
            raise AssertionError("local region mapping size mismatch")

        return mapping

    def _audit_permutation(self) -> None:
        n3 = self.N**3
        if len(self.grid) != n3:
            raise AssertionError("grid length mismatch")
        s = set(self.grid)
        if len(s) != n3:
            raise AssertionError("grid tokens not unique")
        if s != set(range(n3)):
            raise AssertionError("grid tokens out of range")

    def _audit_rot_maps(self) -> None:
        n3 = self.N**3

        if self.last_action is None:
            # one-time validator: all global maps
            for op_id in range(24):
                mp = self.rot_index_map[op_id]
                if len(mp) != n3:
                    raise AssertionError("rotation index map length mismatch")
                if any((j < 0 or j >= n3) for j in mp):
                    raise AssertionError("rotation index map out of range")
                if len(set(mp)) != n3:
                    raise AssertionError("rotation index map is not a bijection")
            return

        kind = self.last_action[0]
        if kind == "global":
            op_id = int(self.last_action[1])
            mp = self.rot_index_map[op_id]
            if len(mp) != n3:
                raise AssertionError("rotation index map length mismatch")
            if any((j < 0 or j >= n3) for j in mp):
                raise AssertionError("rotation index map out of range")
            if len(set(mp)) != n3:
                raise AssertionError("rotation index map is not a bijection")
        elif kind == "local":
            op_id = int(self.last_action[1])
            center = self.last_action[2]
            radius = int(self.last_action[3])
            mapping = self._local_index_mapping(op_id, center, radius)
            dom = list(mapping.keys())
            img = list(mapping.values())
            if any((i < 0 or i >= n3) for i in dom):
                raise AssertionError("local rotation domain out of range")
            if any((j < 0 or j >= n3) for j in img):
                raise AssertionError("local rotation image out of range")
            if len(set(dom)) != len(dom):
                raise AssertionError("local rotation domain has collisions")
            if len(set(img)) != len(img):
                raise AssertionError("local rotation image has collisions")
            if set(dom) != set(img):
                raise AssertionError("local rotation is not a bijection on the region")
        else:
            raise AssertionError("unknown last_action kind")

    def _audit_inverse_roundtrip(self) -> None:
        if self.last_action is None:
            return

        snap = self._canonical_bytes()

        kind = self.last_action[0]
        if kind == "global":
            op_id = int(self.last_action[1])
            inv = self.inverse_op(op_id)
            self.apply(op_id)
            self.apply(inv)
        elif kind == "local":
            op_id = int(self.last_action[1])
            center = self.last_action[2]
            radius = int(self.last_action[3])
            inv_op, inv_center, inv_radius = self.inverse_local(op_id, center, radius)
            self.apply_local(op_id, center, radius)
            self.apply_local(inv_op, inv_center, inv_radius)
        else:
            raise AssertionError("unknown last_action kind")

        if self._canonical_bytes() != snap:
            raise AssertionError("apply(op); apply(inverse) did not restore state")


class LivniumEngineCore(AxionGridCore):
    """Primary public name for the engine core.

    `AxionGridCore` remains as a back-compat alias.
    """

    def perturb(self, steps: int, seed: int) -> None:
        """Apply random *local* operations for `steps` iterations.

        This is an energy-agnostic noise operator used for recovery / stability experiments.

        Invariants:
        - Uses only valid local rotations (op_id in [0..23])
        - Calls audit() after each operation
        """

        if steps < 0:
            raise ValueError("steps must be >= 0")

        rng = random.Random(seed)
        k = self.coords.k

        for _ in range(steps):
            op_id = rng.randrange(24)
            radius = rng.choice([1, 2])
            lo = -k + radius
            hi = k - radius
            cx = rng.randint(lo, hi)
            cy = rng.randint(lo, hi)
            cz = rng.randint(lo, hi)
            center = (cx, cy, cz)
            self.apply_local(op_id, center, radius)
            self.audit()
