"""In-process world registry for local tools and HUD subprocess rollouts."""

from __future__ import annotations

from parliament.models import World
from parliament.worlds import build_world

_WORLDS: dict[str, World] = {}


def register_world(world: World) -> World:
    """Register a world by world_id and return it."""

    _WORLDS[world.world_id] = world
    return world


def create_world(
    *,
    world_id: str,
    domain: str,
    difficulty: str,
    seed: int,
    variant: int | None = None,
) -> World:
    """Build and register a world."""

    return register_world(
        build_world(
            world_id=world_id,
            domain=domain,
            difficulty=difficulty,
            seed=seed,
            variant=variant,
        )
    )


def get_world(world_id: str) -> World:
    """Return a registered world or raise a helpful KeyError."""

    try:
        return _WORLDS[world_id]
    except KeyError as exc:
        raise KeyError(f"Unknown world_id: {world_id}") from exc


def reset_worlds() -> None:
    """Clear the registry. Intended for tests and local simulations."""

    _WORLDS.clear()


def known_world_ids() -> list[str]:
    """Return registered world IDs for diagnostics."""

    return sorted(_WORLDS)

