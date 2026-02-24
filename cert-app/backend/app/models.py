"""SQLAlchemy database models."""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Date, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Qualification(Base):
    """Qualification (certification) model."""
    __tablename__ = "qualification"
    
    qual_id = Column(Integer, primary_key=True, index=True)
    qual_name = Column(String(255), nullable=False, index=True)
    qual_type = Column(String(100), nullable=True, index=True)
    main_field = Column(String(100), nullable=True, index=True)
    ncs_large = Column(String(100), nullable=True, index=True)
    managing_body = Column(String(200), nullable=True, index=True)
    grade_code = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Exam round details from CSV
    written_cnt = Column(Integer, nullable=True, default=0)
    practical_cnt = Column(Integer, nullable=True, default=0)
    interview_cnt = Column(Integer, nullable=True, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    embedding = Column(Vector(1536))
    
    # Relationships
    stats = relationship("QualificationStats", back_populates="qualification", cascade="all, delete-orphan")
    major_mappings = relationship("MajorQualificationMap", back_populates="qualification", cascade="all, delete-orphan")
    jobs = relationship("Job", secondary="qualification_job_map", back_populates="qualifications", viewonly=True)
    
    def __repr__(self):
        return f"<Qualification(id={self.qual_id}, name='{self.qual_name}')>"


class QualificationStats(Base):
    """Qualification statistics model."""
    __tablename__ = "qualification_stats"
    
    stat_id = Column(Integer, primary_key=True, index=True)
    qual_id = Column(Integer, ForeignKey("qualification.qual_id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    exam_round = Column(Integer, nullable=False)
    candidate_cnt = Column(Integer, nullable=True)
    pass_cnt = Column(Integer, nullable=True)
    pass_rate = Column(Float, nullable=True)
    exam_structure = Column(Text, nullable=True)
    difficulty_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    qualification = relationship("Qualification", back_populates="stats")
    
    __table_args__ = (
        UniqueConstraint('qual_id', 'year', 'exam_round', name='uq_qual_year_round'),
    )
    
    def __repr__(self):
        return f"<QualificationStats(qual_id={self.qual_id}, year={self.year}, round={self.exam_round})>"


class MajorQualificationMap(Base):
    """Major to qualification mapping model."""
    __tablename__ = "major_qualification_map"
    
    map_id = Column(Integer, primary_key=True, index=True)
    major = Column(String(100), ForeignKey("major.major_name", ondelete="CASCADE"), nullable=False, index=True)
    qual_id = Column(Integer, ForeignKey("qualification.qual_id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False, default=1.0)
    weight = Column(Float, nullable=True)
    reason = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    qualification = relationship("Qualification", back_populates="major_mappings")
    major_obj = relationship("Major", back_populates="qualification_mappings")
    
    __table_args__ = (
        UniqueConstraint('major', 'qual_id', name='uq_major_qual'),
    )
    
    def __repr__(self):
        return f"<MajorQualificationMap(major='{self.major}', qual_id={self.qual_id}, score={self.score})>"


class UserFavorite(Base):
    """User favorite certifications model."""
    __tablename__ = "user_favorites"
    
    fav_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    qual_id = Column(Integer, ForeignKey("qualification.qual_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'qual_id', name='uq_user_qual_fav'),
    )
    
    # Relationships
    qualification = relationship("Qualification")
    
    
    def __repr__(self):
        return f"<UserFavorite(user_id='{self.user_id}', qual_id={self.qual_id})>"


class UserAcquiredCert(Base):
    """User acquired (earned) certification. Linked to profile via user_id (auth uid)."""
    __tablename__ = "user_acquired_certs"

    acq_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    qual_id = Column(Integer, ForeignKey("qualification.qual_id", ondelete="CASCADE"), nullable=False, index=True)
    acquired_at = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "qual_id", name="uq_user_qual_acquired"),)

    qualification = relationship("Qualification")

    def __repr__(self):
        return f"<UserAcquiredCert(user_id='{self.user_id}', qual_id={self.qual_id})>"


class Profile(Base):
    """User profile model."""
    __tablename__ = "profiles"
    
    id = Column(String(255), primary_key=True, index=True) # UUID string
    userid = Column(String(50), unique=True, index=True)
    name = Column(String(100))
    nickname = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    birth_date = Column(String(10))
    grade_year = Column(Integer)
    detail_major = Column(String(100), ForeignKey("major.major_name", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    major_obj = relationship("Major", backref="profiles")
    
    def __repr__(self):
        return f"<Profile(id='{self.id}', userid='{self.userid}')>"


class Job(Base):
    """Job information model."""
    __tablename__ = "job"
    
    job_id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(255), nullable=False, index=True)
    # Removed outlook, salary_info, description as they were empty
    work_conditions = Column(Text, nullable=True)
    
    # New fields for detailed analysis
    outlook_summary = Column(Text, nullable=True)
    entry_salary = Column(Text, nullable=True)
    
    # Radar chart scores
    reward = Column(Float, nullable=True)
    stability = Column(Float, nullable=True)
    development = Column(Float, nullable=True)
    condition = Column(Float, nullable=True)
    professionalism = Column(Float, nullable=True)
    equality = Column(Float, nullable=True)
    
    similar_jobs = Column(Text, nullable=True)
    aptitude = Column(Text, nullable=True)
    employment_path = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    qualifications = relationship("Qualification", secondary="qualification_job_map", back_populates="jobs", viewonly=True)

    def __repr__(self):
        return f"<Job(id={self.job_id}, name='{self.job_name}')>"


class Major(Base):
    """Major/Department information model."""
    __tablename__ = "major"
    
    major_id = Column(Integer, primary_key=True, index=True)
    major_name = Column(String(100), unique=True, nullable=False, index=True)
    major_category = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    qualification_mappings = relationship("MajorQualificationMap", back_populates="major_obj")
    
    def __repr__(self):
        return f"<Major(id={self.major_id}, name='{self.major_name}')>"


class QualificationJobMap(Base):
    """Mapping between Qualifications and Jobs."""
    __tablename__ = "qualification_job_map"
    
    map_id = Column(Integer, primary_key=True, index=True)
    qual_id = Column(Integer, ForeignKey("qualification.qual_id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("job.job_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationships
    qualification = relationship("Qualification")
    job = relationship("Job")
    
    __table_args__ = (
        UniqueConstraint('qual_id', 'job_id', name='uq_qual_job'),
    )
