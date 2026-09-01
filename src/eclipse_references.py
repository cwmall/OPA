"""Bundled Eclipse reference datasets and event-by-event comparison tools."""

import csv
import math
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from time_utils import format_csv_utc


PROJECT_DIR = Path(__file__).resolve().parents[1]
ECLIPSE_REFERENCE_DIR = PROJECT_DIR / "references" / "eclipse"


@dataclass(frozen=True)
class EclipseReferenceSpec:
    dataset_id: str
    label: str
    satellite: str
    relative_path: str
    source_format: str
    nominal_longitude_deg: float
    coverage_start_utc: datetime
    coverage_end_utc: datetime


@dataclass(frozen=True)
class EclipseReferenceEvent:
    event_number: int
    shadow_body: str
    penumbra_entry_utc: datetime | None
    umbra_entry_utc: datetime | None
    center_utc: datetime | None
    umbra_exit_utc: datetime | None
    penumbra_exit_utc: datetime | None
    total_duration_seconds: float | None
    minimum_sunlight_fraction: float | None

    @property
    def reference_epoch(self):
        return next(
            (
                value
                for value in (
                    self.penumbra_entry_utc,
                    self.umbra_entry_utc,
                    self.center_utc,
                    self.umbra_exit_utc,
                    self.penumbra_exit_utc,
                )
                if value is not None
            ),
            None,
        )


@dataclass(frozen=True)
class EclipseReferenceDataset:
    spec: EclipseReferenceSpec
    events: tuple[EclipseReferenceEvent, ...]


@dataclass(frozen=True)
class EclipseComparisonRow:
    status: str
    shadow_body: str
    reference_event_number: int | None
    output_event_number: int | None
    reference_event: EclipseReferenceEvent | None
    output_event: object | None
    penumbra_entry_delta_seconds: float | None
    umbra_entry_delta_seconds: float | None
    umbra_exit_delta_seconds: float | None
    penumbra_exit_delta_seconds: float | None
    total_duration_delta_seconds: float | None

    @property
    def maximum_absolute_contact_delta_seconds(self):
        values = (
            self.penumbra_entry_delta_seconds,
            self.umbra_entry_delta_seconds,
            self.umbra_exit_delta_seconds,
            self.penumbra_exit_delta_seconds,
        )
        finite = [abs(value) for value in values if value is not None]
        return max(finite) if finite else None


@dataclass(frozen=True)
class EclipseReferenceComparison:
    dataset: EclipseReferenceDataset
    tolerance_seconds: float
    rows: tuple[EclipseComparisonRow, ...]

    @property
    def matched_count(self):
        return sum(row.status == "MATCH" for row in self.rows)

    @property
    def difference_count(self):
        return sum(row.status == "DIFFERENCE" for row in self.rows)

    @property
    def missing_output_count(self):
        return sum(row.status == "MISSING OUTPUT" for row in self.rows)

    @property
    def extra_output_count(self):
        return sum(row.status == "EXTRA OUTPUT" for row in self.rows)

    @property
    def contact_deltas_seconds(self):
        values = []
        for row in self.rows:
            values.extend(
                value
                for value in (
                    row.penumbra_entry_delta_seconds,
                    row.umbra_entry_delta_seconds,
                    row.umbra_exit_delta_seconds,
                    row.penumbra_exit_delta_seconds,
                )
                if value is not None and math.isfinite(float(value))
            )
        return tuple(float(value) for value in values)

    @property
    def rms_contact_error_seconds(self):
        values = self.contact_deltas_seconds
        if not values:
            return None
        return math.sqrt(sum(value * value for value in values) / len(values))

    @property
    def mean_absolute_contact_error_seconds(self):
        values = self.contact_deltas_seconds
        if not values:
            return None
        return sum(abs(value) for value in values) / len(values)

    @property
    def maximum_absolute_contact_error_seconds(self):
        values = self.contact_deltas_seconds
        return max((abs(value) for value in values), default=None)


def _utc(year, month, day):
    return datetime(year, month, day, tzinfo=timezone.utc)


