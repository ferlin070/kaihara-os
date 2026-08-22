"""
Spec Agent — break PRD into detailed feature specs.
Each feature gets: API endpoints, DB schema, UI components, error cases.
"""


class SpecAgent:
    """Break PRD features into detailed implementation specs."""

    def __init__(self, model_router=None, memory=None, token_juice=None):
        self.model = model_router
        self.memory = memory
        self.token_juice = token_juice

    async def generate_specs(self, prd_text: str, parsed: dict) -> list[dict]:
        """Generate detailed specs for each feature in the PRD."""
        specs = []
        for feature in parsed.get("features", []):
            spec = await self._generate_spec(prd_text, feature)
            specs.append(spec)
        return specs

    async def _generate_spec(self, prd_text: str, feature: dict) -> dict:
        if self.model:
            spec_text = await self._generate_with_llm(prd_text, feature)
        else:
            spec_text = self._generate_fallback(feature)

        return {
            "feature_id": feature["id"],
            "feature_name": feature["name"],
            "spec": spec_text,
            "endpoints": self._extract_endpoints(spec_text),
            "tables": self._extract_tables(spec_text),
        }

    async def _generate_with_llm(self, prd_text: str, feature: dict) -> str:
        system = ("You are a technical spec writer. Generate detailed "
                  "implementation specs for a feature. Include API endpoints, "
                  "database schema, UI components, error cases.")
        prompt = f"""
PRD context:
{prd_text[:2000]}

Feature to spec: {feature['id']}: {feature['name']}

Generate a detailed feature spec including:
1. Description
2. User story
3. Acceptance criteria
4. API endpoints (method, path, request, response)
5. Database tables and columns
6. UI components needed
7. Error cases and handling
8. Dependencies on other features
"""
        return await self.model.complete(
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )

    def _generate_fallback(self, feature: dict) -> str:
        return f"""# Feature Spec — {feature['id']}: {feature['name']}

## Description
{feature['name']} implementation.

## User Story
As a user, I want to {feature['name'].lower()}.

## API
- Method: GET/POST
- Path: /api/{feature['id'].lower()}
- Auth: required (JWT)

## Database
- Table: {feature['id'].lower()}_table (id, data, created_at)

## UI Components
- Form component
- List component
"""

    def _extract_endpoints(self, spec_text: str) -> list[str]:
        import re
        endpoints = []
        for match in re.finditer(r"(GET|POST|PUT|DELETE)\s+(/\S+)", spec_text):
            endpoints.append(f"{match.group(1)} {match.group(2)}")
        return endpoints

    def _extract_tables(self, spec_text: str) -> list[str]:
        import re
        tables = []
        for match in re.finditer(r"Table:\s*(\w+)", spec_text):
            tables.append(match.group(1))
        return tables
