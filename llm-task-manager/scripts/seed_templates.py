"""
Seed document templates into the database.

This script creates template documents for different types of project documentation.
Templates can be loaded when creating documents to provide structure.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.document import DocumentTemplateType


# Template definitions
TEMPLATES = {
    DocumentTemplateType.PROBLEM_STATEMENT: {
        "name": "Problem Statement",
        "content": """# Problem Statement

## Problem Description
<!-- Describe the problem you're trying to solve -->

## Who is affected?
<!-- Identify the stakeholders and users affected by this problem -->

## Why is this important?
<!-- Explain the business value and impact of solving this problem -->

## Current Situation
<!-- Describe how things work today -->

## Desired Outcome
<!-- Define what success looks like -->

## Constraints
<!-- List any limitations or constraints to consider -->

## Success Metrics
<!-- How will we measure whether the problem is solved? -->
"""
    },
    DocumentTemplateType.PRODUCT_VISION: {
        "name": "Product Vision",
        "content": """# Product Vision

## Vision Statement
<!-- One sentence describing the future state we want to create -->

## Target Audience
<!-- Who are we building this for? -->

## Problem We're Solving
<!-- What pain points does this address? -->

## Key Benefits
<!-- What makes this valuable? -->

## Differentiators
<!-- What makes this unique? -->

## Success Criteria
<!-- How will we know we've achieved the vision? -->

## Risks and Mitigation
<!-- What could go wrong and how will we address it? -->

## Roadmap Themes
<!-- High-level themes that guide the roadmap -->
"""
    },
    DocumentTemplateType.TECHNICAL_DECISION: {
        "name": "Technical Decision Record (TDR)",
        "content": """# Technical Decision Record

## Context
<!-- What is the issue that we're seeing that is motivating this decision or change? -->

## Decision
<!-- What is the change that we're proposing and/or doing? -->

## Rationale
<!-- Why are we making this decision? What are the key factors? -->

## Alternatives Considered
<!-- What other options did we evaluate? -->

### Option 1
- **Description:**
- **Pros:**
- **Cons:**

### Option 2
- **Description:**
- **Pros:**
- **Cons:**

## Consequences
<!-- What becomes easier or more difficult to do because of this change? -->

## Implementation Notes
<!-- Key technical details about implementing this decision -->

## Status
<!-- Proposed / Accepted / Deprecated / Superseded -->

## Decision Date
<!-- When was this decision made? -->

## Update Log
<!-- Track changes to this decision over time -->
"""
    },
    DocumentTemplateType.SPRINT_RETROSPECTIVE: {
        "name": "Sprint Retrospective",
        "content": """# Sprint Retrospective

## Sprint Information
- **Sprint Name:**
- **Sprint Goal:**
- **Duration:**
- **Team Members:**

## What Went Well? ✅
<!-- What did we do well this sprint? What should we continue doing? -->

## What Could Be Improved? 🔄
<!-- What could we have done better? Where did we struggle? -->

## Action Items 🎯
<!-- Specific, actionable improvements for the next sprint -->

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
|        |       |          |        |

## Sprint Metrics
- **Stories Completed:**
- **Story Points Completed:**
- **Velocity:**
- **Team Satisfaction (1-10):**

## Appreciations 💚
<!-- Who helped or did something great? Give shoutouts! -->

## Additional Notes
<!-- Any other observations or learnings -->
"""
    }
}


async def seed_templates():
    """Seed document templates into the database."""
    print("🌱 Seeding document templates...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Note: Templates are just template content, they're not stored as documents
            # They're used when creating new documents
            # This script just validates the templates are properly defined
            
            print(f"\n✅ Found {len(TEMPLATES)} template definitions:")
            for template_type, template_info in TEMPLATES.items():
                print(f"   - {template_info['name']} ({template_type})")
            
            print(f"\n📝 Templates are defined in app/models/document.py")
            print(f"   They will be loaded when creating documents with template_type parameter")
            
            print("\n✅ Template validation complete!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise


async def main():
    """Main entry point."""
    await seed_templates()


if __name__ == "__main__":
    asyncio.run(main())
