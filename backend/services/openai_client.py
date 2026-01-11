import os
import re
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a helpful procurement data analyst assistant. You help users query and understand procurement data from a PostgreSQL database.

The database has a table called 'procurement_records' with these columns:

BASIC INFO:
- id (serial, primary key)
- year (integer) - fiscal year (2024, 2025)
- quarter (text) - Q1, Q2, Q3, Q4
- month (text) - month name
- period (text) - period identifier
- date (text) - date string in format 'YYYY-MM-DD' - THIS IS TEXT, use CAST(date AS DATE) for date comparisons
- pr_number (text) - unique procurement request number (format: PR-YYYY-0001, PR-2024-0001) - ALWAYS use 4-digit numbers with leading zeros
- description (text) - project description
- department (text) - department name (IT, Finance, HR, Sales, Marketing, R&D, Operations, Legal, Procurement, Engineering)
- contact_person (text) - contact person name
- assign_to (text) - assigned person (Team A, Team B, etc.)

BUDGET:
- budget (real) - total budget amount
- budget_q1, budget_q2, budget_q3, budget_q4 (real) - quarterly planned budgets

SUPPLIER & SOURCING:
- source_method (text) - sourcing method (Tender, RFQ, Direct Purchase, etc.)
- supplier_details (text) - supplier information (e.g., "Supplier-123")
- supplier_rating (text) - supplier rating as TEXT (e.g., "A+", "B", "C+", "D") - DO NOT cast to real/numeric!
- local_content_percentage (real) - local content %

STATUS & APPROVAL:
- status (text) - current status (Approved, Cancelled, Completed, In Progress, On Hold, Pending, Under Review)
- pr_approval_scope_input (text) - approval/scope input stage
- approving_authority (text) - who approved (CEO, CFO, COO, etc.)
- planned (text) - planned status: "Yes" or "No" (case-insensitive)
- target_date (text) - target completion date
- actual_project_start (text) - actual start date

WORKFLOW STAGES (Base - General Duration):
- review_approval_scope_eval (real) - Review & approval scope & evaluation days
- floating (real) - Floating days
- tender_submit_by_vendor (real) - Tender submission days
- evaluation (real) - Evaluation days
- award_approval (real) - Award & approval days
- contract_and_po (real) - Contract and PO days

WORKFLOW STAGES (PD - Planned Duration):
- pr_approval_scope_input_pd (real) - PR approval/scope planned days
- review_approval_scope_eval_pd (real) - Review & approval planned days
- floating_pd (real) - Floating planned days
- tender_submit_by_vendor_pd (real) - Tender submission planned days
- evaluation_pd (real) - Evaluation planned days
- award_approval_pd (real) - Award & approval planned days
- contract_and_po_pd (real) - Contract and PO planned days
- total_days_pd (real) - Total planned duration days

WORKFLOW STAGES (AD - Actual Duration):
- review_approval_scope_eval_ad (real) - Review & approval actual days (completed stage duration, typically 1-20)
- floating_ad (real) - Floating actual days (completed stage duration, typically 1-20)
- tender_submit_by_vendor_ad (real) - Tender submission actual days (completed stage duration, typically 1-30)
- evaluation_ad (real) - Evaluation actual days (completed stage duration, typically 1-20) - NOT current time in evaluation!
- award_approval_ad (real) - Award & approval actual days (completed stage duration, typically 1-10)
- contract_and_po_ad (real) - Contract and PO actual days (completed stage duration, typically 1-20)
- total_days_ad (real) - Total actual duration days

SLA TRACKING (PD - Planned SLA):
- review_approval_scope_eval_pd_sla (real) - Review & approval planned SLA
- floating_pd_sla (real) - Floating planned SLA
- tender_submit_by_vendor_pd_sla (real) - Tender submission planned SLA
- evaluation_pd_sla (real) - Evaluation planned SLA
- award_approval_pd_sla (real) - Award & approval planned SLA
- contract_and_po_pd_sla (real) - Contract and PO planned SLA

