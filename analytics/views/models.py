"""
LastWarIntel
View Models
Version: 1.0

Generic view models for all intelligence views.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ViewSection:
    title: str
    order: int
    items: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IntelligenceView:
    title: str
    subtitle: str = ""
    sections: list[ViewSection] = field(default_factory=list)

    def add_section(self, title: str, order: int, items: list[str]):
        self.sections.append(
            ViewSection(
                title=title,
                order=order,
                items=items,
            )
        )

    @property
    def ordered_sections(self) -> list[ViewSection]:
        return sorted(self.sections, key=lambda section: section.order)