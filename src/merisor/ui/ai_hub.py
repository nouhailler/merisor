"""Point d'entrée unifié des assistants IA et analyses guidées."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class AICard(QFrame):
    requested = Signal(str)

    def __init__(
        self,
        action_id: str,
        title: str,
        description: str,
        button_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setProperty("role", "sectionTitle")
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setProperty("role", "secondary")
        button = QPushButton(button_text)
        button.setAccessibleName(title)
        button.clicked.connect(lambda: self.requested.emit(action_id))
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch(1)
        layout.addWidget(button)


class AIHub(QWidget):
    """Présente les parcours IA sans court-circuiter validation et confirmation."""

    action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aiHub")
        root = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("aiHubContent")
        layout = QVBoxLayout(content)
        title = QLabel("✨ Assistant MERISOR")
        title.setProperty("role", "pageTitle")
        subtitle = QLabel(
            "Construisez, analysez et améliorez un MCD avec une validation locale "
            "et une confirmation explicite avant chaque import ou modification."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "secondary")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        security = QFrame()
        security.setProperty("role", "card")
        security_layout = QVBoxLayout(security)
        security_title = QLabel("🔒 Contrôle et confidentialité")
        security_title.setProperty("role", "sectionTitle")
        security_text = QLabel(
            "La clé OpenRouter reste hors des projets. Les réponses sont validées "
            "localement, prévisualisées et ne modifient jamais le MCD sans votre accord."
        )
        security_text.setWordWrap(True)
        security_text.setProperty("role", "secondary")
        security_layout.addWidget(security_title)
        security_layout.addWidget(security_text)
        layout.addWidget(security)

        grid = QGridLayout()
        cards = (
            (
                "conversation",
                "Concevoir en conversation",
                "Décrivez le métier, répondez aux questions et confirmez le modèle proposé.",
                "Démarrer l'assistant",
            ),
            (
                "create",
                "Créer un MCD",
                "Produisez directement un JSON MERISOR validé depuis une description.",
                "Décrire le modèle",
            ),
            (
                "repair",
                "Analyser et réparer",
                "Recevez des propositions unitaires avec aperçu, diff et sélection.",
                "Analyser le MCD",
            ),
            (
                "quality",
                "Trouver les problèmes",
                "Combinez validation déterministe, cohérence sémantique et score explicable.",
                "Voir la qualité",
            ),
            (
                "normalize",
                "Assistant de normalisation",
                "Étudiez dépendances fonctionnelles, clés candidates, 2NF et 3NF.",
                "Analyser la normalisation",
            ),
            (
                "explain",
                "Expliquer le MLD",
                "Sélectionnez une table MLD puis découvrez pourquoi elle a été produite.",
                "Ouvrir le MLD",
            ),
        )
        for index, spec in enumerate(cards):
            card = AICard(*spec)
            card.requested.connect(self.action_requested)
            grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(grid)
        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll)
