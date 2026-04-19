# 📋 Input Data Confirmation Sheet

> **Instructions for Karthik's friend:**
> 1. Look at both tables below
> 2. Correct any wrong numbers by changing the value in the **"Actual"** column
> 3. For courses, fill in the **"Actual Enrollment"** column with the real number of students who signed up for that elective this semester
> 4. Leave blank if you don't know — the system will keep the current estimate
> 5. Send this file back and I'll update the code

---

## SECTION 1: Room Capacities

> **Current values used in the system.** Please verify the seat count for each room.
> Tip: CEP rooms — just check the physical chairs in the room.

| Room | Current Capacity (seats) | Actual Capacity | Notes |
|------|--------------------------|-----------------|-------|
| LT-1 | 200 | | |
| LT-2 | 280 | | |
| LT-3 | 330 | | |
| CEP102 | 190 | | |
| CEP103 | 110 | | |
| CEP104 | 50 | | |
| CEP105 | 90 | | |
| CEP106 | 120 | | |
| CEP107 | 60 | | |
| CEP108 | 120 | | |
| CEP109 | 40 | | |
| CEP110 | 182 | | |
| CEP202 | 150 | | |
| CEP203 | 100 | | |
| CEP204 | 120 | | |
| CEP205 | 80 | | |
| CEP206 | 90 | | |
| CEP207 | 80 | | |
| CEP209 | 120 | | |
| CEP003 | 60 | | |

---

## SECTION 2: Program-wise Student Intake

> **These are used to estimate how many students attend each class.**
> For electives, the system uses "largest single batch" — so just confirm the section size.

| Program | Current Assumption | Actual Count | Notes |
|---------|-------------------|--------------|-------|
| BTech ICT + CS (per section, Sec A or Sec B) | 180 | | ICT-A (180) + ICT-B (100) = 280 total, split into 2 sections |
| BTech MnC (per section) | 60 | | 60 total, split into 1 section |
| BTech EVD (whole batch) | 40 | | Single section |
| BTech CS-Only (per section) | 60 | | 60 total, split into 1 section |
| MTech ICT-ML (whole batch) | 60 | | |
| MTech ICT-SS (whole batch) | 60 | | |
| MTech ICT-VLSI&ES (whole batch) | 30 | | |
| MTech ICT-WCSP (whole batch) | 7 | | |
| MSc DS (whole batch) | 90 | | **ESTIMATED — please correct** |
| MSc IT (whole batch) | 120 | | **ESTIMATED — please correct** |

---

## SECTION 3: Elective Course Actual Enrollment

> **This section is MOST important.** Elective courses have variable enrollment.
> The system currently assumes the entire section (~72 students for ICT+CS) attends.
> If the actual enrollment is lower, some rooms may not be overbooked.
> Fill in the real number of students registered for each elective this semester.

### HASS Electives (Humanities & Social Sciences)

| Code | Course Name | Room | Current Estimate | Actual Enrollment |
|------|-------------|------|-----------------|-------------------|
| HM377 | The English Novel: Form and History | — | 15 | |
| HM402 | Publics in South Asia | — | 10 | |
| HM409 | Management Skills for Professional Excellence | — | 82 | |
| HM412 | World Literature in Short Fiction | — | 21 | |
| HM413 | Knowledge and Identity in Three Modern Indian Novels | — | 38 | |
| HM414 | A Beginner's Introduction to the Psyche | — | 10| |
| HM469 | Approaches to Globalization | — | 72 | |
| HM481 | Reading Plato | — | 18 | |
| HM489 | *(HASS Elective)* | — | 0 | |
| HM494 | Indian Diaspora and Transnationalism | — | 12 | |
| HM495 | Technology and The Making of Modern India | — | 84 | |

### ICT & Technical Electives

| Code | Course Name | Room | Current Estimate | Actual Enrollment |
|------|-------------|------|-----------------|-------------------|
| IE402 | Optimization (ICT only) | CEP102 | 49 | |
| IE406 | Machine Learning | CEP204 | 60 | |
| IE407 | Internet of Things | CEP108 | 11 | |
| IE411 | Operating Systems | CEP104 | 120 | |
| IE416 | Robot Programming | CEP106 | 119 | |
| IE422 | Soft Computing (ICT only) | CEP206 | 20 | |
| IE423 | AI Literacy, Efficiency, and Ethics | — | 49 | |
| IT401 | Quantum ML | CEP104 | 13 | |
| IT402 | Applied Forecasting Methods | CEP103 | 67 | |
| IT414 | Software Project Management | CEP202 | 56 | |
| IT443 | Resampling Techniques and Bayesian Computation | CEP211 | 5 | |
| IT449 | Specification and Verification of Systems | CEP109 | 5 | |
| IT499 | Biometric Security | CEP109 | 40 | |
| IT504 | Distributed Databases | CEP205 | 25 | |
| IT507 | Advanced Image Processing | CEP205 | 18 | |
| IT549 | Deep Learning | CEP108 | 37 | |
| IT561 | Advanced Software Engineering | — | 20 | MTech SS only |
| IT565 | Reinforcement Learning | CEP107 | 40 | |
| IT568 | GenAI for Software Engineering | CEP204 | 33 | |
| IT584 | Approximation Algorithms | — | 60 | |
| IT590 | Advanced Statistical Tools for Data Science | CEP106 |50  | |

### Science Electives

| Code | Course Name | Room | Current Estimate | Actual Enrollment |
|------|-------------|------|-----------------|-------------------|
| SC301 | Numerical Linear Algebra | CEP106 | 5 | |
| SC402 | Introduction To Cryptography | CEP203 | 72 | |
| SC409 | Introduction to Financial Mathematics | — | 76 | |
| SC421 | Introduction to Modern Algebra | CEP103 | 32 | |
| SC444 | Game Theory | CEP204 | 116 | |
| SC463 | Quantum Computation | CEP205 | 14 | |
| SC475 | Time Series Analysis | CEP108 | 16 | |

### Open / Other Electives

| Code | Course Name | Room | Current Estimate | Actual Enrollment |
|------|-------------|------|-----------------|-------------------|
| CT423 | *(Technical Elective)* | — | 10 | |
| CT548 | Advanced Wireless Communication | CEP108 | 14 | |
| EL203 | *(Core — EVD + ICT Sem-IV)* | CEP102 | 170 | Sum of 2 batches |
| EL464 | *(Technical Elective)* | CEP106 | 95 | |
| EL469 | *(Technical Elective)* | CEP108 | 110 | |
| EL495 | *(Technical Elective)* | CEP105 | 38 | |
| EL527 | *(Technical Elective)* | CEP106 | 82 | |
| HM001 | North Indian Classical Music 1 | CEP003 | 30 | Open elective |

---

## ✅ How to Fill This In

1. Open this file in any text editor or GitHub
2. Fill in the **"Actual"** column for rooms and programs you know
3. Fill **"Actual Enrollment"** for elective courses (this is most valuable!)
4. Send back to Karthik — he'll update the system in 5 minutes

> **Note:** For core courses (not electives), the enrollment = full batch size, no changes needed there.