ECLIPSE_REFERENCE_SPECS = (
    EclipseReferenceSpec(
        dataset_id="synthetic_geo_2030_equinox",
        label="SYNTHETIC/DEMO · 2030 equinox sample",
        satellite="SYNTHETIC GEO DEMO",
        relative_path="",
        source_format="synthetic_memory",
        nominal_longitude_deg=12.0,
        coverage_start_utc=_utc(2030, 3, 20),
        coverage_end_utc=_utc(2030, 3, 23),
    ),
)

_SYNTHETIC_ECLIPSE_EVENTS = (
    EclipseReferenceEvent(
        event_number=1,
        shadow_body="EARTH",
        penumbra_entry_utc=datetime(2030, 3, 20, 22, 41, tzinfo=timezone.utc),
        umbra_entry_utc=datetime(2030, 3, 20, 22, 43, tzinfo=timezone.utc),
        center_utc=datetime(2030, 3, 20, 23, 17, tzinfo=timezone.utc),
        umbra_exit_utc=datetime(2030, 3, 20, 23, 51, tzinfo=timezone.utc),
        penumbra_exit_utc=datetime(2030, 3, 20, 23, 53, tzinfo=timezone.utc),
        total_duration_seconds=4320.0,
        minimum_sunlight_fraction=0.0,
    ),
    EclipseReferenceEvent(
        event_number=2,
        shadow_body="EARTH",
        penumbra_entry_utc=datetime(2030, 3, 21, 22, 37, tzinfo=timezone.utc),
        umbra_entry_utc=datetime(2030, 3, 21, 22, 39, tzinfo=timezone.utc),
        center_utc=datetime(2030, 3, 21, 23, 13, tzinfo=timezone.utc),
        umbra_exit_utc=datetime(2030, 3, 21, 23, 47, tzinfo=timezone.utc),
        penumbra_exit_utc=datetime(2030, 3, 21, 23, 49, tzinfo=timezone.utc),
        total_duration_seconds=4320.0,
        minimum_sunlight_fraction=0.0,
    ),
)

_SPECS_BY_ID = {spec.dataset_id: spec for spec in ECLIPSE_REFERENCE_SPECS}
_SESSION_ECLIPSE_DATASETS = {}


def _parse_session_utc(value):
    if value in (None, ""):
        return None
    epoch = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if epoch.tzinfo is None:
        raise ValueError("Session Eclipse epoch must include a UTC offset.")
    return epoch.astimezone(timezone.utc)


def clear_session_eclipse_reference_datasets():
    """Drop all decrypted Eclipse events from the active process."""

    for dataset_id in tuple(_SESSION_ECLIPSE_DATASETS):
        _SPECS_BY_ID.pop(dataset_id, None)
    _SESSION_ECLIPSE_DATASETS.clear()


def register_session_eclipse_reference_datasets(datasets):
    """Register validated in-memory Eclipse events for an admin session."""

    clear_session_eclipse_reference_datasets()
    public_ids = {spec.dataset_id for spec in ECLIPSE_REFERENCE_SPECS}
    for source in datasets:
        dataset_id = str(source["id"])
        if dataset_id in public_ids:
            raise ValueError("Admin Eclipse identifiers cannot replace public datasets.")
        spec = EclipseReferenceSpec(
            dataset_id=dataset_id,
            label=str(source["label"]),
            satellite=str(source["satellite"]),
            relative_path="",
            source_format="admin_memory",
            nominal_longitude_deg=float(source["nominal_longitude_deg"]),
            coverage_start_utc=_parse_session_utc(source["coverage_start_utc"]),
            coverage_end_utc=_parse_session_utc(source["coverage_end_utc"]),
        )
        events = tuple(
            EclipseReferenceEvent(
                event_number=int(item["event_number"]),
                shadow_body=str(item["shadow_body"]),
                penumbra_entry_utc=_parse_session_utc(item["penumbra_entry_utc"]),
                umbra_entry_utc=_parse_session_utc(item["umbra_entry_utc"]),
                center_utc=_parse_session_utc(item["center_utc"]),
                umbra_exit_utc=_parse_session_utc(item["umbra_exit_utc"]),
                penumbra_exit_utc=_parse_session_utc(item["penumbra_exit_utc"]),
                total_duration_seconds=item["total_duration_seconds"],
                minimum_sunlight_fraction=item["minimum_sunlight_fraction"],
            )
            for item in source["events"]
        )
        dataset = EclipseReferenceDataset(spec=spec, events=events)
        _SPECS_BY_ID[dataset_id] = spec
        _SESSION_ECLIPSE_DATASETS[dataset_id] = dataset


