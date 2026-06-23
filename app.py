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


class ReservationRecord(ReservationResponse):
    team: str
    duration_hours: int
    jenkins_build_id: str


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
    machine_id: str | None = None
    image: str | None = None
    status: DeploymentStatus


class DeploymentRecord(DeploymentStatusResponse):
    poll_count: int = 0


class ReleaseResponse(BaseModel):
    provider: str
    reservation_id: str
    machine_id: str | None = None
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
    Machine(
        provider=PROVIDER,
        machine_id="adl-077",
        platform="ADL",
        os="ubuntu-22.04",
        status="available",
        team_tags=["oneapi", "compiler-validation"],
        supported_images=["compiler-validation-ubuntu22", "oneapi-runtime-ubuntu22"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="adl-088",
        platform="ADL",
        os="windows-10",
        status="available",
        team_tags=["oneapi", "legacy-validation"],
        supported_images=["compiler-validation-win10"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="mtl-121",
        platform="MTL",
        os="windows-11",
        status="available",
        team_tags=["oneapi", "compiler-validation"],
        supported_images=["compiler-validation-win11", "driver-validation-win11"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="dg2-033",
        platform="DG2",
        os="windows-11",
        status="available",
        team_tags=["oneapi", "gpu-validation"],
        supported_images=["gpu-runtime-validation-win11", "compiler-validation-win11"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="dg2-041",
        platform="DG2",
        os="ubuntu-24.04",
        status="available",
        team_tags=["oneapi", "gpu-validation"],
        supported_images=["gpu-runtime-validation-ubuntu24"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="rpl-205",
        platform="RPL",
        os="windows-11",
        status="available",
        team_tags=["oneapi", "ide-validation"],
        supported_images=["ide-extension-validation-win11", "compiler-validation-win11"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="lnl-009",
        platform="LNL",
        os="ubuntu-24.04",
        status="maintenance",
        team_tags=["oneapi", "pre-silicon-validation"],
        supported_images=["compiler-validation-ubuntu24"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="winclient-027",
        platform="windows-client",
        os="windows-11",
        status="available",
        team_tags=["oneapi", "ide-validation", "installer-validation"],
        supported_images=["ide-extension-validation-win11", "installer-validation-win11"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="adl-099",
        platform="ADL",
        os="windows-11",
        status="available",
        team_tags=["another-team"],
        supported_images=["compiler-validation-win11"],
    ),
    Machine(
        provider=PROVIDER,
        machine_id="mtl-144",
        platform="MTL",
        os="windows-11",
        status="available",
        team_tags=["oneapi", "compiler-validation"],
        supported_images=["compiler-validation-win11"],
        dirty=True,
    ),
]

reservations: dict[str, ReservationRecord] = {}
deployments: dict[str, DeploymentRecord] = {}

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


@app.get("/machines/{machine_id}", response_model=Machine)
def get_machine(machine_id: str) -> Machine:
    return find_machine(machine_id)


@app.get("/reservations", response_model=list[ReservationRecord])
def list_reservations() -> list[ReservationRecord]:
    return list(reservations.values())


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
    record = ReservationRecord(
        provider=PROVIDER,
        reservation_id=reservation_id,
        machine_id=machine.machine_id,
        team=request.team,
        duration_hours=request.duration_hours,
        jenkins_build_id=request.jenkins_build_id,
        status="reserved",
    )
    reservations[reservation_id] = record

    return record


@app.get("/reservations/{reservation_id}", response_model=ReservationRecord)
def get_reservation(reservation_id: str) -> ReservationRecord:
    reservation = reservations.get(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail=f"Reservation not found: {reservation_id}")
    return reservation


@app.post("/machines/{machine_id}/deploy-image", response_model=ImageDeployResponse)
def deploy_image(machine_id: str, request: ImageDeployRequest) -> ImageDeployResponse:
    machine = find_machine(machine_id)

    if machine.status != "reserved":
        raise HTTPException(
            status_code=409,
            detail=f"Machine must be reserved before image deployment: {machine.machine_id}",
        )
    if request.image not in machine.supported_images:
        raise HTTPException(
            status_code=400,
            detail=f"Image {request.image} is not supported by {machine.machine_id}",
        )

    deployment_id = f"{PROVIDER}-deploy-{uuid4()}"
    deployment = DeploymentRecord(
        provider=PROVIDER,
        deployment_id=deployment_id,
        machine_id=machine.machine_id,
        image=request.image,
        status=DeploymentStatus.IN_PROGRESS,
        poll_count=0,
    )
    deployments[deployment_id] = deployment

    return ImageDeployResponse(
        provider=PROVIDER,
        deployment_id=deployment_id,
        machine_id=machine.machine_id,
        image=request.image,
        status=DeploymentStatus.IN_PROGRESS,
    )


@app.get("/deployments", response_model=list[DeploymentStatusResponse])
def list_deployments() -> list[DeploymentStatusResponse]:
    return list(deployments.values())


@app.get("/deployments/{deployment_id}/status", response_model=DeploymentStatusResponse)
def get_deployment_status(deployment_id: str) -> DeploymentStatusResponse:
    deployment = deployments.get(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deployment_id}")

    status = DeploymentStatus.READY if deployment.poll_count >= 1 else DeploymentStatus.IN_PROGRESS
    deployments[deployment_id] = deployment.model_copy(
        update={
            "status": status,
            "poll_count": deployment.poll_count + 1,
        }
    )
    return deployments[deployment_id]


@app.post("/reservations/{reservation_id}/release", response_model=ReleaseResponse)
def release_reservation(reservation_id: str) -> ReleaseResponse:
    reservation = reservations.pop(reservation_id, None)
    if reservation is None:
        raise HTTPException(status_code=404, detail=f"Reservation not found: {reservation_id}")

    set_machine_status(reservation.machine_id, "available")

    return ReleaseResponse(
        provider=PROVIDER,
        reservation_id=reservation_id,
        machine_id=reservation.machine_id,
        status="released",
    )


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
