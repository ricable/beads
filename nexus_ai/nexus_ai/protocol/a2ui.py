"""
NexusAI A2UI (Agent-to-User Interface) Protocol

Implements declarative JSON-based UI generation for agents.
Agents emit UI layouts, clients render secure components.

Security Model:
- Strict whitelist of allowed components
- No executable code in UI definitions
- Sandboxed rendering on client side
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ComponentType(str, Enum):
    """Supported UI component types"""
    CARD = "Card"
    TABLE = "Table"
    FORM = "Form"
    CHART = "Chart"
    CODE = "Code"
    TEXT = "Text"
    IMAGE = "Image"
    LIST = "List"
    PROGRESS = "Progress"
    ALERT = "Alert"
    TABS = "Tabs"
    ACCORDION = "Accordion"


class UIComponent(BaseModel, ABC):
    """Base class for UI components"""
    component: ComponentType
    id: str | None = None
    className: str | None = None
    style: dict[str, Any] | None = None

    @abstractmethod
    def to_json(self) -> dict[str, Any]:
        """Convert to A2UI JSON format"""
        pass


class CardComponent(UIComponent):
    """
    Card component for displaying structured content.

    Example:
    {
        "component": "Card",
        "title": "User Profile",
        "content": "Welcome back, John!",
        "footer": "Last login: 2 hours ago"
    }
    """
    component: Literal[ComponentType.CARD] = ComponentType.CARD
    title: str
    content: str | dict[str, Any]
    subtitle: str | None = None
    footer: str | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "content": self.content,
            "footer": self.footer,
            "actions": self.actions,
            "className": self.className,
            "style": self.style,
        }


class TableColumn(BaseModel):
    """Table column definition"""
    key: str
    header: str
    sortable: bool = False
    width: str | None = None


class TableComponent(UIComponent):
    """
    Table component for displaying tabular data.

    Example:
    {
        "component": "Table",
        "columns": [
            {"key": "name", "header": "Name"},
            {"key": "status", "header": "Status"}
        ],
        "data": [
            {"name": "Task 1", "status": "Complete"},
            {"name": "Task 2", "status": "Pending"}
        ]
    }
    """
    component: Literal[ComponentType.TABLE] = ComponentType.TABLE
    columns: list[TableColumn]
    data: list[dict[str, Any]]
    title: str | None = None
    sortable: bool = True
    pagination: bool = True
    pageSize: int = 10

    def to_json(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "id": self.id,
            "title": self.title,
            "columns": [c.model_dump() for c in self.columns],
            "data": self.data,
            "sortable": self.sortable,
            "pagination": self.pagination,
            "pageSize": self.pageSize,
            "className": self.className,
            "style": self.style,
        }


class FormField(BaseModel):
    """Form field definition"""
    name: str
    label: str
    type: str = "text"  # text, number, email, select, textarea, checkbox
    required: bool = False
    placeholder: str | None = None
    options: list[dict[str, str]] | None = None  # For select fields
    defaultValue: Any = None
    validation: dict[str, Any] | None = None


class FormComponent(UIComponent):
    """
    Form component for user input.

    Example:
    {
        "component": "Form",
        "fields": [
            {"name": "email", "label": "Email", "type": "email", "required": true},
            {"name": "message", "label": "Message", "type": "textarea"}
        ],
        "submitLabel": "Send"
    }
    """
    component: Literal[ComponentType.FORM] = ComponentType.FORM
    fields: list[FormField]
    title: str | None = None
    description: str | None = None
    submitLabel: str = "Submit"
    cancelLabel: str | None = "Cancel"
    onSubmit: str | None = None  # Action identifier (not executable code)

    def to_json(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "fields": [f.model_dump() for f in self.fields],
            "submitLabel": self.submitLabel,
            "cancelLabel": self.cancelLabel,
            "onSubmit": self.onSubmit,
            "className": self.className,
            "style": self.style,
        }


class ChartComponent(UIComponent):
    """
    Chart component for data visualization.

    Example:
    {
        "component": "Chart",
        "chartType": "bar",
        "data": {
            "labels": ["Jan", "Feb", "Mar"],
            "datasets": [{"label": "Sales", "data": [10, 20, 30]}]
        }
    }
    """
    component: Literal[ComponentType.CHART] = ComponentType.CHART
    chartType: str  # line, bar, pie, doughnut, scatter, area
    data: dict[str, Any]
    title: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    width: str | None = None
    height: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "id": self.id,
            "chartType": self.chartType,
            "title": self.title,
            "data": self.data,
            "options": self.options,
            "width": self.width,
            "height": self.height,
            "className": self.className,
            "style": self.style,
        }


class CodeComponent(UIComponent):
    """
    Code component for displaying source code.

    Example:
    {
        "component": "Code",
        "language": "python",
        "code": "def hello():\n    print('Hello, World!')",
        "showLineNumbers": true
    }
    """
    component: Literal[ComponentType.CODE] = ComponentType.CODE
    code: str
    language: str = "plaintext"
    title: str | None = None
    showLineNumbers: bool = True
    highlightLines: list[int] = Field(default_factory=list)
    copyable: bool = True

    def to_json(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "id": self.id,
            "title": self.title,
            "code": self.code,
            "language": self.language,
            "showLineNumbers": self.showLineNumbers,
            "highlightLines": self.highlightLines,
            "copyable": self.copyable,
            "className": self.className,
            "style": self.style,
        }


class TextComponent(UIComponent):
    """Text/Markdown component"""
    component: Literal[ComponentType.TEXT] = ComponentType.TEXT
    content: str
    variant: str = "body"  # body, heading, caption, code

    def to_json(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "id": self.id,
            "content": self.content,
            "variant": self.variant,
            "className": self.className,
            "style": self.style,
        }


class AlertComponent(UIComponent):
    """Alert/notification component"""
    component: Literal[ComponentType.ALERT] = ComponentType.ALERT
    message: str
    severity: str = "info"  # info, success, warning, error
    title: str | None = None
    dismissible: bool = True

    def to_json(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "dismissible": self.dismissible,
            "className": self.className,
            "style": self.style,
        }


class ProgressComponent(UIComponent):
    """Progress indicator component"""
    component: Literal[ComponentType.PROGRESS] = ComponentType.PROGRESS
    value: float  # 0-100
    label: str | None = None
    variant: str = "linear"  # linear, circular

    def to_json(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "id": self.id,
            "value": self.value,
            "label": self.label,
            "variant": self.variant,
            "className": self.className,
            "style": self.style,
        }


class A2UILayout(BaseModel):
    """
    Container for multiple UI components.
    Represents a complete UI layout.
    """
    components: list[dict[str, Any]]
    layout: str = "vertical"  # vertical, horizontal, grid
    spacing: str = "medium"  # small, medium, large
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "layout": self.layout,
            "spacing": self.spacing,
            "components": self.components,
            "metadata": self.metadata,
        }


class A2UIRenderer:
    """
    Renderer for A2UI components.

    Handles:
    - Component validation against whitelist
    - JSON serialization
    - Security sanitization
    """

    # Whitelist of allowed component types
    ALLOWED_COMPONENTS = {
        "Card", "Table", "Form", "Chart", "Code",
        "Text", "Image", "List", "Progress", "Alert",
        "Tabs", "Accordion",
    }

    # Dangerous patterns to block
    BLOCKED_PATTERNS = [
        "javascript:",
        "onclick",
        "onerror",
        "onload",
        "<script",
        "eval(",
        "Function(",
    ]

    def __init__(
        self,
        allowed_components: set[str] | None = None,
    ):
        self.allowed_components = allowed_components or self.ALLOWED_COMPONENTS

    def validate_component(self, component: dict[str, Any]) -> bool:
        """
        Validate a component against security rules.

        Returns:
            True if component is safe, False otherwise
        """
        # Check component type
        comp_type = component.get("component", "")
        if comp_type not in self.allowed_components:
            return False

        # Check for blocked patterns
        component_str = str(component).lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern.lower() in component_str:
                return False

        return True

    def sanitize(self, component: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize component data.

        Removes potentially dangerous content while preserving structure.
        """
        sanitized = {}

        for key, value in component.items():
            if isinstance(value, str):
                # Remove dangerous patterns
                safe_value = value
                for pattern in self.BLOCKED_PATTERNS:
                    safe_value = safe_value.replace(pattern, "")
                sanitized[key] = safe_value
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def render(self, component: UIComponent | dict[str, Any]) -> dict[str, Any]:
        """
        Render a component to safe A2UI JSON.

        Args:
            component: UIComponent instance or raw dict

        Returns:
            Validated and sanitized JSON representation

        Raises:
            ValueError: If component fails validation
        """
        if isinstance(component, UIComponent):
            json_data = component.to_json()
        else:
            json_data = component

        if not self.validate_component(json_data):
            raise ValueError(f"Component failed validation: {json_data.get('component')}")

        return self.sanitize(json_data)

    def render_layout(
        self,
        components: list[UIComponent | dict[str, Any]],
        layout: str = "vertical",
        spacing: str = "medium",
    ) -> dict[str, Any]:
        """
        Render multiple components as a layout.

        Args:
            components: List of components
            layout: Layout direction
            spacing: Spacing between components

        Returns:
            A2UI layout JSON
        """
        rendered = []

        for component in components:
            try:
                rendered.append(self.render(component))
            except ValueError:
                # Skip invalid components
                pass

        return A2UILayout(
            components=rendered,
            layout=layout,
            spacing=spacing,
        ).to_json()

    @staticmethod
    def card(
        title: str,
        content: str,
        subtitle: str | None = None,
        footer: str | None = None,
    ) -> dict[str, Any]:
        """Quick helper to create a card"""
        return CardComponent(
            title=title,
            content=content,
            subtitle=subtitle,
            footer=footer,
        ).to_json()

    @staticmethod
    def table(
        columns: list[dict[str, str]],
        data: list[dict[str, Any]],
        title: str | None = None,
    ) -> dict[str, Any]:
        """Quick helper to create a table"""
        return TableComponent(
            columns=[TableColumn(**c) for c in columns],
            data=data,
            title=title,
        ).to_json()

    @staticmethod
    def code(
        code: str,
        language: str = "python",
        title: str | None = None,
    ) -> dict[str, Any]:
        """Quick helper to create a code block"""
        return CodeComponent(
            code=code,
            language=language,
            title=title,
        ).to_json()

    @staticmethod
    def chart(
        chart_type: str,
        labels: list[str],
        datasets: list[dict[str, Any]],
        title: str | None = None,
    ) -> dict[str, Any]:
        """Quick helper to create a chart"""
        return ChartComponent(
            chartType=chart_type,
            title=title,
            data={
                "labels": labels,
                "datasets": datasets,
            },
        ).to_json()

    @staticmethod
    def alert(
        message: str,
        severity: str = "info",
        title: str | None = None,
    ) -> dict[str, Any]:
        """Quick helper to create an alert"""
        return AlertComponent(
            message=message,
            severity=severity,
            title=title,
        ).to_json()
