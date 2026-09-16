"""Import every model here so metadata and relationship registration are complete."""

from app.models.user import User
from app.models.incident import Incident, IncidentStatus, Severity
from app.models.evidence import Evidence
from app.models.timeline import TimelineEvent
from app.models.agent import Agent
from app.models.collection_job import CollectionJob
from app.models.custody import CustodyEvent
from app.models.evidence_annotation import EvidenceNote, EvidenceTag
from app.models.evidence_integrity import EvidenceIntegrityCheck
from app.models.case_history import CaseHistoryEvent

__all__ = ["User", "Incident", "IncidentStatus", "Severity", "Evidence", "TimelineEvent", "Agent", "CollectionJob",
           "CustodyEvent", "EvidenceNote", "EvidenceTag", "EvidenceIntegrityCheck", "CaseHistoryEvent"]

from app.models.indicator import IndicatorObservation
__all__.append("IndicatorObservation")
