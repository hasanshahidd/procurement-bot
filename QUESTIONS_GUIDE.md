# 🤖 Procurement AI - Complete Guide

## 📊 Your Data Overview

**Database:** `procurement_bot` on PostgreSQL 18 (port 5433)
**Records:** 500 procurement records loaded from Excel
**Departments:** 10 (IT, Sales, HR, Finance, Marketing, R&D, Operations, Legal, Procurement, Engineering)
**Total Budget:** $131,417,690 across all projects

---

## 🔄 How the System Works (Data Flow)

### Step 1: You Ask a Question
```
Example: "What is the total budget for IT department?"
```

### Step 2: Frontend Sends to Backend
```
POST /api/chat
{
  "message": "What is the total budget for IT department?",
  "language": "en"
}
```

### Step 3: OpenAI Processes Your Question (AI Thinking)
**The AI receives:**
- Your question
- Complete database schema (all 40+ columns)
- Instructions to generate SQL

**AI thinks:**
1. "User wants total budget for IT department"
2. "I need to SUM(budget) FROM procurement_records"
3. "Filter WHERE department = 'IT'"
4. "Generate SQL query"

**AI generates JSON response:**
```json
{
  "sql": "SELECT SUM(budget) as total_budget FROM procurement_records WHERE department = 'IT'",
  "explanation": "This query calculates the total budget for all IT department projects"
}
```

### Step 4: Backend Validates & Executes SQL
```python
# Security check - only SELECT allowed
if validate_sql(sql):
    data = database.execute_query(sql)  # Runs on PostgreSQL
```

### Step 5: PostgreSQL Returns Data
```
Query Result: [{"total_budget": 12500000}]
```

### Step 6: AI Formats Human-Friendly Response
**AI receives:**
- Original question: "What is the total budget for IT department?"
- Query results: `[{"total_budget": 12500000}]`
- Language preference: "en"

**AI generates:**
```
"The total budget for the IT department is $12,500,000 across all projects."
```

### Step 7: Frontend Displays Response
Shows formatted message in chat bubble with bot avatar

---

## 💬 Questions You Can Ask

### 📈 Budget & Financial Questions

1. **"What is the total budget?"**
   - Shows: Sum of all procurement budgets

2. **"What is the average budget per project?"**
   - Shows: Mean budget value

3. **"What is the total budget for [Department]?"**
   - Examples: IT, Sales, HR, Finance, Marketing, R&D, Operations, Legal

4. **"Show me projects with budget over 500000"**
   - Lists: High-value projects

5. **"What are the top 5 most expensive projects?"**
   - Shows: Highest budget projects

6. **"What's the budget breakdown by department?"**
   - Shows: Budget sum per department

7. **"Show quarterly budget distribution"**
   - Shows: Budget across Q1, Q2, Q3, Q4

---

### 🏢 Department Questions

8. **"How many projects does each department have?"**
   - Shows: Project count by department

9. **"Which department has the highest budget?"**
   - Shows: Top spending department

10. **"Show me all IT department projects"**
    - Lists: All IT projects with details

11. **"How many departments are there?"**
    - Shows: Unique department count (10)

---

### 📊 Status & Progress Questions

12. **"How many projects are completed?"**
    - Shows: Count of completed projects

13. **"Show me projects in progress"**
    - Lists: Active projects

14. **"How many projects are on hold?"**
    - Shows: Paused project count

15. **"What is the status distribution of projects?"**
    - Shows: Count by each status

16. **"Show me delayed projects"**
    - Lists: Projects behind schedule

---

### ⚠️ Risk & Priority Questions

17. **"Show me high risk projects"**
    - Lists: Projects marked as high risk

18. **"How many projects are high risk?"**
    - Shows: Count of risky projects

19. **"What's the risk distribution?"**
    - Shows: High, Medium, Low risk counts

20. **"Show high risk projects in IT department"**
    - Combines: Risk + department filter

---

### 📅 Timeline Questions

21. **"Show projects starting this quarter"**
    - Lists: Q1/Q2/Q3/Q4 projects