def available_eclipse_reference_specs():
    return ECLIPSE_REFERENCE_SPECS + tuple(
        dataset.spec for dataset in _SESSION_ECLIPSE_DATASETS.values()
    )


def _column_index(cell_reference):
    letters = "".join(character for character in cell_reference if character.isalpha())
    result = 0
    for character in letters.upper():
        result = result * 26 + ord(character) - ord("A") + 1
    return result - 1


def _xlsx_rows(path):
    """Read static cell values from the first worksheet using the stdlib."""

    spreadsheet_namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    relationship_namespace = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_relationship_namespace = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall(f"{{{spreadsheet_namespace}}}si"):
                shared_strings.append(
                    "".join(
                        node.text or ""
                        for node in item.iter(f"{{{spreadsheet_namespace}}}t")
                    )
                )

        workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        first_sheet = workbook_root.find(
            f".//{{{spreadsheet_namespace}}}sheet"
        )
        if first_sheet is None:
            return []
        relationship_id = first_sheet.attrib[
            f"{{{relationship_namespace}}}id"
        ]
        relationships_root = ElementTree.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        target = None
        for relationship in relationships_root.findall(
            f"{{{package_relationship_namespace}}}Relationship"
        ):
            if relationship.attrib.get("Id") == relationship_id:
                target = relationship.attrib.get("Target")
                break
        if not target:
            raise ValueError(f"Worksheet relationship is missing in {path.name}.")
        target_path = PurePosixPath(target.lstrip("/"))
        if not str(target_path).startswith("xl/"):
            target_path = PurePosixPath("xl") / target_path
        sheet_root = ElementTree.fromstring(archive.read(str(target_path)))

    rows = []
    for row_element in sheet_root.findall(
        f".//{{{spreadsheet_namespace}}}sheetData/{{{spreadsheet_namespace}}}row"
    ):
        row = {}
        for cell in row_element.findall(f"{{{spreadsheet_namespace}}}c"):
            reference = cell.attrib.get("r", "")
            if not reference:
                continue
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                value = "".join(
                    node.text or ""
                    for node in cell.iter(f"{{{spreadsheet_namespace}}}t")
                )
            else:
                value_element = cell.find(f"{{{spreadsheet_namespace}}}v")
                if value_element is None:
                    continue
                raw_value = value_element.text or ""
                if cell_type == "s":
                    value = shared_strings[int(raw_value)]
                elif cell_type in {"str", "e"}:
                    value = raw_value
                elif cell_type == "b":
                    value = raw_value == "1"
                else:
                    try:
                        value = float(raw_value)
                    except ValueError:
                        value = raw_value
            row[_column_index(reference)] = value
        if row:
            rows.append(row)
    return rows


def _excel_datetime(date_serial, time_fraction):
    if date_serial is None or time_fraction is None:
        return None
    try:
        serial = float(date_serial) + float(time_fraction)
    except (TypeError, ValueError):
        return None
    return datetime(1899, 12, 30, tzinfo=timezone.utc) + timedelta(days=serial)


def _xlsx_minimum_sunlight(value):
    if value is None:
        return None
    numbers = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", str(value))
    if not numbers:
        return None
    maximum_obscuration = float(numbers[-1])
    return min(max(1.0 - maximum_obscuration, 0.0), 1.0)


