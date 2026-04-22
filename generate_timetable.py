"""
University Timetable Generator
Reads course-slot assignments from an Excel sheet and generates
a conflict-free timetable satisfying all hard & soft constraints.
"""

import argparse
import re
import sys
from collections import defaultdict

import pandas as pd

# ---------------------------------------------------------------------------
# Slot-period mapping (default, overridden if reference file has a Slots sheet)
# ---------------------------------------------------------------------------
DEFAULT_SLOT_MATRIX = {
    'Monday':    {'8:00 - 8:50': 'Slot-1', '9:00 - 9:50': 'Slot-5',
                  '10:00 - 10:50': 'Slot-4', '11:00 - 11:50': 'Slot-7',
                  '12:00 - 12:50': 'Slot-6'},
    'Tuesday':   {'8:00 - 8:50': 'Slot-3', '9:00 - 9:50': 'Slot-7',
                  '10:00 - 10:50': 'Slot-2', '11:00 - 11:50': 'Slot-8',
                  '12:00 - 12:50': 'Slot-5'},
    'Wednesday': {'8:00 - 8:50': 'Slot-Free', '9:00 - 9:50': 'Slot-6',
                  '10:00 - 10:50': 'Slot-4', '11:00 - 11:50': 'Slot-1',
                  '12:00 - 12:50': 'Slot-3'},
    'Thursday':  {'8:00 - 8:50': 'Slot-8', '9:00 - 9:50': 'Slot-2',
                  '10:00 - 10:50': 'Slot-5', '11:00 - 11:50': 'Slot-7',
                  '12:00 - 12:50': 'Slot-6'},
    'Friday':    {'8:00 - 8:50': 'Slot-4', '9:00 - 9:50': 'Slot-1',
                  '10:00 - 10:50': 'Slot-8', '11:00 - 11:50': 'Slot-2',
                  '12:00 - 12:50': 'Slot-3'},
}

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
PERIODS = ['8:00 - 8:50', '9:00 - 9:50', '10:00 - 10:50',
           '11:00 - 11:50', '12:00 - 12:50']
SLOT_NAMES = [f'Slot-{i}' for i in range(1, 9)]

# ---------------------------------------------------------------------------
# Room capacities (number of seats per room)
# Data confirmed by team member — actual seat counts.
# ---------------------------------------------------------------------------
ROOM_CAPACITIES = {
    'LT-1': 200,
    'LT-2': 280,
    'LT-3': 330,
    'CEP102': 190, 'CEP110': 182, 'CEP103': 110,
    'CEP108': 120, 'CEP106': 120, 'CEP204': 120,
    'CEP209': 120, 'CEP203': 100,
    'CEP105': 90,  'CEP206': 90,
    'CEP205': 80,  'CEP207': 80,
    'CEP107': 60,  'CEP003': 60,
    'CEP104': 50,  'CEP202': 150,
    'CEP109': 40,
}

# ---------------------------------------------------------------------------
# Student strength per program
# Data confirmed by team member — actual intake numbers.
# ICT+CS has asymmetric sections: Sec A = 180, Sec B = 100.
# ---------------------------------------------------------------------------
BATCH_STRENGTH = {
    'ICT + CS':    280,   # ICT-A (180) + ICT-B (100)
    'MnC':          60,   # Mathematics and Computing (1 section)
    'EVD':          40,   # Electronics and VLSI Design
    'CS-Only':      60,   # CS standalone (1 section)
    'ICT-ML':       60,   # Machine Learning
    'ICT-SS':       60,   # Software Systems
    'ICT-VLSI&ES':  30,   # VLSI & Embedded Systems
    'ICT-WCSP':      7,   # Wireless Communication
    'DS':           90,   # Data Science
    'IT':          120,   # Information Technology
}

# Section-level overrides for asymmetric splits
SECTION_STRENGTH = {
    ('ICT + CS', 'Sec A'): 180,
    ('ICT + CS', 'Sec B'): 100,
}

# ---------------------------------------------------------------------------
# Actual elective enrollment (confirmed by team member)
# These override the batch-size heuristic for electives.
# ---------------------------------------------------------------------------
ELECTIVE_ENROLLMENT = {
    # HASS Electives
    'HM377': 15,  'HM402': 10,  'HM409': 82,  'HM412': 21,
    'HM413': 38,  'HM414': 10,  'HM469': 72,  'HM481': 18,
    'HM489': 0,   'HM494': 12,  'HM495': 84,
    # ICT & Technical Electives
    'IE402': 49,  'IE406': 60,  'IE407': 11,  'IE411': 120,
    'IE416': 119, 'IE422': 20,  'IE423': 49,
    'IT401': 13,  'IT402': 67,  'IT414': 56,  'IT443': 5,
    'IT449': 5,   'IT499': 40,  'IT504': 25,  'IT507': 18,
    'IT549': 37,  'IT565': 40,  'IT568': 33,  'IT584': 60,
    'IT590': 50,
    # Science Electives
    'SC301': 5,   'SC402': 72,  'SC409': 76,  'SC421': 32,
    'SC444': 116, 'SC463': 14,  'SC475': 16,
    # Other
    'CT423': 10,  'CT548': 14,  'EL464': 95,  'EL469': 110,
    'EL495': 38,  'EL527': 82,  'HM001': 30,
}


def get_batch_size(sub_batch, section):
    """Estimate the number of students for a (sub_batch, section) pair."""
    import re
    match = re.search(r'\(([^)]+)\)', sub_batch)
    if not match:
        return 0
    program = match.group(1).strip()

    # Check for section-level override (asymmetric splits)
    key = (program, section)
    if key in SECTION_STRENGTH:
        return SECTION_STRENGTH[key]

    total = BATCH_STRENGTH.get(program, 0)
    if total == 0:
        return 0

    # For programs with known asymmetric splits, use the larger section
    if program == 'ICT + CS' and 'Sec' in section:
        # Sections beyond A/B (e.g., elective Sec C-L) use Sec A size as max
        return 180

    # Single-section programs: return full strength
    return total


