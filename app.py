from __future__ import annotations

from enum import Enum
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class DeploymentStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    FAILED = "FAILED"


class Machine(BaseModel):
    provider: str
    machine_id: str
    platform: str
    os: str
    status: str
    team_tags: list[str]
    supported_images: list[str]
    dirty: bool = False


class ReservationRequest(BaseModel):
    machine_id: str = Field(..., min_length=1)
    team: str = Field(..., min_length=1)
    duration_hours: int = Field(default=4, ge=1, le=24)
    jenkins_build_id: str = Field(..., min_length=1)


class ReservationResponse(BaseModel):
    provider: str
    reservation_id: str
    machine_id: str
    status: str


class ImageDeployRequest(BaseModel):
    image: str = Field(..., min_length=1)


class ImageDeployResponse(BaseModel):
    provider: str
    deployment_id: str
    machine_id: str
    image: str
    status: DeploymentStatus


class DeploymentStatusResponse(BaseModel):
    provider: str
    deployment_id: str
    status: DeploymentStatus


class ReleaseResponse(BaseModel):
    provider: str
    reservation_id: str
    status: str


PROVIDER = "onecloud"

machines: list[Machine] = [
    Machine(
        provider=PROVIDER,
        machine_id="adl-042",
        platform="ADL",
        os="windows-11",
        status="available",
        team_tags=["oneapi", "compiler-validation"],
        supported_images=["compiler-validation-win11"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="winclient-014",
        platform="windows-client",
        os="windows-11",
        status="available",
        team_tags=["oneapi", "ide-validation"],
        supported_images=["ide-extension-validation-win11"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="mtl-117",
        platform="MTL",
        os="ubuntu-24.04",
        status="reserved",
        team_tags=["oneapi"],
        supported_images=["compiler-validation-ubuntu24"],
    ),
]

reservations: dict[str, str] = {}
deployment_polls: dict[str, int] = {}

app = FastAPI(
    title="OneCloud Machine Reservation API",
    description="Dummy OneCloud-style API for hardware inventory, reservations, and OS image deployment.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": PROVIDER}


@app.get("/machines", response_model=list[Machine])
def list_machines() -> list[Machine]:
    return machines


@app.post("/reservations", response_model=ReservationResponse)
def create_reservation(request: ReservationRequest) -> ReservationResponse:
    machine = find_machine(request.machine_id)

    if machine.status != "available":
        raise HTTPException(status_code=409, detail=f"Machine is not available: {machine.machine_id}")
    if request.team not in machine.team_tags:
        raise HTTPException(
            status_code=403,
            detail=f"Team {request.team} is not allowed to reserve {machine.machine_id}",
        )

    set_machine_status(machine.machine_id, "reserved")
    reservation_id = f"{PROVIDER}-res-{uuid4()}"
    reservations[reservation_id] = machine.machine_id

    return ReservationResponse(
        provider=PROVIDER,
        reservation_id=reservation_id,
        machine_id=machine.machine_id,
        status="reserved",
    )


@app.post("/machines/{machine_id}/deploy-image", response_model=ImageDeployResponse)
def deploy_image(machine_id: str, request: ImageDeployRequest) -> ImageDeployResponse:
    machine = find_machine(machine_id)

    if request.image not in machine.supported_images:
        raise HTTPException(
            status_code=400,
            detail=f"Image {request.image} is not supported by {machine.machine_id}",
        )

    deployment_id = f"{PROVIDER}-deploy-{uuid4()}"
    deployment_polls[deployment_id] = 0

    return ImageDeployResponse(
        provider=PROVIDER,
        deployment_id=deployment_id,
        machine_id=machine.machine_id,
        image=request.image,
        status=DeploymentStatus.IN_PROGRESS,
    )


@app.get("/deployments/{deployment_id}/status", response_model=DeploymentStatusResponse)
def get_deployment_status(deployment_id: str) -> DeploymentStatusResponse:
    poll_count = deployment_polls.get(deployment_id)
    if poll_count is None:
        return DeploymentStatusResponse(
            provider=PROVIDER,
            deployment_id=deployment_id,
            status=DeploymentStatus.FAILED,
        )

    deployment_polls[deployment_id] = poll_count + 1
    status = DeploymentStatus.READY if poll_count >= 1 else DeploymentStatus.IN_PROGRESS
    return DeploymentStatusResponse(provider=PROVIDER, deployment_id=deployment_id, status=status)


@app.post("/reservations/{reservation_id}/release", response_model=ReleaseResponse)
def release_reservation(reservation_id: str) -> ReleaseResponse:
    machine_id = reservations.pop(reservation_id, None)
    if machine_id is not None:
        set_machine_status(machine_id, "available")

    return ReleaseResponse(provider=PROVIDER, reservation_id=reservation_id, status="released")


def find_machine(machine_id: str) -> Machine:
    for machine in machines:
        if machine.machine_id == machine_id:
            return machine
    raise HTTPException(status_code=404, detail=f"Machine not found: {machine_id}")


def set_machine_status(machine_id: str, status: str) -> None:
    for index, machine in enumerate(machines):
        if machine.machine_id == machine_id:
            machines[index] = machine.model_copy(update={"status": status})
            return
