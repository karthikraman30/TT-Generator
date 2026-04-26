# Quick Validation Reference

## 🚀 Common Validation Scenarios

### ✅ Valid Examples

#### Faculty
```
Full Name: "Dr. Rajesh Kumar"
Abbreviation: "RK" or "DR-KUMAR"
Email: "rajesh.kumar@dau.ac.in"
Role: "faculty" or "admin"
```

#### Semester
```
Name: "Winter 2025-26"
Start Date: "2025-01-15"
End Date: "2025-05-30"
```

#### Program
```
Name: "Bachelor of Technology"
Code: "BTECH_CS" or "MTECH-ICT"
Degree Type: "BTech", "MTech", "MSc", "PhD", or "Diploma"
```

#### Room
```
Name: "Room 101" or "Lab-A"
Capacity: 50 (1-10000)
Building: "Main Building" (optional)
Room Type: "lecture", "lab", "tutorial", "seminar", or "auditorium"
```

#### Course
```
Code: "CS101" or "MATH-201"
Name: "Data Structures and Algorithms"
L: 3 (0-5)
T: 1 (0-3)
P: 2 (0-6)
C: 4 or 3.5 (0-20)
Type: "Core", "Elective", "Lab", "Project", or "Seminar"
```

---

### ❌ Common Mistakes to Avoid

#### Names
- ❌ "." (just special character)
- ❌ "A" (too short, min 2 chars)
- ❌ "123" (no letters)
- ✅ "Dr. A. Kumar" (correct)

#### Abbreviations
- ❌ "P M J" (contains spaces)
- ❌ "---" (just special characters)
- ❌ "p.m.j" (will be converted to P.M.J but dots not recommended)
- ✅ "PMJ" or "DR-KUMAR" (correct)

#### Emails
- ❌ "john.smith" (missing @domain)
- ❌ "john@" (incomplete)
- ❌ "@dau.ac.in" (missing username)
- ✅ "john.smith@dau.ac.in" (correct)

#### Numbers
- ❌ "0" for capacity (must be at least 1)
- ❌ "-5" (negative not allowed)
- ❌ "fifty" (must be a number)
- ✅ "50" (correct)

#### Dates
- ❌ "2025/01/15" (wrong format)
- ❌ "15-01-2025" (wrong format)
- ❌ "2025-13-01" (invalid month)
- ✅ "2025-01-15" (correct: YYYY-MM-DD)

---

## 🔍 Error Message Guide

| Error Message | What It Means | How to Fix |
|---------------|---------------|------------|
| "cannot be empty" | Field is required | Enter a value |
| "must be at least X characters" | Too short | Add more characters |
| "cannot exceed X characters" | Too long | Shorten the text |
| "must contain at least one letter" | Only numbers/symbols | Add letters |
| "can only contain letters, numbers, hyphens, and underscores" | Invalid characters | Remove spaces and special chars |
| "must be a valid email address" | Wrong email format | Use name@domain.com format |
| "must be a valid number" | Not a number | Enter digits only |
| "must be at least X" | Too small | Increase the value |
| "cannot exceed X" | Too large | Decrease the value |
| "must be in YYYY-MM-DD format" | Wrong date format | Use 2025-01-15 format |
| "End date must be after Start date" | Dates reversed | Swap the dates |
| "must be one of: X, Y, Z" | Invalid choice | Select from allowed options |

---

## 💡 Pro Tips

1. **Abbreviations:** Use uppercase letters and hyphens (e.g., DR-SMITH, PMJ, CS-101)
2. **Emails:** Always use institutional domain (@dau.ac.in)
3. **Dates:** Use the date picker in the form to avoid format errors
4. **Names:** Include proper titles (Dr., Prof.) and full names
5. **Codes:** Keep them short but meaningful (CS101, not C1)
6. **Capacity:** Be realistic (typical classroom: 30-60, lab: 20-30, auditorium: 100-500)

---

## 🧪 Test Your Input

Before submitting, check:
- [ ] No leading/trailing spaces
- [ ] Correct format (especially dates and emails)
- [ ] Within allowed ranges
- [ ] No special characters where not allowed
- [ ] Required fields filled

---

## 📞 Need Help?

If you see a validation error:
1. Read the error message carefully
2. Check this guide for the correct format
3. See `INPUT_VALIDATION_RULES.md` for detailed rules
4. Contact admin if you believe the validation is incorrect