def _read_xlsx_events(path):
    events = []
    for row in _xlsx_rows(path):
        for shadow_column, raw_body in row.items():
            body = str(raw_body).strip().upper()
            if body not in {"EARTH", "MOON"} or shadow_column < 7:
                continue
            date_column = shadow_column - 7
            date_serial = row.get(date_column)
            penumbra_entry = _excel_datetime(
                date_serial,
                row.get(shadow_column - 6),
            )
            umbra_entry = _excel_datetime(
                date_serial,
                row.get(shadow_column - 5),
            )
            center = _excel_datetime(
                date_serial,
                row.get(shadow_column - 4),
            )
            umbra_exit = _excel_datetime(
                date_serial,
                row.get(shadow_column - 3),
            )
            penumbra_exit = _excel_datetime(
                date_serial,
                row.get(shadow_column - 2),
            )
            if penumbra_entry is None and center is None and penumbra_exit is None:
                continue
            duration_value = row.get(shadow_column - 1)
            try:
                duration_seconds = float(duration_value) * 86400.0
            except (TypeError, ValueError):
                duration_seconds = (
                    (penumbra_exit - penumbra_entry).total_seconds()
                    if penumbra_entry is not None and penumbra_exit is not None
                    else None
                )
            events.append(
                EclipseReferenceEvent(
                    event_number=len(events) + 1,
                    shadow_body=body,
                    penumbra_entry_utc=penumbra_entry,
                    umbra_entry_utc=umbra_entry,
                    center_utc=center,
                    umbra_exit_utc=umbra_exit,
                    penumbra_exit_utc=penumbra_exit,
                    total_duration_seconds=duration_seconds,
                    minimum_sunlight_fraction=_xlsx_minimum_sunlight(
                        row.get(shadow_column + 1)
                    ),
                )
            )
    return tuple(events)


_EVENT_SEGMENT_PATTERN = re.compile(
    r"^\s*(PENUMBRA|UMBRA)\s+"
    r"(\d{4}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
    r"(\d{4}/\d{2}/\d{2}-\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
    r"(EARTH|MOON)\s*/\s*([0-9.]+)\s+MIN\s*/\s*([0-9.]+)",
    re.IGNORECASE,
)


def _report_datetime(value):
    return datetime.strptime(value, "%Y/%m/%d-%H:%M:%S.%f").replace(
        tzinfo=timezone.utc
    )


def _read_event_report(path):
    segments = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = _EVENT_SEGMENT_PATTERN.match(line)
        if match is None:
            continue
        kind, start, end, body, _duration, minimum_sunlight = match.groups()
        segments.append(
            {
                "kind": kind.upper(),
                "start": _report_datetime(start),
                "end": _report_datetime(end),
                "body": body.upper(),
                "minimum_sunlight": float(minimum_sunlight),
            }
        )

    events = []
    index = 0
    while index < len(segments):
        segment = segments[index]
        if segment["kind"] == "PENUMBRA":
            penumbra_entry = segment["start"]
            penumbra_exit = segment["end"]
            umbra_entry = None
            umbra_exit = None
            minimum_sunlight = segment["minimum_sunlight"]
            if index + 2 < len(segments):
                umbra = segments[index + 1]
                trailing_penumbra = segments[index + 2]
                is_complete = (
                    umbra["kind"] == "UMBRA"
                    and trailing_penumbra["kind"] == "PENUMBRA"
                    and umbra["body"] == segment["body"]
                    and trailing_penumbra["body"] == segment["body"]
                    and abs((umbra["start"] - segment["end"]).total_seconds()) <= 1.0
                    and abs((trailing_penumbra["start"] - umbra["end"]).total_seconds()) <= 1.0
                )
                if is_complete:
                    umbra_entry = umbra["start"]
                    umbra_exit = umbra["end"]
                    penumbra_exit = trailing_penumbra["end"]
                    minimum_sunlight = min(
                        minimum_sunlight,
                        umbra["minimum_sunlight"],
                        trailing_penumbra["minimum_sunlight"],
                    )
                    index += 2
            center = penumbra_entry + (penumbra_exit - penumbra_entry) / 2
            events.append(
                EclipseReferenceEvent(
                    event_number=len(events) + 1,
                    shadow_body=segment["body"],
                    penumbra_entry_utc=penumbra_entry,
                    umbra_entry_utc=umbra_entry,
                    center_utc=center,
                    umbra_exit_utc=umbra_exit,
                    penumbra_exit_utc=penumbra_exit,
                    total_duration_seconds=(
                        penumbra_exit - penumbra_entry
                    ).total_seconds(),
                    minimum_sunlight_fraction=minimum_sunlight,
                )
            )
        else:
            center = segment["start"] + (segment["end"] - segment["start"]) / 2
            events.append(
                EclipseReferenceEvent(
                    event_number=len(events) + 1,
                    shadow_body=segment["body"],
                    penumbra_entry_utc=None,
                    umbra_entry_utc=segment["start"],
                    center_utc=center,
                    umbra_exit_utc=segment["end"],
                    penumbra_exit_utc=None,
                    total_duration_seconds=(
                        segment["end"] - segment["start"]
                    ).total_seconds(),
                    minimum_sunlight_fraction=segment["minimum_sunlight"],
                )
            )
        index += 1
    return tuple(events)