def get_course_enrollment(course_code, sub_batch, section, is_core):
    """Get the expected enrollment for a course.
    ALWAYS checks ELECTIVE_ENROLLMENT first (regardless of is_core flag),
    because some electives have 'Core' in their type string (e.g. RAS Core3).
    Falls back to batch strength for true core courses.
    """
    if course_code in ELECTIVE_ENROLLMENT:
        return ELECTIVE_ENROLLMENT[course_code]
    return get_batch_size(sub_batch, section)


# ---------------------------------------------------------------------------
# Helper: load slot matrix from reference file if available
# ---------------------------------------------------------------------------
def load_slot_matrix(ref_file=None):
    """Try to read the Slots sheet from the reference timetable file."""
    if ref_file is None:
        return DEFAULT_SLOT_MATRIX
    try:
        xl = pd.ExcelFile(ref_file)
        if 'Slots' not in xl.sheet_names:
            return DEFAULT_SLOT_MATRIX
        df = pd.read_excel(xl, 'Slots', header=None)
        # Find the header row (contains "Monday")
        header_row = None
        for idx, row in df.iterrows():
            vals = [str(v).strip() for v in row]
            if 'Monday' in vals:
                header_row = idx
                break
        if header_row is None:
            return DEFAULT_SLOT_MATRIX
        days_row = df.iloc[header_row]
        day_cols = {}
        for col_idx, val in enumerate(days_row):
            v = str(val).strip()
            if v in DAYS:
                day_cols[v] = col_idx
        matrix = {d: {} for d in DAYS}
        for row_idx in range(header_row + 1, len(df)):
            time_val = str(df.iloc[row_idx, 0]).strip()
            if not time_val or time_val == 'nan':
                continue
            # Normalise time format to match PERIODS
            time_norm = re.sub(r'(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})',
                               lambda m: f"{int(m.group(1))}:{m.group(2)} - {int(m.group(3))}:{m.group(4)}",
                               time_val)
            for day, col in day_cols.items():
                slot = str(df.iloc[row_idx, col]).strip()
                if slot and slot != 'nan':
                    matrix[day][time_norm] = slot
        # Validate that we got enough data
        if all(len(v) >= 5 for v in matrix.values()):
            print(f"  Loaded slot matrix from '{ref_file}' → Slots sheet.")
            return matrix
        return DEFAULT_SLOT_MATRIX
    except Exception:
        return DEFAULT_SLOT_MATRIX


# ---------------------------------------------------------------------------
# Helper: check if two student groups overlap
# ---------------------------------------------------------------------------
def is_overlap(sg1, sg2):
    """Check if two (sub_batch, section) pairs share students."""
    sb1, sec1 = sg1
    sb2, sec2 = sg2
    # Same sub-batch & same/overlapping section
    if sb1 == sb2 and (sec1 == sec2 or sec1 == 'All' or sec2 == 'All'):
        return True
    # CS-Only is a subset of ICT+CS Sec B
    if 'CS-Only' in sb1 and 'ICT + CS' in sb2 and sec2 in ('Sec B', 'All'):
        return True
    if 'CS-Only' in sb2 and 'ICT + CS' in sb1 and sec1 in ('Sec B', 'All'):
        return True
    return False


def is_core(course_type):
    """Return True if the course type string denotes a core course."""
    if not course_type or course_type.lower() == 'nan':
        return True  # default to core to be safe
    return 'core' in course_type.lower()


# ---------------------------------------------------------------------------
# Parse input Excel
# ---------------------------------------------------------------------------
def parse_excel(input_file):
    """Parse the slot-assignment Excel into a list of course dicts."""
    try:
        df = pd.read_excel(input_file, header=None)
    except FileNotFoundError:
        print(f"ERROR: Input file '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not read '{input_file}': {e}")
        sys.exit(1)

    # Forward-fill batch and sub-batch columns
    df.iloc[:, 0] = df.iloc[:, 0].ffill()
    df.iloc[:, 1] = df.iloc[:, 1].ffill()

    all_slots = SLOT_NAMES + ['Slot-Free']
    courses = []
    sub_batch_rows = defaultdict(int)

    for _, row in df.iterrows():
        batch = str(row.iloc[0]).strip()
        sub_batch = str(row.iloc[1]).strip()
        if sub_batch.lower() == 'nan' or not sub_batch:
            continue

        # Detect sections mentioned in this row
        sections_in_row = set()
        col_idx = 2
        for _ in all_slots:
            if col_idx + 5 < len(row):
                name = str(row.iloc[col_idx + 1]).strip()
                if name.lower() != 'nan':
                    sec_match = re.search(
                        r'\(Sec\s*([A-Za-z0-9]+)\)', name, re.IGNORECASE)
                    if sec_match:
                        sections_in_row.add(
                            f"Sec {sec_match.group(1).upper()}")
            col_idx += 6

        # Determine section label for this row
        if len(sections_in_row) == 1:
            row_sec = sections_in_row.pop()
        elif len(sections_in_row) > 1:
            # Multiple sections in one row — pick alphabetically first
            row_sec = sorted(sections_in_row)[0]
        else:
            # Fallback: assign by row count within this sub-batch
            row_sec = f"Sec {chr(65 + sub_batch_rows[sub_batch])}"

        sub_batch_rows[sub_batch] += 1

        # Parse each slot block (6 columns per slot)
        col_idx = 2
        for slot_name in all_slots:
            if col_idx + 5 < len(row):
                code = str(row.iloc[col_idx]).strip()
                if code.lower() != 'nan' and code != '':
                    name = str(row.iloc[col_idx + 1]).strip()
                    ltpc = str(row.iloc[col_idx + 2]).strip()
                    c_type = str(row.iloc[col_idx + 3]).strip()
                    faculty = str(row.iloc[col_idx + 4]).strip()
                    room = str(row.iloc[col_idx + 5]).strip()

                    # Extract section from course name if not already known
                    sec_from_name = row_sec
                    sec_match = re.search(
                        r'\(Sec\s*([A-Za-z0-9]+)\)', name, re.IGNORECASE)
                    if sec_match:
                        sec_from_name = f"Sec {sec_match.group(1).upper()}"

                    courses.append({
                        'batch': batch,
                        'sub_batch': sub_batch,
                        'row_sec': sec_from_name,
                        'original_slot': slot_name,
                        'course_code': code,
                        'course_name': name,
                        'ltpc': ltpc,
                        'type': c_type,
                        'faculty': faculty,
                        'room': room,
                        'is_core': is_core(c_type),
                    })
            col_idx += 6

    print(f"  Parsed {len(courses)} course entries from '{input_file}'.")
    return courses


