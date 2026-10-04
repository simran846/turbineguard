"""Database persistence layer using SQLAlchemy for runs, telemetry, faults, and validation results."""

import os
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

Base = declarative_base()


class SimulationRunModel(Base):
    """Stores metadata of a simulation run."""
    __tablename__ = "simulation_runs"

    id = Column(String(64), primary_key=True)
    scenario_name = Column(String(128), nullable=False)
    duration_s = Column(Float, nullable=False)
    dt = Column(Float, nullable=False)
    total_steps = Column(Integer, nullable=False)
    final_state = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    telemetry_records = relationship("TelemetryModel", back_populates="run", cascade="all, delete-orphan")
    fault_records = relationship("FaultRecordModel", back_populates="run", cascade="all, delete-orphan")
    validation_records = relationship("ValidationResultModel", back_populates="run", cascade="all, delete-orphan")


class TelemetryModel(Base):
    """Stores instantaneous time-series records."""
    __tablename__ = "telemetry_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("simulation_runs.id"), nullable=False, index=True)
    step = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)
    wind_speed_ms = Column(Float, nullable=False)
    pitch_angle_deg = Column(Float, nullable=False)
    target_pitch_deg = Column(Float, nullable=False)
    rotor_speed_rpm = Column(Float, nullable=False)
    generator_speed_rpm = Column(Float, nullable=False)
    target_torque_nm = Column(Float, nullable=False)
    electrical_power_kw = Column(Float, nullable=False)
    generator_temp_c = Column(Float, nullable=False)
    vibration_mm_s = Column(Float, nullable=False)
    operating_state = Column(String(32), nullable=False)
    brake_engaged = Column(Boolean, default=False)
    active_fault = Column(String(64), nullable=True)

    run = relationship("SimulationRunModel", back_populates="telemetry_records")


class FaultRecordModel(Base):
    """Stores injected fault events and controller responses."""
    __tablename__ = "fault_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("simulation_runs.id"), nullable=False, index=True)
    fault_id = Column(String(64), nullable=False)
    fault_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False)
    start_time_s = Column(Float, nullable=False)
    duration_s = Column(Float, nullable=False)
    detected = Column(Boolean, default=False)
    response_time_ms = Column(Float, nullable=True)
    controller_action = Column(String(64), nullable=True)
    passed_verification = Column(Boolean, default=True)

    run = relationship("SimulationRunModel", back_populates="fault_records")


class ValidationResultModel(Base):
    """Stores test validation execution outcomes."""
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("simulation_runs.id"), nullable=True, index=True)
    req_id = Column(String(32), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    status = Column(String(32), nullable=False)
    measured_value = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    tolerance = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    execution_time_ms = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("SimulationRunModel", back_populates="validation_records")


class DatabaseManager:
    """Manages database connection and persistence operations."""

    def __init__(self, db_path: str = "data/turbineguard.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def save_run(
        self,
        run_id: str,
        scenario_name: str,
        duration_s: float,
        dt: float,
        total_steps: int,
        final_state: str,
        telemetry: list[dict[str, Any]],
        faults: list[dict[str, Any]] | None = None,
        validation_items: list[dict[str, Any]] | None = None,
    ) -> None:
        """Persists a complete simulation run with telemetry, faults, and validation items."""
        session = self.get_session()
        try:
            # Check if run exists
            existing = session.query(SimulationRunModel).filter_by(id=run_id).first()
            if existing:
                session.delete(existing)
                session.flush()

            run_obj = SimulationRunModel(
                id=run_id,
                scenario_name=scenario_name,
                duration_s=duration_s,
                dt=dt,
                total_steps=total_steps,
                final_state=final_state
            )
            session.add(run_obj)

            # Bulk add telemetry
            telemetry_objs = [
                TelemetryModel(
                    run_id=run_id,
                    step=t.get("step", 0),
                    timestamp=t.get("timestamp", 0.0),
                    wind_speed_ms=t.get("wind_speed_ms", 0.0),
                    pitch_angle_deg=t.get("pitch_angle_deg", 0.0),
                    target_pitch_deg=t.get("target_pitch_deg", 0.0),
                    rotor_speed_rpm=t.get("rotor_speed_rpm", 0.0),
                    generator_speed_rpm=t.get("generator_speed_rpm", 0.0),
                    target_torque_nm=t.get("target_torque_nm", 0.0),
                    electrical_power_kw=t.get("electrical_power_kw", 0.0),
                    generator_temp_c=t.get("generator_temp_c", 0.0),
                    vibration_mm_s=t.get("vibration_mm_s", 0.0),
                    operating_state=t.get("operating_state", "NORMAL"),
                    brake_engaged=t.get("brake_engaged", False),
                    active_fault=t.get("active_fault")
                )
                for t in telemetry
            ]
            session.bulk_save_objects(telemetry_objs)

            if faults:
                fault_objs = [
                    FaultRecordModel(
                        run_id=run_id,
                        fault_id=f.get("fault_id", "F-000"),
                        fault_type=f.get("fault_type", "Unknown"),
                        severity=f.get("severity", "MEDIUM"),
                        start_time_s=f.get("start_time_s", 0.0),
                        duration_s=f.get("duration_s", 0.0),
                        detected=f.get("detected", True),
                        response_time_ms=f.get("response_time_ms", 0.0),
                        controller_action=f.get("controller_action", ""),
                        passed_verification=f.get("passed_verification", True)
                    )
                    for f in faults
                ]
                session.bulk_save_objects(fault_objs)

            if validation_items:
                val_objs = [
                    ValidationResultModel(
                        run_id=run_id,
                        req_id=v.get("req_id", "REQ-000"),
                        title=v.get("title", ""),
                        status=v.get("status", "PASSED"),
                        measured_value=v.get("measured_value", 0.0),
                        expected_value=v.get("expected_value", 0.0),
                        tolerance=v.get("tolerance", 0.0),
                        unit=v.get("unit", ""),
                        message=v.get("message", ""),
                        execution_time_ms=v.get("execution_time_ms", 0.0)
                    )
                    for v in validation_items
                ]
                session.bulk_save_objects(val_objs)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_latest_run(self) -> dict[str, Any] | None:
        """Fetches summary of latest simulation run."""
        session = self.get_session()
        try:
            run = session.query(SimulationRunModel).order_by(SimulationRunModel.created_at.desc()).first()
            if not run:
                return None
            return {
                "id": run.id,
                "scenario_name": run.scenario_name,
                "duration_s": run.duration_s,
                "total_steps": run.total_steps,
                "final_state": run.final_state,
                "created_at": run.created_at.isoformat()
            }
        finally:
            session.close()