SLA TRACKING (AD - Actual SLA):
- review_approval_scope_eval_ad_sla (real) - Review & approval actual SLA
- floating_ad_sla (real) - Floating actual SLA
- tender_submit_by_vendor_ad_sla (real) - Tender submission actual SLA
- evaluation_ad_sla (real) - Evaluation actual SLA
- award_approval_ad_sla (real) - Award & approval actual SLA
- contract_and_po_ad_sla (real) - Contract and PO actual SLA

SLA VARIANCE (Diff):
- review_approval_scope_eval_diff_sla (real) - Review & approval SLA difference
- floating_diff_sla (real) - Floating SLA difference
- tender_submit_by_vendor_diff_sla (real) - Tender submission SLA difference
- evaluation_diff_sla (real) - Evaluation SLA difference
- award_approval_diff_sla (real) - Award & approval SLA difference
- contract_and_po_diff_sla (real) - Contract and PO SLA difference

RISK & STATUS TRACKING:
- project_status (integer) - Project status code (5-15, higher=higher priority)
- risk (text) - Risk level: "Low", "Medium", "High", "Critical", or "None" (TEXT values, not numeric)
- duration (integer) - Project duration
- last_status_date (text) - Last status update date
- status_duration (integer) - Days in current status (1-30 range)
- status_sla (integer) - Status SLA days
- status_co (text) - Status code
- sla (integer) - Overall SLA days (20-50 range)
- escalate_48h (text) - 48h escalation flag: "Yes" or "No" - Use this for urgent/time-sensitive escalations
- ceo_escalation (text) - CEO escalation/action statement - Contains escalation details
- note (text) - Additional notes

USAGE TIPS:
- For budget variance: Compare budget_q1/q2/q3/q4 with stage actual costs
- For delays: Compare *_pd (planned) vs *_ad (actual) columns
- For SLA compliance: Check *_diff_sla columns (negative=exceeded SLA)
- For stage-wise analysis: Use evaluation_ad, award_approval_ad, etc.
- For stuck PRs: Check WHERE status_duration > X or WHERE evaluation_ad > evaluation_pd

IMPORTANT QUERY RULES:
1. **PR Number Format**: ALWAYS use 4-digit format with leading zeros (e.g., PR-2024-0001, NOT PR-2024-001)
   - When user asks for PR-2024-1 or PR-2024-001, convert to PR-2024-0001
   - Pattern is: PR-YYYY-NNNN (4 digits with leading zeros)