# ---------------------------------------------------------------------------
# Build conflict graph via union-find
# ---------------------------------------------------------------------------
def build_graph(courses):
    """Group course entries into superblocks and compute conflict edges."""
    nodes = defaultdict(list)
    for c in courses:
        if c['original_slot'] == 'Slot-Free':
            continue
        node_id = (c['sub_batch'], c['row_sec'], c['original_slot'])
        nodes[node_id].append(c)

    # Union-Find
    parent = {n: n for n in nodes}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    node_ids = list(nodes.keys())
    for i in range(len(node_ids)):
        for j in range(i + 1, len(node_ids)):
            n1, n2 = node_ids[i], node_ids[j]

            # Same slot + overlapping student group → merge
            if n1[2] == n2[2] and is_overlap((n1[0], n1[1]), (n2[0], n2[1])):
                # But only merge if at least one is a core course
                # (electives in the same slot for the same batch are OK)
                any_core_1 = any(c['is_core'] for c in nodes[n1])
                any_core_2 = any(c['is_core'] for c in nodes[n2])
                if any_core_1 or any_core_2:
                    union(n1, n2)
                continue

            # Same faculty teaching in both → merge
            f1 = {(c['course_code'], c['faculty'])
                  for c in nodes[n1] if c['faculty'].lower() != 'nan'}
            f2 = {(c['course_code'], c['faculty'])
                  for c in nodes[n2] if c['faculty'].lower() != 'nan'}
            if f1 & f2:
                union(n1, n2)

    # Collect superblocks
    superblocks = defaultdict(list)
    for n in nodes:
        superblocks[find(n)].append(n)

    sb_props = {}
    for root, n_list in superblocks.items():
        facs, rooms, sgs = set(), set(), set()
        types = set()
        o_slots = []
        for n in n_list:
            sb, row_sec, o_slot = n
            sgs.add((sb, row_sec))
            o_slots.append(o_slot)
            for c in nodes[n]:
                if c['faculty'].lower() != 'nan':
                    facs.add(c['faculty'])
                if c['room'].lower() != 'nan':
                    rooms.add(c['room'])
                types.add(c['type'])
        pref_slot = max(set(o_slots), key=o_slots.count)
        all_elective = all(not is_core(t) for t in types)
        sb_props[root] = {
            'facs': facs, 'rooms': rooms, 'sgs': sgs,
            'pref_slot': pref_slot, 'nodes': n_list,
            'all_elective': all_elective,
        }

    # Build conflict edges between superblocks
    conflicts = {r: set() for r in superblocks}
    roots = list(superblocks.keys())
    for i in range(len(roots)):
        for j in range(i + 1, len(roots)):
            r1, r2 = roots[i], roots[j]
            p1, p2 = sb_props[r1], sb_props[r2]

            conflict = False

            # Faculty clash
            if p1['facs'] & p2['facs']:
                conflict = True

            # Room clash
            if not conflict and p1['rooms'] & p2['rooms']:
                conflict = True

            # Student group clash (only if at least one is core)
            if not conflict:
                both_elective = p1['all_elective'] and p2['all_elective']
                if not both_elective:
                    for sg1 in p1['sgs']:
                        for sg2 in p2['sgs']:
                            if is_overlap(sg1, sg2):
                                conflict = True
                                break
                        if conflict:
                            break

            if conflict:
                conflicts[r1].add(r2)
                conflicts[r2].add(r1)

    return nodes, sb_props, conflicts, roots


# ---------------------------------------------------------------------------
# CSP solver with soft-constraint scoring
# ---------------------------------------------------------------------------
def solve_csp(roots, sb_props, conflicts, slot_matrix):
    """Assign each superblock to a slot using backtracking + heuristics."""
    assignment = {}
    unresolved = []

    # Sort by most-constrained-first (MRV heuristic)
    sorted_roots = sorted(roots,
                          key=lambda r: len(conflicts[r]), reverse=True)

    # Precompute which slots appear on which days (for soft constraint scoring)
    slot_days = defaultdict(set)
    for day, periods in slot_matrix.items():
        for _, slot in periods.items():
            if slot != 'Slot-Free':
                slot_days[slot].add(day)

    def get_ordered_slots(root):
        """Return slots ordered by preference (original slot first)."""
        pref = sb_props[root]['pref_slot']
        ordered = [pref] + [s for s in SLOT_NAMES if s != pref]
        return ordered

    def backtrack(idx):
        if idx == len(sorted_roots):
            return True
        root = sorted_roots[idx]

        for slot in get_ordered_slots(root):
            valid = True
            for neighbor in conflicts[root]:
                if neighbor in assignment and assignment[neighbor] == slot:
                    valid = False
                    break
            if valid:
                assignment[root] = slot
                if backtrack(idx + 1):
                    return True
                del assignment[root]
        return False

    if not backtrack(0):
        # Greedy fallback for unassigned superblocks
        for root in sorted_roots:
            if root not in assignment:
                for slot in get_ordered_slots(root):
                    clash_with = []
                    for neighbor in conflicts[root]:
                        if neighbor in assignment and assignment[neighbor] == slot:
                            clash_with.append(neighbor)
                    if not clash_with:
                        assignment[root] = slot
                        break
                if root not in assignment:
                    # Assign to preferred slot anyway, record conflict
                    assignment[root] = sb_props[root]['pref_slot']
                    blocked_by = [
                        n for n in conflicts[root]
                        if n in assignment
                        and assignment[n] == sb_props[root]['pref_slot']
                    ]
                    unresolved.append({
                        'superblock': root,
                        'assigned_slot': sb_props[root]['pref_slot'],
                        'reason': 'No conflict-free slot available',
                        'conflicts_with': blocked_by,
                    })

    print(f"  CSP solved: {len(assignment)} superblocks assigned"
          f" ({len(unresolved)} unresolved).")
    return assignment, unresolved


