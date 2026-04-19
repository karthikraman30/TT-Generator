-- ============================================================================
-- Seed: Scheduling Constraints
-- Pre-populates all scheduling rules from the project specification.
-- These are the rules the CSP solver enforces, now stored as queryable data.
-- ============================================================================

INSERT INTO scheduling_constraint (constraint_name, constraint_type, scope, rule_description, enforcement_level, is_active, parameters_json)
VALUES
-- ========== HARD CONSTRAINTS ==========

('No Faculty Double-Booking',
 'HARD', 'FACULTY',
 'A faculty member shall not be scheduled to teach in two different rooms or sections at the exact same time period.',
 'DATABASE',
 TRUE,
 '{"enforced_by": "UNIQUE(assignment_id, slot_id) on master_timetable"}'
),

('No Room Double-Booking',
 'HARD', 'ROOM',
 'A room shall not be assigned to more than one class in the same time period.',
 'DATABASE',
 TRUE,
 '{"enforced_by": "UNIQUE(room_id, slot_id) on master_timetable"}'
),

('Core Course Non-Overlap',
 'HARD', 'BATCH',
 'Only one core course can be scheduled in a given time period for a specific batch/section. All students in the section must be able to attend.',
 'APPLICATION',
 TRUE,
 '{"applies_to": "core_courses_only", "enforced_by": "CSP solver conflict graph"}'
),

('Wednesday 8AM Free',
 'HARD', 'GLOBAL',
 'No class shall be scheduled on Wednesday at 8:00 AM. This is a university-designated free period.',
 'BOTH',
 TRUE,
 '{"day": "Wednesday", "time": "08:00", "enforced_by": "Slot-Free mapping in time_slot + CSP validation"}'
),

('Elective Same-Slot Allowed',
 'HARD', 'BATCH',
 'Multiple elective courses CAN be offered in the exact same time period for a batch. Students choose and attend only one. This is NOT a conflict.',
 'APPLICATION',
 TRUE,
 '{"applies_to": "elective_courses_only", "note": "Exception to the general no-overlap rule"}'
),

('Room Capacity Check',
 'HARD', 'ROOM',
 'Room capacity must be greater than or equal to the enrolled batch/section strength. The system validates Room.capacity >= Student_Batch.headcount before assignment.',
 'APPLICATION',
 TRUE,
 '{"enforced_by": "Application-layer query before room assignment"}'
),

('No Course Twice on Same Day',
 'HARD', 'COURSE',
 'A course shall not have more than one class scheduled on the same day.',
 'APPLICATION',
 TRUE,
 '{"enforced_by": "CSP solver slot-day mapping validation"}'
),

('Morning Sessions Only',
 'HARD', 'GLOBAL',
 'Classes shall only be scheduled within the 24 available morning periods (8:00 AM to 12:50 PM). Afternoon sessions (2:00 PM+) are reserved for labs.',
 'DATABASE',
 TRUE,
 '{"max_periods_per_week": 24, "session": "morning", "enforced_by": "time_slot table only contains morning slots"}'
),

-- ========== SOFT CONSTRAINTS (Optimization Goals) ==========

('Minimize Room Changes',
 'SOFT', 'BATCH',
 'Minimize room changes for a batch/section on any given day. Penalty applied for each room switch.',
 'APPLICATION',
 TRUE,
 '{"penalty_per_change": 2, "enforced_by": "soft_score() in apply_soft_constraints()"}'
),

('Space Out Lectures',
 'SOFT', 'COURSE',
 'Space out lectures for the same course across the week as evenly as possible.',
 'APPLICATION',
 TRUE,
 '{"enforced_by": "soft_score() consecutive-day penalty in apply_soft_constraints()"}'
),

('Faculty No Consecutive Lectures',
 'SOFT', 'FACULTY',
 'Prevent faculty from being assigned to consecutive teaching periods to mitigate fatigue.',
 'APPLICATION',
 TRUE,
 '{"max_consecutive": 2, "enforced_by": "soft_score() will add penalty for back-to-back slots"}'
)

ON CONFLICT (constraint_name) DO UPDATE SET
    rule_description = EXCLUDED.rule_description,
    parameters_json = EXCLUDED.parameters_json;

-- ============================================================================
-- Verify: Show all loaded constraints
-- ============================================================================
-- SELECT constraint_id, constraint_name, constraint_type, scope, enforcement_level, is_active
-- FROM scheduling_constraint
-- ORDER BY constraint_type, constraint_id;