@lru_cache(maxsize=None)
def load_eclipse_reference_dataset(dataset_id):
    session_dataset = _SESSION_ECLIPSE_DATASETS.get(str(dataset_id))
    if session_dataset is not None:
        return session_dataset
    try:
        spec = _SPECS_BY_ID[str(dataset_id)]
    except KeyError as error:
        raise ValueError(f"Unknown Eclipse reference dataset: {dataset_id}") from error
    if spec.source_format == "synthetic_memory":
        return EclipseReferenceDataset(
            spec=spec,
            events=_SYNTHETIC_ECLIPSE_EVENTS,
        )
    path = ECLIPSE_REFERENCE_DIR / spec.relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Eclipse reference file is missing: {path}")
    if spec.source_format == "xlsx":
        events = _read_xlsx_events(path)
    elif spec.source_format == "event_report":
        events = _read_event_report(path)
    else:
        raise ValueError(f"Unsupported Eclipse reference format: {spec.source_format}")
    events = tuple(
        event
        for event in events
        if event.reference_epoch is not None
        and spec.coverage_start_utc <= event.reference_epoch < spec.coverage_end_utc
    )
    if not events:
        raise ValueError(f"No usable Eclipse events were found in {path.name}.")
    return EclipseReferenceDataset(spec=spec, events=events)


def _event_epoch(event):
    return next(
        (
            value
            for value in (
                getattr(event, "penumbra_entry_utc", None),
                getattr(event, "umbra_entry_utc", None),
                getattr(event, "center_utc", None),
                getattr(event, "umbra_exit_utc", None),
                getattr(event, "penumbra_exit_utc", None),
            )
            if value is not None
        ),
        None,
    )


def _event_body(event):
    return str(getattr(event, "shadow_body", "EARTH")).upper()


def _delta_seconds(output_value, reference_value):
    if output_value is None or reference_value is None:
        return None
    return float((output_value - reference_value).total_seconds())


