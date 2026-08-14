"""Repair application DTOs — pure Python, no ORM, no Django objects."""

from apps.repair.application.dto.repair_dto import (
    AddRepairActivityDTO,
    AddRepairPartDTO,
    AssignRepairOrderDTO,
    CloseRepairOrderDTO,
    CompleteRepairOrderDTO,
    CreateRepairOrderDTO,
    DeleteRepairActivityDTO,
    RepairActivityResponseDTO,
    RepairOrderResponseDTO,
    RepairPartResponseDTO,
    SyncRepairToSAPDTO,
    UpdateRepairActivityDTO,
)

__all__ = [
    "CreateRepairOrderDTO",
    "AssignRepairOrderDTO",
    "CloseRepairOrderDTO",
    "CompleteRepairOrderDTO",
    "AddRepairActivityDTO",
    "AddRepairPartDTO",
    "DeleteRepairActivityDTO",
    "UpdateRepairActivityDTO",
    "SyncRepairToSAPDTO",
    "RepairOrderResponseDTO",
    "RepairActivityResponseDTO",
    "RepairPartResponseDTO",
]