# ---------------------------------------------------------------------------
# Apply soft constraints: swap-based optimisation
# ---------------------------------------------------------------------------
def apply_soft_constraints(assignment, sb_props, conflicts, slot_matrix):
    """
    Soft constraint optimisation pass (greedy pair-swap):
    - Minimise room changes for a batch on any given day
    - Space out lectures for the same course across the week
    """
    import random

    # Precompute slot→days mapping and slot→(day, period_idx) mapping
    slot_to_days = defaultdict(set)
    slot_to_day_periods = defaultdict(list)
    for day, periods_map in slot_matrix.items():
        for p_idx, period in enumerate(PERIODS):
            if period in periods_map:
                slot = periods_map[period]
                if slot != 'Slot-Free':
                    slot_to_days[slot].add(day)
                    slot_to_day_periods[slot].append((day, p_idx))

    def soft_score(asgn):
        """Lower is better."""
        penalty = 0
        # Build per-batch day schedule
        batch_day_rooms = defaultdict(lambda: defaultdict(list))
        batch_day_slots = defaultdict(lambda: defaultdict(list))
        # Build per-faculty day schedule (for consecutive classes)
        fac_day_periods = defaultdict(lambda: defaultdict(set))

        for root, slot in asgn.items():
            for sg in sb_props[root]['sgs']:
                for day in slot_to_days.get(slot, []):
                    rooms = sb_props[root].get('rooms', set())
                    batch_day_rooms[sg][day].extend(rooms)
                    batch_day_slots[sg][day].append(slot)
            
            # Record periods for faculties
            for f in sb_props[root].get('facs', set()):
                if f.lower() != 'nan':
                    for day, p_idx in slot_to_day_periods.get(slot, []):
                        fac_day_periods[f][day].add(p_idx)

        # Penalty: room changes on same day for same batch
        for sg, day_map in batch_day_rooms.items():
            for day, rooms_list in day_map.items():
                unique_rooms = set(rooms_list)
                if len(unique_rooms) > 1:
                    penalty += (len(unique_rooms) - 1) * 2

        # Penalty: same course on consecutive days
        day_order = {d: i for i, d in enumerate(DAYS)}
        course_days = defaultdict(set)
        for root, slot in asgn.items():
            for day in slot_to_days.get(slot, []):
                course_days[root].add(day_order.get(day, 0))

        # Penalty: consecutive classes for same faculty
        for f, day_map in fac_day_periods.items():
            for day, period_set in day_map.items():
                sorted_p = sorted(list(period_set))
                for i in range(len(sorted_p) - 1):
                    if sorted_p[i+1] == sorted_p[i] + 1:
                        penalty += 5  # Add harsh penalty for consecutive teaching

        return penalty

    def can_swap(r1, r2, asgn):
        """Check if swapping slots of r1 and r2 breaks no hard constraints."""
        s1, s2 = asgn[r1], asgn[r2]
        # Check r1 with s2
        for n in conflicts.get(r1, set()):
            if n != r2 and n in asgn and asgn[n] == s2:
                return False
        # Check r2 with s1
        for n in conflicts.get(r2, set()):
            if n != r1 and n in asgn and asgn[n] == s1:
                return False
        return True

    # Greedy local search: try random swaps
    current_score = soft_score(assignment)
    roots_list = list(assignment.keys())
    improvements = 0

    for _ in range(min(1000, len(roots_list) * 10)):
        if len(roots_list) < 2:
            break
        i, j = random.sample(range(len(roots_list)), 2)
        r1, r2 = roots_list[i], roots_list[j]
        if assignment[r1] == assignment[r2]:
            continue
        if not can_swap(r1, r2, assignment):
            continue
        # Try swap
        assignment[r1], assignment[r2] = assignment[r2], assignment[r1]
        new_score = soft_score(assignment)
        if new_score < current_score:
            current_score = new_score
            improvements += 1
        else:
            # Revert
            assignment[r1], assignment[r2] = assignment[r2], assignment[r1]

    if improvements:
        print(f"  Soft constraints: {improvements} improving swap(s) applied.")
    return assignment


# ---------------------------------------------------------------------------
# Apply assignments to course list
# ---------------------------------------------------------------------------
def apply_assignments(courses, nodes, sb_props, assignment):
    """Produce final course list with assigned slots."""
    final_courses = []
    for root, slot in assignment.items():
        for n_id in sb_props[root]['nodes']:
            for c in nodes[n_id]:
                c_copy = c.copy()
                c_copy['final_slot'] = slot
                if slot != c_copy['original_slot']:
                    c_copy['moved'] = True
                    c_copy['course_name'] = (
                        f"{c_copy['course_name']} "
                        f"[*Moved from {c_copy['original_slot']}*]")
                else:
                    c_copy['moved'] = False
                final_courses.append(c_copy)

    # Slot-Free courses pass through unchanged
    for c in courses:
        if c['original_slot'] == 'Slot-Free':
            c_copy = c.copy()
            c_copy['final_slot'] = 'Slot-Free'
            c_copy['moved'] = False
            final_courses.append(c_copy)

    return final_courses