def _duration_seconds(event):
    value = getattr(event, "total_duration_seconds", None)
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def compare_eclipse_events(
    output_events,
    dataset_id,
    *,
    tolerance_seconds=120.0,
    pairing_window_seconds=43200.0,
):
    """Pair output/reference events and calculate signed UTC contact deltas."""

    dataset = load_eclipse_reference_dataset(dataset_id)
    tolerance_seconds = float(tolerance_seconds)
    pairing_window_seconds = float(pairing_window_seconds)
    if tolerance_seconds < 0.0 or pairing_window_seconds <= 0.0:
        raise ValueError("Comparison tolerances must be non-negative.")

    reference_bodies = {event.shadow_body for event in dataset.events}
    candidates = []
    for output_number, output_event in enumerate(output_events, start=1):
        epoch = _event_epoch(output_event)
        if epoch is None:
            continue
        if epoch.tzinfo is None:
            raise ValueError("Output Eclipse event times must be timezone-aware.")
        if not (
            dataset.spec.coverage_start_utc
            <= epoch.astimezone(timezone.utc)
            < dataset.spec.coverage_end_utc
        ):
            continue
        if _event_body(output_event) not in reference_bodies:
            continue
        candidates.append((output_number, output_event))

    unused_output_indexes = set(range(len(candidates)))
    rows = []
    for reference_event in dataset.events:
        reference_epoch = reference_event.reference_epoch
        nearest_index = None
        nearest_distance = None
        for candidate_index in unused_output_indexes:
            _output_number, output_event = candidates[candidate_index]
            if _event_body(output_event) != reference_event.shadow_body:
                continue
            output_epoch = _event_epoch(output_event)
            distance = abs((output_epoch - reference_epoch).total_seconds())
            if nearest_distance is None or distance < nearest_distance:
                nearest_index = candidate_index
                nearest_distance = distance

        if nearest_index is None or nearest_distance > pairing_window_seconds:
            rows.append(
                EclipseComparisonRow(
                    status="MISSING OUTPUT",
                    shadow_body=reference_event.shadow_body,
                    reference_event_number=reference_event.event_number,
                    output_event_number=None,
                    reference_event=reference_event,
                    output_event=None,
                    penumbra_entry_delta_seconds=None,
                    umbra_entry_delta_seconds=None,
                    umbra_exit_delta_seconds=None,
                    penumbra_exit_delta_seconds=None,
                    total_duration_delta_seconds=None,
                )
            )
            continue

        unused_output_indexes.remove(nearest_index)
        output_number, output_event = candidates[nearest_index]
        deltas = (
            _delta_seconds(
                getattr(output_event, "penumbra_entry_utc", None),
                reference_event.penumbra_entry_utc,
            ),
            _delta_seconds(
                getattr(output_event, "umbra_entry_utc", None),
                reference_event.umbra_entry_utc,
            ),
            _delta_seconds(
                getattr(output_event, "umbra_exit_utc", None),
                reference_event.umbra_exit_utc,
            ),
            _delta_seconds(
                getattr(output_event, "penumbra_exit_utc", None),
                reference_event.penumbra_exit_utc,
            ),
        )
        comparable = [abs(value) for value in deltas if value is not None]
        status = (
            "MATCH"
            if comparable and max(comparable) <= tolerance_seconds
            else "DIFFERENCE"
        )
        output_duration = _duration_seconds(output_event)
        reference_duration = reference_event.total_duration_seconds
        duration_delta = (
            None
            if output_duration is None or reference_duration is None
            else output_duration - reference_duration
        )
        rows.append(
            EclipseComparisonRow(
                status=status,
                shadow_body=reference_event.shadow_body,
                reference_event_number=reference_event.event_number,
                output_event_number=output_number,
                reference_event=reference_event,
                output_event=output_event,
                penumbra_entry_delta_seconds=deltas[0],
                umbra_entry_delta_seconds=deltas[1],
                umbra_exit_delta_seconds=deltas[2],
                penumbra_exit_delta_seconds=deltas[3],
                total_duration_delta_seconds=duration_delta,
            )
        )

    for candidate_index in sorted(unused_output_indexes):
        output_number, output_event = candidates[candidate_index]
        rows.append(
            EclipseComparisonRow(
                status="EXTRA OUTPUT",
                shadow_body=_event_body(output_event),
                reference_event_number=None,
                output_event_number=output_number,
                reference_event=None,
                output_event=output_event,
                penumbra_entry_delta_seconds=None,
                umbra_entry_delta_seconds=None,
                umbra_exit_delta_seconds=None,
                penumbra_exit_delta_seconds=None,
                total_duration_delta_seconds=None,
            )
        )
    rows.sort(
        key=lambda row: (
            _event_epoch(row.reference_event or row.output_event)
            or datetime.max.replace(tzinfo=timezone.utc),
            row.status,
        )
    )
    return EclipseReferenceComparison(
        dataset=dataset,
        tolerance_seconds=tolerance_seconds,
        rows=tuple(rows),
    )


def _contact_conditioning(output_event):
    """Return the model event's contact conditioning label, if it has one."""

    if output_event is None:
        return ""
    return str(getattr(output_event, "conditioning", "") or "")


def _contact_sensitivity(output_event):
    """Return the model event's least certain contact, seconds per mdeg."""

    if output_event is None:
        return None
    value = getattr(output_event, "worst_contact_sensitivity", None)
    if value is None or not math.isfinite(float(value)):
        return None
    return float(value)


def _csv_datetime(value):
    if value is None:
        return ""
    return format_csv_utc(value)


def _csv_number(value):
    return "" if value is None else f"{float(value):.6f}"


