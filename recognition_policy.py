"""Conservative matching and fresh-observation confirmation for recognition."""
import numpy as np


def match_identity(vector, known_faces, threshold=0.36, margin=0.08):
    # Use up to three enrollment images, including older small datasets.
    scores = []
    for name, vectors in known_faces.items():
        if len(vectors) == 0:
            continue
        distances = np.sort(np.clip(1 - vectors @ vector, 0, 2))
        scores.append((float(np.mean(distances[:3])), name))
    scores.sort()
    if not scores or scores[0][0] >= threshold:
        return "Unknown"
    if len(scores) > 1 and scores[1][0] - scores[0][0] < margin:
        return "Unknown"
    return scores[0][1]


class Confirmation:
    def __init__(self, duration=0.3, max_gap=2.5, min_samples=2):
        self.duration = duration
        self.max_gap = max_gap
        self.min_samples = min_samples
        self.reset()

    def reset(self):
        self.name = None
        self.started = None
        self.last_seen = None
        self.samples = 0

    def observe(self, name, captured_at):
        if self.last_seen is not None and captured_at <= self.last_seen:
            return None
        if name in (None, "Unknown", "Searching..."):
            self.reset()
            return None
        if (name != self.name or self.last_seen is None
                or captured_at - self.last_seen > self.max_gap):
            self.reset()
            self.name = name
            self.started = captured_at
        self.last_seen = captured_at
        self.samples += 1
        if (captured_at - self.started >= self.duration
                and self.samples >= self.min_samples):
            return name
        return None


def boxes_match(a, b):
    """Require overlapping faces; proximity alone can attach a name to a stranger."""
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, right-left) * max(0, bottom-top)
    area_a = max(0, a[2]-a[0]) * max(0, a[3]-a[1])
    area_b = max(0, b[2]-b[0]) * max(0, b[3]-b[1])
    union = area_a + area_b - intersection
    return union > 0 and intersection / union >= 0.3


class PersonTrack:
    def __init__(self, identity, box):
        self.id = identity
        self.box = self.display_box = box
        self.confirmation = Confirmation()
        self.name = 'Searching...'
        self.confirmed = None
        self.result_time = None
        self.mismatches = 0
        self.visible = True
        self.last_seen = None

    def clear(self):
        self.confirmation.reset()
        self.name = 'Searching...'
        self.confirmed = None
        self.result_time = None
        self.mismatches = 0

    def needs_recognition(self, now):
        return self.visible and (not self.confirmed or self.result_time is None
                                 or now - self.result_time >= 1.5)

    def label(self):
        if self.confirmed:
            return self.confirmed, (0, 255, 0)
        if self.name == 'Unknown':
            return 'Unknown', (0, 0, 255)
        return 'Searching...', (0, 200, 255)


class MultiFaceTracker:
    """Independent confirmation per visible face; IDs never get reused.

    Overlap associates detections, not identity. Ambiguous crossings start new
    tracks rather than transferring a confirmed name to another face.
    """
    def __init__(self, missing_grace=0.3):
        self.missing_grace = missing_grace
        self.tracks = {}
        self.next_id = 0

    def reset(self):
        self.tracks.clear()

    def update(self, boxes, now):
        # Brief detection gaps keep identity, but absent faces are not drawn.
        self.tracks = {i: t for i,t in self.tracks.items()
                       if t.visible or now - t.last_seen <= self.missing_grace}
        candidates = [[t for t in self.tracks.values() if boxes_match(t.box, box)]
                      for box in boxes]
        usage = {}
        for matches in candidates:
            for t in matches:
                usage[t.id] = usage.get(t.id, 0) + 1
        retained = {}
        ordered = []
        for box, matches in zip(boxes, candidates):
            if len(matches) == 1 and usage[matches[0].id] == 1:
                t = matches[0]
                t.display_box = tuple(round(.6*a + .4*b) for a,b in zip(t.display_box, box))
                t.box = box
            else:
                t = PersonTrack(self.next_id, box)
                self.next_id += 1
            if not t.confirmed and t.result_time is not None and now - t.result_time > t.confirmation.max_gap:
                t.clear()
            t.last_seen = now
            t.visible = True
            retained[t.id] = t
            ordered.append(t)
        for identity,t in self.tracks.items():
            # Ambiguous overlap invalidates a track; an empty frame gets grace.
            if identity not in retained and identity not in usage:
                t.visible = False
                if now - t.last_seen <= self.missing_grace:
                    retained[identity] = t
        self.tracks = retained
        return ordered

    def apply(self, answers, captured_at, now):
        # An enrolled name cannot belong to two visible people simultaneously.
        owners = {t.confirmed: t.id for t in self.tracks.values() if t.confirmed}
        counts = {}
        for _, name in answers:
            counts[name] = counts.get(name, 0) + 1
        confirmed = []
        for identity, name in answers:
            t = self.tracks.get(identity)
            if t is None or not t.visible or now - captured_at > t.confirmation.max_gap:
                continue
            if t.result_time is not None and captured_at <= t.result_time:
                continue
            if t.confirmed:
                t.result_time = captured_at
                if name == t.confirmed:
                    t.mismatches = 0
                else:
                    t.mismatches += 1
                    # One blurry observation never removes a confirmed label.
                    if t.mismatches >= 3:
                        owners.pop(t.confirmed, None)
                        t.clear()
                        t.name = 'Unknown'
                        t.result_time = captured_at
                continue
            if name not in ('Unknown', 'Searching...'):
                if name in owners and owners[name] != identity:
                    name = 'Unknown'
                elif counts[name] > 1 and name not in owners:
                    name = 'Unknown'
            previous = t.confirmed
            t.name = name
            t.result_time = captured_at
            t.confirmed = t.confirmation.observe(name, captured_at)
            if t.confirmed and t.confirmed != previous:
                owners[t.confirmed] = identity
                confirmed.append(t.confirmed)
        return confirmed