22. **"What projects are in Q1 2026?"**
    - Shows: First quarter projects

23. **"Show me projects by year"**
    - Groups: Projects per year

24. **"What's the average project duration?"**
    - Shows: Mean duration days

---

### 🔍 Detailed Search Questions

25. **"Show me projects with 'Cloud' in description"**
    - Searches: Description field

26. **"List all projects for contact person John Smith"**
    - Filters: By contact person

27. **"Show projects assigned to Sarah"**
    - Filters: By assigned person

28. **"What's the status of PR-2024-0001?"**
    - Shows: Specific PR number details

---

### 📊 Analytics & Insights

29. **"Show me the most common sourcing method"**
    - Analyzes: Source method distribution

30. **"What's the average SLA for projects?"**
    - Shows: Mean SLA days

31. **"How many projects have local content over 50%?"**
    - Filters: Local content percentage

32. **"Show supplier ratings distribution"**
    - Groups: By supplier rating

33. **"What are the top 5 departments by project count?"**
    - Ranks: Departments by activity

---

### 🔄 Complex Queries

34. **"Show me high risk IT projects over $500k"**
    - Multiple filters: Risk + Department + Budget

35. **"What's the total budget for completed projects in Q1?"**
    - Combines: Status + Quarter + Sum

36. **"List delayed high-budget projects"**
    - Filters: Delayed + Budget threshold

37. **"Show projects that exceeded planned duration"**
    - Compares: Actual vs Planned days

---

## 🌍 Multi-Language Support

Ask in any language! Examples:

### Spanish
- **"¿Cuál es el presupuesto total?"**
- **"Muéstrame proyectos de alto riesgo"**

### Arabic
- **"ما هي الميزانية الإجمالية؟"**
- **"أرني المشاريع عالية المخاطر"**

### French
- **"Quel est le budget total?"**
- **"Montrez-moi les projets à haut risque"**

### Chinese
- **"总预算是多少？"**
- **"显示高风险项目"**

---

## 🎯 Understanding AI Responses

### When You Get Data:
```
You: "What is the total budget?"

AI Response:
"The total budget across all 500 procurement projects is $131,417,690.

This includes projects from 10 departments:
- IT, Sales, HR, Finance, Marketing, R&D, Operations, Legal, Procurement, and Engineering"

[Behind the scenes SQL]:
SELECT SUM(budget) as total_budget, COUNT(*) as project_count 
FROM procurement_records
```

### When No Data Found:
```
You: "Show me projects from XYZ department"

AI Response:
"No data found matching your query. The XYZ department doesn't exist in the database. 
Available departments are: IT, Sales, HR, Finance, Marketing, R&D, Operations, Legal, Procurement, Engineering."
```

---

## 🛡️ Security Features

1. **Only SELECT queries allowed** - Can't modify data
2. **SQL injection prevention** - Validates all queries
3. **Read-only access** - Database is protected

---

## 💡 Pro Tips

1. **Be specific**: "Show IT projects over $500k" vs "Show projects"
2. **Use department names**: IT, Sales, HR, Finance, Marketing, R&D, Operations, Legal, Procurement, Engineering
3. **Combine filters**: "High risk IT projects in Q1"
4. **Ask for summaries**: "Summarize projects by department"
5. **Request top/bottom**: "Top 10 projects by budget"

---

## 📁 Database Schema (What's Available)

Your data includes these fields for each project:
- **Identification**: PR Number, Description
- **Organization**: Department, Contact Person, Assigned To
- **Financial**: Budget, Q1-Q4 Budgets
- **Status**: Status, Project Status, Risk Level
- **Timeline**: Year, Quarter, Month, Dates, Duration
- **Procurement**: Source Method, Supplier Details, Local Content %
- **Compliance**: Approving Authority, SLA, Escalation Status

---

## 🚀 Try It Now!

Go to http://localhost:5000 and ask:
1. "What is the total budget?"
2. "Show me high risk projects"
3. "Which department has the most projects?"

The AI will understand, generate SQL, fetch data, and explain results! 🎉