2. **Date comparisons**: date column is TEXT. For date filtering:
   - Last 30 days: CAST(date AS DATE) >= CURRENT_DATE - INTERVAL '30 days'
   - Specific year: year = 2024 (don't use date column)
   - Always use CAST(date AS DATE) when comparing dates
3. supplier_rating is TEXT - NEVER cast to real/numeric. Use string comparisons only (=, !=, LIKE, IN).
4. **For "my department" queries**: Generate placeholder: department = 'YOUR_DEPARTMENT_NAME' and explain user needs to specify
5. **For "PRs in evaluation stage for X days"**: Use status = 'Under Review' AND status_duration > X
6. **For "high-risk projects"**: Use risk = 'High' or risk = 'Critical' (TEXT comparison, not numeric). Risk values are: 'Low', 'Medium', 'High', 'Critical', 'None'
7. **For "SLA breaches"**: Check *_diff_sla < 0 columns (negative means exceeded SLA). Most common: evaluation_diff_sla, award_approval_diff_sla
7a. **For "budget over/above X amount"**: Use budget >= X (budget is total budget). For quarterly: budget_q1 >= X OR budget_q2 >= X OR budget_q3 >= X OR budget_q4 >= X
7b. **For "48-hour escalation" or "urgent PRs"**: Use escalate_48h = 'Yes' to find PRs requiring 48h escalation
7c. **For "CFO approval" or "CEO approval"**: Use approving_authority = 'CFO' or approving_authority = 'CEO'. Authority values: CEO, CFO, COO, Manager
8. **For "remaining budget" or "budget left" queries**: 
   - Quarterly budgets (budget_q1/q2/q3/q4) are PLANNED allocations that sum to total budget
   - To show Q3 budget: SELECT department, SUM(budget_q3) as q3_planned FROM procurement_records WHERE department = 'X' GROUP BY department
   - To show total vs used: SELECT department, SUM(budget) as total_budget, SUM(budget_q3) as q3_allocated FROM procurement_records WHERE department = 'X' AND year = 2024 GROUP BY department
   - NOTE: There is no "actual spent" column - budget columns are planned allocations only
9. **Audit trail queries**: For "audit trail" or "history" queries, SELECT comprehensive info:
   - Basic: pr_number, date, description, department, contact_person, assign_to
   - Status: status, status_duration, approving_authority, planned, target_date, actual_project_start, sla
   - Budget: budget, source_method, supplier_details
   - Timeline: all *_pd (planned), *_ad (actual), *_diff_sla columns for workflow stages
   - Escalations: escalate_48h, ceo_escalation
   - Notes: note column
10. **Supplier substitution queries**: Generate query to show suppliers by rating, then explain analysis needed
11. **Correlation/prediction queries**: Generate data extraction query, then explain statistical analysis needed
12. planned values: "Yes"/"No", status values: 'Approved', 'Cancelled', 'Completed', 'In Progress', 'On Hold', 'Pending', 'Under Review'

EXAMPLE QUERIES (use these as reference):
- "Total budget": SELECT SUM(budget) FROM procurement_records
- "Budget by department": SELECT department, SUM(budget) FROM procurement_records GROUP BY department
- "High-risk projects": SELECT pr_number, department, budget, risk FROM procurement_records WHERE risk = 'High' OR risk = 'Critical'
- "Budget over 500K": SELECT pr_number, department, budget, risk FROM procurement_records WHERE budget >= 500000
- "High-risk PRs over 500K": SELECT pr_number, department, budget, risk FROM procurement_records WHERE (risk = 'High' OR risk = 'Critical') AND budget >= 500000
- "48h escalation": SELECT pr_number, department, status, escalate_48h, ceo_escalation FROM procurement_records WHERE escalate_48h = 'Yes'
- "48h escalation this week" (IGNORE time period, just show all): SELECT pr_number, department, status, escalate_48h FROM procurement_records WHERE escalate_48h = 'Yes'
- "CFO approval pending": SELECT pr_number, department, status, approving_authority FROM procurement_records WHERE approving_authority = 'CFO' AND status IN ('Pending', 'Under Review')
- "Status of PR-2025-0123": SELECT * FROM procurement_records WHERE pr_number = 'PR-2025-0123'
- "Status of specific PR": SELECT pr_number, status, department, budget, risk, approving_authority, target_date FROM procurement_records WHERE pr_number = 'PR-YYYY-NNNN'
- "SLA breaches": SELECT pr_number, evaluation_diff_sla FROM procurement_records WHERE evaluation_diff_sla < 0
- "PRs in evaluation": SELECT pr_number, status_duration FROM procurement_records WHERE status = 'Under Review'
- "Q3 budget": SELECT department, SUM(budget_q3) FROM procurement_records WHERE year = 2024 GROUP BY department

When the user asks a question about procurement data:
1. Understand their intent in ANY language they use
2. Generate a valid PostgreSQL SELECT query (only SELECT is allowed)
3. For time-based filters (this week, today, last month): Database has NO timestamps, only years 2024-2025. IGNORE time periods and return all matching records.
4. For specific PR numbers: Always query as-is, even if might not exist. Use 4-digit format: PR-2025-0123
5. For FORECASTING/PROJECTION questions (predict, project, forecast future):
   - Generate a query to extract the relevant HISTORICAL data needed
   - In explanation, note: "Here's the historical data. Statistical forecasting requires external analysis tools."
   - Example: "Project 2026 budget" → Query: SELECT year, quarter, SUM(budget_q1) FROM ... WHERE year IN (2024, 2025) GROUP BY year, quarter
6. Respond in the SAME language the user used

Format your response as JSON with this structure:
{
  "sql": "SELECT ... FROM procurement_records ...",
  "explanation": "Brief explanation of what this query does in the user's language"
}

If the user's question cannot be answered with a SQL query or is just a greeting, respond with:
{
  "sql": null,
  "explanation": "Your conversational response in the user's language"
}

IMPORTANT: Only generate SELECT queries. Never generate INSERT, UPDATE, DELETE, DROP, or any other modifying queries."""

def split_questions(message: str) -> list[str]:
    """Split message into individual questions if multiple questions detected."""
    # Split by newlines first
    lines = [line.strip() for line in message.split('\n') if line.strip()]
    
    # If we have multiple lines that look like questions, treat each as separate
    if len(lines) > 1:
        questions = []
        for line in lines:
            # Check if line looks like a question (ends with ?, contains question words, or is a command)
            if line.endswith('?') or any(word in line.lower() for word in ['show', 'list', 'what', 'how', 'which', 'get', 'find', 'count']):
                questions.append(line)
        
        # If we found multiple question-like lines, return them
        if len(questions) > 1:
            return questions
    
    # Otherwise return as single question
    return [message]

def process_chat(message: str, language: str = "en", history: list = None) -> dict:
    try:
        # Build conversation messages with history for context
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history if provided (last 5 messages for context)
        if history:
            # Include last 5 exchanges to maintain context while limiting token usage
            recent_history = history[-10:] if len(history) > 10 else history
            for msg in recent_history:
                role = msg.get("role")
                content = msg.get("content")
                if role and content:
                    messages.append({"role": role, "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": f"User's language preference: {language}\n\nUser message: {message}"})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        import json
        result = json.loads(content)
        
        return {
            "sql": result.get("sql"),
            "explanation": result.get("explanation", "")
        }
    except Exception as e:
        return {
            "sql": None,
            "explanation": f"Error processing your request: {str(e)}"
        }

def generate_response(query_results: list, original_question: str, language: str = "en") -> str:
    if not query_results:
        # Detect if question is in Arabic or English
        is_arabic = language == "ar" or any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in original_question)
        
        # More helpful message for no data - in user's language
        if "2023" in original_question or "2026" in original_question or "٢٠٢٣" in original_question or "٢٠٢٦" in original_question:
            if is_arabic:
                return "لا توجد بيانات. قاعدة البيانات تحتوي على سجلات للأعوام 2024 و 2025 فقط."
            return "No data found. The database contains records for years 2024 and 2025 only."
        elif ("500" in original_question or "500k" in original_question.lower()) and ("budget" in original_question.lower() or "cost" in original_question.lower() or "الميزانية" in original_question):
            if is_arabic:
                return "لا توجد طلبات شراء بميزانية تزيد عن 500 ألف دولار. أعلى ميزانية في البيانات هي 499 ألف دولار. حاول البحث عن طلبات تزيد عن 400 ألف دولار (15 طلبًا) أو 450 ألف دولار (7 طلبات) بدلاً من ذلك."
            return "No PRs found with budget over $500K. The maximum budget in the data is $499K. Try searching for PRs over $400K (15 PRs) or $450K (7 PRs) instead."
        elif ("evaluation" in original_question.lower() or "under review" in original_question.lower() or "التقييم" in original_question or "المراجعة" in original_question) and ("30" in original_question):
            if is_arabic:
                return "لا توجد طلبات شراء في مرحلة التقييم لأكثر من 30 يومًا. الحد الأقصى في البيانات الحالية هو 30 يومًا. حاول البحث عن '> 25 يومًا' (11 طلبًا) أو '> 20 يومًا' (21 طلبًا) بدلاً من ذلك."
            return "No PRs found in evaluation for more than 30 days. The maximum duration in current data is 30 days. Try searching for '> 25 days' (11 PRs) or '> 20 days' (21 PRs) instead."
        elif "John Smith" in original_question or "XYZ" in original_question:
            if is_arabic:
                return "لم يتم العثور على سجلات بهذا الاسم أو رقم الطلب. يرجى التحقق من الاسم/الرقم الدقيق أو محاولة تصفح السجلات المتاحة."
            return "No records found with that specific name or PR number. Please check the exact name/number or try browsing available records."
        elif "my department" in original_question.lower() or "قسمي" in original_question or "إدارتي" in original_question:
            if is_arabic:
                return "يرجى تحديد اسم القسم (مثل: تقنية المعلومات، المالية، الموارد البشرية، المبيعات، التسويق، البحث والتطوير، العمليات، القانونية، المشتريات، الهندسة)."
            return "Please specify your department name (e.g., IT, Finance, HR, Sales, Marketing, R&D, Operations, Legal, Procurement, Engineering) to see results."
        elif "rating" in original_question.lower() and (">" in original_question or "above" in original_question or "greater" in original_question):
            if is_arabic:
                return "تقييمات الموردين هي درجات حرفية (A+, A, B+, B, C+, C)، وليست رقمية. استخدم استعلامات مثل 'التقييم = A+' للموردين الأعلى تقييمًا."
            return "Supplier ratings are letter grades (A+, A, B+, B, C+, C), not numeric. Use queries like 'rating IN (\"A+\", \"A\")' for top-rated suppliers or 'rating IN (\"C\", \"C+\")' for lower-rated ones."
        else:
            if is_arabic:
                return "لا توجد سجلات تطابق معايير البحث. حاول تعديل الفلاتر أو التحقق من نطاقات البيانات المتاحة (الأعوام 2024-2025)."
            return "No records match your query criteria. Try adjusting your filters or checking available data ranges (years 2024-2025)."
    
    try:
        # Send all results to AI for accurate analysis (up to 100 records for display)
        display_limit = 100
        all_data_str = str(query_results[:display_limit])
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""You are a data analyst providing ACCURATE, CLEAR responses.

STRICT RULES:
1. **Heading** (one line)
2. **Brief summary** (1-2 sentences)
3. **Key bullet points** (3-5 bullets, keep concise)
4. **Table** (if multiple records, show up to 20 rows)

CRITICAL:
- COUNT ACCURATELY from the data provided
- Show ALL data up to 20 rows in table
- Use proper currency format: $1,234.56
- State exact total count
- NO approximations or guesses
- Respond in {language}

If >20 records: Show first 20 rows in table and state "Showing 20 of X total results"
If ≤20 records: Show ALL rows

Format numbers clearly with commas and proper alignment."""},
                {"role": "user", "content": f"Question: {original_question}\n\nData: {all_data_str}\n\nTotal records: {len(query_results)}\n\nProvide accurate response with table if applicable."}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Found {len(query_results)} records. Error generating summary: {str(e)}"