def save_eclipse_reference_comparison_csv(comparison, file_path):
    output_path = Path(file_path)
    if output_path.suffix.lower() != ".csv":
        output_path = output_path.with_suffix(".csv")
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "Status",
                "ShadowBody",
                "ReferenceEvent",
                "OutputEvent",
                "ReferencePenumbraEntryUTC",
                "OutputPenumbraEntryUTC",
                "PenumbraEntryDeltaSeconds",
                "ReferenceUmbraEntryUTC",
                "OutputUmbraEntryUTC",
                "UmbraEntryDeltaSeconds",
                "ReferenceUmbraExitUTC",
                "OutputUmbraExitUTC",
                "UmbraExitDeltaSeconds",
                "ReferencePenumbraExitUTC",
                "OutputPenumbraExitUTC",
                "PenumbraExitDeltaSeconds",
                "ReferenceDurationSeconds",
                "OutputDurationSeconds",
                "DurationDeltaSeconds",
                "ToleranceSeconds",
                "ReferenceDataset",
                "ReferenceSourceFile",
                "FinalRmsContactErrorSeconds",
                "MeanAbsoluteContactErrorSeconds",
                "MaximumAbsoluteContactErrorSeconds",
                "MissingOutputEvents",
                "ExtraOutputEvents",
                "ContactConditioning",
                "WorstContactSensitivitySecondsPerMillidegree",
            )
        )
        for row in comparison.rows:
            reference = row.reference_event
            output = row.output_event
            writer.writerow(
                (
                    row.status,
                    row.shadow_body,
                    "" if row.reference_event_number is None else row.reference_event_number,
                    "" if row.output_event_number is None else row.output_event_number,
                    _csv_datetime(None if reference is None else reference.penumbra_entry_utc),
                    _csv_datetime(None if output is None else getattr(output, "penumbra_entry_utc", None)),
                    _csv_number(row.penumbra_entry_delta_seconds),
                    _csv_datetime(None if reference is None else reference.umbra_entry_utc),
                    _csv_datetime(None if output is None else getattr(output, "umbra_entry_utc", None)),
                    _csv_number(row.umbra_entry_delta_seconds),
                    _csv_datetime(None if reference is None else reference.umbra_exit_utc),
                    _csv_datetime(None if output is None else getattr(output, "umbra_exit_utc", None)),
                    _csv_number(row.umbra_exit_delta_seconds),
                    _csv_datetime(None if reference is None else reference.penumbra_exit_utc),
                    _csv_datetime(None if output is None else getattr(output, "penumbra_exit_utc", None)),
                    _csv_number(row.penumbra_exit_delta_seconds),
                    _csv_number(None if reference is None else reference.total_duration_seconds),
                    _csv_number(None if output is None else _duration_seconds(output)),
                    _csv_number(row.total_duration_delta_seconds),
                    _csv_number(comparison.tolerance_seconds),
                    comparison.dataset.spec.label,
                    comparison.dataset.spec.relative_path,
                    _csv_number(comparison.rms_contact_error_seconds),
                    _csv_number(
                        comparison.mean_absolute_contact_error_seconds
                    ),
                    _csv_number(
                        comparison.maximum_absolute_contact_error_seconds
                    ),
                    comparison.missing_output_count,
                    comparison.extra_output_count,
                    _contact_conditioning(output),
                    _csv_number(_contact_sensitivity(output)),
                )
            )
    return output_path


# ============================================================
# SIDE-BY-SIDE EXPORT
# ============================================================
#
# Spreadsheet imports may lay one event out per row as
# DATE | ENTER | CENTER | EXIT | DURATION | SHADOW.  The technical CSV above
# keeps machine-readable ISO stamps and repeats the run metadata on every row,
# which cannot be placed beside those workbooks in Excel.  This second export
# mirrors the workbook shape and puts reference, model and signed delta next to
# each other for every contact.


def _sbs_date(value):
    """Return the application-wide DD/MM/YYYY CSV date form."""

    if value is None:
        return ""
    return value.astimezone(timezone.utc).strftime("%d/%m/%Y")


def _sbs_clock(value):
    """Return HH:MM:SS rounded to the nearest second, as the workbooks do."""

    if value is None:
        return ""
    moment = value.astimezone(timezone.utc)
    if moment.microsecond >= 500000:
        moment += timedelta(seconds=1)
    return moment.strftime("%H:%M:%S")


def _sbs_duration(seconds):
    """Return the workbook's H:MM:SS duration form."""

    if seconds is None:
        return ""
    total = int(round(float(seconds)))
    sign = "-" if total < 0 else ""
    total = abs(total)
    return f"{sign}{total // 3600}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def _sbs_delta(value):
    """Return a signed delta in seconds, one decimal, empty when undefined."""

    if value is None:
        return ""
    return f"{float(value):+.1f}"


