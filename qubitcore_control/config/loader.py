from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass(frozen=True)
class HeatingSpec:
    distribution: str
    mean: float

@dataclass(frozen=True)
class RouteSpec:
    from_zone: int
    to_zone: int
    duration_us: float
    heating: HeatingSpec
    waveform_ref: str # placeholder

@dataclass(frozen=True)
class TrapConfig:
    zones: tuple[int, ...]
    interaction_zone: int
    routes: dict[tuple[int, int], RouteSpec]

DEFAULT_PATH = Path(__file__).parent / "routes.yaml"

def load_trap_config(path: Path = DEFAULT_PATH) -> TrapConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    routes: dict[tuple[int, int], RouteSpec] = {}
    for r in raw["routes"]:
        key = (r["from"], r["to"])
        if key in routes:
            raise ValueError(f"Duplicate route {key} in {path}")
        routes[key] = RouteSpec(
            from_zone=r["from"],
            to_zone=r["to"],
            duration_us=float(r["duration_us"]),
            heating=HeatingSpec(**r["heating"]),
            waveform_ref=r["waveform_ref"],
        )

    cfg = TrapConfig(
          zones=tuple(raw["trap"]["zones"]),
          interaction_zone=int(raw["trap"]["interaction_zone"]),
          routes=routes,
    )
    _validate(cfg, path)
    return cfg

def _validate(cfg: TrapConfig, path: Path) -> None:
    if cfg.interaction_zone not in cfg.zones:
        raise ValueError(f"{path}: interaction_zone {cfg.interaction_zone} not in zones {cfg.zones}")
    for (a, b) in cfg.routes:
        if a not in cfg.zones or b not in cfg.zones:
            raise ValueError(f"{path}: route {a}->{b} references unknown zone")
        if a == b:
            raise ValueError(f"{path}: self-loop route {a}->{a}")