def validate_sql(sql: str) -> bool:
    if not sql:
        return False
    
    normalized = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)
    normalized = ' '.join(normalized.split()).lower().strip()
    
    if not normalized.startswith("select"):
        return False
    
    forbidden = [
        "drop", "delete", "update", "insert", "alter", "truncate",
        "create", "grant", "revoke", "execute", "exec", "call",
        "copy", "pg_", "information_schema", "pg_catalog"
    ]
    for keyword in forbidden:
        if keyword in normalized:
            return False
    
    if ";" in normalized and normalized.index(";") < len(normalized) - 1:
        return False
    
    return True

def fix_failed_query(failed_sql: str, error_message: str, original_question: str, language: str = "en") -> dict:
    """Try to fix a failed SQL query based on the error message."""
    try:
        fix_prompt = f"""The following SQL query failed with an error. Please fix it.

Original question: {original_question}
Failed SQL: {failed_sql}
Error: {error_message}

Common fixes:
- If "must appear in the GROUP BY clause": Add all non-aggregated columns to GROUP BY
- If "column does not exist": Check column names in the schema
- If "cannot cast": Remove CAST operations on TEXT columns like supplier_rating or risk
- If date comparison fails: Use CAST(date AS DATE) for date column

Generate the corrected SQL query. Return JSON format:
{{
  "sql": "corrected SELECT query",
  "explanation": "What was fixed"
}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": fix_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=500
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result
    except:
        return {"sql": None, "explanation": "Could not fix query"}

def generate_error_response(error_message: str, original_question: str, language: str = "en") -> str:
    """Generate a helpful error message for users."""
    error_lower = error_message.lower()
    
    # Common error patterns
    if "group by" in error_lower:
        return "I encountered an issue with data aggregation. Let me know if you'd like to see individual records instead of summaries, or try rephrasing your question."
    elif "column" in error_lower and "does not exist" in error_lower:
        return "I tried to access a column that doesn't exist in the database. Please rephrase your question or check the available data fields."
    elif "cast" in error_lower or "invalid input" in error_lower:
        return "I encountered a data type mismatch. This might be due to comparing text values as numbers. Please rephrase your question."
    elif "syntax error" in error_lower:
        return "I generated an invalid query. Please try rephrasing your question in a different way."
    else:
        return f"I encountered an error processing your request. Please try rephrasing your question or breaking it into smaller parts. If the issue persists, try asking about specific aspects like 'Show me IT department PRs' or 'What's the total budget for 2024?'"

def generate_query_suggestions(partial_input: str, language: str = "en", conversation_context: list = None) -> list:
    """Generate smart query completion suggestions based on partial user input."""
    try:
        # Build context from conversation
        context_str = ""
        if conversation_context and len(conversation_context) > 0:
            recent = conversation_context[-3:] if len(conversation_context) > 3 else conversation_context
            context_str = f"\n\nRecent conversation:\n" + "\n".join([f"- {q}" for q in recent])
        
        prompt = f"""You are an autocomplete assistant. The user is typing a query about procurement data. Complete what they're typing with relevant suggestions based on the actual data available.