def save_eclipse_reference_side_by_side_csv(comparison, file_path):
    """Write the comparison in the supplied workbook's own row layout.

    Each contact appears as a REFERENCE / MODEL / delta triplet so the file can
    sit directly beside the original workbook in Excel.  Times are UTC and
    rounded to whole seconds for reading; the delta columns keep the precision.
    """

    output_path = Path(file_path)
    if output_path.suffix.lower() != ".csv":
        output_path = output_path.with_suffix(".csv")

    spec = comparison.dataset.spec

    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)

        writer.writerow((f"{spec.satellite} ECLIPSE PREDICTION — MODEL vs REFERENCE",))
        writer.writerow((spec.label,))
        writer.writerow((f"Source: {spec.relative_path}",))
        writer.writerow(())

        writer.writerow(
            (
                "",
                "",
                "ENTER PENUMBRA", "", "",
                "ENTER UMBRA", "", "",
                "EXIT UMBRA", "", "",
                "EXIT PENUMBRA", "", "",
                "DURATION", "", "",
                "", "",
            )
        )
        writer.writerow(
            (
                "DATE",
                "SHADOW",
                "REFERENCE", "MODEL", "DIFF [s]",
                "REFERENCE", "MODEL", "DIFF [s]",
                "REFERENCE", "MODEL", "DIFF [s]",
                "REFERENCE", "MODEL", "DIFF [s]",
                "REFERENCE", "MODEL", "DIFF [s]",
                "QUALITY",
                "STATUS",
            )
        )

        for row in comparison.rows:
            reference = row.reference_event
            output = row.output_event

            def side(attribute):
                return (
                    None if reference is None
                    else getattr(reference, attribute, None),
                    None if output is None
                    else getattr(output, attribute, None),
                )

            reference_epoch = (
                None if reference is None else reference.reference_epoch
            )
            if reference_epoch is None and output is not None:
                reference_epoch = _event_epoch(output)

            reference_penumbra_in, output_penumbra_in = side("penumbra_entry_utc")
            reference_umbra_in, output_umbra_in = side("umbra_entry_utc")
            reference_umbra_out, output_umbra_out = side("umbra_exit_utc")
            reference_penumbra_out, output_penumbra_out = side("penumbra_exit_utc")

            writer.writerow(
                (
                    _sbs_date(reference_epoch),
                    row.shadow_body,
                    _sbs_clock(reference_penumbra_in),
                    _sbs_clock(output_penumbra_in),
                    _sbs_delta(row.penumbra_entry_delta_seconds),
                    _sbs_clock(reference_umbra_in),
                    _sbs_clock(output_umbra_in),
                    _sbs_delta(row.umbra_entry_delta_seconds),
                    _sbs_clock(reference_umbra_out),
                    _sbs_clock(output_umbra_out),
                    _sbs_delta(row.umbra_exit_delta_seconds),
                    _sbs_clock(reference_penumbra_out),
                    _sbs_clock(output_penumbra_out),
                    _sbs_delta(row.penumbra_exit_delta_seconds),
                    _sbs_duration(
                        None if reference is None
                        else reference.total_duration_seconds
                    ),
                    _sbs_duration(
                        None if output is None else _duration_seconds(output)
                    ),
                    _sbs_delta(row.total_duration_delta_seconds),
                    _contact_conditioning(output),
                    row.status,
                )
            )

        writer.writerow(())
        writer.writerow(
            (
                "QUALITY = how sharply the limb margin crosses zero at the "
                "contacts. SHARP: a millidegree of geometric error moves the "
                "contact under 0.5 s. GRAZING: over 2 s, so a large residual "
                "there is expected rather than a defect.",
            )
        )
        writer.writerow(())
        writer.writerow(("SUMMARY",))
        for caption, value in (
            ("Tolerance [s]", _csv_number(comparison.tolerance_seconds)),
            ("Matched", comparison.matched_count),
            ("Different", comparison.difference_count),
            ("Missing in model", comparison.missing_output_count),
            ("Extra in model", comparison.extra_output_count),
            ("RMS contact error [s]", _csv_number(comparison.rms_contact_error_seconds)),
            (
                "Mean absolute error [s]",
                _csv_number(comparison.mean_absolute_contact_error_seconds),
            ),
            (
                "Maximum absolute error [s]",
                _csv_number(comparison.maximum_absolute_contact_error_seconds),
            ),
        ):
            writer.writerow((caption, value))

    return output_path
