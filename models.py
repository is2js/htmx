from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


############
# movie
############
class Film(Base):
    __tablename__ = "films"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    director = Column(String)


############
# EmpDept
############

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    surname = Column(String)
    job_title = Column(String)

    department_id = Column(Integer, ForeignKey("departments.id"))
    department = relationship("Department", back_populates="employees",
                              foreign_keys=[department_id],
                              uselist=False,
                              )


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

    employees = relationship("Employee", back_populates="department")
