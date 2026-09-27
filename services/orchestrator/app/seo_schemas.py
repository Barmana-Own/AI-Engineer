"""API contracts for the SEO capability."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SeoSiteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    base_url: str | None = Field(default=None, max_length=500)
    source_mode: Literal["public_url_only", "source_code_only", "public_url_and_source", "wordpress_api"]
    workspace: str | None = Field(default=None, max_length=500)
    language: str | None = Field(default=None, max_length=20)
    region: str | None = Field(default=None, max_length=50)
    max_pages: int = Field(default=50, ge=1, le=500)
    max_depth: int = Field(default=3, ge=0, le=12)
    allow_local: bool = False


class SeoSiteResponse(BaseModel):
    id: str
    project_id: str
    name: str
    base_url: str | None
    platform: str
    source_mode: str
    workspace: str | None
    language: str | None
    region: str | None
    status: str
    crawl_policy: dict[str, Any]
    rendering_mode: str
    created_at: str
    updated_at: str


class SeoAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline: bool = False
    html: str | None = Field(default=None, max_length=2_000_000)


class SeoKeywordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keywords: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(min_length=1, max_length=10_000)
    pages: list[Annotated[str, Field(min_length=1, max_length=1_000)]] = Field(default_factory=list, max_length=2_000)
    audience: str = Field(default="unknown", max_length=500)
    conversion_objective: str = Field(default="unknown", max_length=500)


class SeoDelegateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_role: str | None = Field(default=None, max_length=80)
    mode: Literal["interactive", "autonomous"] = "interactive"


class SeoVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    evidence: list[Annotated[str, Field(min_length=1, max_length=5_000)]] = Field(default_factory=list, max_length=20)
