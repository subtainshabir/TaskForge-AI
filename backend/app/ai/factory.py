import json
import re
import urllib.error
import urllib.request
from typing import Any, Optional

from fastapi import HTTPException, status

from app.ai.base import AIProvider
from app.core.config import get_settings


class NoopProvider(AIProvider):
    def is_configured(self) -> bool:
        return False

    def complete(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please configure an AI provider in backend settings.",
        )


class MockAIProvider(AIProvider):
    def is_configured(self) -> bool:
        return True

    def complete(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        title = ""
        description = ""
        priority = "medium"

        for line in prompt.splitlines():
            if line.startswith("Task Title:"):
                title = line.replace("Task Title:", "").strip()
            elif line.startswith("Priority:"):
                priority = line.replace("Priority:", "").strip().lower()
            elif line.startswith("Description:"):
                description = line.replace("Description:", "").strip()

        lower_text = f"{title} {description}".lower()

        # Check if requested to generate AI progress insights
        if system_prompt and any(w in system_prompt.lower() for w in ["progress analysis engine", "progress insight", "progress data to provide useful"]):
            if "[FORCE_INVALID_PROGRESS_INSIGHTS]" in prompt:
                return "Not valid JSON"
            if "[FORCE_EMPTY_INSIGHTS]" in prompt:
                return json.dumps({"summary": "Not enough task data for meaningful AI insights yet.", "insights": []})

            total_tasks = 0
            completed_tasks = 0
            in_progress_tasks = 0
            todo_tasks = 0
            avg_progress = 0

            for line in prompt.splitlines():
                if "- Total Tasks:" in line:
                    try:
                        total_tasks = int(line.split("- Total Tasks:")[1].strip())
                    except ValueError:
                        pass
                elif "- Completed Tasks:" in line:
                    try:
                        completed_tasks = int(line.split("- Completed Tasks:")[1].strip())
                    except ValueError:
                        pass
                elif "- In-Progress Tasks:" in line:
                    try:
                        in_progress_tasks = int(line.split("- In-Progress Tasks:")[1].strip())
                    except ValueError:
                        pass
                elif "- Todo (Not Started) Tasks:" in line:
                    try:
                        todo_tasks = int(line.split("- Todo (Not Started) Tasks:")[1].strip())
                    except ValueError:
                        pass
                elif "- Average Task Progress:" in line:
                    try:
                        val = line.split("- Average Task Progress:")[1].replace("%", "").strip()
                        avg_progress = int(val)
                    except ValueError:
                        pass

            if total_tasks == 0:
                return json.dumps({
                    "summary": "Not enough task data for meaningful AI insights yet.",
                    "insights": [],
                })

            insights = []
            if completed_tasks > 0:
                insights.append({
                    "type": "positive",
                    "title": f"{completed_tasks} tasks have reached 100% completion",
                    "description": f"Currently, {completed_tasks} of {total_tasks} workspace tasks have reached full completion.",
                    "severity": "info",
                })

            if "Active tasks with low progress" in prompt:
                insights.append({
                    "type": "bottleneck",
                    "title": "Active tasks have limited phase completion",
                    "description": "Several in-progress tasks currently remain below 25% phase progress.",
                    "severity": "medium",
                })

            if "Incomplete tasks with deadlines" in prompt:
                insights.append({
                    "type": "deadline",
                    "title": "Tasks with approaching deadlines need attention",
                    "description": "Incomplete tasks with registered deadlines are currently active.",
                    "severity": "high",
                })

            insights.append({
                "type": "progress",
                "title": f"Workspace average progress stands at {avg_progress}%",
                "description": f"Current data reflects {in_progress_tasks} active and {todo_tasks} unstarted tasks across projects.",
                "severity": "info",
            })

            return json.dumps({
                "summary": f"Your workspace currently has {total_tasks} tasks with an average progress of {avg_progress}%.",
                "insights": insights,
            })

        # Check if requested to regenerate task
        if system_prompt and any(w in system_prompt.lower() for w in ["regenerat", "regeneration principles", "improve an existing task"]):
            if "[FORCE_INVALID_REGEN_RESPONSE]" in prompt:
                return "Not valid JSON"

            instruction = ""
            for idx, line in enumerate(prompt.splitlines()):
                if line.strip() == "User Instruction:" and idx + 1 < len(prompt.splitlines()):
                    instruction = prompt.splitlines()[idx + 1].strip()
                elif "User Instruction:" in line:
                    instruction = line.split("User Instruction:")[1].strip()

            orig_title = title or "Task"
            orig_desc = description or ""

            if "login" in orig_title.lower() or "auth" in orig_title.lower():
                prop_title = "Fix authentication failure during user login"
                prop_desc = (
                    "Investigate and resolve the authentication failure occurring when valid credentials are submitted. "
                    "Verify token generation, error response status codes, and confirm seamless redirection upon successful login."
                )
                changes = [
                    "Clarified the problem statement and error scenario",
                    "Defined expected outcome and definition of done",
                    "Made implementation steps actionable",
                ]
            elif "cart" in orig_title.lower() or "checkout" in orig_title.lower() or "payment" in orig_title.lower():
                prop_title = "Resolve checkout calculation and transaction failure"
                prop_desc = (
                    "Audit and fix cart item total calculations, discount code application, and payment gateway submission. "
                    "Ensure error states are displayed clearly to the customer and successful transactions create verified orders."
                )
                changes = [
                    "Specified exact calculation and payment submission touchpoints",
                    "Added requirement for customer-facing error recovery",
                    "Clarified order completion criteria",
                ]
            else:
                clean_t = orig_title.strip()
                if clean_t.lower().startswith("fix "):
                    prop_title = f"Diagnose and resolve {clean_t[4:]}"
                elif clean_t.lower().startswith("add ") or clean_t.lower().startswith("create "):
                    prop_title = f"Implement and verify {clean_t.split(' ', 1)[1]}"
                else:
                    prop_title = f"Refine and complete {clean_t}"

                prop_desc = (
                    f"Thoroughly analyze and implement the requirements for '{orig_title}'. "
                    "Address edge cases, ensure input validation, add automated tests covering standard workflows, "
                    "and verify end-to-end functionality meets expected acceptance criteria."
                )
                changes = [
                    "Replaced ambiguous wording with a concrete, actionable objective",
                    "Added specific implementation and edge-case scope",
                    "Defined test coverage and verification criteria as definition of done",
                ]

            if instruction:
                prop_desc += f" (Tailored to instruction: {instruction})"
                changes.append(f"Applied user instruction: {instruction}")

            return json.dumps({
                "title": prop_title,
                "description": prop_desc,
                "changes": changes,
            })

        # Check if requested to suggest tasks
        if system_prompt and any(w in system_prompt.lower() for w in ["task suggestion", "suggest tasks", "suggest additional tasks", "missing, high-value"]):
            if "[FORCE_EMPTY_SUGGESTIONS]" in prompt:
                return json.dumps({"suggestions": []})

            lower_prompt = prompt.lower()
            existing_lines = []
            for line in prompt.splitlines():
                line_s = line.strip()
                if line_s.startswith("- ") and " (Status:" in line_s:
                    title_part = line_s[2:].split(" (Status:")[0].strip().lower()
                    existing_lines.append(title_part)
                elif line_s.startswith("Task Title:"):
                    existing_lines.append(line_s.replace("Task Title:", "").strip().lower())

            if any(w in lower_prompt for w in ["ecommerce", "e-commerce", "store", "shop", "cart", "product", "checkout", "payment"]):
                pool = [
                    {
                        "title": "Add Email Verification",
                        "description": "Send confirmation emails to users after registration to verify their email addresses.",
                        "reason": "User authentication exists, but email verification has not been implemented yet.",
                        "priority": "medium",
                    },
                    {
                        "title": "Implement Order Management",
                        "description": "Create order creation, status tracking, and order history functionality.",
                        "reason": "Shopping cart exists, but order management and processing is missing.",
                        "priority": "high",
                    },
                    {
                        "title": "Add Payment Failure Handling",
                        "description": "Handle declined transactions, payment retry workflows, and customer notification.",
                        "reason": "Payment integration exists, but error recovery and failure flows are missing.",
                        "priority": "high",
                    },
                    {
                        "title": "Add API Integration Tests",
                        "description": "Test critical authentication, product management, and checkout backend workflows.",
                        "reason": "Core features are present, but dedicated integration testing coverage is absent.",
                        "priority": "medium",
                    },
                ]
            else:
                pool = [
                    {
                        "title": "Add API Integration Tests",
                        "description": "Write automated test suites for critical backend endpoints and workflows.",
                        "reason": "The project currently has implementation tasks but no testing coverage task.",
                        "priority": "medium",
                    },
                    {
                        "title": "Add Input Validation & Error Handling",
                        "description": "Implement request validation bounds and consistent error response formats.",
                        "reason": "Ensures robust handling of malformed client requests and failure states.",
                        "priority": "medium",
                    },
                    {
                        "title": "Configure CI/CD Deployment Pipeline",
                        "description": "Set up continuous integration and automated deployment pipelines for the service.",
                        "reason": "Streamlines deployment verification and production releases.",
                        "priority": "low",
                    },
                    {
                        "title": "Add System Documentation & API Guide",
                        "description": "Document system architecture, setup instructions, and endpoint schemas.",
                        "reason": "Improves developer onboarding and API contract transparency.",
                        "priority": "low",
                    },
                ]

            filtered_pool = [
                item for item in pool
                if not any(item["title"].lower() in ex or ex in item["title"].lower() for ex in existing_lines)
            ]
            return json.dumps({"suggestions": filtered_pool})

        # Check if requested to evaluate task quality
        if system_prompt and ("quality" in system_prompt.lower() or "actionable, and complete" in system_prompt.lower()):
            is_vague = len(title.strip()) < 20 and (not description or len(description.strip()) < 30)

            if is_vague:
                overall_score = 58
                summary = "The task description is too vague and lacks a specific expected outcome."
                dimensions = [
                    {"name": "clarity", "score": 60, "explanation": "The general intent is understandable but lacks scope."},
                    {"name": "specificity", "score": 50, "explanation": "No specific problem, element, or component is identified."},
                    {"name": "actionability", "score": 60, "explanation": "Work cannot easily proceed without clarification."},
                    {"name": "completeness", "score": 55, "explanation": "Missing acceptance criteria and definition of done."},
                    {"name": "context", "score": 65, "explanation": "Basic project reference is known."},
                ]
                issues = [
                    {"title": "The task description is too vague", "description": "The description does not explain the exact problem or requirements.", "severity": "high"},
                    {"title": "No specific problem is identified", "description": "Lacks specific component names, error messages, or reproduction steps.", "severity": "medium"},
                    {"title": "Expected result is undefined", "description": "No measurable definition of success or done state.", "severity": "medium"},
                ]
                suggestions = [
                    {"title": "Describe the exact problem", "description": "Specify the affected pages, components, or user scenarios."},
                    {"title": "Specify the expected result", "description": "Describe what should be different after this task is completed."},
                    {"title": "Add acceptance criteria", "description": "Include a brief checklist of required outcomes."},
                ]
            else:
                overall_score = 85
                summary = "The task has clear objectives, well-defined scope, and actionable implementation details."
                dimensions = [
                    {"name": "clarity", "score": 90, "explanation": "The main objective is clear and unambiguous."},
                    {"name": "specificity", "score": 85, "explanation": "Identifies targeted components and deliverables."},
                    {"name": "actionability", "score": 85, "explanation": "Implementation can begin immediately."},
                    {"name": "completeness", "score": 80, "explanation": "Sufficient detail provided for successful execution."},
                    {"name": "context", "score": 85, "explanation": "Strong architectural and operational context."},
                ]
                issues = [
                    {"title": "Edge cases could be clarified", "description": "Specific failure modes or validation bounds could be documented.", "severity": "low"},
                ]
                suggestions = [
                    {"title": "Add verification checklist", "description": "List automated test requirements and expected edge case handling."},
                ]

            return json.dumps({
                "overall_score": overall_score,
                "summary": summary,
                "dimensions": dimensions,
                "issues": issues,
                "suggestions": suggestions,
            })

        # Check if requested to analyze task priority
        if system_prompt and "priority" in system_prompt.lower():
            current_priority = priority or "medium"
            is_overdue = False
            has_deadline = False
            blocks_tasks = False
            is_blocked = False

            for line in prompt.splitlines():
                if line.startswith("Current Priority:"):
                    current_priority = line.replace("Current Priority:", "").strip().lower()
                elif line.startswith("Deadline:"):
                    if "None" not in line:
                        has_deadline = True
                        if "OVERDUE" in line:
                            is_overdue = True
                elif line.startswith("Downstream Impact:"):
                    blocks_tasks = True
                elif line.startswith("Blocked Status:"):
                    is_blocked = True

            factors = []
            if any(w in lower_text for w in ["payment", "checkout", "outage", "security", "vulnerability", "crash"]):
                recommended = "urgent" if (is_overdue or blocks_tasks) else "high"
                factors.append("Critical payment or checkout transaction path affected")
                if blocks_tasks:
                    factors.append("Task blocks dependent work")
                if is_overdue:
                    factors.append("Deadline is overdue")
                elif has_deadline:
                    factors.append("Deadline is approaching")
                reasoning = "The task has high business impact and critical customer-facing exposure."
                confidence = 0.92
            elif is_overdue:
                recommended = "high" if current_priority != "urgent" else "urgent"
                factors.append("Task deadline has passed")
                if blocks_tasks:
                    factors.append("Task blocks dependent work")
                reasoning = "The task has exceeded its scheduled deadline and requires priority attention."
                confidence = 0.89
            elif blocks_tasks:
                recommended = "high"
                factors.append("Task blocks downstream deliverables")
                if has_deadline:
                    factors.append("Deadline is approaching")
                reasoning = "The task has a near deadline and blocks other work."
                confidence = 0.88
            elif any(w in lower_text for w in ["typo", "cosmetic", "cleanup", "minor", "nice to have"]):
                recommended = "low"
                factors.append("Minor enhancement with minimal operational impact")
                factors.append("No blocking dependencies")
                reasoning = "This item is low risk and does not impede other deliverables."
                confidence = 0.91
            elif current_priority in ("high", "urgent") and not has_deadline and not blocks_tasks:
                recommended = "medium"
                factors.append("Standard deliverable without blocking dependencies")
                factors.append("No hard deadline specified")
                reasoning = "Task scope is manageable and lacks urgent blocking bottlenecks."
                confidence = 0.84
            else:
                recommended = current_priority
                factors.append(f"Current priority of {current_priority} is consistent with task scope")
                if has_deadline:
                    factors.append("Deadline aligns with normal schedule")
                reasoning = f"The current {current_priority} priority appears appropriate for the defined scope."
                confidence = 0.85

            return json.dumps({
                "current_priority": current_priority,
                "recommended_priority": recommended,
                "confidence": confidence,
                "reasoning": reasoning,
                "factors": factors,
                "is_inconsistent": recommended != current_priority,
            })

        # Check if requested to refine/review existing phases
        if system_prompt and any(w in system_prompt.lower() for w in ["refinement", "refine", "review your existing", "review a user's"]):
            current_phase_list = []
            for line in prompt.splitlines():
                match = re.search(r"\[Phase ID: (\d+)\] \"([^\"]+)\"", line)
                if match:
                    current_phase_list.append({"id": int(match.group(1)), "title": match.group(2)})

            suggestions = []
            # Look for setup phase to rename
            setup_phase = next((p for p in current_phase_list if "setup" in p["title"].lower() and "project" not in p["title"].lower()), None)
            if setup_phase:
                suggestions.append({
                    "id": "sug-1",
                    "type": "rename",
                    "phase_id": setup_phase["id"],
                    "title": setup_phase["title"],
                    "proposed_title": "Project Setup",
                    "description": "More specific title that explicitly communicates tooling, repository, and environment setup."
                })
            elif current_phase_list:
                first_p = current_phase_list[0]
                suggestions.append({
                    "id": "sug-1",
                    "type": "rename",
                    "phase_id": first_p["id"],
                    "title": first_p["title"],
                    "proposed_title": f"{first_p['title']} & Architecture",
                    "description": "Expand title to clarify initial architecture and scope setup."
                })

            # Look for backend or broad phase to split
            backend_phase = next((p for p in current_phase_list if "backend" in p["title"].lower()), None)
            if not backend_phase and len(current_phase_list) > 1:
                backend_phase = next((p for p in current_phase_list if any(w in p["title"].lower() for w in ["api", "core", "implementation", "development"])), None)

            if backend_phase:
                suggestions.append({
                    "id": "sug-2",
                    "type": "split",
                    "phase_id": backend_phase["id"],
                    "title": backend_phase["title"],
                    "description": f"The '{backend_phase['title']}' phase is too broad. Splitting into focused milestones ensures clearer tracking.",
                    "split_phases": [
                        {"title": "Database Design", "description": "Define data schemas, models, and initial migrations."},
                        {"title": "Authentication", "description": "Implement user authentication, registration, and tokens."},
                        {"title": "Product API", "description": "Build business domain endpoints and query operations."}
                    ]
                })

            # Look for missing phase to add (e.g. Payment Integration or Testing & QA)
            has_payment = any("payment" in p["title"].lower() for p in current_phase_list)
            if not has_payment and any(w in lower_text for w in ["ecommerce", "e-commerce", "store", "shop", "checkout"]):
                suggestions.append({
                    "id": "sug-3",
                    "type": "add",
                    "proposed_title": "Payment Integration",
                    "proposed_description": "Integrate payment processing gateway, webhook listeners, and transaction receipts.",
                    "description": "Missing payment gateway milestone which is critical for an e-commerce workflow."
                })
            else:
                has_qa = any(w in p["title"].lower() for p in current_phase_list for w in ["qa", "test", "verification"])
                if not has_qa:
                    suggestions.append({
                        "id": "sug-3",
                        "type": "add",
                        "proposed_title": "Testing & Quality Assurance",
                        "proposed_description": "Write automated unit and integration tests for critical user flows.",
                        "description": "Add testing milestone to verify system stability before deployment."
                    })
                else:
                    suggestions.append({
                        "id": "sug-3",
                        "type": "add",
                        "proposed_title": "Monitoring & Production Readiness",
                        "proposed_description": "Configure health check endpoints, logging, and performance metrics.",
                        "description": "Ensure production observabilty and operational stability."
                    })

            data = {
                "summary": "The current phases cover the main workflow, but some phases are too broad and important milestones can be structured more clearly.",
                "suggestions": suggestions
            }
            return json.dumps(data)

        # Check if requested to generate phases
        if system_prompt and ("phases" in system_prompt.lower() or "phase" in system_prompt.lower()):
            if any(w in lower_text for w in ["e-commerce", "ecommerce", "store", "shop"]):
                phases = [
                    {"title": "Project Setup & Dependencies", "description": "Configure project repository, dependencies, and environment variables."},
                    {"title": "Database Design & Schema", "description": "Design data models and schema for products, orders, and users."},
                    {"title": "Authentication & Authorization", "description": "Implement user authentication, registration, and session management."},
                    {"title": "Product Catalog & Management", "description": "Create API endpoints and views for listing, filtering, and managing products."},
                    {"title": "Shopping Cart Implementation", "description": "Build cart state management, add/remove items, and persistence."},
                    {"title": "Checkout & Payment Integration", "description": "Integrate payment processing and order confirmation workflows."},
                    {"title": "Testing & Quality Assurance", "description": "Write automated unit and integration tests for critical flows."},
                    {"title": "Deployment & Production Verification", "description": "Deploy services and verify monitoring, logs, and performance."},
                ]
            elif any(w in lower_text for w in ["endpoint", "api", "backend", "fastapi", "django", "server", "controller"]):
                phases = [
                    {"title": "Architecture & Endpoint Design", "description": "Outline API specifications, route definitions, and schema structures."},
                    {"title": "Data Modeling & Storage", "description": "Define database models, relations, and necessary schema migrations."},
                    {"title": "Core Business Logic & Services", "description": "Implement core domain services, validation rules, and operations."},
                    {"title": "API Routing & Validation", "description": "Implement HTTP controllers, input sanitization, and error handling."},
                    {"title": "Authentication & Permissions", "description": "Enforce access controls, ownership validation, and security policies."},
                    {"title": "Integration Testing & Verification", "description": "Write comprehensive unit and integration test coverage."},
                ]
            elif any(w in lower_text for w in ["ui", "frontend", "react", "component", "css", "layout", "page", "modal"]):
                phases = [
                    {"title": "UI Wireframing & Component Layout", "description": "Plan UI hierarchy, accessibility structure, and layout requirements."},
                    {"title": "Component Architecture", "description": "Create modular frontend components and custom hooks for state management."},
                    {"title": "API Integration & Data Fetching", "description": "Connect UI components with backend APIs and handle loading/error states."},
                    {"title": "Form Handling & Client Validation", "description": "Add user input forms with validation and responsive feedback."},
                    {"title": "Styling & Responsive Polish", "description": "Refine design tokens, mobile responsiveness, and micro-interactions."},
                    {"title": "End-to-End & Cross-Browser Testing", "description": "Verify component behavior across browsers and viewport sizes."},
                ]
            elif any(w in lower_text for w in ["sql", "database", "postgres", "migration", "query", "schema"]):
                phases = [
                    {"title": "Schema Analysis & Planning", "description": "Analyze query patterns, relationship cardinality, and indexing needs."},
                    {"title": "Migration Script Development", "description": "Write reversible database migration scripts and constraints."},
                    {"title": "ORM Models & Relationships", "description": "Update ORM entities and relationship configurations."},
                    {"title": "Query Performance & Indexing", "description": "Add indexes and optimize high-frequency queries."},
                    {"title": "Data Validation & Integrity Checks", "description": "Verify foreign key constraints, rollback safety, and data consistency."},
                ]
            else:
                phases = [
                    {"title": "Requirements & Scope Breakdown", "description": "Review requirements and break down key deliverables."},
                    {"title": "Initial Setup & Environment", "description": "Prepare dependencies, configurations, and prerequisites."},
                    {"title": "Core Implementation", "description": f"Implement the core functionality for '{title or 'the task'}'."},
                    {"title": "Validation & Edge Cases", "description": "Handle edge cases, input errors, and operational stability."},
                    {"title": "Testing & Verification", "description": "Verify correctness through unit tests and manual validation."},
                    {"title": "Documentation & Review", "description": "Document changes and perform final review."},
                ]
            return json.dumps({"phases": phases})

        # Determine category
        if any(w in lower_text for w in ["endpoint", "api", "backend", "fastapi", "django", "server", "controller"]):
            category = "Backend Development"
        elif any(w in lower_text for w in ["ui", "frontend", "react", "component", "css", "layout", "page", "modal"]):
            category = "Frontend Development"
        elif any(w in lower_text for w in ["sql", "database", "postgres", "migration", "query", "schema"]):
            category = "Database Engineering"
        elif any(w in lower_text for w in ["deploy", "docker", "ci/cd", "pipeline", "devops", "cloud", "aws", "kubernetes"]):
            category = "DevOps & Infrastructure"
        elif any(w in lower_text for w in ["auth", "jwt", "login", "security", "token", "permission"]):
            category = "Security & Authentication"
        elif any(w in lower_text for w in ["test", "unittest", "pytest", "qa", "coverage"]):
            category = "Quality Assurance & Testing"
        else:
            category = "Software Engineering"

        # Determine complexity
        if priority in ("urgent", "high") or len(description) > 300:
            complexity = "High"
        elif priority == "low":
            complexity = "Low"
        else:
            complexity = "Medium"

        # Determine skills
        skills = []
        if "react" in lower_text or "ui" in lower_text or "frontend" in lower_text:
            skills.extend(["React", "JavaScript", "CSS"])
        if "api" in lower_text or "fastapi" in lower_text or "backend" in lower_text:
            skills.extend(["REST API", "FastAPI", "Python"])
        if "database" in lower_text or "sql" in lower_text or "postgres" in lower_text:
            skills.extend(["PostgreSQL", "SQLAlchemy"])
        if "auth" in lower_text or "jwt" in lower_text:
            skills.extend(["Authentication", "JWT"])
        if not skills:
            skills = ["Problem Solving", "Software Architecture", "Code Implementation"]

        # Potential challenges
        challenges = []
        if category == "Backend Development":
            challenges = [
                "Input validation and comprehensive error handling",
                "Maintaining backwards compatibility with existing clients",
                "Database performance and index optimization",
            ]
        elif category == "Frontend Development":
            challenges = [
                "Cross-browser and responsive layout compatibility",
                "Consistent state synchronization across components",
                "Accessibility standards (ARIA, keyboard navigation)",
            ]
        elif category == "Database Engineering":
            challenges = [
                "Migration execution with zero downtime",
                "Foreign key constraints and cascade integrity",
            ]
        elif category == "Security & Authentication":
            challenges = [
                "Token expiration and revocation management",
                "Preventing unauthorized cross-tenant data access",
            ]
        else:
            challenges = [
                "Ensuring robust test coverage for edge cases",
                "Clear documentation for maintainability",
            ]

        summary = f"Implement and verify {title.lower() if title else 'the task requirements'}."
        goal = f"Deliver a reliable, well-tested implementation for '{title}' that fulfills project requirements."

        data = {
            "summary": summary,
            "goal": goal,
            "category": category,
            "complexity": complexity,
            "skills": skills,
            "potential_challenges": challenges,
        }
        return json.dumps(data)


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model
        if base_url and base_url.strip():
            url = base_url.strip()
            if not url.endswith("/chat/completions"):
                url = url.rstrip("/") + "/chat/completions"
            self.endpoint = url
        elif api_key and api_key.startswith("gsk_"):
            self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        elif api_key and api_key.startswith("sk-or-"):
            self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        else:
            self.endpoint = "https://api.openai.com/v1/chat/completions"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def complete(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is not configured. Please configure an AI provider in backend settings.",
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key.strip()}",
                "User-Agent": "TaskForge-AI/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                return res_json["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid AI provider credentials.",
                )
            if e.code == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="AI provider rate limit exceeded. Please try again shortly.",
                )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI provider returned an error: HTTP {e.code}",
            )
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="AI provider request timed out. Please try again.",
                )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not connect to AI provider. Please check network connectivity.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unexpected error communicating with AI provider: {str(e)}",
            )


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider_type = (settings.ai_provider or "").strip().lower()

    if provider_type == "mock":
        return MockAIProvider()

    if provider_type in ("openai", "custom", "groq") or bool(settings.ai_api_key and settings.ai_api_key.strip()):
        if settings.ai_api_key and settings.ai_api_key.strip():
            default_model = "openai/gpt-oss-120b" if settings.ai_api_key.startswith("gsk_") else "gpt-4o-mini"
            return OpenAIProvider(
                api_key=settings.ai_api_key,
                model=settings.ai_model or default_model,
                base_url=settings.ai_base_url,
            )

    return NoopProvider()