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
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def complete(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key is missing. Please configure AI_API_KEY in settings.",
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
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key.strip()}",
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
                detail="AI provider returned an error while processing the request.",
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
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unexpected error communicating with AI provider.",
            )


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider_type = (settings.ai_provider or "none").strip().lower()

    if provider_type == "mock":
        return MockAIProvider()
    if provider_type in ("openai", "custom"):
        return OpenAIProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model or "gpt-4o-mini",
        )
    if provider_type == "none":
        if settings.ai_api_key and settings.ai_api_key.strip():
            return OpenAIProvider(
                api_key=settings.ai_api_key,
                model=settings.ai_model or "gpt-4o-mini",
            )
        return NoopProvider()

    return NoopProvider()