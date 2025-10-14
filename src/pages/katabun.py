from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Resource:
    """Structured representation of a Katabun resource."""

    title: str
    description: str
    url: str
    tags: List[str]
    featured: bool = False


class Katabun:
    """Provide curated ADHD-friendly learning resources for the Katabun hub."""

    def __init__(self) -> None:
        self._resources: List[Resource] = [
            Resource(
                title="Getting Started with ADHD-Friendly Studying",
                description=(
                    "Build a study routine with micro-goals, sensory breaks, and "
                    "accountability prompts tailored for neurodivergent learners."
                ),
                url="https://adhd.care/study-starter",
                tags=["foundations", "study-skills", "adhd"],
                featured=True,
            ),
            Resource(
                title="Focus Toolkits You Can Use Today",
                description=(
                    "Downloadable checklists, timer templates, and movement cues "
                    "designed to keep momentum without relying on willpower alone."
                ),
                url="https://adhd.care/focus-toolkits",
                tags=["toolkit", "productivity"],
                featured=True,
            ),
            Resource(
                title="Body Doubling Communities",
                description=(
                    "Find moderated online coworking rooms where facilitators help "
                    "you warm up, stay on task, and celebrate small wins in real time."
                ),
                url="https://adhd.care/body-doubling",
                tags=["community", "support"],
                featured=True,
            ),
            Resource(
                title="Executive Function Emergency Guide",
                description=(
                    "Quick reference for when overwhelm hits—grounding prompts, "
                    "transition scripts, and energy triage questions."
                ),
                url="https://adhd.care/ef-emergency",
                tags=["executive-function", "mental-health"],
            ),
            Resource(
                title="Movement Snacks for Brain Breaks",
                description=(
                    "Five-minute movement patterns that reset focus without "
                    "needing gym equipment."
                ),
                url="https://adhd.care/movement-snacks",
                tags=["movement", "self-care"],
            ),
            Resource(
                title="Sensory-Friendly Workspace Checklist",
                description=(
                    "Audit lighting, sound, and tactile inputs to build a workspace "
                    "that anchors your attention instead of scattering it."
                ),
                url="https://adhd.care/workspace-checklist",
                tags=["environment", "workspace"],
            ),
            Resource(
                title="Medication & Coaching Primer",
                description=(
                    "Explore evidence-based treatments, coaching frameworks, and "
                    "how to advocate during appointments."
                ),
                url="https://adhd.care/treatment-primer",
                tags=["health", "advocacy"],
            ),
            Resource(
                title="Parents & Partners Communication Cards",
                description=(
                    "Printable prompts to co-plan routines, household tasks, and "
                    "emotional check-ins with your support crew."
                ),
                url="https://adhd.care/communication-cards",
                tags=["relationships", "family"],
            ),
        ]

    def get_all_resources(self) -> List[Resource]:
        """Return every resource in the catalog."""

        return list(self._resources)

    def get_featured_resources(self, limit: Optional[int] = None) -> List[Resource]:
        """Return featured resources, optionally capped at ``limit`` items."""

        featured_resources = [resource for resource in self._resources if resource.featured]
        if limit is None:
            return featured_resources
        return featured_resources[:limit]

    def get_tags(self) -> List[str]:
        """Return a sorted list of unique tags across resources."""

        unique_tags = {tag for resource in self._resources for tag in resource.tags}
        return sorted(unique_tags)
