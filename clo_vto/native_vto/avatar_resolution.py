"""Resolve which avatar a try-on run should load, for one named user.

This replaces `_discover_default_native_avatar()` in the live path. That function globbed
`clo_vto/output/*.avt` and took whatever it found, which is fine for a one-user dev box
and wrong everywhere else: with two users on disk it can hand a shopper somebody else's
avatar. Once avatars carry real faces that stops being a mix-up and becomes a privacy
incident, which is why the delivery plan has this as Phase 0 - ahead of every other item,
because everything else makes the consequence worse.

The rule is the one in `face-pipeline-architecture-26_10_28.md` 3.3 and 4.3:

    faced.glb  ->  faced.avt  ->  avatar.avt  ->  base template

first that exists, and **every rung is keyed by user**. The ladder also doubles as the
degradation ladder: a face problem costs the shopper their face, never their try-on.

The safety property is structural rather than checked after the fact. Candidate paths are
*built* from the user id - `output/<user_id>-face-<run>/...` - so a directory belonging to
another user is never a candidate in the first place and cannot be returned by accident.
There is no glob over a shared directory anywhere in this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
# Each pipeline writes under its own package, so the two rungs that scan disk look in two
# different places. They were both pointed at a single shared tree at the repo root, which
# was wrong for Step 1 runs even before the face runs moved out of it: `avatar.avt` has
# always been written to `clo_avatar_generation/output`, so that rung never matched
# anything.
DEFAULT_FACE_OUTPUT_ROOT = WORKSPACE_ROOT / 'face_fitting' / 'output'
DEFAULT_AVATAR_OUTPUT_ROOT = WORKSPACE_ROOT / 'clo_avatar_generation' / 'output'
DEFAULT_BASE_TEMPLATE = WORKSPACE_ROOT / 'clo_avatar_generation' / 'input' / 'base-1.avt'

# Step 1 writes `output/<user_id>-<NNN>/`; the face job writes
# `output/<user_id>-face-<NNN>/`. Both are per-user by construction.
_RUN_SUFFIX = re.compile(r'^(\d{3,})$')

# Filenames to look for on each rung, in preference order within that rung.
FACED_GLB_NAMES = ('faced.glb', 'faced_avatar.glb')
FACED_AVT_NAMES = ('faced.avt',)  # plus '<user_id>.avt', added per user at lookup time
STEP1_AVT_NAMES = ('result_avatar.avt', 'result_avatar_from_project.avt', 'avatar.avt')

# A named dev fixture, used only when there is no user to confuse. Never reached once a
# user id is in play, however empty that user's folders are.
DEV_AVATAR = Path(__file__).resolve().parents[1] / 'output' / 'clo_test.avt'

TIERS = ('explicit', 'faced_glb', 'faced_avt', 'avatar_avt', 'dev_fixture', 'base_template')


@dataclass
class AvatarResolution:
    """Which avatar was chosen, and the full audit trail of what was looked at."""
    path: Path | None
    tier: str
    user_id: str | None
    considered: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_personalised(self) -> bool:
        """True when the shopper is getting their own avatar rather than a stand-in."""
        return self.tier in ('explicit', 'faced_glb', 'faced_avt', 'avatar_avt')

    @property
    def has_face(self) -> bool:
        return self.tier in ('faced_glb', 'faced_avt')

    def as_dict(self) -> dict:
        return {
            'path': None if self.path is None else str(self.path),
            'tier': self.tier,
            'user_id': self.user_id,
            'is_personalised': self.is_personalised,
            'has_face': self.has_face,
            'considered': self.considered,
            'warnings': self.warnings,
        }


def _run_number(directory: Path, prefix: str) -> int | None:
    """The run number of `<prefix><NNN>`, or None when the name does not fit."""
    name = directory.name
    if not name.startswith(prefix):
        return None
    match = _RUN_SUFFIX.match(name[len(prefix):])
    return int(match.group(1)) if match else None


def _user_run_dirs(output_root: Path, user_id: str, *, faced: bool) -> list[Path]:
    """This user's run directories, newest first.

    The prefix is built from the user id, so `u_002`'s folders are never even enumerated
    while resolving `u_001`. `u_001-face-001` also cannot be mistaken for a Step 1 run of
    `u_001`, because the Step 1 prefix requires digits straight after the dash.
    """
    if not output_root.is_dir():
        return []
    prefix = f'{user_id}-face-' if faced else f'{user_id}-'
    numbered: list[tuple[int, Path]] = []
    for directory in output_root.iterdir():
        if not directory.is_dir():
            continue
        number = _run_number(directory, prefix)
        if number is not None:
            numbered.append((number, directory))
    return [directory for _number, directory in sorted(numbered, reverse=True)]


def _first_existing(directories: list[Path], names: tuple[str, ...]) -> Path | None:
    for directory in directories:
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def resolve_avatar(
    user_id: str | None,
    *,
    explicit: Path | str | None = None,
    faced_avatar: Path | str | None = None,
    profile_avatar: Path | str | None = None,
    output_root: Path | str | None = None,
    face_output_root: Path | str | None = None,
    avatar_output_root: Path | str | None = None,
    base_template: Path | str | None = None,
    allow_dev_fixture: bool | None = None,
) -> AvatarResolution:
    """Pick the avatar for `user_id`, highest rung of the ladder that exists.

    `explicit` short-circuits everything, for a caller that already knows the path.

    `faced_avatar` and `profile_avatar` are the paths this user's stored profile records,
    slotting into the `faced_avt` and `avatar_avt` rungs ahead of anything discovered on
    disk. The face job writes beside the avatar it personalised rather than into the run
    tree, so without these the ladder would never see its output.

    `profile_avatar` is this user's avatar as their stored profile records it, and slots
    into the `avatar_avt` rung ahead of anything found on disk. The live try-on worker has
    that path already, so passing it lets the ladder prefer a faced avatar when one exists
    and otherwise land exactly where the worker would have anyway. It is not `explicit`,
    because `explicit` would skip the faced rungs and defeat the point.

    `allow_dev_fixture` defaults to True only when there is no user id: an ad-hoc CLI run
    has no shopper to hand the wrong face to, whereas a named user must get their own
    avatar or the stock template and nothing in between.
    """
    # `output_root` sets both roots at once, which is what a test with one temporary
    # directory wants; the specific two override it.
    face_root = Path(face_output_root or output_root or DEFAULT_FACE_OUTPUT_ROOT)
    avatar_root = Path(avatar_output_root or output_root or DEFAULT_AVATAR_OUTPUT_ROOT)
    template = Path(base_template) if base_template else DEFAULT_BASE_TEMPLATE
    if allow_dev_fixture is None:
        allow_dev_fixture = user_id is None

    considered: list[dict] = []
    warnings: list[str] = []

    def note(tier: str, path: Path | None, used: bool, reason: str = '') -> None:
        considered.append({'tier': tier, 'path': None if path is None else str(path),
                           'used': used, 'reason': reason})

    if explicit is not None:
        explicit_path = Path(explicit)
        if explicit_path.is_file():
            note('explicit', explicit_path, True, 'caller supplied the path')
            return AvatarResolution(explicit_path.resolve(), 'explicit', user_id, considered,
                                    warnings)
        note('explicit', explicit_path, False, 'supplied path does not exist')
        warnings.append(f'Explicit avatar path does not exist, falling back: {explicit_path}')

    if user_id:
        faced_dirs = _user_run_dirs(face_root, user_id, faced=True)
        step1_dirs = _user_run_dirs(avatar_root, user_id, faced=False)

        faced_glb = _first_existing(faced_dirs, FACED_GLB_NAMES)
        if faced_glb is not None:
            note('faced_glb', faced_glb, True, 'face geometry available')
            return AvatarResolution(faced_glb.resolve(), 'faced_glb', user_id, considered, warnings)
        note('faced_glb', None, False, f'none in {len(faced_dirs)} face run(s)')

        faced_avt = None
        if faced_avatar is not None and Path(faced_avatar).is_file():
            faced_avt = Path(faced_avatar)
        else:
            if faced_avatar is not None:
                warnings.append(f'The faced avatar recorded for {user_id} is missing from '
                                f'disk: {faced_avatar}')
            faced_avt = _first_existing(faced_dirs, FACED_AVT_NAMES + (f'{user_id}.avt',))
        if faced_avt is not None:
            note('faced_avt', faced_avt, True, 'face texture available')
            return AvatarResolution(faced_avt.resolve(), 'faced_avt', user_id, considered, warnings)
        note('faced_avt', None, False, f'none in {len(faced_dirs)} face run(s)')

        avatar_avt = None
        if profile_avatar is not None and Path(profile_avatar).is_file():
            avatar_avt = Path(profile_avatar)
        else:
            if profile_avatar is not None:
                warnings.append(f'The profile avatar for {user_id} is missing from disk: '
                                f'{profile_avatar}')
            avatar_avt = _first_existing(step1_dirs, STEP1_AVT_NAMES)
        if avatar_avt is not None:
            note('avatar_avt', avatar_avt, True, 'measured body, stock head')
            warnings.append(f'{user_id} has a measured avatar but no faced one; '
                            'the try-on will show the template head.')
            return AvatarResolution(avatar_avt.resolve(), 'avatar_avt', user_id, considered,
                                    warnings)
        note('avatar_avt', None, False, f'none in {len(step1_dirs)} Step 1 run(s)')

        # Deliberately not reached for a named user: handing them a fixture whose face
        # might be somebody else's is the exact failure this module exists to prevent.
        note('dev_fixture', DEV_AVATAR, False, 'skipped - a named user never gets a fixture')
        warnings.append(f'No avatar of any kind for {user_id}; falling back to the base '
                        'template. The try-on will not be personalised.')
    elif allow_dev_fixture and DEV_AVATAR.is_file():
        note('dev_fixture', DEV_AVATAR, True, 'ad-hoc run with no user id')
        warnings.append('No user id supplied; using the development fixture avatar. '
                        'This path must never be reached by a real try-on.')
        return AvatarResolution(DEV_AVATAR.resolve(), 'dev_fixture', None, considered, warnings)

    if template.is_file():
        note('base_template', template, True, 'last rung of the degradation ladder')
        return AvatarResolution(template.resolve(), 'base_template', user_id, considered, warnings)

    note('base_template', template, False, 'base template is missing too')
    warnings.append(f'No avatar could be resolved at all; base template missing: {template}')
    return AvatarResolution(None, 'base_template', user_id, considered, warnings)


def describe(resolution: AvatarResolution) -> str:
    """One line for the run log, naming the rung so a surprise is visible in the output."""
    label = {
        'explicit': 'explicit path',
        'faced_glb': "the user's faced avatar (head + hair)",
        'faced_avt': "the user's faced avatar (texture)",
        'avatar_avt': "the user's measured avatar, stock head",
        'dev_fixture': 'the development fixture',
        'base_template': 'the stock base template - NOT personalised',
    }.get(resolution.tier, resolution.tier)
    who = resolution.user_id or 'no user'
    return f'Avatar for {who}: {label} -> {resolution.path}'