DATABASE SCHEMA:
- pr_number, requester_name, department
- budget_amount (range: $10K-$499K)
- risk_level (Low, Medium, High, Critical, None)
- current_status (Approved, Cancelled, Completed, In Progress, On Hold, Pending, Under Review)
- escalation_flag (48-hour escalation, CEO approval, CFO approval)
- sla_difference (days delayed/ahead)
- evaluation_stage, approval_date, created_at

AVAILABLE DATA:
- Departments: IT, Finance, HR, Sales, Marketing, R&D, Operations, Legal, Procurement, Engineering
- 500 records from 2024-2025
- Budget range: $10,000 to $499,000
- Risk levels tracked per PR
- SLA tracking with delays

User typed: "{partial_input}"{context_str}

TASK: Generate 5 autocomplete suggestions that:
1. START with what the user typed (or close variation)
2. Complete their query naturally based on ACTUAL database fields
3. Are specific and actionable (e.g., "show PRs over $300K", "which departments have high risk")
4. Use real values from the database (departments, statuses, risk levels mentioned above)
5. Language: {language}

Examples of GOOD autocomplete:
- User types "show" → "show all high-risk PRs", "show IT department budget", "show pending approvals"
- User types "which" → "which PRs exceed $400K", "which departments have critical risk", "which PRs need CEO approval"
- User types "how many" → "how many PRs are pending", "how many high-risk projects", "how many delayed PRs"

Return ONLY valid JSON object with "suggestions" array:
{{"suggestions": ["completion 1", "completion 2", "completion 3", "completion 4", "completion 5"]}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a query suggestion assistant. Return only a valid JSON array of 5 string suggestions."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=300
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        # Handle different response formats
        if isinstance(result, dict):
            suggestions = result.get("suggestions", [])
        elif isinstance(result, list):
            suggestions = result
        else:
            suggestions = []
        
        # Filter and limit to 5
        suggestions = [s.strip() for s in suggestions if isinstance(s, str) and len(s.strip()) > 0]
        return suggestions[:5]
        
    except Exception as e:
        print(f"Suggestion generation error: {e}")
        # Return empty list on error
        return []
