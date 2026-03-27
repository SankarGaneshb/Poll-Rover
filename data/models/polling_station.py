"""
Poll-Rover Data Schema
Pydantic models for polling station data — the source-of-truth schema
that all agents read from and write to.

Aligned with ooru.space YAML structure (data/entries.yml pattern).
"""

from datetime import date, time
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# --- Enums for constrained fields ---

class RampStatus(str, Enum):
    """Wheelchair ramp / accessible parking availability."""
    YES = "yes"
    NO = "no"
    PARTIAL = "partial"


class AssistanceType(str, Enum):
    """Types of assistance services available at a station."""
    LIP_READER = "lip_reader"
    ATTENDANT = "attendant"
    SIGN_LANGUAGE = "sign_language"
    BRAILLE_ASSISTANT = "braille_assistant"
    VOLUNTEER = "volunteer"


class VerifiedByType(str, Enum):
    """Who verified the station data."""
    ECI = "ECI"
    COMMUNITY = "community"
    NGO = "NGO"
    UNVERIFIED = "unverified"


class CrowdingLevel(str, Enum):
    """Crowding difficulty level for elderly/disabled."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class DataSourceType(str, Enum):
    """Origin of the polling station data."""
    ECI_OFFICIAL = "ECI_official"
    STATE_CEO = "state_CEO"
    COMMUNITY = "community"
    NGO_REPORT = "NGO_report"
    OPENSTREETMAP = "OpenStreetMap"
    MIXED = "mixed"


# --- Sub-models ---

class AccessibilityInfo(BaseModel):
    """Standardized accessibility features per station (PRD Feature F2)."""
    wheelchair_ramp: RampStatus = RampStatus.NO
    accessible_parking: RampStatus = RampStatus.NO
    audio_booth: bool = False
    braille_materials: bool = False
    assistance_services: List[AssistanceType] = Field(default_factory=list)
    accessibility_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    crowding_difficulty: CrowdingLevel = CrowdingLevel.MODERATE
    last_verified: Optional[date] = None
    verified_by: VerifiedByType = VerifiedByType.UNVERIFIED
    notes: Optional[str] = None


class ElectionDetails(BaseModel):
    """Election-specific information for a station."""
    voting_date: Optional[date] = None
    voting_phase: Optional[int] = Field(default=None, ge=1, le=10)
    start_time: Optional[str] = None  # "07:00" format
    end_time: Optional[str] = None    # "18:00" format
    number_of_booths: Optional[int] = Field(default=None, ge=1)
    estimated_voters: Optional[int] = Field(default=None, ge=0)


class ContactInfo(BaseModel):
    """Contact and operations information."""
    election_officer: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    presiding_officer: Optional[str] = None


class CommunityData(BaseModel):
    """Community-contributed information (crowdsourced)."""
    wait_time_estimate: Optional[str] = None  # e.g., "15 mins"
    crowd_level_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    accessibility_notes: Optional[str] = None
    last_updated: Optional[date] = None
    updates_count: int = Field(default=0, ge=0)
    active: bool = True


class StationMetadata(BaseModel):
    """Data quality and provenance metadata."""
    data_source: DataSourceType = DataSourceType.COMMUNITY
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    last_audit: Optional[date] = None
    needs_update: bool = False
    notes: Optional[str] = None


# --- Main Model ---

class PollingStation(BaseModel):
    """Complete polling station entry — maps 1:1 to YAML structure.

    This is the canonical schema that all agents operate on.
    Each entry in data/polling_stations.yml conforms to this model.

    Station ID format: {STATE_CODE}_{DISTRICT_CODE}_{PSxxxxx}
    Example: TN_CHN_PS00001
    """

    # --- Core Identity ---
    station_id: str = Field(
        ...,
        pattern=r"^[A-Z]{2}_[A-Z]{3}_PS\d{5}$",
        description="Unique ID: STATE_DIST_PSxxxxx"
    )
    state: str
    state_code: str = Field(..., pattern=r"^[A-Z]{2}$")
    district: str
    district_code: str = Field(..., pattern=r"^[A-Z]{3}$")
    name: str = Field(..., min_length=3)
    address: str = Field(..., min_length=5)
    landmark: Optional[str] = None
    pin_code: Optional[str] = Field(default=None, pattern=r"^\d{6}$")

    # --- Coordinates ---
    latitude: float = Field(..., ge=6.0, le=38.0)   # India bounds
    longitude: float = Field(..., ge=68.0, le=98.0)  # India bounds

    # --- Electoral Boundaries ---
    assembly_constituency: str
    parliamentary_constituency: str
    ward: Optional[str] = None

    # --- Nested Data Groups ---
    accessibility: AccessibilityInfo = Field(default_factory=AccessibilityInfo)
    election_details: ElectionDetails = Field(default_factory=ElectionDetails)
    contact: ContactInfo = Field(default_factory=ContactInfo)
    community_data: CommunityData = Field(default_factory=CommunityData)
    metadata: StationMetadata = Field(default_factory=StationMetadata)

    def to_yaml_dict(self) -> dict:
        """Convert to YAML-serializable dictionary.

        Handles enum → string conversion and date → ISO string conversion.
        """
        data = self.model_dump(mode="json", exclude_none=True)
        return data

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "PollingStation":
        """Create a PollingStation from a YAML-parsed dictionary."""
        return cls.model_validate(data)

    @property
    def accessibility_score_label(self) -> str:
        """Human-readable accessibility label."""
        rating = self.accessibility.accessibility_rating
        if rating >= 4.0:
            return "Highly Accessible"
        elif rating >= 2.5:
            return "Moderately Accessible"
        elif rating > 0:
            return "Limited Accessibility"
        return "Not Assessed"

    @property
    def confidence_label(self) -> str:
        """Human-readable confidence label."""
        score = self.metadata.confidence_score
        if score >= 0.8:
            return "High Confidence"
        elif score >= 0.5:
            return "Moderate Confidence"
        return "Low Confidence"
