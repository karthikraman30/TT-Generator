-- ============================================================================
-- Seed: Time Slots
-- Pre-populates the 25 time periods (5 days × 5 periods) with slot group
-- mappings matching the university's scheduling grid.
-- ============================================================================

INSERT INTO time_slot (day_of_week, start_time, end_time, slot_group) VALUES
-- Monday
('Monday',    '08:00', '08:50', 'Slot-1'),
('Monday',    '09:00', '09:50', 'Slot-5'),
('Monday',    '10:00', '10:50', 'Slot-4'),
('Monday',    '11:00', '11:50', 'Slot-7'),
('Monday',    '12:00', '12:50', 'Slot-6'),

-- Tuesday
('Tuesday',   '08:00', '08:50', 'Slot-3'),
('Tuesday',   '09:00', '09:50', 'Slot-7'),
('Tuesday',   '10:00', '10:50', 'Slot-2'),
('Tuesday',   '11:00', '11:50', 'Slot-8'),
('Tuesday',   '12:00', '12:50', 'Slot-5'),

-- Wednesday (8:00 AM = Slot-Free, designated free period)
('Wednesday', '08:00', '08:50', 'Slot-Free'),
('Wednesday', '09:00', '09:50', 'Slot-6'),
('Wednesday', '10:00', '10:50', 'Slot-4'),
('Wednesday', '11:00', '11:50', 'Slot-1'),
('Wednesday', '12:00', '12:50', 'Slot-3'),

-- Thursday
('Thursday',  '08:00', '08:50', 'Slot-8'),
('Thursday',  '09:00', '09:50', 'Slot-2'),
('Thursday',  '10:00', '10:50', 'Slot-5'),
('Thursday',  '11:00', '11:50', 'Slot-7'),
('Thursday',  '12:00', '12:50', 'Slot-6'),

-- Friday
('Friday',    '08:00', '08:50', 'Slot-4'),
('Friday',    '09:00', '09:50', 'Slot-1'),
('Friday',    '10:00', '10:50', 'Slot-8'),
('Friday',    '11:00', '11:50', 'Slot-2'),
('Friday',    '12:00', '12:50', 'Slot-3')

ON CONFLICT (day_of_week, start_time) DO UPDATE SET
    slot_group = EXCLUDED.slot_group;

-- ============================================================================
-- Verify: Show the Monday schedule
-- ============================================================================
-- SELECT day_of_week, start_time, end_time, slot_group
-- FROM time_slot
-- WHERE day_of_week = 'Monday'
-- ORDER BY start_time;
