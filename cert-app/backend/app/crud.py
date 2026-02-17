
"""CRUD operations for database models."""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, or_, and_

from app.models import Qualification, QualificationStats, MajorQualificationMap, UserFavorite, Job, Major
from app.schemas import (
    QualificationCreate, QualificationUpdate,
    QualificationStatsCreate, QualificationStatsUpdate,
    MajorQualificationMapCreate
)


# ============== Qualification CRUD ==============

class QualificationCRUD:
    """CRUD operations for Qualification."""
    
    @staticmethod
    def get_by_id(db: Session, qual_id: int) -> Optional[Qualification]:
        """Get qualification by ID."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return data_loader.get_qualification_by_id(qual_id)
            
        return db.query(Qualification).filter(Qualification.qual_id == qual_id).first()
    
    @staticmethod
    def get_with_stats(db: Session, qual_id: int) -> Optional[Qualification]:
        """Get qualification with stats."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return data_loader.get_qual_with_stats(qual_id)
            
        return db.query(Qualification).options(
            joinedload(Qualification.stats)
        ).filter(Qualification.qual_id == qual_id).first()
    
    @staticmethod
    def get_list(
        db: Session,
        q: Optional[str] = None,
        main_field: Optional[str] = None,
        ncs_large: Optional[str] = None,
        qual_type: Optional[str] = None,
        managing_body: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort: str = "name",
        sort_desc: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Qualification], int]:
        """Get paginated list of qualifications with filters."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return data_loader.get_qualifications_list(q, main_field, ncs_large, qual_type, managing_body, is_active, sort, page, page_size)
        
        query = db.query(Qualification)
        
        # Apply filters
        if q:
            query = query.filter(
                or_(
                    Qualification.qual_name.ilike(f"%{q}%"),
                    Qualification.managing_body.ilike(f"%{q}%")
                )
            )
        
        if main_field:
            query = query.filter(Qualification.main_field == main_field)
        
        if ncs_large:
            query = query.filter(Qualification.ncs_large == ncs_large)
        
        if qual_type:
            query = query.filter(Qualification.qual_type == qual_type)
        
        if managing_body:
            query = query.filter(Qualification.managing_body == managing_body)
        
        if is_active is not None:
            query = query.filter(Qualification.is_active == is_active)
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        if sort == "name":
            query = query.order_by(desc(Qualification.qual_name) if sort_desc else asc(Qualification.qual_name))
        elif sort == "recent":
            query = query.order_by(desc(Qualification.created_at) if sort_desc else asc(Qualification.created_at))
        elif sort in ["pass_rate", "difficulty"]:
            # These require joining with stats
            query = query.outerjoin(QualificationStats).group_by(Qualification.qual_id)
            if sort == "pass_rate":
                query = query.order_by(
                    desc(func.avg(QualificationStats.pass_rate)) if sort_desc else asc(func.avg(QualificationStats.pass_rate))
                )
            else:
                query = query.order_by(
                    desc(func.avg(QualificationStats.difficulty_score)) if sort_desc else asc(func.avg(QualificationStats.difficulty_score))
                )
        
        # Apply pagination
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        
        return items, total
    
    @staticmethod
    def get_filter_options(db: Session) -> dict:
        """Get available filter options."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return data_loader.get_filter_options()
            
        return {
            "main_fields": [r[0] for r in db.query(Qualification.main_field).distinct().all() if r[0]],
            "ncs_large": [r[0] for r in db.query(Qualification.ncs_large).distinct().all() if r[0]],
            "qual_types": [r[0] for r in db.query(Qualification.qual_type).distinct().all() if r[0]],
            "managing_bodies": [r[0] for r in db.query(Qualification.managing_body).distinct().all() if r[0]],
        }
    
    @staticmethod
    def create(db: Session, obj_in: QualificationCreate) -> Qualification:
        """Create new qualification."""
        db_obj = Qualification(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def update(
        db: Session, 
        db_obj: Qualification, 
        obj_in: QualificationUpdate
    ) -> Qualification:
        """Update qualification."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def delete(db: Session, db_obj: Qualification) -> None:
        """Delete qualification."""
        db.delete(db_obj)
        db.commit()


# ============== QualificationStats CRUD ==============

class QualificationStatsCRUD:
    """CRUD operations for QualificationStats."""
    
    @staticmethod
    def get_by_id(db: Session, stat_id: int) -> Optional[QualificationStats]:
        """Get stats by ID."""
        # Stats usually fetched via qual_id in data loader
        return db.query(QualificationStats).filter(
            QualificationStats.stat_id == stat_id
        ).first()
    
    @staticmethod
    def get_by_qual_id(
        db: Session, 
        qual_id: int,
        year: Optional[int] = None
    ) -> List[QualificationStats]:
        """Get stats by qualification ID."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     stats = data_loader.get_stats_by_qual_id(qual_id)
        #     if year:
        #         stats = [s for s in stats if s.year == year]
        #     # sort desc
        #     stats.sort(key=lambda x: (x.year, x.exam_round), reverse=True)
        #     return stats
            
        query = db.query(QualificationStats).filter(
            QualificationStats.qual_id == qual_id
        )
        if year:
            query = query.filter(QualificationStats.year == year)
        return query.order_by(desc(QualificationStats.year), desc(QualificationStats.exam_round)).all()
    
    @staticmethod
    def get_latest_by_qual_id(
        db: Session, 
        qual_id: int
    ) -> Optional[QualificationStats]:
        """Get latest stats for a qualification."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     stats = data_loader.get_stats_by_qual_id(qual_id)
        #     if not stats: return None
        #     return max(stats, key=lambda s: (s.year, s.exam_round))

        return db.query(QualificationStats).filter(
            QualificationStats.qual_id == qual_id
        ).order_by(
            desc(QualificationStats.year), 
            desc(QualificationStats.exam_round)
        ).first()
    
    @staticmethod
    def create(db: Session, obj_in: QualificationStatsCreate) -> QualificationStats:
        """Create new stats entry."""
        db_obj = QualificationStats(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def upsert(
        db: Session, 
        qual_id: int,
        year: int,
        exam_round: int,
        **kwargs
    ) -> QualificationStats:
        """Upsert stats entry."""
        db_obj = db.query(QualificationStats).filter(
            and_(
                QualificationStats.qual_id == qual_id,
                QualificationStats.year == year,
                QualificationStats.exam_round == exam_round
            )
        ).first()
        
        if db_obj:
            for key, value in kwargs.items():
                setattr(db_obj, key, value)
        else:
            db_obj = QualificationStats(
                qual_id=qual_id,
                year=year,
                exam_round=exam_round,
                **kwargs
            )
            db.add(db_obj)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def update(
        db: Session,
        db_obj: QualificationStats,
        obj_in: QualificationStatsUpdate
    ) -> QualificationStats:
        """Update stats entry."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def delete(db: Session, db_obj: QualificationStats) -> None:
        """Delete stats entry."""
        db.delete(db_obj)
        db.commit()


# ============== MajorQualificationMap CRUD ==============

class MajorQualificationMapCRUD:
    """CRUD operations for MajorQualificationMap."""
    
    @staticmethod
    def get_by_major(
        db: Session, 
        major: str,
        limit: int = 50
    ) -> List[MajorQualificationMap]:
        """Get qualification mappings for a major."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return data_loader.get_recommendations_by_major(major, limit)

        return db.query(MajorQualificationMap).options(
            joinedload(MajorQualificationMap.qualification)
        ).filter(
            MajorQualificationMap.major == major
        ).order_by(
            desc(MajorQualificationMap.score)
        ).limit(limit).all()
    
    @staticmethod
    def get_by_major_with_stats(
        db: Session,
        major: str,
        limit: int = 50
    ) -> List[MajorQualificationMap]:
        """Get qualification mappings with qualification stats."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     # data_loader returns mappings with qualifications linked (and stats linked to qual)
        #     return data_loader.get_recommendations_by_major(major, limit)
            
        return db.query(MajorQualificationMap).options(
            joinedload(MajorQualificationMap.qualification).joinedload(Qualification.stats)
        ).filter(
            MajorQualificationMap.major == major
        ).order_by(
            desc(MajorQualificationMap.score)
        ).limit(limit).all()
    
    @staticmethod
    def get_majors_list(db: Session) -> List[str]:
        """Get list of all majors."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     return list(data_loader.major_mappings.keys())

        return [r[0] for r in db.query(MajorQualificationMap.major).distinct().all()]
    
    @staticmethod
    def create(db: Session, obj_in: MajorQualificationMapCreate) -> MajorQualificationMap:
        """Create new mapping."""
        db_obj = MajorQualificationMap(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def upsert(
        db: Session,
        major: str,
        qual_id: int,
        score: float = 1.0,
        weight: Optional[float] = None,
        reason: Optional[str] = None
    ) -> MajorQualificationMap:
        """Upsert mapping."""
        db_obj = db.query(MajorQualificationMap).filter(
            and_(
                MajorQualificationMap.major == major,
                MajorQualificationMap.qual_id == qual_id
            )
        ).first()
        
        if db_obj:
            db_obj.score = score
            if weight is not None:
                db_obj.weight = weight
            if reason is not None:
                db_obj.reason = reason
        else:
            db_obj = MajorQualificationMap(
                major=major,
                qual_id=qual_id,
                score=score,
                weight=weight,
                reason=reason
            )
            db.add(db_obj)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj


# ============== UserFavorite CRUD ==============

class UserFavoriteCRUD:
    """CRUD operations for UserFavorite."""
    
    @staticmethod
    def get_by_user(
        db: Session, 
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[UserFavorite], int]:
        """Get user's favorites."""
        query = db.query(UserFavorite).filter(UserFavorite.user_id == user_id)
        total = query.count()
        
        offset = (page - 1) * page_size
        items = query.options(
            joinedload(UserFavorite.qualification)
        ).order_by(
            desc(UserFavorite.created_at)
        ).offset(offset).limit(page_size).all()
        
        return items, total
    
    @staticmethod
    def get_by_user_and_qual(
        db: Session,
        user_id: str,
        qual_id: int
    ) -> Optional[UserFavorite]:
        """Get specific favorite."""
        return db.query(UserFavorite).filter(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.qual_id == qual_id
            )
        ).first()
    
    @staticmethod
    def is_favorite(db: Session, user_id: str, qual_id: int) -> bool:
        """Check if qualification is in user's favorites."""
        return db.query(UserFavorite).filter(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.qual_id == qual_id
            )
        ).first() is not None
    
    @staticmethod
    def add_favorite(db: Session, user_id: str, qual_id: int) -> UserFavorite:
        """Add to favorites."""
        existing = UserFavoriteCRUD.get_by_user_and_qual(db, user_id, qual_id)
        if existing:
            return existing
        
        db_obj = UserFavorite(user_id=user_id, qual_id=qual_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def remove_favorite(db: Session, user_id: str, qual_id: int) -> bool:
        """Remove from favorites."""
        db_obj = UserFavoriteCRUD.get_by_user_and_qual(db, user_id, qual_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
            return True
        return False


# ============== Aggregated Stats ==============

def get_qualification_aggregated_stats(
    db: Session,
    qual_id: int
) -> dict:
    """Get aggregated stats for a qualification."""
    # from app.services.data_loader import data_loader
    
    # if data_loader.is_ready:
    #     stats = data_loader.get_stats_by_qual_id(qual_id)
    #     latest = max(stats, key=lambda s: (s.year, s.exam_round)) if stats else None
        
    #     if not latest:
    #         return {
    #             "latest_pass_rate": None,
    #             "avg_difficulty": None,
    #             "total_candidates": None,
    #         }
        
    #     # Calculate avg difficult
    #     valid_diff = [s.difficulty_score for s in stats if s.difficulty_score is not None]
    #     avg_difficulty = sum(valid_diff)/len(valid_diff) if valid_diff else None
        
    #     # Total candidates
    #     total_candidates = sum((s.candidate_cnt or 0) for s in stats)
        
    #     return {
    #         "latest_pass_rate": latest.pass_rate,
    #         "avg_difficulty": round(avg_difficulty, 2) if avg_difficulty is not None else None,
    #         "total_candidates": total_candidates,
    #     }

    latest = QualificationStatsCRUD.get_latest_by_qual_id(db, qual_id)
    
    if not latest:
        return {
            "latest_pass_rate": None,
            "avg_difficulty": None,
            "total_candidates": None,
        }
    
    # Calculate average difficulty
    avg_difficulty = db.query(
        func.avg(QualificationStats.difficulty_score)
    ).filter(
        QualificationStats.qual_id == qual_id
    ).scalar()
    
    # Calculate total candidates
    total_candidates = db.query(
        func.sum(QualificationStats.candidate_cnt)
    ).filter(
        QualificationStats.qual_id == qual_id
    ).scalar()
    
    return {
        "latest_pass_rate": latest.pass_rate,
        "avg_difficulty": round(avg_difficulty, 2) if avg_difficulty else None,
        "total_candidates": int(total_candidates) if total_candidates else None,
    }


# ============== Job CRUD ==============

class JobCRUD:
    """CRUD operations for Job."""
    
    @staticmethod
    def get_list(
        db: Session,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Job], int]:
        """Get list of jobs."""
        # from app.services.data_loader import data_loader
        # if data_loader.is_ready:
        #     items = data_loader.get_jobs_list(q)
        #     return items, len(items)
            
        query = db.query(Job)
        if q:
            query = query.filter(
                or_(
                    Job.job_name.ilike(f"%{q}%"),
                    Job.outlook_summary.ilike(f"%{q}%")
                )
            )
        total = query.count()
        
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    @staticmethod
    def get_by_id(db: Session, job_id: int) -> Optional[Job]:
        """Get job by ID with related qualifications."""
        # Always use DB for detailed view to show enriched mappings
        return db.query(Job).options(
            joinedload(Job.qualifications)
        ).filter(Job.job_id == job_id).first()


# ============== Major CRUD ==============

class MajorCRUD:
    """CRUD operations for Major."""
    
    @staticmethod
    def get_list(
        db: Session,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Major], int]:
        """Get list of majors."""
        query = db.query(Major)
        if q:
            query = query.filter(Major.major_name.ilike(f"%{q}%"))
        
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        
        return items, total


# ============== Export CRUD instances ==============

qualification_crud = QualificationCRUD()
stats_crud = QualificationStatsCRUD()
major_map_crud = MajorQualificationMapCRUD()
favorite_crud = UserFavoriteCRUD()
job_crud = JobCRUD()
major_crud = MajorCRUD()