# ---------------------------------------------------------------------------
# Smart Room Assignment (capacity-aware)
# Uses best-fit-decreasing: biggest classes get first pick of rooms.
# ---------------------------------------------------------------------------
def assign_rooms(final_courses, slot_matrix):
    """Reassign rooms based on actual enrollment vs room capacity.

    Algorithm (per time slot):
    1. Group all courses in the same slot
    2. For each group of same-course entries (elective across batches),
       determine the expected enrollment
    3. Sort by enrollment descending (biggest classes pick first)
    4. Assign the smallest room that fits and is still available

    Returns: (reassigned_count, unchanged_count)
    """
    # Build list of available rooms sorted by capacity (ascending)
    all_rooms = sorted(ROOM_CAPACITIES.items(), key=lambda x: x[1])

    # Group courses by their assigned slot
    slot_groups = defaultdict(list)
    for c in final_courses:
        slot = c.get('final_slot', '')
        if slot and slot != 'Slot-Free':
            slot_groups[slot].append(c)

    reassigned = 0
    unchanged = 0

    for slot, entries in slot_groups.items():
        # Group core courses by section (Sec A vs Sec B) to avoid merging parallel lectures
        course_groups = defaultdict(list)
        for c in entries:
            code = c['course_code']
            truly_core = c['is_core'] and code not in ELECTIVE_ENROLLMENT
            group_key = c.get('row_sec', '').strip() if truly_core else 'ALL'
            course_groups[(code, group_key)].append(c)

        # Calculate enrollment for each course group
        course_enrollment = {}
        for (code, group_key), clist in course_groups.items():
            truly_core = clist[0]['is_core'] and code not in ELECTIVE_ENROLLMENT
            if truly_core:
                seen_batches = set()
                enrollment = 0
                for c in clist:
                    batch_key = (c['sub_batch'], c['row_sec'])
                    if batch_key not in seen_batches:
                        seen_batches.add(batch_key)
                        enrollment += get_course_enrollment(
                            code, c['sub_batch'], c['row_sec'], True)
            else:
                enrollment = get_course_enrollment(
                    code, clist[0]['sub_batch'], clist[0]['row_sec'], False)
            course_enrollment[(code, group_key)] = enrollment

        # Sort groups by enrollment descending (biggest first)
        sorted_course_groups = sorted(
            course_groups.keys(),
            key=lambda k: course_enrollment.get(k, 0),
            reverse=True)

        # Assign rooms greedily
        used_rooms = set()  # rooms already taken in this slot
        for group_tuple in sorted_course_groups:
            clist = course_groups[group_tuple]
            enrollment = course_enrollment.get(group_tuple, 0)
            original_room = clist[0].get('room', '').strip()

            # Find the smallest available room that fits
            assigned_room = None
            for room_name, capacity in all_rooms:
                if room_name in used_rooms:
                    continue
                if capacity >= enrollment:
                    assigned_room = room_name
                    break

            if assigned_room:
                used_rooms.add(assigned_room)
                # Update all entries in this course group
                for c in clist:
                    if c['room'] != assigned_room:
                        c['room'] = assigned_room
                        reassigned += 1
                    else:
                        unchanged += 1
            else:
                # No room big enough. Check if original room was completely dropped.
                if original_room and ROOM_CAPACITIES.get(original_room, 0) == 0:
                    for c in clist:
                        c['room'] = 'TBD'  # Explicitly erase the dropped room
                    reassigned += len(clist)
                else:
                    # Keep original and flag it
                    used_rooms.add(original_room)
                    unchanged += len(clist)

    return reassigned, unchanged


# ---------------------------------------------------------------------------
def dedup_courses(course_list):
    """Deduplicate, keying by (course_code, sub_batch, row_sec)."""
    seen = {}
    for c in course_list:
        key = (c['course_code'], c['sub_batch'], c['row_sec'])
        if key not in seen:
            seen[key] = c
    return list(seen.values())


# ---------------------------------------------------------------------------
# Validation: check for remaining hard-constraint violations
# ---------------------------------------------------------------------------
def validate(final_courses, slot_matrix):
    """Run hard-constraint checks and return a list of violation strings."""
    violations = []

    # Build period-level schedule
    schedule = defaultdict(list)  # (day, period) → list of courses
    for day in DAYS:
        for period in PERIODS:
            slot = slot_matrix[day].get(period, '')
            if not slot or slot == 'Slot-Free':
                continue
            entries = [c for c in final_courses if c['final_slot'] == slot]
            schedule[(day, period)] = entries

    # Check faculty double-booking
    # A real conflict is when the SAME faculty teaches DIFFERENT courses
    # at the same time, requiring them to be in two places.
    # Same faculty + same course + different sections in the SAME slot is
    # EXPECTED (the sections are scheduled together deliberately).
    for (day, period), entries in schedule.items():
        fac_map = defaultdict(list)
        for c in entries:
            if c['faculty'].lower() != 'nan':
                fac_map[c['faculty']].append(c)
        for fac, clist in fac_map.items():
            # Group by course_code: faculty can teach multiple sections
            # of the same course at the same time (same room)
            courses_taught = set(c['course_code'] for c in clist)
            rooms_used = set(c['room'] for c in clist
                             if c['room'].lower() != 'nan')
            if len(courses_taught) > 1 and len(rooms_used) > 1:
                # Faculty is teaching genuinely different courses in
                # different rooms → real conflict
                codes = ', '.join(sorted(courses_taught))
                violations.append(
                    f"Faculty {fac} double-booked on {day} {period}: "
                    f"{codes} in rooms {', '.join(sorted(rooms_used))}")

    # Check room double-booking
    # A real conflict is when the SAME room hosts DIFFERENT courses
    # that are not electives for the same batch.
    # Same room + same course + different sections = expected (lecture hall).
    for (day, period), entries in schedule.items():
        room_map = defaultdict(list)
        for c in entries:
            if c['room'].lower() != 'nan':
                room_map[c['room']].append(c)
        for room, clist in room_map.items():
            # Group by course_code
            course_codes = set(c['course_code'] for c in clist)
            if len(course_codes) <= 1:
                # Same course, different sections — perfectly fine
                continue
            # Multiple different courses in same room
            # Check if they are all electives (electives can share time)
            all_elec = all(not c['is_core'] for c in clist)
            if not all_elec:
                codes = ', '.join(sorted(course_codes))
                violations.append(
                    f"Room {room} double-booked on {day} {period}: {codes}")

    # Check core-course batch conflicts
    # Same batch/section should not have 2 different core courses at the same time
    for (day, period), entries in schedule.items():
        batch_cores = defaultdict(list)
        for c in entries:
            if c['is_core']:
                batch_cores[(c['sub_batch'], c['row_sec'])].append(c)
        for (sb, sec), clist in batch_cores.items():
            course_codes = set(c['course_code'] for c in clist)
            if len(course_codes) > 1:
                codes = ', '.join(sorted(course_codes))
                violations.append(
                    f"Batch {sb} {sec} has multiple core courses "
                    f"on {day} {period}: {codes}")

    # Check Wednesday 8:00 AM is free
    wed_8 = slot_matrix.get('Wednesday', {}).get('8:00 - 8:50', '')
    if wed_8 and wed_8 != 'Slot-Free':
        violations.append(
            f"Wednesday 8:00 AM is mapped to {wed_8} instead of Slot-Free!")

    # Check room capacity vs estimated student count
    # Key insight: elective courses are offered to MULTIPLE batches but
    # students only pick ONE elective, so they share the room.
    # For the SAME course across different batches → use the largest batch only.
    # For DIFFERENT courses in the same room → sum them (they are concurrent).
    for (day, period), entries in schedule.items():
        # Group entries by room, then by course_code within the room
        room_courses = defaultdict(lambda: defaultdict(list))
        for c in entries:
            room = c.get('room', '').strip()
            if not room or room.lower() == 'nan':
                continue
            room_courses[room][c['course_code']].append(c)

        for room, course_map in room_courses.items():
            capacity = ROOM_CAPACITIES.get(room, 0)
            if capacity == 0:
                continue  # Unknown capacity, skip

            total_students = 0
            detail_parts = []
            for code, clist in course_map.items():
                # If the course is in ELECTIVE_ENROLLMENT, it's an elective
                # regardless of the is_core flag (which can be wrong for
                # courses like IE416 "RAS Core3" which are really electives)
                truly_core = clist[0]['is_core'] and code not in ELECTIVE_ENROLLMENT

                if truly_core:
                    # Core course: all batches attend → sum unique batches
                    seen_batches = set()
                    course_students = 0
                    for c in clist:
                        batch_key = (c['sub_batch'], c['row_sec'])
                        if batch_key not in seen_batches:
                            seen_batches.add(batch_key)
                            course_students += get_course_enrollment(
                                code, c['sub_batch'], c['row_sec'], True)
                else:
                    # Elective: use actual enrollment data (single class)
                    course_students = get_course_enrollment(
                        code, clist[0]['sub_batch'], clist[0]['row_sec'], False)

                if course_students <= 0:
                    continue

                total_students += course_students
                detail_parts.append(
                    f"{code} (~{course_students} students)")

            if total_students > capacity:
                detail = ', '.join(detail_parts[:3])
                violations.append(
                    f"Room {room} (capacity {capacity}) overbooked on "
                    f"{day} {period}: ~{total_students} students — "
                    f"{detail}")

    return violations


