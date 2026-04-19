# TimeTable Generator

## 1. Objective

The system shall automatically generate a valid university timetable by assigning specific daily time periods to courses (which are pre-grouped into specific "Slots" and assigned to faculty in an input Excel sheet) while satisfying all given constraints. 

## 2. Input Requirements

*   **Input Data Source:** An Excel spreadsheet containing the predefined mapping of batches, sections, courses, faculty, and their assigned "Slots" (e.g., Slot-1, Slot-2).
*   List of courses (derived from the Excel input), including:
    *   Course type: Core or Elective
    *   Course structure (L-T-P-C format: Lecture-Tutorial-Practical-Credits)
    *   Pre-assigned Slot Group (e.g., Slot-1, Slot-2 out of the 8 available slots)
    *   Pre-assigned Faculty
    *   Target student batches and specific Sections (e.g., BTech Sem-IV Sec A, Sec B)
    *   Pre-assigned Room (from Excel) or expected Room capacity if dynamic assignment is needed.
*   Standard Time Structure:
    *   5 working days per week.
    *   5 class periods per day (Morning session only: 8:00 AM to 12:50 PM).
    *   Each period is 50 minutes followed by a 10-minute break.
    *   Wednesday 8:00 AM is a designated free period.
    *   Total of 24 available class periods per week, divided into 8 designated Slots (each slot generally gets 3 periods).
    *   1:00 PM - 2:00 PM is a 1-hour Lunch Break.
    *   Afternoon session (2:00 PM onwards) is reserved for labs (not handled in the current scheduling phase).

## 3. Hard Constraints

*   **3.1 Slot & Period Constraints**
    *   A course shall not have more than one class scheduled on the same day.
    *   Classes shall only be scheduled within the 24 available morning periods.
    *   No class shall be scheduled on Wednesday at 8:00 AM (Free period).
*   **3.2 Room Constraints**
    *   A room shall not be assigned to more than one class in the same time period.
    *   *(If room assignment is dynamic)* Room capacity must be strictly ≥ course batch/section strength.
*   **3.3 Batch / Student / Section Constraints**
    *   **Core Courses:** Only one core course can be scheduled in a given time period for a specific batch/section. All students in the section must be able to attend.
    *   **Elective Courses:** Multiple electives can be offered in the exact same time period for a specific batch (students choose and attend only one).
    *   **Section Conflict Resolution:** If a batch is divided into multiple sections (e.g., Sec A, Sec B) and both are taught by the same professor for the same course (e.g., IT214 taught by PMJ for both Sec A and Sec B), their classes must be scheduled in completely non-overlapping time periods, even if they belong to the same parent "Slot group".
*   **3.4 Faculty Constraints**
    *   A faculty member shall not be scheduled to teach in two different rooms or sections at the exact same time period.

## 4. Soft Constraints (Optimization Goals)

*   Minimize room changes for a batch/section on any given day.
*   Space out lectures for the same course across the week as evenly as possible.

## 5. Output Requirements

*   A conflict-free timetable for each batch and section.
*   A faculty-wise timetable.
*   A room-wise allocation schedule.
*   A list of unresolved conflicts (if a perfect solution is not possible).
*   Outputs must be exportable in **Excel** and **PDF** formats.