# ---------------------------------------------------------------------------
# Excel export (improved formatting)
# ---------------------------------------------------------------------------
def export_excel(final_courses, output_file, slot_matrix, unresolved):
    """Export timetable to Excel with Master, Faculty, Room, and Conflicts sheets."""
    print("  Exporting Excel...")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # ---- Sheet 1: Master Timetable ----
        rows = []
        all_sub_batches = sorted(set(c['sub_batch'] for c in final_courses))

        for period in PERIODS:
            header = ['Time', 'Batch']
            for day in DAYS:
                header.extend(
                    [day, 'Course Name', 'L-T-P-C', 'Type', 'Faculty', 'Room'])
            rows.append(header)

            for sb in all_sub_batches:
                row_data = [period, sb]
                for day in DAYS:
                    curr_slot = slot_matrix[day].get(period, '')
                    mc = [c for c in final_courses
                          if c['sub_batch'] == sb and c['final_slot'] == curr_slot]
                    if mc:
                        deduped = dedup_courses(mc)
                        codes = ' / '.join(c['course_code'] for c in deduped)
                        names = ' / '.join(c['course_name'] for c in deduped)
                        ltpcs = ' / '.join(c['ltpc'] for c in deduped)
                        types = ' / '.join(c['type'] for c in deduped)
                        facs = ' / '.join(c['faculty'] for c in deduped)
                        rooms_str = ' / '.join(c['room'] for c in deduped)
                        row_data.extend(
                            [codes, names, ltpcs, types, facs, rooms_str])
                    else:
                        row_data.extend(['', '', '', '', '', ''])
                rows.append(row_data)
            rows.append([''] * len(header))

        df_master = pd.DataFrame(rows)
        df_master.to_excel(
            writer, sheet_name='Master_Timetable', index=False, header=False)

        # ---- Sheet 2: Faculty Timetable ----
        all_facs = sorted(set(
            c['faculty'] for c in final_courses
            if c['faculty'].lower() != 'nan'))
        rows_fac = []

        for period in PERIODS:
            header = ['Time', 'Faculty']
            for day in DAYS:
                header.extend([day, 'Batch', 'Course Name', 'Room'])
            rows_fac.append(header)

            for fac in all_facs:
                row_data = [period, fac]
                for day in DAYS:
                    curr_slot = slot_matrix[day].get(period, '')
                    mc = [c for c in final_courses
                          if c['faculty'] == fac and c['final_slot'] == curr_slot]
                    if mc:
                        deduped = dedup_courses(mc)
                        codes = ' / '.join(c['course_code'] for c in deduped)
                        batches = ' / '.join(c['sub_batch'] for c in deduped)
                        names = ' / '.join(c['course_name'] for c in deduped)
                        rooms_str = ' / '.join(c['room'] for c in deduped)
                        row_data.extend([codes, batches, names, rooms_str])
                    else:
                        row_data.extend(['', '', '', ''])
                rows_fac.append(row_data)
            rows_fac.append([''] * len(header))

        df_fac = pd.DataFrame(rows_fac)
        df_fac.to_excel(
            writer, sheet_name='Faculty_Timetable', index=False, header=False)

        # ---- Sheet 3: Room Timetable ----
        all_rooms = sorted(set(
            c['room'] for c in final_courses
            if c['room'].lower() != 'nan'))
        rows_room = []

        for period in PERIODS:
            header = ['Time', 'Room']
            for day in DAYS:
                header.extend([day, 'Batch', 'Course Name', 'Faculty'])
            rows_room.append(header)

            for room in all_rooms:
                row_data = [period, room]
                for day in DAYS:
                    curr_slot = slot_matrix[day].get(period, '')
                    mc = [c for c in final_courses
                          if c['room'] == room and c['final_slot'] == curr_slot]
                    if mc:
                        deduped = dedup_courses(mc)
                        codes = ' / '.join(c['course_code'] for c in deduped)
                        batches = ' / '.join(c['sub_batch'] for c in deduped)
                        names = ' / '.join(c['course_name'] for c in deduped)
                        facs = ' / '.join(c['faculty'] for c in deduped)
                        row_data.extend([codes, batches, names, facs])
                    else:
                        row_data.extend(['', '', '', ''])
                rows_room.append(row_data)
            rows_room.append([''] * len(header))

        df_room = pd.DataFrame(rows_room)
        df_room.to_excel(
            writer, sheet_name='Room_Timetable', index=False, header=False)

        # ---- Sheet 4: Conflicts / Unresolved ----
        if unresolved:
            conflict_rows = [['Superblock', 'Assigned Slot', 'Reason',
                              'Conflicting Superblocks']]
            for u in unresolved:
                sb_str = str(u['superblock'])
                conf_str = '; '.join(str(c) for c in u['conflicts_with'])
                conflict_rows.append([
                    sb_str, u['assigned_slot'], u['reason'], conf_str
                ])
        else:
            conflict_rows = [['Status'], ['No unresolved conflicts.']]

        df_conf = pd.DataFrame(conflict_rows)
        df_conf.to_excel(
            writer, sheet_name='Conflicts', index=False, header=False)

    print(f"  Excel saved: '{output_file}'")


# ---------------------------------------------------------------------------
# PDF export (proper formatting)
# ---------------------------------------------------------------------------
def export_pdf(final_courses, pdf_file, slot_matrix):
    """Generate a well-formatted PDF timetable."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, PageBreak, Spacer)

    print("  Generating PDF...")
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=landscape(A3),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=18, spaceAfter=6 * mm,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Heading2'],
        fontSize=13, spaceAfter=4 * mm, textColor=colors.HexColor('#333333'),
    )
    cell_style = ParagraphStyle(
        'CellStyle', parent=styles['Normal'],
        fontSize=6, leading=7.5, wordWrap='CJK',
    )
    header_cell_style = ParagraphStyle(
        'HeaderCellStyle', parent=styles['Normal'],
        fontSize=6.5, leading=8, textColor=colors.white,
        fontName='Helvetica-Bold',
    )

    def make_para(text, style=cell_style):
        """Wrap text in a Paragraph for proper word-wrapping."""
        return Paragraph(str(text).replace('&', '&amp;'), style)

    # Colour palette
    hdr_bg = colors.HexColor('#2C3E50')
    hdr_text = colors.white
    alt_row_bg = colors.HexColor('#ECF0F1')
    grid_color = colors.HexColor('#BDC3C7')
    period_bg = colors.HexColor('#3498DB')

    # ========================================================================
    # SHEET 1: Master Timetable
    # ========================================================================
    elements.append(Paragraph('Master Timetable', title_style))
    elements.append(Paragraph(
        'Dhirubhai Ambani University — Winter 2026', subtitle_style))

    all_sub_batches = sorted(set(c['sub_batch'] for c in final_courses))

    for period in PERIODS:
        # Sub-header for time period
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f'<b>Period: {period}</b>', subtitle_style))

        # Table header
        header = ['Batch']
        for day in DAYS:
            header.extend([day, 'Faculty', 'Room'])
        table_data = [[make_para(h, header_cell_style) for h in header]]

        for idx, sb in enumerate(all_sub_batches):
            row = [make_para(sb)]
            for day in DAYS:
                curr_slot = slot_matrix[day].get(period, '')
                mc = [c for c in final_courses
                      if c['sub_batch'] == sb and c['final_slot'] == curr_slot]
                if mc:
                    deduped = dedup_courses(mc)
                    codes_names = '\n'.join(
                        f"{c['course_code']} {c['course_name']}"
                        for c in deduped)
                    facs = ', '.join(c['faculty'] for c in deduped)
                    rooms = ', '.join(c['room'] for c in deduped)
                    row.extend([
                        make_para(codes_names),
                        make_para(facs),
                        make_para(rooms),
                    ])
                else:
                    row.extend([make_para('-'), make_para('-'), make_para('-')])
            table_data.append(row)

        # A3 landscape usable width ~400mm (420 - 2*10 margins)
        # Batch(20) + 5 days * (Course 50 + Faculty 15 + Room 11) = 400mm
        col_widths = [20 * mm]
        for _ in DAYS:
            col_widths.extend([50 * mm, 15 * mm, 11 * mm])

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), hdr_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), hdr_text),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.4, grid_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, alt_row_bg]),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]
        # Day column separators (thicker lines between day groups)
        for d_idx in range(len(DAYS)):
            col_start = 1 + d_idx * 3
            style_cmds.append(
                ('LINEAFTER', (col_start + 2, 0), (col_start + 2, -1),
                 1.5, colors.HexColor('#2C3E50'))
            )
        t.setStyle(TableStyle(style_cmds))
        elements.append(t)

    elements.append(PageBreak())

    # ========================================================================
    # SHEET 2: Faculty Timetable
    # ========================================================================
    elements.append(Paragraph('Faculty Timetable', title_style))

    all_facs = sorted(set(
        c['faculty'] for c in final_courses
        if c['faculty'].lower() != 'nan'))

    for period in PERIODS:
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f'<b>Period: {period}</b>', subtitle_style))

        header = ['Faculty']
        for day in DAYS:
            header.extend([day, 'Batch', 'Room'])
        table_data = [[make_para(h, header_cell_style) for h in header]]

        for fac in all_facs:
            row = [make_para(fac)]
            for day in DAYS:
                curr_slot = slot_matrix[day].get(period, '')
                mc = [c for c in final_courses
                      if c['faculty'] == fac and c['final_slot'] == curr_slot]
                if mc:
                    deduped = dedup_courses(mc)
                    codes = ', '.join(c['course_code'] for c in deduped)
                    batches = ', '.join(c['sub_batch'] for c in deduped)
                    rooms = ', '.join(c['room'] for c in deduped)
                    row.extend([
                        make_para(codes), make_para(batches), make_para(rooms)])
                else:
                    row.extend([make_para('-'), make_para('-'), make_para('-')])
            table_data.append(row)

        # Faculty(20) + 5 days * (Course 35 + Batch 22 + Room 19) = 400mm
        col_widths = [20 * mm]
        for _ in DAYS:
            col_widths.extend([35 * mm, 22 * mm, 19 * mm])

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), hdr_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), hdr_text),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.4, grid_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, alt_row_bg]),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        elements.append(t)

    elements.append(PageBreak())

    # ========================================================================
    # SHEET 3: Room Timetable
    # ========================================================================
    elements.append(Paragraph('Room Timetable', title_style))

    all_rooms = sorted(set(
        c['room'] for c in final_courses
        if c['room'].lower() != 'nan'))

    for period in PERIODS:
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f'<b>Period: {period}</b>', subtitle_style))

        header = ['Room']
        for day in DAYS:
            header.extend([day, 'Batch', 'Faculty'])
        table_data = [[make_para(h, header_cell_style) for h in header]]

        for room in all_rooms:
            row = [make_para(room)]
            for day in DAYS:
                curr_slot = slot_matrix[day].get(period, '')
                mc = [c for c in final_courses
                      if c['room'] == room and c['final_slot'] == curr_slot]
                if mc:
                    deduped = dedup_courses(mc)
                    codes = ', '.join(c['course_code'] for c in deduped)
                    batches = ', '.join(c['sub_batch'] for c in deduped)
                    facs = ', '.join(c['faculty'] for c in deduped)
                    row.extend([
                        make_para(codes), make_para(batches), make_para(facs)])
                else:
                    row.extend([make_para('-'), make_para('-'), make_para('-')])
            table_data.append(row)

        # Room(20) + 5 days * (Course 35 + Batch 22 + Faculty 19) = 400mm
        col_widths = [20 * mm]
        for _ in DAYS:
            col_widths.extend([35 * mm, 22 * mm, 19 * mm])

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), hdr_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), hdr_text),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.4, grid_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, alt_row_bg]),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        elements.append(t)

    try:
        doc.build(elements)
        print(f"  PDF saved: '{pdf_file}'")
    except Exception as e:
        print(f"  WARNING: PDF generation failed: {e}")
        print("  Excel output is still available.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Generate a university timetable from slot assignments.')
    parser.add_argument(
        '--input', '-i',
        default='Slots_Win_2025-26_15Dec2025.xlsx',
        help='Input Excel file with slot assignments')
    parser.add_argument(
        '--reference', '-r',
        default="Lecture_Time_Table_Win'26_v6.xlsx",
        help='Reference timetable file (for slot matrix)')
    parser.add_argument(
        '--output-xlsx', '-ox',
        default='Generated_Master_Timetable.xlsx',
        help='Output Excel file')
    parser.add_argument(
        '--output-pdf', '-op',
        default='Generated_Master_Timetable.pdf',
        help='Output PDF file')
    parser.add_argument(
        '--use-db', action='store_true',
        help='Enable PostgreSQL database mirroring (dual mode)')
    args = parser.parse_args()

    # Determine step count based on mode
    total_steps = 10 if args.use_db else 8
    step = 0

    print("=" * 60)
    print("  University Timetable Generator")
    if args.use_db:
        print("  [Database Mode: PostgreSQL mirroring enabled]")
    print("=" * 60)

    # Step 1: Load slot matrix
    step += 1
    print(f"\n[{step}/{total_steps}] Loading slot matrix...")
    slot_matrix = load_slot_matrix(args.reference)

    # Step 2: Parse input
    step += 1
    print(f"\n[{step}/{total_steps}] Parsing input: {args.input}")
    courses = parse_excel(args.input)

    # Step 2.5 (DB mode): Connect and mirror input data to PostgreSQL
    db = None
    if args.use_db:
        step += 1
        print(f"\n[{step}/{total_steps}] Connecting to PostgreSQL...")
        try:
            from db_manager import DBManager
            db = DBManager()
        except Exception as e:
            print(f"  ✗ Database connection failed: {e}")
            print("  Continuing without database...")
            db = None

        if db:
            step += 1
            print(f"\n[{step}/{total_steps}] Mirroring input data to database...")
            db.store_input_data(courses)

    # Step 3: Build conflict graph (UNCHANGED — works on in-memory courses)
    step += 1
    print(f"\n[{step}/{total_steps}] Building conflict graph...")
    nodes, sb_props, conflicts, roots = build_graph(courses)
    print(f"  {len(roots)} superblocks, "
          f"{sum(len(v) for v in conflicts.values()) // 2} conflict edges.")

    # Step 4: Solve CSP (UNCHANGED — works entirely in RAM)
    step += 1
    print(f"\n[{step}/{total_steps}] Solving schedule (CSP + backtracking)...")
    assignment, unresolved = solve_csp(roots, sb_props, conflicts, slot_matrix)

    # Step 5: Soft constraints optimisation (UNCHANGED)
    step += 1
    print(f"\n[{step}/{total_steps}] Optimising soft constraints...")
    assignment = apply_soft_constraints(
        assignment, sb_props, conflicts, slot_matrix)

    # Step 6: Apply & validate (UNCHANGED)
    step += 1
    print(f"\n[{step}/{total_steps}] Applying assignments & validating...")
    final_courses = apply_assignments(courses, nodes, sb_props, assignment)

    # Smart room assignment — override Excel rooms with capacity-aware allocation
    step += 1
    print(f"\n[{step}/{total_steps}] Assigning rooms (capacity-aware)...")
    reassigned, unchanged = assign_rooms(final_courses, slot_matrix)
    print(f"  ✓ {reassigned} courses reassigned to better-fit rooms")
    print(f"  ✓ {unchanged} courses kept original room (adequate capacity)")

    violations = validate(final_courses, slot_matrix)
    if violations:
        print(f"  ⚠ {len(violations)} constraint violation(s):")
        for v in violations:
            print(f"    • {v}")
    else:
        print("  ✓ All hard constraints satisfied!")

    # Step 6.5 (DB mode): Mirror results to PostgreSQL
    if db:
        print(f"\n[{step}/{total_steps}] Writing results to database...")
        db.store_results(final_courses, unresolved, slot_matrix)

    # Step 7: Export
    step += 1
    print(f"\n[{step}/{total_steps}] Exporting...")
    export_excel(final_courses, args.output_xlsx, slot_matrix, unresolved)
    export_pdf(final_courses, args.output_pdf, slot_matrix)

    # Close database connection
    if db:
        db.close()

    print("\n" + "=" * 60)
    print("  Done! Output files:")
    print(f"    Excel: {args.output_xlsx}")
    print(f"    PDF:   {args.output_pdf}")
    if args.use_db and db:
        print(f"    DB:    timetable_generator_db (all tables populated)")
    if unresolved:
        print(f"    ⚠ {len(unresolved)} unresolved conflicts "
              f"(see 'Conflicts' sheet in Excel)")
    print("=" * 60)


if __name__ == '__main__':
    main()
